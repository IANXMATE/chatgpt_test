# Phase-2 G3 Escape Analyzer V5

## Why this is the next targeted experiment

V4 increased structural coverage from roughly 6/140 to 13-16/140, but the
exact LP optimum still used only 5 rewrites and retained the paper's `-4 G3`
exposure.  For delta=0.2 the observed loss is numerically almost entirely
explained by the worsening of G3.

Phase-1 already contains an exact Buchstab expansion of G3:

```text
G3 = BASE - CORRECTION
```

Therefore in the lower-bound certificate:

```text
-G3 = -BASE + CORRECTION.
```

The positive correction can be discarded by non-negativity.  The first
obstruction is the NEG BASE state:

```text
factor_count = 1
sieve_set    = P(N)
threshold    = fixed tau
region       = tau <= u1 <= 1/2
```

V5 deliberately does NOT invent an upper bound for this BASE state.

Instead it answers:

> How strong would such an upper bound need to be?

If

```text
BASE <= U * C(N)N/log^2 N,
```

V5 disables the paper's direct G3 upper terminal, forces the exact G3
Buchstab route, and solves the complete flow LP.

It then binary-searches the largest value

```text
Ucrit
```

for which the final certificate still has the requested nonnegative margin.

`Ucrit` is therefore a **theorem-design target**, not a theorem.

## Commands

### 1. Full diagnosis near the boundary

```bash
python main.py --delta 0.11 --report
```

This prints:

- baseline margin using the paper G3 terminal;
- whether the proof remains feasible if that terminal is simply removed;
- the first genuine unresolved blocker;
- `Ucrit`;
- `Ucrit / current dynamic G3 upper`.

### 2. Paper point

```bash
python main.py --paper-point --report
```

### 3. Test a hypothetical theorem constant

```bash
python main.py --delta 0.11 --report --hypothetical-base-upper 0.80
```

No mathematical claim is made; this is sensitivity analysis.

### 4. Pareto: reduce direct G3 usage

```bash
python main.py --delta 0.11 --report --pareto --hypothetical-base-upper 0.80
```

### 5. Search alpha,beta,gamma for the easiest G3-base theorem target

```bash
python main.py --delta 0.11
```

The search objective is NOT best current margin.  It is:

```text
maximize Ucrit(alpha,beta,gamma).
```

A larger Ucrit means a weaker/easier future upper-bound theorem would be
sufficient to close the proof.

### 6. Known benchmark

The Li-Liu preprint explicitly remarks that `1.9` can be improved to `1.894`
using more intricate parameters and Wu's double sieve.  V5 does not implement
that double sieve.  A useful benchmark is therefore:

```bash
python main.py --delta 0.106
```

If the G3 escape route requires an implausibly sharp BASE theorem even around
delta=0.106, implementing Wu's double-sieve branch is the more grounded next
direction.

## Certification status

- Phase-1 G3 rewrite: exact structural identity.
- Flow conservation: exact LP constraints up to solver tolerance.
- Existing G1..G12 / frontier bounds: same numerical theorem-aware machinery
  as V4.
- `HYPOTHETICAL_G3_BASE_UPPER`: **not proved**.
- `Ucrit`: sensitivity target only.

Never interpret a positive result obtained with a hypothetical BASE upper as
a proof of a new exponent.
