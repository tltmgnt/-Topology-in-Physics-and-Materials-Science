# Topology compatibility and curriculum v2 — -Topology-in-Physics-and-Materials-Science

Version 2 adapts the explicit-molecular-graph teaching pattern to this repository's actual role. This is documentation and a learning/decision framework; it introduces no mathematical engine, runtime dependency or operational permission.

## Repository decision

| Question | Repository-specific answer |
| --- | --- |
| Architectural role | specialized physical model |
| Minimum useful mathematics | Winding of the SSH Bloch loop plus finite-chain linear algebra |
| Relationships to preserve | Unit-cell convention, orientation, gap resolution and boundary conditions |
| Concrete operation / capstone | Compare intracell/intercell dimer limits and equal hoppings; explain unresolved winding at gap closure |
| Necessity and scope boundary | A finite threshold-localized mode is not proof of a protected physical edge state or a real material |

The decision is a source-based recommendation, not measured proof that a new specialty improves this repository. Start with the existing implementation and compare any proposed abstraction against a simpler alternative.

## Six-criterion compatibility scorecard

Complete one scorecard per proposed candidate and per concrete operation. Leave unmeasured entries unknown. Scores are human judgments from 0 (no fit) to 5 (strong evidenced fit); unknown is not zero. Do not sum an incomplete card. A total out of 30 is a heuristic, not adoption approval, and feasibility or necessity can veto a high total.

| Criterion | Score | Required evidence |
| --- | --- | --- |
| Structural compatibility | Not yet scored | Map the repository objects and the relationships above without losing direction, labels, units or missingness. |
| Transformation support | Not yet scored | Demonstrate the capstone operation on accepted and rejected inputs. |
| Invariant preservation | Not yet scored | State the property preserved and supply a counterexample or perturbation. |
| Computational feasibility | Not yet scored | Measure size, time and memory on bounded fixtures; record limits. |
| Integration compatibility | Not yet scored | Verify existing schemas, APIs and neighboring contracts remain compatible. |
| Mathematical necessity | Not yet scored | Compare with winding of the ssh bloch loop plus finite-chain linear algebra and explain the additional capability, if any. |

## Curriculum

Prerequisites: basic programming, sets, functions and graph vocabulary. Work in six competency-gated sessions, approximately 60–90 minutes each; empirical evaluation is a separate research activity.

| Session | Learning objective | Exercise | Completion evidence |
| --- | --- | --- | --- |
| 1. Model | Identify unit-cell convention, orientation, gap resolution and boundary conditions. | Draw a minimal valid example and one excluded relationship. | Annotated object/relation inventory with explicit assumptions. |
| 2. Contract | Distinguish schema validity from substantive correctness. | Trace validation and propose malformed, missing and boundary inputs. | Input-to-rejection table grounded in current source. |
| 3. Operation | Explain winding of the ssh bloch loop plus finite-chain linear algebra. | Compare intracell/intercell dimer limits and equal hoppings; explain unresolved winding at gap closure. | Hand trace compared with existing software, or a clearly labeled specification when no runtime exists. |
| 4. Preservation | State what a transformation must preserve. | Rename identifiers, reorder records, then alter one meaningful relation; predict each effect under the actual contract. | Separate invariant, expected change and unsupported transformation. |
| 5. Comparison | Justify mathematical necessity and cost. | Complete the six-criterion card for the existing approach and one proposed alternative; record unknowns honestly. | Evidence-backed recommendation with baseline and explicit veto conditions. |
| 6. Reproduction | Communicate the bounded result. | Reproduce the capstone using existing offline fixtures and record software version, inputs, outputs and limitations. | Reviewable notebook or report distinguishing computation, replay, independent evaluation and authorization. |

## Source-linked reading laboratory

The table is a guided selection of source lines, not an assertion that the whole repository is covered. Line numbers refer to the inspected source blob `6e95c8d6285a24a2bcbe416ed406733992f83fde` in [materials_topology/analysis.py](../../materials_topology/analysis.py). Recheck anchors after source changes.

| Line | Statement | Learning check |
| --- | --- | --- |
| [16](../../materials_topology/analysis.py#L16) | `def runtime_info():` | State the input/output contract and trace one normal and one failing case. |
| [17](../../materials_topology/analysis.py#L17) | `return {'python': platform.python_version(), 'numpy': np.__version__}` | Predict the returned value and distinguish a computed result from authorization. |
| [20](../../materials_topology/analysis.py#L20) | `def canonical(value):` | State the input/output contract and trace one normal and one failing case. |
| [21](../../materials_topology/analysis.py#L21) | `return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()` | Predict the returned value and distinguish a computed result from authorization. |
| [24](../../materials_topology/analysis.py#L24) | `def fingerprint(value):` | State the input/output contract and trace one normal and one failing case. |
| [25](../../materials_topology/analysis.py#L25) | `return hashlib.sha256(canonical(value)).hexdigest()` | Explain the exact bytes bound by the digest and why hashing does not authenticate the source. |
| [28](../../materials_topology/analysis.py#L28) | `def number(value):` | State the input/output contract and trace one normal and one failing case. |
| [30](../../materials_topology/analysis.py#L30) | `return float(format(float(value), '.12g'))` | Predict the returned value and distinguish a computed result from authorization. |
| [33](../../materials_topology/analysis.py#L33) | `def hamiltonian(model):` | State the input/output contract and trace one normal and one failing case. |
| [42](../../materials_topology/analysis.py#L42) | `return matrix` | Predict the returned value and distinguish a computed result from authorization. |
| [45](../../materials_topology/analysis.py#L45) | `def bulk(model, policy):` | State the input/output contract and trace one normal and one failing case. |
| [62](../../materials_topology/analysis.py#L62) | `return {'gap_eV': number(gap), 'effective_resolution_eV': number(resolution),` | Predict the returned value and distinguish a computed result from authorization. |
| [68](../../materials_topology/analysis.py#L68) | `def finite_chain(model, policy):` | State the input/output contract and trace one normal and one failing case. |
| [73](../../materials_topology/analysis.py#L73) | `raise ValueError('finite-chain eigensolver did not converge') from error` | Construct the triggering input and explain why rejection preserves the contract. |
| [75](../../materials_topology/analysis.py#L75) | `raise ValueError('eigensolver returned nonfinite values')` | Construct the triggering input and explain why rejection preserves the contract. |
| [104](../../materials_topology/analysis.py#L104) | `return {'sites': len(matrix), 'boundary': model.boundary, 'modes': modes,` | Predict the returned value and distinguish a computed result from authorization. |
| [110](../../materials_topology/analysis.py#L110) | `def build_report(data, requirements):` | State the input/output contract and trace one normal and one failing case. |
| [143](../../materials_topology/analysis.py#L143) | `return {'schema_version': 1, 'engine_version': ENGINE_VERSION,` | Separate type, shape and value checks; test a missing field and an invalid value. |
## Assessment and verification

A learner must explain the model, trace the capstone, identify a counterexample and state the scope boundary. Assess these four competencies equally; a numerical score cannot compensate for an unsupported scientific or operational claim.

Relevant existing checks:

- [tests/test_materials.py](../../tests/test_materials.py)
- [tests/test_researchos.py](../../tests/test_researchos.py)

Follow [README](../../README.md) for environment and installed-package instructions. Read scripts before execution; source-reading exercises do not authorize provider calls, model downloads, live orders, hardware actions or messages. Synthetic fixtures establish software behavior only. This documentation change does not report those exercises as already executed.

## Interoperability and adoption gate

Retain explicit domain contracts. Shared assurance records should refer to domain evidence and its assumptions rather than relabeling graph reachability, homology, statistical calibration and epistemic acceptance as interchangeable quantities. The canonical ResearchOs controller remains owned by ResearchOs; this curriculum does not create another controller fork.

Adopt additional mathematics only after a versioned experiment demonstrates a useful operation, the scorecard has evidence, the simpler baseline is inadequate and existing conformance checks remain satisfied. A finite threshold-localized mode is not proof of a protected physical edge state or a real material.
