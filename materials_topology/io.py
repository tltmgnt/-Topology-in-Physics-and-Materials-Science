"""Bounded strict JSON input and exclusively created replay-verifiable bundles."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
from .analysis import build_report, canonical, runtime_info
from .render import render_html

MAX_BYTES = 4 * 1024 * 1024
FILES = {'model.json', 'requirements.json', 'report.json', 'review.html', 'manifest.json'}


def read_bytes(path, limit=MAX_BYTES, no_symlink=False):
    flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0)
    if no_symlink:
        flags |= getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError('bounded regular file required')
        value = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        if len(value) > limit or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('input too large or changed during read')
        return value


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _constant(_value):
    raise ValueError('nonfinite JSON number')


def decode(raw):
    try:
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeError, RecursionError) as error:
        raise ValueError('invalid UTF8 or JSON nesting') from error
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 64:
            raise ValueError('JSON nesting limit exceeded')
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('nonfinite JSON number')
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    return value


def read_json(path):
    return decode(read_bytes(path))


def bundle_contents(data, requirements):
    report = build_report(data, requirements)
    files = {'model.json': canonical(data), 'requirements.json': canonical(requirements),
             'report.json': canonical(report), 'review.html': render_html(data, report).encode()}
    if any(len(value) > MAX_BYTES for value in files.values()):
        raise ValueError('output exceeds bundle limits')
    manifest = {'schema_version': 1, 'files': {name: {'sha256': hashlib.sha256(value).hexdigest(),
                                                  'bytes': len(value)} for name, value in sorted(files.items())}}
    files['manifest.json'] = canonical(manifest)
    return files, report


def create_bundle(destination, data, requirements):
    files, report = bundle_contents(data, requirements)
    path = Path(destination)
    # Exclusive directory creation prevents overwriting inputs or prior runs.
    path.mkdir(mode=0o700)
    try:
        for name, value in files.items():
            with (path / name).open('xb') as stream:
                stream.write(value)
    except (OSError, ValueError):
        shutil.rmtree(path)
        raise
    return report


def verify_bundle(destination):
    path = Path(destination)
    if path.is_symlink() or not path.is_dir() or {p.name for p in path.iterdir()} != FILES:
        raise ValueError('exact bundle directory required')
    actual = {}
    for name in sorted(FILES):
        item = path / name
        if item.is_symlink():
            raise ValueError('bundle symlinks forbidden')
        actual[name] = read_bytes(item, no_symlink=True)
    supplied = decode(actual['report.json'])
    if not isinstance(supplied, dict) or supplied.get('environment') != runtime_info():
        raise ValueError('replay requires the recorded Python and NumPy versions; inspect report environment')
    expected, report = bundle_contents(decode(actual['model.json']), decode(actual['requirements.json']))
    if actual != expected:
        raise ValueError('bundle differs from recomputed analysis')
    return report



def compare_bundles(baseline, scenario):
    left, right = verify_bundle(baseline), verify_bundle(scenario)
    old_model, new_model = left['normalized_model'], right['normalized_model']
    parameters = [key for key in old_model if key != 'label' and old_model[key] != new_model[key]]
    old_winding, new_winding = left['summary']['bulk_winding'], right['summary']['bulk_winding']
    old_gaps = {(gap['code'], gap['subject']) for gap in left['gaps']}
    new_gaps = {(gap['code'], gap['subject']) for gap in right['gaps']}
    boundary_changed = old_model['boundary'] != new_model['boundary']
    return {'schema_version': 1, 'baseline_model_sha256': left['model_sha256'],
            'scenario_model_sha256': right['model_sha256'],
            'baseline_requirements_sha256': left['requirements_sha256'],
            'scenario_requirements_sha256': right['requirements_sha256'],
            'changed_model_parameters': parameters, 'assessment_policy_changed': left['requirements'] != right['requirements'],
            'boundary_changed': boundary_changed,
            'bulk_winding_delta': new_winding - old_winding if old_winding is not None and new_winding is not None else None,
            'bulk_gap_delta_eV': right['summary']['bulk_gap_eV'] - left['summary']['bulk_gap_eV'],
            'boundary_candidate_delta': None if boundary_changed else right['summary']['boundary_candidates'] - left['summary']['boundary_candidates'],
            'new_gaps': [{'code': code, 'subject': subject} for code, subject in sorted(new_gaps - old_gaps)],
            'resolved_gaps': [{'code': code, 'subject': subject} for code, subject in sorted(old_gaps - new_gaps)],
            'baseline_status': left['status'], 'scenario_status': right['status'],
            'experimental_validation_established': False, 'execution_authorized': False,
            'limitation': 'Toy-model parameter and criterion comparison, not experimental evidence or real-material performance'}
