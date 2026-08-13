# Phase-1 depth exploration report

## Parameter point

- `a` = `1.9`
- `alpha` = `0.0754716981132`
- `beta` = `0.121212121212`
- `gamma` = `0.272727272727`
- `epsilon` = `1e-12`
- `tau` = `0.473684210525`

## Source certificate

\[
4D \ge 3G_1+G_2-4G_3-G_4-G_5+G_6+G_7-2G_8-G_9-G_{10}-G_{11}-G_{12}+\mathrm{error}.
\]

Source: Proposition 4.3, equation (4.18), arXiv:2606.05224v2.

## Exact paper rewrite chain

### Step 1: `combine_two_weighted_inequalities`
- source: `(4.19)+(4.20)->(4.21)`
- relation: `inequality`
- output: `4D >= 2G1+2G2-4G3-G4-2G8-G9-S3(beta,gamma)-S5(beta,gamma)+S6(alpha,1/3)+error`
- note: S4(1/3)=0
- note: S6(beta,gamma) dropped by non-negativity

### Step 2: `expand_G2`
- source: `(4.22)-(4.23)`
- relation: `identity_up_to_error`
- output: `G2 = G1 - G13 + G6 - G14 + error`

### Step 3: `expand_S3`
- source: `(4.25)-(4.26)`
- relation: `identity_up_to_error`
- output: `S3(beta,gamma) = G5 - G13 - G7 + G15 + error`

### Step 4: `cancel_G13`
- source: `(4.24)-(4.27)`
- relation: `algebraic_cancellation`
- output: `G13 cancels, producing the next certificate state`

### Step 5: `expand_S5`
- source: `(4.28)-(4.29)`
- relation: `identity_up_to_error`
- output: `S5(beta,gamma) = G10 + G16 + error`

### Step 6: `final_domination_target`
- source: `(4.30)-(4.31)`
- relation: `inequality`
- output: `S6(alpha,1/3) >= G14+G15+G16-G11-G12`

### Step 7: `G14_minus_G11`
- source: `(4.32)`
- relation: `buchstab_identity_up_to_error`
- output: `G14-G11 becomes a restricted nonnegative 3-factor state`

### Step 8: `G15_minus_G12`
- source: `(4.33)`
- relation: `buchstab_identity_up_to_error`
- output: `G15-G12 becomes a restricted nonnegative 3-factor state`

### Step 9: `dominate_G16`
- source: `(4.34)`
- relation: `upper_domination`
- output: `G16 is bounded by a larger 3-factor state`

### Step 10: `split_S6`
- source: `(4.35)-(4.36)`
- relation: `partition_and_region_domination`
- output: `S6 split covers the three positive states above`

### Step 11: `final_certificate`
- source: `(4.18)`
- relation: `inequality`
- output: `4D >= 3G1+G2-4G3-G4-G5+G6+G7-2G8-G9-G10-G11-G12+error`

## Root-by-root exploration

### G1

- certificate coefficient: `+3`
- source equation: `(4.18)`
- root factor depth: `0`
- crude structural maximum factor depth: `0`
- root threshold: `N^alpha`
- anchor: `None`
- candidate analytic oracles: `linear_sieve_lower`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G1` | +3 | 0 | 0 | root | `N^alpha` | paper_exact |

### G2

- certificate coefficient: `+1`
- source equation: `(4.22)-(4.23)`
- root factor depth: `0`
- crude structural maximum factor depth: `13`
- root threshold: `N^beta`
- anchor: `N^alpha`
- candidate analytic oracles: `linear_sieve_lower, buchstab_expand`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G2` | +1 | 0 | 0 | root | `N^beta` | paper_exact |
| `G2.paper.G1` | +1 | 0 | 1 | paper_alias_G1 | `N^alpha` | paper_exact |
| `G2.paper.G13` | -1 | 1 | 1 | paper_G13 | `N^alpha` | paper_exact |
| `G2.paper.G14` | -1 | 3 | 1 | paper_G14 | `p1` | paper_exact |
| `G2.paper.G6` | +1 | 2 | 1 | paper_alias_G6 | `N^alpha` | paper_exact |

### G3

- certificate coefficient: `-4`
- source equation: `definition in (4.18)`
- root factor depth: `1`
- crude structural maximum factor depth: `2`
- root threshold: `p1`
- anchor: `N^tau`
- candidate analytic oracles: `switching_upper, buchstab_expand`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G3` | -4 | 1 | 0 | root | `p1` | paper_exact |
| `G3.B` | -4 | 1 | 1 | base_lowered_threshold | `N^tau` | identity_exact |
| `G3.C` | +4 | 2 | 1 | buchstab_correction | `q_new` | identity_exact |

### G4

- certificate coefficient: `-1`
- source equation: `definition in (4.18)`
- root factor depth: `1`
- crude structural maximum factor depth: `1`
- root threshold: `N^alpha`
- anchor: `None`
- candidate analytic oracles: `linear_sieve_upper`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G4` | -1 | 1 | 0 | root | `N^alpha` | paper_exact |

### G5

- certificate coefficient: `-1`
- source equation: `definition in (4.18)`
- root factor depth: `1`
- crude structural maximum factor depth: `1`
- root threshold: `N^alpha`
- anchor: `None`
- candidate analytic oracles: `linear_sieve_upper`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G5` | -1 | 1 | 0 | root | `N^alpha` | paper_exact |

### G6

- certificate coefficient: `+1`
- source equation: `definition in (4.18)`
- root factor depth: `2`
- crude structural maximum factor depth: `2`
- root threshold: `N^alpha`
- anchor: `None`
- candidate analytic oracles: `linear_sieve_lower`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G6` | +1 | 2 | 0 | root | `N^alpha` | paper_exact |

### G7

- certificate coefficient: `+1`
- source equation: `definition in (4.18)`
- root factor depth: `2`
- crude structural maximum factor depth: `2`
- root threshold: `N^alpha`
- anchor: `None`
- candidate analytic oracles: `linear_sieve_lower`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G7` | +1 | 2 | 0 | root | `N^alpha` | paper_exact |

### G8

- certificate coefficient: `-2`
- source equation: `definition in (4.18)`
- root factor depth: `2`
- crude structural maximum factor depth: `3`
- root threshold: `p2`
- anchor: `p1`
- candidate analytic oracles: `switching_upper, buchstab_expand`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G8` | -2 | 2 | 0 | root | `p2` | paper_exact |
| `G8.B` | -2 | 2 | 1 | base_lowered_threshold | `p1` | identity_exact |
| `G8.C` | +2 | 3 | 1 | buchstab_correction | `q_new` | identity_exact |

### G9

- certificate coefficient: `-1`
- source equation: `definition in (4.18)`
- root factor depth: `2`
- crude structural maximum factor depth: `9`
- root threshold: `p2`
- anchor: `p1`
- candidate analytic oracles: `switching_upper, piecewise_distribution_upper, buchstab_expand`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G9` | -1 | 2 | 0 | root | `p2` | paper_exact |
| `G9.B` | -1 | 2 | 1 | base_lowered_threshold | `p1` | identity_exact |
| `G9.C` | +1 | 3 | 1 | buchstab_correction | `q_new` | identity_exact |
| `G9.C.B` | +1 | 3 | 2 | base_lowered_threshold | `p1` | identity_exact |
| `G9.C.C` | -1 | 4 | 2 | buchstab_correction | `q_new` | identity_exact |
| `G9.C.C.B` | -1 | 4 | 3 | base_lowered_threshold | `p1` | identity_exact |
| `G9.C.C.C` | +1 | 5 | 3 | buchstab_correction | `q_new` | identity_exact |
| `G9.C.C.C.B` | +1 | 5 | 4 | base_lowered_threshold | `p1` | identity_exact |
| `G9.C.C.C.C` | -1 | 6 | 4 | buchstab_correction | `q_new` | identity_exact |
| `G9.C.C.C.C.B` | -1 | 6 | 5 | base_lowered_threshold | `p1` | identity_exact |
| `G9.C.C.C.C.C` | +1 | 7 | 5 | buchstab_correction | `q_new` | identity_exact |
| `G9.C.C.C.C.C.B` | +1 | 7 | 6 | base_lowered_threshold | `p1` | identity_exact |
| `G9.C.C.C.C.C.C` | -1 | 8 | 6 | buchstab_correction | `q_new` | identity_exact |
| `G9.C.C.C.C.C.C.B` | -1 | 8 | 7 | base_lowered_threshold | `p1` | identity_exact |
| `G9.C.C.C.C.C.C.C` | +1 | 9 | 7 | buchstab_correction | `q_new` | identity_exact |

### G10

- certificate coefficient: `-1`
- source equation: `definition in (4.18)`
- root factor depth: `2`
- crude structural maximum factor depth: `4`
- root threshold: `sqrt(N/(p1*p2))`
- anchor: `p2`
- candidate analytic oracles: `switching_upper, buchstab_expand`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G10` | -1 | 2 | 0 | root | `sqrt(N/(p1*p2))` | paper_exact |
| `G10.B` | -1 | 2 | 1 | base_lowered_threshold | `p2` | identity_exact |
| `G10.C` | +1 | 3 | 1 | buchstab_correction | `q_new` | identity_exact |
| `G10.C.B` | +1 | 3 | 2 | base_lowered_threshold | `p2` | identity_exact |
| `G10.C.C` | -1 | 4 | 2 | buchstab_correction | `q_new` | identity_exact |

### G11

- certificate coefficient: `-1`
- source equation: `definition in (4.18), §5.4`
- root factor depth: `4`
- crude structural maximum factor depth: `13`
- root threshold: `p2`
- anchor: `p1`
- candidate analytic oracles: `buchstab_function_upper, buchstab_expand`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G11` | -1 | 4 | 0 | root | `p2` | paper_exact |
| `G11.B` | -1 | 4 | 1 | base_lowered_threshold | `p1` | identity_exact |
| `G11.C` | +1 | 5 | 1 | buchstab_correction | `q_new` | identity_exact |
| `G11.C.B` | +1 | 5 | 2 | base_lowered_threshold | `p1` | identity_exact |
| `G11.C.C` | -1 | 6 | 2 | buchstab_correction | `q_new` | identity_exact |
| `G11.C.C.B` | -1 | 6 | 3 | base_lowered_threshold | `p1` | identity_exact |
| `G11.C.C.C` | +1 | 7 | 3 | buchstab_correction | `q_new` | identity_exact |
| `G11.C.C.C.B` | +1 | 7 | 4 | base_lowered_threshold | `p1` | identity_exact |
| `G11.C.C.C.C` | -1 | 8 | 4 | buchstab_correction | `q_new` | identity_exact |
| `G11.C.C.C.C.B` | -1 | 8 | 5 | base_lowered_threshold | `p1` | identity_exact |
| `G11.C.C.C.C.C` | +1 | 9 | 5 | buchstab_correction | `q_new` | identity_exact |
| `G11.C.C.C.C.C.B` | +1 | 9 | 6 | base_lowered_threshold | `p1` | identity_exact |
| `G11.C.C.C.C.C.C` | -1 | 10 | 6 | buchstab_correction | `q_new` | identity_exact |
| `G11.C.C.C.C.C.C.B` | -1 | 10 | 7 | base_lowered_threshold | `p1` | identity_exact |
| `G11.C.C.C.C.C.C.C` | +1 | 11 | 7 | buchstab_correction | `q_new` | identity_exact |
| `G11.C.C.C.C.C.C.C.B` | +1 | 11 | 8 | base_lowered_threshold | `p1` | identity_exact |
| `G11.C.C.C.C.C.C.C.C` | -1 | 12 | 8 | buchstab_correction | `q_new` | identity_exact |
| `G11.C.C.C.C.C.C.C.C.B` | -1 | 12 | 9 | base_lowered_threshold | `p1` | identity_exact |
| `G11.C.C.C.C.C.C.C.C.C` | +1 | 13 | 9 | buchstab_correction | `q_new` | identity_exact |

### G12

- certificate coefficient: `-1`
- source equation: `definition in (4.18), §5.4`
- root factor depth: `4`
- crude structural maximum factor depth: `12`
- root threshold: `p2`
- anchor: `p1`
- candidate analytic oracles: `buchstab_function_upper, buchstab_expand`

| node | coeff | factors | rule-depth | branch | threshold | status |
|---|---:|---:|---:|---|---|---|
| `G12` | -1 | 4 | 0 | root | `p2` | paper_exact |
| `G12.B` | -1 | 4 | 1 | base_lowered_threshold | `p1` | identity_exact |
| `G12.C` | +1 | 5 | 1 | buchstab_correction | `q_new` | identity_exact |
| `G12.C.B` | +1 | 5 | 2 | base_lowered_threshold | `p1` | identity_exact |
| `G12.C.C` | -1 | 6 | 2 | buchstab_correction | `q_new` | identity_exact |
| `G12.C.C.B` | -1 | 6 | 3 | base_lowered_threshold | `p1` | identity_exact |
| `G12.C.C.C` | +1 | 7 | 3 | buchstab_correction | `q_new` | identity_exact |
| `G12.C.C.C.B` | +1 | 7 | 4 | base_lowered_threshold | `p1` | identity_exact |
| `G12.C.C.C.C` | -1 | 8 | 4 | buchstab_correction | `q_new` | identity_exact |
| `G12.C.C.C.C.B` | -1 | 8 | 5 | base_lowered_threshold | `p1` | identity_exact |
| `G12.C.C.C.C.C` | +1 | 9 | 5 | buchstab_correction | `q_new` | identity_exact |
| `G12.C.C.C.C.C.B` | +1 | 9 | 6 | base_lowered_threshold | `p1` | identity_exact |
| `G12.C.C.C.C.C.C` | -1 | 10 | 6 | buchstab_correction | `q_new` | identity_exact |
| `G12.C.C.C.C.C.C.B` | -1 | 10 | 7 | base_lowered_threshold | `p1` | identity_exact |
| `G12.C.C.C.C.C.C.C` | +1 | 11 | 7 | buchstab_correction | `q_new` | identity_exact |
| `G12.C.C.C.C.C.C.C.B` | +1 | 11 | 8 | base_lowered_threshold | `p1` | identity_exact |
| `G12.C.C.C.C.C.C.C.C` | -1 | 12 | 8 | buchstab_correction | `q_new` | identity_exact |

## Terminal leaves for stage 2

Each leaf is a candidate terminal estimator state. Stage 2 may instead stop at a shallower ancestor by introducing binary branch variables.

### `G1`
- root: `G1`
- coefficient: `+3`
- factor dimension: `0`
- minimum exponent-sum diagnostic: `0`
- region: `sift threshold = alpha`
- sieve set: `P(N)`
- threshold: `N^alpha`
- proof status: `paper_exact`
- candidate oracles: `linear_sieve_lower`
- note: Paper-compatible exploration does not go below alpha.

### `G10.B`
- root: `G10`
- coefficient: `-1`
- factor dimension: `2`
- minimum exponent-sum diagnostic: `0.393939393939`
- region: `beta <= u1 <= gamma <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `p2`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, buchstab_expand`
- note: Threshold lowered from sqrt(N/(p1*p2)) to p2.
- note: STOP candidate under current paper-compatible cutoff.

### `G10.C.B`
- root: `G10`
- coefficient: `+1`
- factor dimension: `3`
- minimum exponent-sum diagnostic: `0.666666666667`
- region: `beta <= u1 <= gamma <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `p2`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, buchstab_expand`
- note: Threshold lowered from q_new to p2.
- note: STOP candidate under current paper-compatible cutoff.

### `G10.C.C`
- root: `G10`
- coefficient: `-1`
- factor dimension: `4`
- minimum exponent-sum diagnostic: `0.939393939394`
- region: `beta <= u1 <= gamma <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `q_new`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, buchstab_expand`
- note: New factor q is constrained between anchor p2 and old threshold q_new.
- note: Coefficient sign flips.
- note: Stage 2 must reconstruct the full ordered region constraints.

### `G11.B`
- root: `G11`
- coefficient: `-1`
- factor dimension: `4`
- minimum exponent-sum diagnostic: `0.301886792453`
- region: `alpha <= u1 <= u2 <= u3 <= u4 <= beta`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from p2 to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G11.C.B`
- root: `G11`
- coefficient: `+1`
- factor dimension: `5`
- minimum exponent-sum diagnostic: `0.377358490566`
- region: `alpha <= u1 <= u2 <= u3 <= u4 <= beta`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G11.C.C.B`
- root: `G11`
- coefficient: `-1`
- factor dimension: `6`
- minimum exponent-sum diagnostic: `0.452830188679`
- region: `alpha <= u1 <= u2 <= u3 <= u4 <= beta`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G11.C.C.C.B`
- root: `G11`
- coefficient: `+1`
- factor dimension: `7`
- minimum exponent-sum diagnostic: `0.528301886792`
- region: `alpha <= u1 <= u2 <= u3 <= u4 <= beta`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G11.C.C.C.C.B`
- root: `G11`
- coefficient: `-1`
- factor dimension: `8`
- minimum exponent-sum diagnostic: `0.603773584906`
- region: `alpha <= u1 <= u2 <= u3 <= u4 <= beta`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G11.C.C.C.C.C.B`
- root: `G11`
- coefficient: `+1`
- factor dimension: `9`
- minimum exponent-sum diagnostic: `0.679245283019`
- region: `alpha <= u1 <= u2 <= u3 <= u4 <= beta`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G11.C.C.C.C.C.C.B`
- root: `G11`
- coefficient: `-1`
- factor dimension: `10`
- minimum exponent-sum diagnostic: `0.754716981132`
- region: `alpha <= u1 <= u2 <= u3 <= u4 <= beta`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G11.C.C.C.C.C.C.C.B`
- root: `G11`
- coefficient: `+1`
- factor dimension: `11`
- minimum exponent-sum diagnostic: `0.830188679245`
- region: `alpha <= u1 <= u2 <= u3 <= u4 <= beta`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G11.C.C.C.C.C.C.C.C.B`
- root: `G11`
- coefficient: `-1`
- factor dimension: `12`
- minimum exponent-sum diagnostic: `0.905660377358`
- region: `alpha <= u1 <= u2 <= u3 <= u4 <= beta`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G11.C.C.C.C.C.C.C.C.C`
- root: `G11`
- coefficient: `+1`
- factor dimension: `13`
- minimum exponent-sum diagnostic: `0.981132075472`
- region: `alpha <= u1 <= u2 <= u3 <= u4 <= beta`
- sieve set: `P(N*p1)`
- threshold: `q_new`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: New factor q is constrained between anchor p1 and old threshold q_new.
- note: Coefficient sign flips.
- note: Stage 2 must reconstruct the full ordered region constraints.

### `G12.B`
- root: `G12`
- coefficient: `-1`
- factor dimension: `4`
- minimum exponent-sum diagnostic: `0.347627215552`
- region: `alpha <= u1 <= u2 <= u3 <= beta <= u4 <= gamma`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from p2 to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G12.C.B`
- root: `G12`
- coefficient: `+1`
- factor dimension: `5`
- minimum exponent-sum diagnostic: `0.423098913665`
- region: `alpha <= u1 <= u2 <= u3 <= beta <= u4 <= gamma`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G12.C.C.B`
- root: `G12`
- coefficient: `-1`
- factor dimension: `6`
- minimum exponent-sum diagnostic: `0.498570611778`
- region: `alpha <= u1 <= u2 <= u3 <= beta <= u4 <= gamma`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G12.C.C.C.B`
- root: `G12`
- coefficient: `+1`
- factor dimension: `7`
- minimum exponent-sum diagnostic: `0.574042309891`
- region: `alpha <= u1 <= u2 <= u3 <= beta <= u4 <= gamma`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G12.C.C.C.C.B`
- root: `G12`
- coefficient: `-1`
- factor dimension: `8`
- minimum exponent-sum diagnostic: `0.649514008005`
- region: `alpha <= u1 <= u2 <= u3 <= beta <= u4 <= gamma`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G12.C.C.C.C.C.B`
- root: `G12`
- coefficient: `+1`
- factor dimension: `9`
- minimum exponent-sum diagnostic: `0.724985706118`
- region: `alpha <= u1 <= u2 <= u3 <= beta <= u4 <= gamma`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G12.C.C.C.C.C.C.B`
- root: `G12`
- coefficient: `-1`
- factor dimension: `10`
- minimum exponent-sum diagnostic: `0.800457404231`
- region: `alpha <= u1 <= u2 <= u3 <= beta <= u4 <= gamma`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G12.C.C.C.C.C.C.C.B`
- root: `G12`
- coefficient: `+1`
- factor dimension: `11`
- minimum exponent-sum diagnostic: `0.875929102344`
- region: `alpha <= u1 <= u2 <= u3 <= beta <= u4 <= gamma`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G12.C.C.C.C.C.C.C.C`
- root: `G12`
- coefficient: `-1`
- factor dimension: `12`
- minimum exponent-sum diagnostic: `0.951400800457`
- region: `alpha <= u1 <= u2 <= u3 <= beta <= u4 <= gamma`
- sieve set: `P(N*p1)`
- threshold: `q_new`
- proof status: `identity_exact`
- candidate oracles: `buchstab_function_upper, buchstab_expand`
- note: New factor q is constrained between anchor p1 and old threshold q_new.
- note: Coefficient sign flips.
- note: Stage 2 must reconstruct the full ordered region constraints.

### `G2.paper.G1`
- root: `G2`
- coefficient: `+1`
- factor dimension: `0`
- minimum exponent-sum diagnostic: `0`
- region: `sift threshold = beta`
- sieve set: `P(N)`
- threshold: `N^alpha`
- proof status: `paper_exact`
- candidate oracles: `linear_sieve_lower, buchstab_expand`
- note: Exact term from equations (4.22)-(4.23).
- note: v1 stops at G14; further continuation needs the P(N) / P(N*p1) rewrite formalized.

### `G2.paper.G13`
- root: `G2`
- coefficient: `-1`
- factor dimension: `1`
- minimum exponent-sum diagnostic: `0.0754716981132`
- region: `sift threshold = beta`
- sieve set: `P(N)`
- threshold: `N^alpha`
- proof status: `paper_exact`
- candidate oracles: `linear_sieve_lower, buchstab_expand`
- note: Exact term from equations (4.22)-(4.23).
- note: v1 stops at G14; further continuation needs the P(N) / P(N*p1) rewrite formalized.

### `G2.paper.G14`
- root: `G2`
- coefficient: `-1`
- factor dimension: `3`
- minimum exponent-sum diagnostic: `0.22641509434`
- region: `sift threshold = beta`
- sieve set: `P(N)`
- threshold: `p1`
- proof status: `paper_exact`
- candidate oracles: `linear_sieve_lower, buchstab_expand`
- note: Exact term from equations (4.22)-(4.23).
- note: v1 stops at G14; further continuation needs the P(N) / P(N*p1) rewrite formalized.

### `G2.paper.G6`
- root: `G2`
- coefficient: `+1`
- factor dimension: `2`
- minimum exponent-sum diagnostic: `0.150943396226`
- region: `sift threshold = beta`
- sieve set: `P(N)`
- threshold: `N^alpha`
- proof status: `paper_exact`
- candidate oracles: `linear_sieve_lower, buchstab_expand`
- note: Exact term from equations (4.22)-(4.23).
- note: v1 stops at G14; further continuation needs the P(N) / P(N*p1) rewrite formalized.

### `G3.B`
- root: `G3`
- coefficient: `-4`
- factor dimension: `1`
- minimum exponent-sum diagnostic: `0.473684210525`
- region: `tau <= u1 <= 1/2`
- sieve set: `P(N)`
- threshold: `N^tau`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, buchstab_expand`
- note: Threshold lowered from p1 to N^tau.
- note: STOP candidate under current paper-compatible cutoff.

### `G3.C`
- root: `G3`
- coefficient: `+4`
- factor dimension: `2`
- minimum exponent-sum diagnostic: `0.947368421051`
- region: `tau <= u1 <= 1/2`
- sieve set: `P(N)`
- threshold: `q_new`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, buchstab_expand`
- note: New factor q is constrained between anchor N^tau and old threshold p1.
- note: Coefficient sign flips.
- note: Stage 2 must reconstruct the full ordered region constraints.

### `G4`
- root: `G4`
- coefficient: `-1`
- factor dimension: `1`
- minimum exponent-sum diagnostic: `0.0754716981132`
- region: `alpha <= u1 <= 1/3`
- sieve set: `P(N)`
- threshold: `N^alpha`
- proof status: `paper_exact`
- candidate oracles: `linear_sieve_upper`

### `G5`
- root: `G5`
- coefficient: `-1`
- factor dimension: `1`
- minimum exponent-sum diagnostic: `0.0754716981132`
- region: `alpha <= u1 <= gamma`
- sieve set: `P(N)`
- threshold: `N^alpha`
- proof status: `paper_exact`
- candidate oracles: `linear_sieve_upper`

### `G6`
- root: `G6`
- coefficient: `+1`
- factor dimension: `2`
- minimum exponent-sum diagnostic: `0.150943396226`
- region: `alpha <= u1 <= u2 <= beta`
- sieve set: `P(N)`
- threshold: `N^alpha`
- proof status: `paper_exact`
- candidate oracles: `linear_sieve_lower`

### `G7`
- root: `G7`
- coefficient: `+1`
- factor dimension: `2`
- minimum exponent-sum diagnostic: `0.196683819325`
- region: `alpha <= u1 <= beta <= u2 <= gamma`
- sieve set: `P(N)`
- threshold: `N^alpha`
- proof status: `paper_exact`
- candidate oracles: `linear_sieve_lower`

### `G8.B`
- root: `G8`
- coefficient: `-2`
- factor dimension: `2`
- minimum exponent-sum diagnostic: `0.545454545455`
- region: `gamma <= u1 <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, buchstab_expand`
- note: Threshold lowered from p2 to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G8.C`
- root: `G8`
- coefficient: `+2`
- factor dimension: `3`
- minimum exponent-sum diagnostic: `0.818181818182`
- region: `gamma <= u1 <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `q_new`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, buchstab_expand`
- note: New factor q is constrained between anchor p1 and old threshold p2.
- note: Coefficient sign flips.
- note: Stage 2 must reconstruct the full ordered region constraints.

### `G9.B`
- root: `G9`
- coefficient: `-1`
- factor dimension: `2`
- minimum exponent-sum diagnostic: `0.408805031447`
- region: `alpha <= u1 <= 1/3 <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, piecewise_distribution_upper, buchstab_expand`
- note: Threshold lowered from p2 to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G9.C.B`
- root: `G9`
- coefficient: `+1`
- factor dimension: `3`
- minimum exponent-sum diagnostic: `0.48427672956`
- region: `alpha <= u1 <= 1/3 <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, piecewise_distribution_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G9.C.C.B`
- root: `G9`
- coefficient: `-1`
- factor dimension: `4`
- minimum exponent-sum diagnostic: `0.559748427673`
- region: `alpha <= u1 <= 1/3 <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, piecewise_distribution_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G9.C.C.C.B`
- root: `G9`
- coefficient: `+1`
- factor dimension: `5`
- minimum exponent-sum diagnostic: `0.635220125786`
- region: `alpha <= u1 <= 1/3 <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, piecewise_distribution_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G9.C.C.C.C.B`
- root: `G9`
- coefficient: `-1`
- factor dimension: `6`
- minimum exponent-sum diagnostic: `0.710691823899`
- region: `alpha <= u1 <= 1/3 <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, piecewise_distribution_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G9.C.C.C.C.C.B`
- root: `G9`
- coefficient: `+1`
- factor dimension: `7`
- minimum exponent-sum diagnostic: `0.786163522013`
- region: `alpha <= u1 <= 1/3 <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, piecewise_distribution_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G9.C.C.C.C.C.C.B`
- root: `G9`
- coefficient: `-1`
- factor dimension: `8`
- minimum exponent-sum diagnostic: `0.861635220126`
- region: `alpha <= u1 <= 1/3 <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `p1`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, piecewise_distribution_upper, buchstab_expand`
- note: Threshold lowered from q_new to p1.
- note: STOP candidate under current paper-compatible cutoff.

### `G9.C.C.C.C.C.C.C`
- root: `G9`
- coefficient: `+1`
- factor dimension: `9`
- minimum exponent-sum diagnostic: `0.937106918239`
- region: `alpha <= u1 <= 1/3 <= u2; 2*u2 + u1 <= 1`
- sieve set: `P(N*p1)`
- threshold: `q_new`
- proof status: `identity_exact`
- candidate oracles: `switching_upper, piecewise_distribution_upper, buchstab_expand`
- note: New factor q is constrained between anchor p1 and old threshold q_new.
- note: Coefficient sign flips.
- note: Stage 2 must reconstruct the full ordered region constraints.

## Stage-2 reconstruction contract

Read `optimizer_manifest.json`. For any ancestor with outgoing edges, introduce a STOP/EXPAND binary choice. EXPAND activates the edge identity and its children. STOP activates one certified terminal bound. Preserve edge coefficient multipliers exactly.

This explorer never invents an analytic estimate. Unknown oracles must be supplied or proved before stage 2 may use them.
