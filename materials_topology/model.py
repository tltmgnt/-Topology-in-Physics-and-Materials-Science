"""Strict unit-aware contracts for the real, spinless, nearest-neighbor SSH model."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Model:
    label: str
    cells: int
    boundary: str
    intracell_eV: float
    intercell_eV: float


def fields(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError('exact contract fields required')


def name(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 160:
        raise ValueError('trimmed text of 1 to 160 characters required')
    return value


def integer(value, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError('integer outside permitted range')
    return value


def finite(value, low, high):
    if type(value) not in (int, float):
        raise ValueError('finite numeric value required')
    try:
        valid = math.isfinite(value) and low <= value <= high
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError('number outside permitted range')
    return float(value)


def energy(value, signed=False, positive=False):
    fields(value, {'value', 'unit'})
    if value['unit'] not in ('eV', 'meV'):
        raise ValueError('only explicit eV and meV energy units supported')
    number = finite(value['value'], -1e9 if signed else 0, 1e9)
    normalized = number * (0.001 if value['unit'] == 'meV' else 1.0)
    if abs(normalized) > 1e6 or (positive and normalized < 1e-12):
        raise ValueError('normalized energy outside permitted range')
    return normalized


def parse_model(data):
    fields(data, {'schema_version', 'model', 'label', 'cells', 'boundary', 'intracell', 'intercell'})
    integer(data['schema_version'], 1, 1)
    if data['model'] != 'ssh' or data['boundary'] not in ('open', 'periodic'):
        raise ValueError('SSH model and open/periodic boundary required')
    model = Model(name(data['label']), integer(data['cells'], 3, 32), data['boundary'],
                  energy(data['intracell'], signed=True), energy(data['intercell'], signed=True))
    if max(abs(model.intracell_eV), abs(model.intercell_eV)) > 1000:
        raise ValueError('hopping magnitude exceeds 1000 eV computational bound')
    return model


def parse_requirements(data, model):
    fields(data, {'schema_version', 'expected_winding', 'minimum_bulk_gap', 'gap_tolerance', 'numerical_tolerance',
                  'near_zero_window', 'minimum_boundary_weight', 'minimum_boundary_candidates', 'winding_samples', 'reference_gap'})
    integer(data['schema_version'], 1, 1)
    expected = data['expected_winding']
    if expected is not None:
        integer(expected, 0, 1)
    minimum = integer(data['minimum_boundary_candidates'], 0, 2 * model.cells)
    if model.boundary == 'periodic' and minimum:
        raise ValueError('periodic chains have no physical boundary candidates; require zero')
    samples = integer(data['winding_samples'], 64, 4096)
    if samples % 2:
        raise ValueError('winding sample count must be even')
    reference = data['reference_gap']
    if reference is not None:
        fields(reference, {'value', 'absolute_tolerance', 'source', 'kind'})
        if reference['kind'] not in ('synthetic', 'declared_measurement'):
            raise ValueError('unsupported reference kind')
        reference = {'value_eV': energy(reference['value']), 'absolute_tolerance_eV': energy(reference['absolute_tolerance']),
                     'source': name(reference['source']), 'kind': reference['kind']}
    return {'schema_version': 1, 'expected_winding': expected,
            'minimum_bulk_gap_eV': energy(data['minimum_bulk_gap']),
            'gap_tolerance_eV': energy(data['gap_tolerance'], positive=True),
            'numerical_tolerance_eV': energy(data['numerical_tolerance'], positive=True),
            'near_zero_window_eV': energy(data['near_zero_window'], positive=True),
            'minimum_boundary_weight': finite(data['minimum_boundary_weight'], 0, 1),
            'minimum_boundary_candidates': minimum, 'winding_samples': samples, 'reference_gap': reference}
