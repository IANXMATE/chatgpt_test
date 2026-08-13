# Phase-1 proof-space exploration

## What this file means

This is the complete Stage-1 structural manifest. It does not optimize parameters and it does not invent analytic bounds. It enumerates all states reachable by the registered exact Buchstab grammar over the whole Proposition 4.3 linear parameter domain, then records every possible named region split and every known terminal estimator.

## Root certificate

\[4D\ge 3G_1+G_2-4G_3-G_4-G_5+G_6+G_7-2G_8-G_9-G_{10}-G_{11}-G_{12}+O(N^{1-\alpha}).\]

## Depth map

| root | reachable canonical states | max factor depth | rule depth |
|---|---:|---:|---:|
| G1 | 1 | 0 | 0 |
| G2 | 36 | 17 | 18 |
| G3 | 4 | 2 | 2 |
| G4 | 1 | 1 | 0 |
| G5 | 1 | 1 | 0 |
| G6 | 1 | 2 | 0 |
| G7 | 1 | 2 | 0 |
| G8 | 8 | 5 | 4 |
| G9 | 22 | 12 | 11 |
| G10 | 8 | 5 | 4 |
| G11 | 28 | 17 | 14 |
| G12 | 28 | 17 | 14 |

## Search-space counts

- canonical states: **137**
- exact Buchstab transitions: **67**
- candidate region splits: **6684**
- collision/cancellation groups: **5**
- full-expand canonical leaves: **70**

## Collision groups

### `S_27cd3a9e8b68ef`
- aliases: `['G1']`
- incoming contexts: `1`

### `S_5383a71c09b61c`
- aliases: `['G6']`
- incoming contexts: `1`

### `S_306d2030a98fc2`
- aliases: `['G16_expected_3factor_shape']`
- incoming contexts: `1`

### `S_1e8fccac91d3f6`
- aliases: `['G13']`
- incoming contexts: `1`

### `S_05a4a9cb1ade47`
- aliases: `['G14']`
- incoming contexts: `1`

## Special paper rewrite

The compiler retains equations (4.31)-(4.36) as an additional legal multi-state rewrite. It is not conflated with ordinary single-state Buchstab expansion.

## Stage-2 contract

Read `stage2_blueprint.json`. Every expandable state receives a STOP/EXPAND binary variable; every terminal estimator receives an estimator-choice binary; every meaningful named cut receives a region-split binary. Identical canonical states share one state ID, so coefficients must be aggregated before evaluating the final margin.

## Safety boundary

A structural path being present here does **not** imply that it has a useful certified upper/lower bound. Leaves tagged `high_dimensional_terminal_needs_certification` are exactly where Stage 2 or new number theory must supply one.
