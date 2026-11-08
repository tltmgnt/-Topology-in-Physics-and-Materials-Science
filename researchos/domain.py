"""Scoped adapter for the existing domain analyzer, not external validation."""
from materials_topology import build_report
DATA={'schema_version': 1, 'model': 'ssh', 'label': 'Synthetic SSH reference', 'cells': 12, 'boundary': 'open', 'intracell': {'value': 0.4, 'unit': 'eV'}, 'intercell': {'value': 1.0, 'unit': 'eV'}}
REQUIREMENTS={'schema_version': 1, 'expected_winding': 1, 'minimum_bulk_gap': {'value': 1, 'unit': 'eV'}, 'gap_tolerance': {'value': 1e-06, 'unit': 'eV'}, 'numerical_tolerance': {'value': 1e-10, 'unit': 'eV'}, 'near_zero_window': {'value': 0.01, 'unit': 'eV'}, 'minimum_boundary_weight': 0.8, 'minimum_boundary_candidates': 2, 'winding_samples': 256, 'reference_gap': {'value': {'value': 1.2, 'unit': 'eV'}, 'absolute_tolerance': {'value': 1e-10, 'unit': 'eV'}, 'source': 'synthetic:closed-form arithmetic', 'kind': 'synthetic'}}

def check():
    report=build_report(DATA,REQUIREMENTS)
    passed=report['status']=='MODEL_CHECKS_PASSED' and report['bulk']['analytic_winding']==1 and not report['experimental_validation_established']
    observed={k:v for k,v in report.items() if k not in ('bulk','finite')}
    observed['bulk']={k:v for k,v in report['bulk'].items() if k!='bands'}
    return {'domain':'physics','statement':'The supplied unit-aware synthetic SSH model passes its declared bulk and finite numerical requirements without establishing experimental validation.','passed':passed,
            'configuration':{'input':DATA,'requirements':REQUIREMENTS},'observed':observed,
            'scope':'Synthetic software/model requirements only; no independent scientific certification or execution authority'}
