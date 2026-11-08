"""Unit-aware SSH-model studies, exact-environment replay and comparison."""
import argparse
import json
import sys
from .io import compare_bundles, create_bundle, read_json, verify_bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    analyze = commands.add_parser('analyze', help='Create a new SSH-model research bundle')
    analyze.add_argument('model')
    analyze.add_argument('--requirements', required=True)
    analyze.add_argument('--output', required=True)
    verify = commands.add_parser('verify', help='Recompute a bundle in its recorded numerical environment')
    verify.add_argument('bundle')
    compare = commands.add_parser('compare', help='Compare two verified SSH-model studies')
    compare.add_argument('baseline')
    compare.add_argument('scenario')
    args = parser.parse_args(argv)
    try:
        if args.command == 'analyze':
            report = create_bundle(args.output, read_json(args.model), read_json(args.requirements))
            result = {'bundle_created': True, 'status': report['status'], 'summary': report['summary']}
            code = 1 if report['gaps'] else 0
        elif args.command == 'verify':
            report = verify_bundle(args.bundle)
            result = {'bundle_consistent': True, 'status': report['status'], 'summary': report['summary']}
            code = 0
        else:
            result = compare_bundles(args.baseline, args.scenario)
            code = 0
        result['experimental_validation_established'] = False
        result['execution_authorized'] = False
    except (ValueError, OSError) as error:
        print(json.dumps({'error': str(error), 'experimental_validation_established': False,
                          'execution_authorized': False}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
