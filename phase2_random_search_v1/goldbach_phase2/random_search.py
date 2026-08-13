from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional
import math
import numpy as np

from .dynamic_bounds import DynamicParameters, PaperPathDynamicEvaluator


@dataclass
class SearchHit:
    batch_index: int
    sample_index: int
    batch_seed: int
    params: DynamicParameters
    evaluation: object

    def score(self):
        return self.evaluation.margin_4D


class RandomPaperPathSearch:
    """Randomly sample legal Proposition-4.3 parameters at fixed a=2-delta.

    Sampling is concentrated on the paper-path analytic region, not the whole
    abstract Proposition-4.3 polytope:
      alpha in (1/18, 1/12],
      beta in (alpha, 1/6),
      gamma in (max(1/4, 1/3-beta), 1/3).
    """

    def __init__(self, evaluator: PaperPathDynamicEvaluator,
                 delta: float,
                 epsilon: float = 1e-10,
                 samples_per_batch: int = 256,
                 base_seed: int = 260605224,
                 required_margin_4D: float = 1e-5):
        self.evaluator = evaluator
        self.delta = float(delta)
        self.a = 2.0 - self.delta
        self.epsilon = float(epsilon)
        self.samples_per_batch = int(samples_per_batch)
        self.base_seed = int(base_seed)
        self.required_margin_4D = float(required_margin_4D)

        if not (0.0 < self.delta < 0.5 - 3*self.epsilon):
            raise ValueError(
                "delta must satisfy 0 < delta < 0.5-3epsilon "
                "for the current Proposition-4.3 architecture."
            )

    def _sample(self, rng) -> DynamicParameters:
        # Beta must leave room for alpha<beta and beta<1/6.
        # Bias around the useful paper neighborhood while retaining global
        # support over the registered analytic region.
        alpha_lo = 1/18 + 2e-6
        alpha_hi = 1/12 - 2e-6

        # Mix 70% local-paper-biased samples with 30% uniform exploration.
        if rng.random() < 0.70:
            alpha = float(np.clip(
                rng.normal(4/53, 0.006),
                alpha_lo, alpha_hi
            ))
        else:
            alpha = float(rng.uniform(alpha_lo, alpha_hi))

        beta_lo = alpha + 2e-5
        beta_hi = 1/6 - 2e-5
        if rng.random() < 0.70:
            beta = float(np.clip(
                rng.normal(4/33, 0.012),
                beta_lo, beta_hi
            ))
        else:
            beta = float(rng.uniform(beta_lo, beta_hi))

        gamma_lo = max(1/4 + 2e-5, 1/3 - beta + 2e-5)
        gamma_hi = 1/3 - 2e-5
        if gamma_lo >= gamma_hi:
            # This is possible only for very small beta; push beta upward.
            beta = max(beta, 1/12 + 1e-4)
            gamma_lo = max(1/4 + 2e-5, 1/3 - beta + 2e-5)

        if rng.random() < 0.70:
            gamma = float(np.clip(
                rng.normal(3/11, 0.018),
                gamma_lo, gamma_hi
            ))
        else:
            gamma = float(rng.uniform(gamma_lo, gamma_hi))

        return DynamicParameters(
            a=self.a,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            epsilon=self.epsilon,
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

            hit = SearchHit(
                batch_index=batch_index,
                sample_index=sample_index,
                batch_seed=seed,
                params=p,
                evaluation=ev,
            )
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
