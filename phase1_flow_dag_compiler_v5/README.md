# Phase-1 Flow / AND-OR-DAG Compiler v5

This version is built around a stronger observation:

> Most of the proof's apparent discrete choices are linear operations on
> coefficients and therefore do **not** need binary path variables.

Primary source:
Jiamin Li & Jianya Liu, *Theorem (1+1.9) on the Goldbach Conjecture*,
arXiv:2606.05224v2.

## Main abstraction

Every canonical sieve state has two signed resource pools:

```text
POS::X
NEG::X
```

All coefficient magnitudes are nonnegative flows.

An exact linear rewrite

```text
X = A - B + C
```

uses a continuous variable `x`:

```text
x units of X
 -> x units of A
 -> x units of -B
 -> x units of C
```

Thus if the current certificate contains `2 X`, there is no need for two
binary variables saying which copy is expanded. Any amount

```text
0 <= x <= 2
```

can be expanded, and the remaining `2-x` can stop or use another valid
linear identity.

This strictly contains the paper's manual choice to expand one of two `G2`s.

## Exact cancellation

If both `POS::X` and `NEG::X` are present, one continuous variable consumes
equal mass from both. No proof-tree branching is needed.

## AND/OR interpretation

- A linear identity is an **AND hyperedge**: all children are generated.
- Different valid linear identities or terminal estimators are resource-flow
  alternatives, not necessarily exclusive proof paths; coefficient mass can
  split among them.
- A true parameter-regime change is an **OR branch**.
- A multi-resource theorem such as (4.31)-(4.36) is a hyperedge consuming a
  signed bundle of several resources.
- Only *crossing* multi-resource hyperedges or mutually exclusive parameter
  regimes form the genuine global combinatorial core.

## Paper facts explicitly used by v5

1. The proof forms Proposition 4.3 by adding the two Proposition 4.2 instances
   (4.19) and (4.20). v5 keeps them as two source certificates and allows a
   nonnegative continuous mixture.
2. The paper says it applies (4.22) to **one of the two G2 terms**. v5 replaces
   this integer-looking choice by continuous coefficient allocation.
3. The switching principle only gives upper bounds. Therefore switching-based
   terminal rules attach to negative signed resources in a lower-bound proof.
4. The paper says the 12-term inequality was needed because `S6` had no useful
   lower bound via switching. v5 marks positive `S6` as a pressure point:
   trivial nonnegative drop or structural elimination.
5. Distribution levels change with the prime-size range. Split boundaries are
   stored lazily from theorem applicability rather than materialized eagerly.
6. Section 8.2.3 warns that crossing a parameter regime can change the
   weighted inequality itself. Such changes are modeled as genuine OR regimes.

## Run

```bash
pip install -r requirements.txt
python main.py --out phase1_flow_output
```

## Most important outputs

```text
phase1_flow_output/
  phase1_manifest_v5.json
  flow_blueprint.json
  flow_conservation.txt
  chain_analysis.json
  bundle_conflicts.json
  lazy_boundaries.json
  regime_templates.json
  summary.txt
```

The second-stage solver should consume `phase1_manifest_v5.json`.

## Certification policy

`UNRESOLVED_FRONTIER` flow must be forced to zero in a rigorous solve.

The paper's G16 source-shape mismatch is retained as a hard verification
warning; v5 does not silently identify `A_{p1p2}` with `A_{p1p2p3}`.
