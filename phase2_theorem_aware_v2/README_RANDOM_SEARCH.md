# Phase-2 Random Paper-Path Search v1

The user-facing program is still only:

```bash
python main.py --delta 0.10
```

or edit the single line near the top of `main.py`:

```python
DELTA = 0.10
```

The target is `1 + (2-delta)`.

## What this version searches

It keeps the paper's twelve-term Proposition-4.3 architecture fixed and
randomly searches `alpha,beta,gamma` while `a=2-delta` and
`tau=(a-1)/a-epsilon`.

The previously fixed Section-5 constants are replaced by parameter-dependent
numerical evaluators:

- G1,G2: linear-sieve lower bounds via numerical F/f.
- G4,G5: one-dimensional linear-sieve upper-bound integrals.
- G6,G7: two-dimensional lower-bound integrals.
- G3: switching integral depending on tau.
- G8: switching integral depending on gamma.
- G9: theorem-driven split at u=1/10.
- G10: two-dimensional switching integral.
- G11,G12: reduced two-dimensional integrals with the Buchstab envelope used
  in Section 5.4.

The formulas are the parameterized form of the paper's Section-5 displayed
integrals.  The search is intentionally restricted to the analytic regime in
which the same estimator family remains applicable.

## Storage

The program determines its own folder using:

```python
os.path.dirname(os.path.abspath(__file__))
```

and creates:

```text
storage/
```

Every successful batch writes e.g.

```text
delta_0p1_batch_000123.txt
```

The file includes:

- delta and a,
- alpha,beta,gamma,tau,epsilon,
- random seed, batch and sample index,
- manifest/flow/script SHA256,
- evaluator settings,
- full Proposition-4.3 paper replay chain,
- all G1..G12 dynamic bounds,
- all signed contributions,
- final 4D and D margins,
- Buchstab envelope diagnostics,
- exact replay metadata.

This is enough to reconstruct the numerical candidate.

## Important certification status

A stored hit is labeled:

```text
NUMERICAL_CANDIDATE_NOT_INTERVAL_CERTIFIED
```

This random stage is for discovering candidate parameters quickly.  Before a
new exponent can be claimed rigorously, the saved candidate should be replayed
with high precision / interval arithmetic and every theorem applicability
condition should be certified.

## Deterministic resume

Each batch uses:

```text
batch_seed = BASE_SEED + batch_index
```

so a hit is reproducible from the stored batch/sample metadata.

Resume at batch 5000:

```bash
python main.py --delta 0.10 --start-batch 5000
```

Run exactly 20 batches:

```bash
python main.py --delta 0.10 --max-batches 20
```
