from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import numpy as np

from .theorem_aware_evaluator import Parameters, TheoremAwarePaperPathEvaluator


@dataclass
class SearchHit:
    batch_index: int
    sample_index: int
    batch_seed: int
    params: Parameters
    evaluation: object

    def score(self):
        return self.evaluation.margin_4D


class RandomTheoremAwareSearch:
    def __init__(
        self,
        evaluator: TheoremAwarePaperPathEvaluator,
        delta: float,
        epsilon: float = 1e-10,
        samples_per_batch: int = 64,
        base_seed: int = 260605224,
        required_margin_4D: float = 1e-5,
    ):
        self.evaluator = evaluator
        self.delta = float(delta)
        self.a = 2.0-self.delta
        self.epsilon = float(epsilon)
        self.samples_per_batch = int(samples_per_batch)
        self.base_seed = int(base_seed)
        self.required_margin_4D = float(required_margin_4D)

    def _sample(self, rng) -> Parameters:
        # Sample within the current paper-path estimator regime:
        # alpha<1/12 and gamma>1/4. Proposition 4.3 guards are still checked
        # independently by the evaluator; sampling does not replace proof.
        alpha_lo = 1/18 + 2e-5
        alpha_hi = 1/12 - 2e-5

        if rng.random() < 0.7:
            alpha = float(np.clip(rng.normal(4/53, 0.006), alpha_lo, alpha_hi))
        else:
            alpha = float(rng.uniform(alpha_lo, alpha_hi))

        # P4.3 implies beta<1/6.
        beta_lo = alpha + 3e-5
        beta_hi = 1/6 - 3e-5
        if rng.random() < 0.7:
            beta = float(np.clip(rng.normal(4/33, 0.014), beta_lo, beta_hi))
        else:
            beta = float(rng.uniform(beta_lo, beta_hi))

        middle = 1/3 - beta
        gamma_lo = max(1/4 + 3e-5, middle + 3e-5)
        gamma_hi = 1/3 - 3e-5
        if gamma_lo >= gamma_hi:
            # Extremely unlikely after beta sampling, but keep deterministic.
            beta = max(beta, 0.09)
            middle = 1/3-beta
            gamma_lo = max(1/4+3e-5, middle+3e-5)

        if rng.random() < 0.7:
            gamma = float(np.clip(rng.normal(3/11, 0.025), gamma_lo, gamma_hi))
        else:
            gamma = float(rng.uniform(gamma_lo, gamma_hi))

        return Parameters(
            a=self.a, alpha=alpha, beta=beta, gamma=gamma,
            epsilon=self.epsilon
        )

    def run_batch(self, batch_index: int):
        seed = self.base_seed + int(batch_index)
        rng = np.random.default_rng(seed)
        best: Optional[SearchHit] = None
        success: Optional[SearchHit] = None
        valid_count = 0

        for sample_index in range(self.samples_per_batch):
            p = self._sample(rng)
            ev = self.evaluator.evaluate(p)
            if not ev.valid:
                continue
            valid_count += 1
            hit = SearchHit(batch_index, sample_index, seed, p, ev)
            if best is None or hit.score() > best.score():
                best = hit
            if ev.margin_4D >= self.required_margin_4D:
                if success is None or hit.score() > success.score():
                    success = hit

        return {
            "batch_index": batch_index,
            "batch_seed": seed,
            "samples": self.samples_per_batch,
            "valid_count": valid_count,
            "best": best,
            "success": success,
        }


# v1 compatibility alias
RandomPaperPathSearch = RandomTheoremAwareSearch
