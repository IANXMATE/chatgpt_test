# Phase-2 Frontier Theorem Compiler V4

V3 exposed 140 rewrite allocations, but strict `unresolved=0` allowed only
6/140 to be nonzero.  V4 attacks that bottleneck directly.

## Pipeline

```text
Phase-1 NEG unresolved frontier
        |
        v
read canonical state metadata
(region, factor_count, threshold, sieve_set, analytic_oracles)
        |
        v
match theorem family
        |
        +--> generic linear-sieve upper
        |
        +--> generic switched-Buchstab upper
        |
        v
check theorem guard on the ENTIRE state region by LP
        |
        +--> mixed/invalid -> DEFER (do not fake a bound)
        |
        `--> valid -> compile the unresolved sink into a terminal
        |
        v
dynamic numerical F / w integral over the canonical polytope
        |
        v
re-open exactly those terminal variables in the 576-variable flow LP
        |
        v
recompute how many of the 140 rewrites are actually reachable
        |
        v
exact LP proof-flow optimization
```

## Current theorem families

### 1. GENERIC_LINEAR_SIEVE_UPPER

Phase-1 must mark the state:

```text
linear_sieve_candidate
sieve_set = P(N)
threshold = fixed alpha/beta/tau
```

For a state with factor exponents `u_i`, V4 checks by LP that the whole region
satisfies

```text
(1/2 - sum u_i) / rho >= 2
```

before applying the parameterized Lemma-2.5 upper integral.

### 2. GENERIC_SWITCHED_BUCHSTAB_UPPER

Phase-1 must mark:

```text
buchstab_or_switching_upper_candidate
sieve_set = P(N*p1)
threshold = factor j
```

V4 checks the whole region satisfies

```text
(1 - sum u_i) / u_j >= 1.
```

It then integrates the Section-5.4 style switched Buchstab density

```text
w((1-sum u)/u_j) / (prod(u_i) * u_j)
```

with the theorem-induced `u1=1/10` split:

```text
u1 < 1/10  -> (36/5)/(1-u1)
u1 >= 1/10 -> 8
```

## Why mixed regions are not compiled yet

If only part of a canonical region satisfies a theorem condition, V4 does NOT
clip the integral and pretend the rest disappeared.  The state is deferred.

The next compiler layer would materialize a true canonical split and route
both child cells separately.

## Paper-point regression

Run:

```bash
python main.py --paper-point --compile-only --show-compiled
```

With the packaged Phase-1 V5 files and the default
`max_factor_count=6`, the structural rewrite coverage should increase from

```text
6/140
```

to

```text
15/140
```

at the paper point.

That is the key V4 regression target.

## Exact proof-flow at paper point

```bash
python main.py --paper-point
```

## Random parameter search with compiled frontier terminals

```bash
python main.py --delta 0.105
```

The parameters are random, but for each parameter point the proof-flow
subproblem is solved exactly as a linear program.

## Frontier blocker ranking

```bash
python main.py --diagnose-frontier
```

This asks, for each currently forced-zero rewrite, which unresolved sinks are
needed when that rewrite is pushed near its feasible maximum.  It ranks the
frontier states by the number of rewrites they block.

## Numerical status

Theorem guards are explicit and checked by LP.  However, generic polytope
integrals use scrambled Sobol QMC with a positive search pad.

Therefore a saved hit is still:

```text
NUMERICAL_CANDIDATE ... NOT_INTERVAL_CERTIFIED
```

A genuinely improved exponent must later be replayed with certified interval
integration and source-level verification of every generic terminal family.
