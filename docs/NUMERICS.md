# Numerical contracts and acceptance scope

## Fixed domain and topology convention

The only accepted model is the real, spinless, noninteracting nearest-neighbor SSH
chain with zero onsite energies. N cells define the site order A0 B0 A1 B1 ... .
Intracell hopping connects Ai to Bi; intercell hopping connects Bi to A(i+1).
Open boundaries omit the last wraparound bond; periodic boundaries retain it.
The Hamiltonian is real symmetric and off-diagonal in the alternating sublattices.
Complex hoppings, onsite terms, disorder and alternative models are not accepted.

The Bloch convention is q=v+w exp(ik), H=[[0,q*],[q,0]], k from 0 to 2π. This fixes
unit-cell and orientation choices. Bulk bands are ±|q|, with direct gap
2 ||v|-|w||. The analytic winding is 1 for |w|>|v| and 0 for |v|>|w|; gap closure
leaves it undefined. No other topological invariant is implemented.

The reported finite spectral gap is twice the smallest absolute finite-chain
eigenvalue, measured about zero energy. It is not the infinite periodic bulk gap.
The two can differ substantially in an open finite system.

## Preflight and units

Root and nested objects require exactly the documented keys. Schema versions are
integer 1, not booleans. Labels are trimmed 1–160 character strings. Cells must be
an integer in 3–32. Boundary is open or periodic. Energy objects contain value and
unit, where unit is eV or meV. All accepted numbers are finite and booleans are
rejected. Hopping magnitudes after conversion cannot exceed 1000 eV.

Other normalized energy quantities are bounded to 10^6 eV. Minimum gap and reference
absolute tolerance may be zero; gap tolerance, numerical tolerance and near-zero
window must be at least 10^-12 eV. These are numerical software bounds. Boundary
weight is dimensionless in [0,1]; minimum candidates is an integer from 0 to 2N,
and must be zero for periodic input. Winding samples are even integers in 64–4096.
Expected winding is integer 0/1 or null.

A reference is null or exactly value, absolute_tolerance, source, kind. Its quantities
carry explicit units. Source is supplied text, not a downloaded or authenticated
artifact; kind is synthetic or declared_measurement. Comparison does not turn a
reference declaration into experimental validation.

Files are regular UTF8 JSON, optionally with a BOM, at most 4 MiB each. Duplicate
keys, nonfinite values including overflowing literals, and JSON nesting over 64
levels are rejected. Metadata is checked before/after bounded reads. No network,
credentials or external model calls occur during analysis.

## Gap resolution and winding cross-check

Effective bulk gap resolution is max(gap_tolerance_eV, 2*numerical_tolerance_eV).
Gap <= resolution is UNRESOLVED_NEAR_GAP_CLOSURE, with null winding and a
BULK_GAP_UNRESOLVED finding. This remains a gap even if expected winding is null;
disabling a comparison cannot supply a missing invariant.

For a resolved gap, q is normalized by max(|v|,|w|) before phase increments are
computed. The code sums atan2(Im(conj(q_j)*q_(j+1)), Re(conj(q_j)*q_(j+1))) over the
sampled closed loop. Its winding estimate must agree with the analytic result within
10^-6. This is a model-specific numerical cross-check, not arbitrary-loop homology
or a mechanically checked proof.

Band data includes the closed endpoint and uses dimensional eV values. Samples do
not determine the analytic minimum bulk gap. The analytic formula supplies that
quantity; no coarse-grid minimum is mislabeled as a continuum result.

## Finite numerical diagnostics

NumPy eigh diagonalizes the real symmetric matrix. The following are checked:

- Maximum absolute H-H.T residual, in eV.
- Maximum absolute ΓH+HΓ residual, in eV, Γ alternating +1/-1.
- Maximum absolute HV-Vdiag(E) residual, in eV.
- Maximum absolute V.T V-I residual, dimensionless.
- Relative residual of sum(E_i^2) against the analytic trace(H^2) bond sum.

The first three must not exceed numerical_tolerance_eV. Orthogonality and relative
trace-square residuals must not exceed 10^-10. Trace(H^2)=2[Nv²+(N-1)w²] for open
chains and 2N(v²+w²) for periodic chains. Nonconvergence or nonfinite solver output
is an input/run failure, not a passing model assessment.

Acceptance uses unrounded numbers. Reports format numerical values to 12 significant
digits; close boundary decisions can differ from what rounded displayed values
appear to imply. The mathematical known-limit tests provide additional independent
checks of the matrix assembly, not only repeated execution of this implementation.

## Boundary localization

For an open chain, boundary weight is sum of squared amplitudes on site indices
0,1,2N-2,2N-1. This measures both complete end cells, not only the two outermost
sites. N>=3 keeps this region smaller than the whole chain. Weights can depend on
the basis chosen inside degenerate eigenspaces; this implementation does not
construct a basis-invariant boundary-subspace invariant.

A mode outside the near-zero energy window by more than numerical_tolerance is
OUTSIDE_NEAR_ZERO_WINDOW. A mode below the minimum weight by more than 10^-10 is
NOT_BOUNDARY_LOCALIZED. A potentially qualifying mode within either margin is
THRESHOLD_UNRESOLVED. Only modes separated positively from both margins are
BOUNDARY_CANDIDATE. If candidates are required, unresolved threshold modes add an
explicit gap. Periodic mode weights are null and classification is not applicable.

These diagnostics do not assert protected boundary states, robustness under disorder,
or experimental localization. They cannot be used to infer a real material's phase.

## Findings and overall status

| Code | Meaning |
|---|---|
| BULK_GAP_UNRESOLVED | Infinite-chain gap too small for declared resolution |
| WINDING_MISMATCH | Resolved invariant differs from requested value |
| BULK_GAP_BELOW_MINIMUM | Analytic gap below supplied minimum |
| WINDING_CROSSCHECK_FAILED | Sampled phase sum disagrees with analytic winding |
| NUMERICAL_CHECK_FAILED | Residual exceeds the applicable tolerance |
| BOUNDARY_CANDIDATES_BELOW_MINIMUM | Too few finite threshold-defined candidates |
| BOUNDARY_CLASSIFICATION_UNRESOLVED | Requested candidate analysis has borderline modes |
| DECLARED_REFERENCE_DISAGREEMENT | Analytic gap disagrees with a supplied scalar/tolerance |

MODEL_CHECKS_PASSED means no findings under these model-specific rules. It is not
scientific discovery, material characterization, calibration, independent replication,
a certification, or permission to operate equipment. Experimental validation and
execution authorization remain false in reports and CLI responses.

## Reports, replay and comparisons

Bundles contain exactly model.json, requirements.json, report.json, review.html and
manifest.json. Inputs are captured as canonical sorted-key JSON with a final newline;
arrays and numeric encodings remain significant. No randomness or timestamp enters
the calculation. Reports retain engine version, Python patch version, NumPy version,
normalized parameters, conventions, policy and limitations.

Replay requires the recorded Python and NumPy versions and compatible numerical
backend behavior. It reconstructs every file and compares bytes, detecting edits even
with rewritten manifest hashes. Different BLAS/LAPACK libraries, platforms, library
versions or degenerate-basis choices may change results/residuals and fail exact
replay. Recreate the original environment rather than ignoring these differences.
The version check is necessary but not sufficient for bit-for-bit reproducibility.

This mechanism establishes consistency against the current implementation in the
specified environment, not source authenticity or formal numerical certification.
Replacing inputs and regenerating everything creates a different consistent study.
Future engine output changes can also require the original version for replay.

Destinations are created exclusively; existing output is preserved. Handled write
failures remove the new directory. Abrupt termination can leave a partial directory
that fails verification. Parent directories must exist. Symlink bundles/files are
rejected. Hostile concurrent filesystem modification is outside the supported model.

Comparison verifies both studies before showing parameter/policy changes. A winding
delta is null if either winding is unresolved. Candidate-count delta is null when
open/periodic boundaries differ. Finite size, changed thresholds and reference policy
can still explain other differences, so comparison is not causal experimental evidence.
