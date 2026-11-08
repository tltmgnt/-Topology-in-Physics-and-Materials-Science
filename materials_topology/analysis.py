"""SSH bulk topology and bounded finite-chain numerical diagnostics."""
from dataclasses import asdict
import hashlib
import json
import math
import platform
import numpy as np
from .model import parse_model, parse_requirements

ENGINE_VERSION = '0.1.0'
ORTHOGONALITY_TOLERANCE = 1e-10
WINDING_TOLERANCE = 1e-6
WEIGHT_TOLERANCE = 1e-10


def runtime_info():
    return {'python': platform.python_version(), 'numpy': np.__version__}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def number(value):
    """Round for readable reports; all acceptance decisions use unrounded values."""
    return float(format(float(value), '.12g'))


def hamiltonian(model):
    size = 2 * model.cells
    matrix = np.zeros((size, size), dtype=float)
    for cell in range(model.cells):
        a, b = 2 * cell, 2 * cell + 1
        matrix[a, b] = matrix[b, a] = model.intracell_eV
        if cell < model.cells - 1 or model.boundary == 'periodic':
            next_a = 2 * ((cell + 1) % model.cells)
            matrix[b, next_a] = matrix[next_a, b] = model.intercell_eV
    return matrix


def bulk(model, policy):
    v, w = model.intracell_eV, model.intercell_eV
    gap = 2 * abs(abs(v) - abs(w))
    resolution = max(policy['gap_tolerance_eV'], 2 * policy['numerical_tolerance_eV'])
    winding = None if gap <= resolution else int(abs(w) > abs(v))
    samples = policy['winding_samples']
    ks = [2 * math.pi * i / samples for i in range(samples + 1)]
    bands = [{'k_over_pi': number(k / math.pi),
              'lower_eV': number(-abs(complex(v, 0) + w * complex(math.cos(k), math.sin(k)))),
              'upper_eV': number(abs(complex(v, 0) + w * complex(math.cos(k), math.sin(k))))} for k in ks]
    estimate = None
    if winding is not None:
        scale = max(abs(v), abs(w))
        points = [complex(v / scale, 0) + (w / scale) * complex(math.cos(k), math.sin(k)) for k in ks]
        phase = sum(math.atan2((a.conjugate() * b).imag, (a.conjugate() * b).real)
                    for a, b in zip(points, points[1:]))
        estimate = phase / (2 * math.pi)
    return {'gap_eV': number(gap), 'effective_resolution_eV': number(resolution),
            'classification': 'UNRESOLVED_NEAR_GAP_CLOSURE' if winding is None else 'GAPPED',
            'analytic_winding': winding, 'sampled_winding': None if estimate is None else number(estimate),
            'bands': bands}, gap, winding, estimate


def finite_chain(model, policy):
    matrix = hamiltonian(model)
    try:
        eigenvalues, vectors = np.linalg.eigh(matrix)
    except np.linalg.LinAlgError as error:
        raise ValueError('finite-chain eigensolver did not converge') from error
    if not np.isfinite(eigenvalues).all() or not np.isfinite(vectors).all():
        raise ValueError('eigensolver returned nonfinite values')
    sigma = np.array([1 if site % 2 == 0 else -1 for site in range(len(matrix))])
    chiral = sigma[:, None] * matrix + matrix * sigma[None, :]
    metrics = {'hermiticity_residual_eV': float(np.max(np.abs(matrix - matrix.T))),
               'chiral_residual_eV': float(np.max(np.abs(chiral))),
               'eigen_residual_eV': float(np.max(np.abs(matrix @ vectors - vectors * eigenvalues[None, :]))),
               'orthogonality_residual': float(np.max(np.abs(vectors.T @ vectors - np.eye(len(matrix)))))}
    expected_trace_square = 2 * (model.cells * model.intracell_eV ** 2
                               + (model.cells if model.boundary == 'periodic' else model.cells - 1) * model.intercell_eV ** 2)
    metrics['trace_square_relative_residual'] = abs(float(np.sum(eigenvalues ** 2)) - expected_trace_square) / max(1.0, expected_trace_square)
    modes, candidates, ambiguous = [], [], []
    for index, value in enumerate(eigenvalues):
        weight, classification = None, 'NOT_APPLICABLE_PERIODIC'
        if model.boundary == 'open':
            weight = float(np.sum(vectors[[0, 1, len(matrix) - 2, len(matrix) - 1], index] ** 2))
            energy_margin = policy['near_zero_window_eV'] - abs(float(value))
            weight_margin = weight - policy['minimum_boundary_weight']
            if energy_margin < -policy['numerical_tolerance_eV']:
                classification = 'OUTSIDE_NEAR_ZERO_WINDOW'
            elif weight_margin < -WEIGHT_TOLERANCE:
                classification = 'NOT_BOUNDARY_LOCALIZED'
            elif energy_margin <= policy['numerical_tolerance_eV'] or weight_margin <= WEIGHT_TOLERANCE:
                classification = 'THRESHOLD_UNRESOLVED'
                ambiguous.append(index)
            else:
                classification = 'BOUNDARY_CANDIDATE'
                candidates.append(index)
        modes.append({'index': index, 'energy_eV': number(value),
                      'boundary_weight': None if weight is None else number(weight), 'classification': classification})
    return {'sites': len(matrix), 'boundary': model.boundary, 'modes': modes,
            'finite_spectral_gap_eV': number(2 * min(abs(float(value)) for value in eigenvalues)),
            'boundary_candidate_indices': candidates, 'threshold_unresolved_indices': ambiguous,
            'numerical_checks': {key: number(value) for key, value in metrics.items()}}, metrics


def build_report(data, requirements):
    model = parse_model(data)
    policy = parse_requirements(requirements, model)
    bulk_result, gap, winding, estimate = bulk(model, policy)
    finite, metrics = finite_chain(model, policy)
    gaps = []
    if winding is None:
        gaps.append({'code': 'BULK_GAP_UNRESOLVED', 'subject': 'bulk'})
    elif policy['expected_winding'] is not None and winding != policy['expected_winding']:
        gaps.append({'code': 'WINDING_MISMATCH', 'subject': 'bulk'})
    if gap < policy['minimum_bulk_gap_eV']:
        gaps.append({'code': 'BULK_GAP_BELOW_MINIMUM', 'subject': 'bulk'})
    if estimate is not None and abs(estimate - winding) > WINDING_TOLERANCE:
        gaps.append({'code': 'WINDING_CROSSCHECK_FAILED', 'subject': 'bulk'})
    for key in ('hermiticity_residual_eV', 'chiral_residual_eV', 'eigen_residual_eV'):
        if metrics[key] > policy['numerical_tolerance_eV']:
            gaps.append({'code': 'NUMERICAL_CHECK_FAILED', 'subject': key})
    for key in ('orthogonality_residual', 'trace_square_relative_residual'):
        if metrics[key] > ORTHOGONALITY_TOLERANCE:
            gaps.append({'code': 'NUMERICAL_CHECK_FAILED', 'subject': key})
    if len(finite['boundary_candidate_indices']) < policy['minimum_boundary_candidates']:
        gaps.append({'code': 'BOUNDARY_CANDIDATES_BELOW_MINIMUM', 'subject': 'finite_chain'})
    if policy['minimum_boundary_candidates'] and finite['threshold_unresolved_indices']:
        gaps.append({'code': 'BOUNDARY_CLASSIFICATION_UNRESOLVED', 'subject': 'finite_chain'})
    reference = policy['reference_gap']
    reference_result = None
    if reference is not None:
        residual = gap - reference['value_eV']
        agreement = abs(residual) <= reference['absolute_tolerance_eV']
        reference_result = {**reference, 'residual_eV': number(residual), 'status': 'AGREES' if agreement else 'DISAGREES',
                            'source_authenticated': False, 'experimental_validation_established': False}
        if not agreement:
            gaps.append({'code': 'DECLARED_REFERENCE_DISAGREEMENT', 'subject': 'bulk_gap'})
    return {'schema_version': 1, 'engine_version': ENGINE_VERSION,
            'environment': runtime_info(),
            'model_sha256': fingerprint(data), 'requirements_sha256': fingerprint(requirements),
            'status': 'GAPS_FOUND' if gaps else 'MODEL_CHECKS_PASSED', 'normalized_model': asdict(model),
            'requirements': policy, 'bulk': bulk_result, 'finite_chain': finite, 'reference_check': reference_result,
            'summary': {'cells': model.cells, 'sites': 2 * model.cells, 'bulk_winding': winding,
                        'bulk_gap_eV': number(gap), 'boundary_candidates': len(finite['boundary_candidate_indices']),
                        'gap_count': len(gaps)},
            'convention': 'q(k)=v+w*exp(i*k); H(k)=[[0,conj(q)],[q,0]]; k increases from 0 to 2*pi; fixed A-B unit cell',
            'assumptions': ['Real nearest-neighbor hoppings, zero onsite energies, spinless noninteracting SSH model',
                            'Bulk invariant describes an infinite periodic chain under the recorded unit-cell convention',
                            'Open-chain boundary weight sums the first and last complete two-site cells'],
            'gaps': gaps, 'execution_authorized': False, 'experimental_validation_established': False,
            'limitations': ['Model calculations and declared references are not experimental material validation',
                            'Boundary candidates depend on finite size and thresholds, and are not proof of protected edge states',
                            'Degenerate eigenspaces can have basis-dependent localization weights',
                            'No DFT, disorder, interactions, finite temperature, Chern/Z2 invariants or real-device predictions',
                            'Acceptance uses unrounded numbers; reports use 12 significant digits',
                            'Exact replay requires compatible recorded numerical software and backend behavior']}
