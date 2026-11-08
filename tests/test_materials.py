"""Known-limit physics, units, numerical diagnostics and complete workflow tests."""
import ast
import contextlib
import copy
import hashlib
import io
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
import numpy as np
from materials_topology import build_report, compare_bundles, create_bundle, parse_model, parse_requirements, verify_bundle
from materials_topology.analysis import canonical
from materials_topology.io import MAX_BYTES, decode, read_json
from materials_topology.__main__ import main

ROOT = Path(__file__).resolve().parents[1]


def sample():
    return read_json(ROOT / 'examples/model.json'), read_json(ROOT / 'examples/requirements.json')


def q(value, unit='eV'):
    return {'value': value, 'unit': unit}


def relaxed(policy, expected=None):
    return {**policy, 'expected_winding': expected, 'minimum_bulk_gap': q(0),
            'minimum_boundary_candidates': 0, 'reference_gap': None}


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.model, self.policy = sample()

    def test_reference_bulk_and_boundary_diagnostics(self):
        report = build_report(self.model, self.policy)
        self.assertEqual(report['status'], 'MODEL_CHECKS_PASSED')
        self.assertEqual(report['bulk']['analytic_winding'], 1)
        self.assertAlmostEqual(report['bulk']['sampled_winding'], 1, places=10)
        self.assertAlmostEqual(report['bulk']['gap_eV'], 1.2)
        self.assertEqual(report['summary']['boundary_candidates'], 2)
        self.assertLess(report['finite_chain']['finite_spectral_gap_eV'], 0.001)
        self.assertFalse(report['experimental_validation_established'])

    def test_trivial_and_critical_are_distinct(self):
        trivial = build_report(read_json(ROOT / 'examples/trivial.json'), self.policy)
        self.assertEqual(trivial['summary']['bulk_winding'], 0)
        self.assertIn({'code': 'WINDING_MISMATCH', 'subject': 'bulk'}, trivial['gaps'])
        critical = build_report(read_json(ROOT / 'examples/critical.json'), self.policy)
        self.assertIsNone(critical['summary']['bulk_winding'])
        self.assertIsNone(critical['bulk']['sampled_winding'])
        self.assertEqual(critical['bulk']['classification'], 'UNRESOLVED_NEAR_GAP_CLOSURE')
        self.assertGreater(critical['finite_chain']['finite_spectral_gap_eV'], 0)

    def test_short_chain_does_not_guarantee_near_zero_boundary_candidates(self):
        report = build_report(read_json(ROOT / 'examples/short.json'), self.policy)
        self.assertEqual(report['summary']['bulk_winding'], 1)
        self.assertEqual(report['summary']['boundary_candidates'], 0)
        self.assertIn({'code': 'BOUNDARY_CANDIDATES_BELOW_MINIMUM', 'subject': 'finite_chain'}, report['gaps'])

    def test_intracell_dimer_limit(self):
        model = {**self.model, 'intracell': q(2), 'intercell': q(0), 'cells': 5}
        report = build_report(model, relaxed(self.policy, 0))
        actual = [mode['energy_eV'] for mode in report['finite_chain']['modes']]
        np.testing.assert_allclose(actual, [-2] * 5 + [2] * 5, atol=1e-10)
        self.assertEqual(report['bulk']['gap_eV'], 4)
        self.assertEqual(report['summary']['boundary_candidates'], 0)

    def test_intercell_dimer_limit_has_two_unpaired_end_sites(self):
        model = {**self.model, 'intracell': q(0), 'intercell': q(2), 'cells': 5}
        report = build_report(model, {**relaxed(self.policy, 1), 'minimum_boundary_candidates': 2})
        actual = [mode['energy_eV'] for mode in report['finite_chain']['modes']]
        np.testing.assert_allclose(actual, [-2] * 4 + [0, 0] + [2] * 4, atol=1e-10)
        self.assertEqual(report['summary']['boundary_candidates'], 2)
        self.assertEqual(report['status'], 'MODEL_CHECKS_PASSED')

    def test_uniform_open_chain_against_closed_form_spectrum(self):
        for cells in range(3, 11):
            with self.subTest(cells=cells):
                model = {**self.model, 'cells': cells, 'intracell': q(0.7), 'intercell': q(0.7)}
                report = build_report(model, relaxed(self.policy))
                expected = sorted(1.4 * math.cos(j * math.pi / (2 * cells + 1)) for j in range(1, 2 * cells + 1))
                actual = [mode['energy_eV'] for mode in report['finite_chain']['modes']]
                np.testing.assert_allclose(actual, expected, atol=1e-10)
                self.assertIsNone(report['summary']['bulk_winding'])

    def test_periodic_chain_against_discrete_bloch_spectrum(self):
        for cells in range(3, 10):
            for v, w in [(0.4, 1), (1, 0.4), (-0.4, 1), (0.4, -1)]:
                with self.subTest(cells=cells, v=v, w=w):
                    model = {**self.model, 'cells': cells, 'boundary': 'periodic', 'intracell': q(v), 'intercell': q(w)}
                    report = build_report(model, relaxed(self.policy))
                    expected = []
                    for sector in range(cells):
                        k = 2 * math.pi * sector / cells
                        energy = math.sqrt(max(0, v*v + w*w + 2*v*w*math.cos(k)))
                        expected += [-energy, energy]
                    actual = [mode['energy_eV'] for mode in report['finite_chain']['modes']]
                    np.testing.assert_allclose(actual, sorted(expected), atol=1e-10)
                    self.assertTrue(all(mode['boundary_weight'] is None for mode in report['finite_chain']['modes']))

    def test_winding_crosscheck_in_signed_hopping_limits(self):
        for v, w, expected in [(0, 1, 1), (0, -1, 1), (1, 0, 0), (-1, 0.4, 0), (0.4, -1, 1)]:
            model = {**self.model, 'intracell': q(v), 'intercell': q(w)}
            report = build_report(model, relaxed(self.policy, expected))
            self.assertEqual(report['bulk']['analytic_winding'], expected)
            self.assertAlmostEqual(report['bulk']['sampled_winding'], expected, places=10)

    def test_zero_hamiltonian_is_unresolved(self):
        model = {**self.model, 'intracell': q(0), 'intercell': q(0)}
        report = build_report(model, relaxed(self.policy))
        self.assertIsNone(report['summary']['bulk_winding'])
        self.assertTrue(all(mode['energy_eV'] == 0 for mode in report['finite_chain']['modes']))
        self.assertIn({'code': 'BULK_GAP_UNRESOLVED', 'subject': 'bulk'}, report['gaps'])

    def test_resolution_and_threshold_uncertainty_are_explicit(self):
        model = {**self.model, 'intracell': q(1 - 1e-8), 'intercell': q(1)}
        report = build_report(model, relaxed(self.policy))
        self.assertIsNone(report['summary']['bulk_winding'])
        reference = build_report(self.model, self.policy)
        policy = {**self.policy, 'near_zero_window': q(abs(reference['finite_chain']['modes'][11]['energy_eV']))}
        result = build_report(self.model, policy)
        self.assertTrue(result['finite_chain']['threshold_unresolved_indices'])
        self.assertIn({'code': 'BOUNDARY_CLASSIFICATION_UNRESOLVED', 'subject': 'finite_chain'}, result['gaps'])

    def test_numerical_failures_are_reported_not_ignored(self):
        original = np.linalg.eigh
        def corrupted(matrix):
            values, vectors = original(matrix)
            return values + 0.001, vectors
        with patch('materials_topology.analysis.np.linalg.eigh', side_effect=corrupted):
            report = build_report(self.model, self.policy)
        self.assertIn({'code': 'NUMERICAL_CHECK_FAILED', 'subject': 'eigen_residual_eV'}, report['gaps'])

    def test_solver_failure_is_clean(self):
        with patch('materials_topology.analysis.np.linalg.eigh', side_effect=np.linalg.LinAlgError('synthetic failure')):
            with self.assertRaisesRegex(ValueError, 'did not converge'):
                build_report(self.model, self.policy)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.model, self.policy = sample()

    def test_unit_equivalence_and_dimension_rejection(self):
        reference = build_report(self.model, self.policy)
        equivalent = build_report(read_json(ROOT / 'examples/mev.json'), self.policy)
        self.assertEqual(reference['bulk'], equivalent['bulk'])
        self.assertEqual(reference['finite_chain'], equivalent['finite_chain'])
        with self.assertRaises(ValueError):
            parse_model({**self.model, 'intracell': q(1, 'K')})
        with self.assertRaises(ValueError):
            parse_model({**self.model, 'intracell': q(1, 'joule')})

    def test_invalid_shapes_ranges_and_unknown_fields(self):
        changes = [{'schema_version': True}, {'cells': 2}, {'cells': 33}, {'cells': 3.0},
                   {'boundary': 'other'}, {'model': 'chern'}, {'onsite': q(1)},
                   {'intracell': q(True)}, {'intracell': q(float('nan'))},
                   {'intracell': q(float('inf'))}, {'intracell': q(1001)}]
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    parse_model({**self.model, **change})

    def test_invalid_requirements(self):
        model = parse_model(self.model)
        for change in ({'expected_winding': True}, {'winding_samples': 65}, {'winding_samples': 4098},
                       {'minimum_boundary_weight': 1.1}, {'numerical_tolerance': q(0)},
                       {'minimum_bulk_gap': q(-1)}, {'near_zero_window': q(1e-15)}):
            with self.assertRaises(ValueError):
                parse_requirements({**self.policy, **change}, model)
        periodic = parse_model(read_json(ROOT / 'examples/periodic.json'))
        with self.assertRaises(ValueError):
            parse_requirements(self.policy, periodic)

    def test_reference_disagreement_does_not_become_experimental_validation(self):
        policy = copy.deepcopy(self.policy)
        policy['reference_gap']['value'] = q(0.5)
        policy['reference_gap']['kind'] = 'declared_measurement'
        report = build_report(self.model, policy)
        self.assertEqual(report['reference_check']['status'], 'DISAGREES')
        self.assertFalse(report['reference_check']['experimental_validation_established'])
        self.assertFalse(report['reference_check']['source_authenticated'])
        self.assertIn({'code': 'DECLARED_REFERENCE_DISAGREEMENT', 'subject': 'bulk_gap'}, report['gaps'])

    def test_reference_mev_units_normalize(self):
        policy = copy.deepcopy(self.policy)
        policy['reference_gap']['value'] = q(1200, 'meV')
        report = build_report(self.model, policy)
        self.assertEqual(report['reference_check']['status'], 'AGREES')

    def test_json_and_python_syntax(self):
        for raw in (b'{"x":1,"x":1}', b'{"x":NaN}', b'{"x":1e999}', b'\xff',
                    ('[' * 70 + '0' + ']' * 70).encode()):
            with self.assertRaises(ValueError):
                decode(raw)
        for path in (ROOT / 'materials_topology').glob('*.py'):
            ast.parse(path.read_text(), filename=str(path), feature_version=(3, 10))


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.model, self.policy = sample()
        self.temp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'run'

    def test_full_bundle_replays_and_preserves_existing_output(self):
        report = create_bundle(self.path, self.model, self.policy)
        self.assertEqual(report, verify_bundle(self.path))
        with self.assertRaises(FileExistsError):
            create_bundle(self.path, self.model, self.policy)
        self.assertEqual(report, verify_bundle(self.path))

    def test_rehashed_report_forgery_fails(self):
        create_bundle(self.path, self.model, self.policy)
        report = read_json(self.path / 'report.json')
        report['experimental_validation_established'] = True
        raw = canonical(report)
        (self.path / 'report.json').write_bytes(raw)
        manifest = read_json(self.path / 'manifest.json')
        manifest['files']['report.json'] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        (self.path / 'manifest.json').write_bytes(canonical(manifest))
        with self.assertRaises(ValueError):
            verify_bundle(self.path)

    def test_each_file_tamper_fails(self):
        create_bundle(self.path, self.model, self.policy)
        for path in self.path.iterdir():
            raw = path.read_bytes()
            path.write_bytes(raw + b' ')
            with self.assertRaises(ValueError):
                verify_bundle(self.path)
            path.write_bytes(raw)

    def test_environment_mismatch_is_explicit(self):
        create_bundle(self.path, self.model, self.policy)
        report = read_json(self.path / 'report.json')
        report['environment']['numpy'] = 'different'
        (self.path / 'report.json').write_bytes(canonical(report))
        with self.assertRaisesRegex(ValueError, 'recorded Python and NumPy'):
            verify_bundle(self.path)

    def test_comparison_flags_model_policy_and_boundary_changes(self):
        create_bundle(self.path, self.model, self.policy)
        trivial = Path(self.temp.name) / 'trivial'
        create_bundle(trivial, read_json(ROOT / 'examples/trivial.json'), self.policy)
        result = compare_bundles(self.path, trivial)
        self.assertEqual(result['bulk_winding_delta'], -1)
        self.assertEqual(result['changed_model_parameters'], ['intracell_eV', 'intercell_eV'])
        self.assertFalse(result['assessment_policy_changed'])
        critical = Path(self.temp.name) / 'critical'
        create_bundle(critical, read_json(ROOT / 'examples/critical.json'), self.policy)
        self.assertIsNone(compare_bundles(self.path, critical)['bulk_winding_delta'])
        periodic = Path(self.temp.name) / 'periodic'
        create_bundle(periodic, read_json(ROOT / 'examples/periodic.json'), read_json(ROOT / 'examples/periodic-requirements.json'))
        result = compare_bundles(self.path, periodic)
        self.assertTrue(result['boundary_changed'])
        self.assertIsNone(result['boundary_candidate_delta'])

    def test_html_svg_and_escaped_label(self):
        self.model['label'] = '<script>alert(1)</script>'
        create_bundle(self.path, self.model, self.policy)
        html = (self.path / 'review.html').read_text()
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        fragments = html.split('<svg')[1:]
        self.assertEqual(len(fragments), 2)
        for fragment in fragments:
            ET.fromstring('<svg' + fragment.split('</svg>')[0] + '</svg>')

    def test_gap_bundle_is_consistent_without_passing(self):
        report = create_bundle(self.path, read_json(ROOT / 'examples/critical.json'), self.policy)
        self.assertEqual(report['status'], 'GAPS_FOUND')
        self.assertEqual(verify_bundle(self.path)['status'], 'GAPS_FOUND')

    def test_extra_file_and_symlink_rejected(self):
        create_bundle(self.path, self.model, self.policy)
        extra = self.path / 'extra'
        extra.write_text('x')
        with self.assertRaises(ValueError):
            verify_bundle(self.path)
        extra.unlink()
        source = self.path / 'report.json'
        target = Path(self.temp.name) / 'external'
        target.write_bytes(source.read_bytes())
        source.unlink()
        try:
            source.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            verify_bundle(self.path)

    def test_cli_exit_codes_and_scenarios(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['analyze', str(ROOT / 'examples/model.json'), '--requirements',
                                   str(ROOT / 'examples/requirements.json'), '--output', str(self.path)]), 0)
            self.assertEqual(main(['verify', str(self.path)]), 0)
            scenario = Path(self.temp.name) / 'critical'
            self.assertEqual(main(['analyze', str(ROOT / 'examples/critical.json'), '--requirements',
                                   str(ROOT / 'examples/requirements.json'), '--output', str(scenario)]), 1)
            self.assertEqual(main(['compare', str(self.path), str(scenario)]), 0)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['verify', str(Path(self.temp.name) / 'absent')]), 2)

    def test_file_size_limits(self):
        path = Path(self.temp.name) / 'large'
        with path.open('wb') as stream:
            stream.truncate(MAX_BYTES + 1)
        with self.assertRaises(ValueError):
            read_json(path)


if __name__ == '__main__':
    unittest.main()
