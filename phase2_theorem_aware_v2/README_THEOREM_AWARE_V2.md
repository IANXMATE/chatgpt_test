# Phase-2 theorem-aware evaluator v2

This version implements the requested pipeline:

```text
parameters
  -> theorem guards
  -> automatic theorem-induced splits
  -> dynamic linear-sieve F/f and Buchstab w
  -> G1,...,G12
  -> Proposition-4.3 twelve-term margin
```

## 1. Direct evaluation

```bash
python main.py --delta 0.10 \
  --alpha 0.07547169811320754 \
  --beta 0.12121212121212122 \
  --gamma 0.2727272727272727 \
  --show-trace
```

## 2. Paper point

```bash
python main.py --paper-point --show-trace
```

## 3. Random theorem-aware search

```bash
python main.py --delta 0.105
```

Successful candidates are saved under `storage/`, located using
`os.path.dirname(os.path.abspath(__file__))`.

## What changed from v1

### Genuine hard guards

- Proposition 4.3:
  `1.5+3eps<a<2`,
  `1/18<alpha<beta<(1-3beta)/3<gamma<1/3<tau`.
- G4 paper-path upper estimator:
  `alpha<1/12`.
- G5:
  `2*alpha+gamma<1/2`.
- G8 switching structure:
  `gamma>1/4`.
- G11/G12:
  only the genuine Buchstab domain `argument>1` is required.

### Automatic splits

- G6/G7:
  split at `u+v = 1/2 - 2 alpha`.
  The eligible side uses Lemma 2.5 lower sieve; the other side uses the
  rigorous trivial lower bound 0.
- G9:
  split at `u=1/10`; the left uses Lemma 3.5 and the right Lemma 3.1.
- G11/G12:
  split at `t1=1/10` for the same distribution-level change.

### Dynamic special functions

- F(s), f(s): numerically solve the linear-sieve delay equations by
  method of steps.
- w(u): numerically solve the Buchstab delay equation on all `u>=1`
  needed by the parameter domain.
- Therefore G11/G12 no longer reject a parameter because the Buchstab
  argument falls below 3.  The paper's original Section-5.4 formula contains
  `w(argument)`; its constants 0.561522/0.561990/0.564383 are later
  simplifications, not the domain of the function.

## Certification status

Theorem applicability is explicitly checked and recorded, but numerical
quadrature and delay-equation tables are still ordinary floating point.

Stored successes are therefore labeled:

```text
NUMERICAL_CANDIDATE_THEOREM_GUARDED_NOT_INTERVAL_CERTIFIED
```

A claimed new exponent still requires interval/high-precision certification.
