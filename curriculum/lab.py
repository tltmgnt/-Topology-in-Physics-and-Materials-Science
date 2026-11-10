"""Offline curriculum answer key. Synthetic checks, never operational approval."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
for base in (ROOT, ROOT / "src", ROOT / "layer-b"):
    sys.path.insert(0, str(base))
CASES = []

def check(name, actual, expected):
    passed = actual == expected
    CASES.append({"case": name, "actual": actual, "expected": expected, "passed": passed})
    if not passed:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")

def rejects(name, call, error=ValueError):
    try:
        call()
    except error:
        check(name, error.__name__, error.__name__)
    else:
        raise AssertionError(f"{name}: expected {error.__name__}")

def sample(path):
    return json.loads((ROOT / path).read_text())



def run():
    from materials_topology.analysis import build_report
    policy = sample("examples/requirements.json")
    r = build_report(sample("examples/model.json"),policy)
    check("SSH winding in declared convention", r["summary"]["bulk_winding"], 1)
    check("bulk gap: 2*abs(1-.4) eV", round(r["bulk"]["gap_eV"],12), 1.2)
    check("finite boundary candidates", r["summary"]["boundary_candidates"], 2)
    q = build_report(sample("examples/trivial.json"),policy)
    check("reversed hopping regime", q["summary"]["bulk_winding"], 0)
    critical = build_report(sample("examples/critical.json"),policy)
    check("gap closure stays unresolved", critical["summary"]["bulk_winding"], None)
    check("short chain need not meet boundary threshold", build_report(sample("examples/short.json"),policy)["summary"]["boundary_candidates"], 0)
    check("no established experimental validation", r["experimental_validation_established"], False)

if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--verify"]):
        raise SystemExit("Usage: python curriculum/lab.py [--verify]")
    run()
    report = {"schema_version": 1, "status": "PASS", "case_count": len(CASES),
              "cases": CASES, "scope": "Synthetic curriculum checks only"}
    if sys.argv[1:] == ["--verify"]:
        expected = json.loads((Path(__file__).parent / "expected.json").read_text())
        if report != expected:
            raise AssertionError("Observed answers differ from curriculum/expected.json")
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
