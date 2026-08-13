# Phase-2 Paper Replay

This is the first, deliberately narrow, Phase-2 model.

It wraps the Phase-1 flow/DAG artifacts in a reusable Python library and gives
you one executable `main.py`.  The only job of `main.py` is to answer:

> Does the generated Phase-1 structure reproduce the paper's own 1+1.9 proof
> path and final published numerical margin?

## What it validates

1. The Phase-1 reference parameters satisfy Proposition 4.3:
   `a=1.9`, `alpha=4/53`, `beta=4/33`, `gamma=3/11`,
   `tau=9/19-epsilon`.

2. Starting from the two generated source certificates `(4.19)` and `(4.20)`,
   the model replays:
   - drop `S6(beta,gamma)` by non-negativity;
   - expand one of the two `G2` coefficients;
   - substitute `-S3(beta,gamma)`;
   - canonical cancellation of `G13`;
   - substitute `-S5(beta,gamma)`;
   - use the `(4.31)-(4.36)` nonnegative closure bundle.

3. The resulting canonical coefficient ledger must be exactly:
   `3G1 + G2 - 4G3 - G4 - G5 + G6 + G7
    -2G8 - G9 - G10 - G11 - G12`.

4. The Section-5 rounded constants used in equation `(5.51)` must give:
   `4D margin = 0.00172`,
   hence `D margin = 0.00043 > 0.0004`.

## Run

```bash
python main.py
```

For every intermediate certificate:

```bash
python main.py --show-stages
```

To deliberately refuse the unresolved arXiv-v2 G16 shape bridge:

```bash
python main.py --strict-g16
```

That strict mode is expected to stop before the final closure.

## Library layout

```text
goldbach_phase2/
  io.py               Phase-1 artifact loading
  model.py            parameters, aliases, rules, constraints wrapper
  certificate.py      linear certificate ledger
  paper_replay.py     deterministic paper-path replay
  paper_bounds.py     Section-5 published rounded bounds
  replay_validator.py regression checks
  validation.py       report object
main.py               only user-facing entry point
```

## Important scope boundary

A PASS validates the *model plumbing* against the paper:
- structural coefficient path,
- sign/bound direction,
- final arithmetic from published Section-5 constants.

It is not yet an independent recomputation of every multi-dimensional integral
in Section 5.  That numerical evaluator is the next layer to plug into the same
library before freeing parameters or optimizing `a`.
