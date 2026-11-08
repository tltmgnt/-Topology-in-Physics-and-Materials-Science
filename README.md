# Topology in Physics and Materials Science

An end-to-end **idealized SSH-chain research workflow** with explicit energy units,
bulk winding and gap analysis, finite-chain spectra, numerical consistency checks,
threshold-aware boundary-localization diagnostics and replayable offline reports.

The software implements a bounded noninteracting lattice model. It does not validate
a real material, predict a device's performance or certify an experimentally observed
phase. Synthetic examples demonstrate model calculations and software behavior.

## Install and complete a study

Requires Python 3.10 or later and NumPy. Installation resolves `numpy>=1.26,<3`.
No API credentials or paid service is needed.

```sh
python -m pip install .
mkdir -p runs
materials-topology analyze examples/model.json --requirements examples/requirements.json --output runs/reference
materials-topology verify runs/reference
```

Open `runs/reference/review.html` for offline bulk-band and finite-spectrum SVG plots,
eigenmode diagnostics, assumptions, gaps and numerical environment. Output directories
must be new; their parents must exist. Without installation, use
`python -m materials_topology` from the repository root.

```sh
python -m unittest discover -s tests -v
python tests/check_installed.py
```

The installed-workflow script requires normal installation and uses isolated imports
outside the checkout. It covers successful and failing studies plus replay and
comparison.

## Implemented model and convention

The model has N cells, two sites A/B per cell, real intracell hopping v and intercell
hopping w, zero onsite energies, and no interactions, disorder or temperature effects.
The finite chain supports open or periodic boundaries. Both positive and negative
real hoppings are accepted within documented computational bounds.

The fixed Bloch convention is:

`q(k) = v + w exp(i k)`

`H(k) = [[0, conjugate(q(k))], [q(k), 0]]`, with k increasing from 0 to 2π.

The bulk energies are `±|q(k)|` and the infinite-chain gap is
`2 * abs(abs(v) - abs(w))`. The winding in this convention is 1 when `abs(w)>abs(v)`
and 0 otherwise, provided the gap is resolved. The unit cell and orientation matter;
the invariant must not be compared across silently changed conventions.

Near a gap closure, the result is explicitly unresolved and the winding is null.
The effective energy resolution is the larger of the declared gap tolerance and
twice the numerical tolerance. The software does not silently assign winding zero
at criticality. A separate phase-increment sum on a sampled q loop cross-checks the
analytic result when the gap is resolved.

The finite real symmetric Hamiltonian is diagonalized with NumPy `eigh`. Numerical
diagnostics check Hermiticity, chiral anticommutation, eigenpair residuals,
orthogonality and a closed-form trace-square sum rule. The periodic bulk gap and
finite-chain spectral gap are reported separately.

Background: [Asbóth Oroszlány and Pályi lecture notes](https://arxiv.org/abs/1509.02295),
particularly the SSH chapter; [NumPy eigh documentation](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eigh.html).
This project is a numerical implementation of a known model, not a new physical theory.

## Synthetic studies

| Example | Purpose | Expected result with supplied requirements |
|---|---|---|
| `model.json` | v=0.4 eV, w=1 eV, 12 open cells | Winding 1, bulk gap 1.2 eV, two threshold-defined boundary candidates |
| `trivial.json` | Reversed hopping strengths | Winding mismatch and too few boundary candidates |
| `critical.json` | Equal hoppings | Unresolved winding at bulk gap closure |
| `short.json` | Three open cells with the reference hoppings | Bulk winding remains 1; finite candidates miss the declared window |
| `periodic.json` | Periodic finite chain | No physical boundaries; candidate requirement must be zero |
| `mev.json` | Equivalent 400/1000 meV hoppings | Same computed spectrum and bulk result as the reference |

```sh
materials-topology analyze examples/trivial.json --requirements examples/requirements.json --output runs/trivial
# Expected exit 1; a complete gap bundle is still produced.
materials-topology verify runs/trivial
# Expected exit 0; internal consistency does not remove the model requirement gaps.
materials-topology compare runs/reference runs/trivial
```

For the periodic example, use `examples/periodic-requirements.json`. A positive
boundary-candidate requirement for a periodic chain is rejected as incompatible input.

## Exact contracts and units

Model:

```json
{
  "schema_version":1,
  "model":"ssh",
  "label":"Synthetic SSH reference",
  "cells":12,
  "boundary":"open",
  "intracell":{"value":0.4,"unit":"eV"},
  "intercell":{"value":1,"unit":"eV"}
}
```

All energy inputs require explicit `value` and `unit`; eV and meV are supported and
normalized to eV. Kelvin, joules, unitless energies, booleans and nonfinite values
are rejected. No implicit energy-to-temperature or other dimensional conversion is
performed. Model sizes are bounded to 3–32 cells and hopping magnitudes to 1000 eV.
These are computational limits, not claims that every input represents a real material.

Requirements:

```json
{
  "schema_version":1,
  "expected_winding":1,
  "minimum_bulk_gap":{"value":1,"unit":"eV"},
  "gap_tolerance":{"value":0.000001,"unit":"eV"},
  "numerical_tolerance":{"value":0.0000000001,"unit":"eV"},
  "near_zero_window":{"value":0.01,"unit":"eV"},
  "minimum_boundary_weight":0.8,
  "minimum_boundary_candidates":2,
  "winding_samples":256,
  "reference_gap":null
}
```

Every key is required; unknown fields are rejected. `expected_winding:null` disables
only the expected-invariant comparison. It does not make an unresolved bulk gap
pass. The optional reference value may be null or a declared reference object with
explicit value/tolerance energies, source and kind. See the complete example.

## Boundary candidates and numerical limits

For open chains, a mode's boundary weight sums its probability on the first and
last complete two-site cells. Candidate status requires energy inside the near-zero
window and boundary weight above the minimum, each separated from its threshold
by the declared numerical/fixed weight tolerance. Borderline modes are unresolved,
not automatically accepted. Periodic chains have null boundary weights and no
candidate classification.

These are finite-size, threshold-based diagnostics. A candidate is not proof of a
protected edge mode. Degenerate eigenspaces can have basis-dependent localization
weights, and a short chain can split nominal edge states away from the selected
window. No conclusion about real material robustness follows.

## Declared reference comparisons

A reference object has `value`, `absolute_tolerance`, `source`, `kind`; kind is
`synthetic` or `declared_measurement`. The tool compares the computed bulk gap with
that provided scalar. It does not retrieve, authenticate, fit, calibrate or validate
the source. Agreement with a declared measurement never sets
`experimental_validation_established` to true. The shipped reference is synthetic
closed-form arithmetic only.

## Review bundles and replay

Each bundle contains exactly model.json, requirements.json, report.json,
review.html and manifest.json. It captures inputs, normalized units, conventions,
thresholds, software versions, spectra, diagnostics and limitations. The renderer
uses no scripts or external fonts, images or services. Data-dependent labels are
escaped; plots are native SVG.

Exact verification recomputes every file, so editing a report and rewriting its
manifest cannot conceal a changed calculation. Raw report numbers use 12 significant
digits; acceptance decisions use unrounded values. Python and NumPy versions are
recorded and must match for replay. Numerical backend/platform differences can
still change eigenspaces or low-order residuals; exact replay may reject such a
bundle. Use the recorded environment/backend to reproduce it rather than weakening
checks. This is a consistency mechanism, not a numerical proof or source signature.

| Command | Exit 0 | Exit 1 | Exit 2 |
|---|---|---|---|
| `analyze` | Declared model checks passed | Gaps found; complete bundle created | Invalid input, size, solver or I/O failure |
| `verify` | Bundle matches recomputation | Not used | Edited, incompatible or incomplete bundle |
| `compare` | Both studies verified and compared | Not used | Invalid or incompatible bundle |

Comparison records changed hopping/size/boundary parameters and changed policy.
An unresolved winding yields a null delta. Boundary-candidate delta is null when
boundary conditions differ. Cell-size changes and threshold differences must still
be considered before interpreting other deltas. No comparison establishes an
experimental phase transition or a real-material improvement.

## Validation and CI

Tests include the disconnected intracell/intercell dimer limits, uniform open-chain
closed-form eigenvalues, periodic Bloch spectra, signed hopping limits, zero hopping,
near-critical resolution, finite-size splitting, threshold uncertainty, unit
conversion, reference disagreement, injected solver failures, malformed input,
replay tampering and command-line workflows.

CI tests Python 3.10, 3.12 and 3.13, installs the package normally and exercises
isolated installed workflows. Successful runs publish a seven-day
`synthetic-materials-review` artifact. Extract it and open review.html. To verify it,
use the Python/NumPy versions recorded in report.json; backend compatibility is also
required. Only synthetic model data is uploaded.

See [numerical contracts and boundaries](docs/NUMERICS.md). DFT, Chern/Z2 invariants,
complex/disordered hoppings, interactions, finite temperature, experimental data
adapters, material synthesis and device control remain outside this implementation.
The repository's original Apache-2.0 license is retained.

## ResearchOS / TECT concept integration

The [ResearchOS / Topological Epistemic Control Theory technical concept paper](docs/researchos/TECT_WHITE_PAPER.md) proposes an epistemic control and assurance infrastructure for AI-generated knowledge. Read the [repository integration status](docs/researchos/INTEGRATION.md) and [machine-readable scope](docs/researchos/integration.json) for the boundary between the concept and implemented capabilities. Performance targets are research objectives, not achieved results. This documentation addition does not implement the complete ResearchOS architecture or change operational authority.
