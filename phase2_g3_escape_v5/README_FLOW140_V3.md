# Phase-2 140-rewrite randomized flow search v3

This version opens all 140 Phase-1 rewrite allocation variables.

## Why it does NOT sample 140 independent Uniform(0,1) numbers

The 140 variables are coefficient flows, not independent parameters.  They
must satisfy the complete signed-resource conservation model:

- 140 rewrite allocations
- 155 terminal allocations
- 143 exact cancellations
- 2 source weights
- 1 multi-resource bundle
- 135 unresolved diagnostics
- source normalization
- optional G16 bridge

Therefore each random trial generates a 140-dimensional rewrite-preference
vector and solves a linear feasibility/optimization problem that projects it
onto the proof-flow polytope.

Every scored result has:

```text
unresolved = 0
max conservation residual ~ numerical LP tolerance
```

## Important Phase-1 V5 bundle fix

V5's mathematical bundle is:

```text
S6 - G14 - G15 - G16 + G11 + G12 >= 0
```

The intended closure is:

```text
S6-G14-G15-G16 >= -G11-G12.
```

Thus bundle use creates NEG G11 and NEG G12.

The V5 generated conservation equations accidentally attached the bundle to
POS G11/POS G12 outputs.  This makes the paper flow infeasible when
`unresolved=0`.

V3 corrects that incidence in the Stage-2 loader and includes a regression
test at the paper point.

## Current 140-dimensional coverage limitation

With the uploaded Phase-1 terminal theorem registry and `unresolved=0`, only
6 of the 140 rewrite variables can currently be nonzero.

This is not a random-search limitation.  The other deep rewrites eventually
produce negative frontier resources for which Phase 1 has not yet registered
a certified terminal upper estimator.

Run:

```bash
python main.py --diagnose-140
```

to see every forced-zero rewrite.

This means v3 is also a precise diagnostic of what must be added before all
140 dimensions can become mathematically usable.

## Commands

Random alpha,beta,gamma + 140 rewrite preferences:

```bash
python main.py --delta 0.105
```

One batch:

```bash
python main.py --delta 0.105 --max-batches 1
```

Paper point randomized flow:

```bash
python main.py --paper-point --flow-trials 50
```

Exact LP optimum at the paper point:

```bash
python main.py --paper-point --exact-flow
```

The exact LP mode is included because, conditional on fixed
`a,alpha,beta,gamma` and the currently registered terminal bounds, the flow
subproblem is linear.  It is therefore a useful upper benchmark for the
randomized 140-preference search.

## Storage

A successful candidate saves:

- delta/a/alpha/beta/gamma/tau
- theorem guards and splits
- dynamic G1..G12 values
- the full 140-dimensional random preference vector
- the full 140 actual rewrite allocations after conservation projection
- source weights
- nonzero terminal/cancellation/bundle/bridge flows
- effective final G1..G12 certificate coefficients
- margin in 2D, 4D-equivalent and D normalization
- max conservation residual
- max unresolved
- random seeds
- SHA256 of manifest, flow blueprint and main script

under `storage/` next to `main.py`.
