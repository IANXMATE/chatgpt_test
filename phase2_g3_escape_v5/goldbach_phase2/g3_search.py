from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .theorem_aware_evaluator import Parameters


@dataclass
class G3TargetHit:
    batch_index: int
    sample_index: int
    seed: int
    params: Parameters
    theorem_eval: object
    compile_result: object
    baseline: object
    critical: object

    def score(self):
        if self.critical.critical_upper is None:
            return float("-inf")
        return float(self.critical.critical_upper)


class RandomG3TargetSearch:
    """Search parameter space for the easiest hypothetical G3-base theorem target."""

    def __init__(
        self,
        evaluator,
        compiler,
        analyzer,
        delta: float,
        epsilon: float = 1e-10,
        samples_per_batch: int = 24,
        base_seed: int = 260605224,
        target_margin_4D: float = 0.0,
        upper_cap: float = 5.0,
    ):
        self.evaluator = evaluator
        self.compiler = compiler
        self.analyzer = analyzer
        self.delta = float(delta)
        self.a = 2.0 - self.delta
        self.epsilon = float(epsilon)
        self.samples_per_batch = int(samples_per_batch)
        self.base_seed = int(base_seed)
        self.target_margin_4D = float(target_margin_4D)
        self.upper_cap = float(upper_cap)

    def _sample(self, rng):
        alpha_lo = 1/18 + 2e-5
        alpha_hi = 1/12 - 2e-5

        if rng.random() < 0.75:
            alpha = float(np.clip(rng.normal(4/53, 0.006), alpha_lo, alpha_hi))
        else:
            alpha = float(rng.uniform(alpha_lo, alpha_hi))

        beta_lo = alpha + 3e-5
        beta_hi = 1/6 - 3e-5
        if rng.random() < 0.75:
            beta = float(np.clip(rng.normal(4/33, 0.014), beta_lo, beta_hi))
        else:
            beta = float(rng.uniform(beta_lo, beta_hi))

        middle = 1/3 - beta
        gamma_lo = max(1/4 + 3e-5, middle + 3e-5)
        gamma_hi = 1/3 - 3e-5

        if rng.random() < 0.75:
            gamma = float(np.clip(rng.normal(3/11, 0.025), gamma_lo, gamma_hi))
        else:
            gamma = float(rng.uniform(gamma_lo, gamma_hi))

        return Parameters(
            a=self.a,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            epsilon=self.epsilon,
        )

    def run_batch(self, batch_index):
        seed = self.base_seed + 1000003 * int(batch_index)
        rng = np.random.default_rng(seed)

        best: Optional[G3TargetHit] = None
        valid = 0
        escape_feasible_at_zero = 0

        for sample_index in range(self.samples_per_batch):
            p = self._sample(rng)
            tev = self.evaluator.evaluate(p)
            if not tev.valid:
                continue
            valid += 1

            cres = self.compiler.compile(p)
            baseline = self.analyzer.baseline(tev, cres.terminals)
            critical = self.analyzer.critical_base_upper(
                tev,
                cres.terminals,
                target_margin_4D=self.target_margin_4D,
                upper_search_cap=self.upper_cap,
            )
            if critical.feasible_with_zero_bound:
                escape_feasible_at_zero += 1

            hit = G3TargetHit(
                batch_index=batch_index,
                sample_index=sample_index,
                seed=seed,
                params=p,
                theorem_eval=tev,
                compile_result=cres,
                baseline=baseline,
                critical=critical,
            )
            if best is None or hit.score() > best.score():
                best = hit

        return {
            "batch_index": batch_index,
            "seed": seed,
            "samples": self.samples_per_batch,
            "valid": valid,
            "escape_feasible_at_zero": escape_feasible_at_zero,
            "best": best,
        }
