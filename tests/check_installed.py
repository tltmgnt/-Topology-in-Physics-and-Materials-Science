"""Exercise installed SSH-model workflows outside the checkout."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def run(arguments, directory, expected=0):
    result = subprocess.run([sys.executable, '-I', '-m', 'materials_topology', *arguments],
                            cwd=directory, capture_output=True, text=True, check=False)
    if result.returncode != expected:
        raise AssertionError(result.stderr or result.stdout)
    response = json.loads(result.stdout)
    if response['experimental_validation_established'] or response['execution_authorized']:
        raise AssertionError('model checks cannot establish real-world validation or authority')
    return response


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as directory:
        cases = [('baseline','model.json','requirements.json',0),
                 ('trivial','trivial.json','requirements.json',1),
                 ('critical','critical.json','requirements.json',1),
                 ('short','short.json','requirements.json',1),
                 ('periodic','periodic.json','periodic-requirements.json',0),
                 ('units','mev.json','requirements.json',0)]
        for label, model, requirements, expected in cases:
            path = Path(directory) / label
            run(['analyze',str(root / 'examples' / model),'--requirements',
                 str(root / 'examples' / requirements),'--output',str(path)], directory, expected)
            if not run(['verify',str(path)],directory)['bundle_consistent']:
                raise AssertionError('bundle replay failed')
        comparison = run(['compare',str(Path(directory) / 'baseline'),str(Path(directory) / 'trivial')],directory)
        if comparison['bulk_winding_delta'] != -1 or comparison['assessment_policy_changed']:
            raise AssertionError('phase comparison mismatch')
    print('Installed reference, trivial, critical, short-chain, periodic, unit and comparison workflows passed')


if __name__ == '__main__':
    main()
