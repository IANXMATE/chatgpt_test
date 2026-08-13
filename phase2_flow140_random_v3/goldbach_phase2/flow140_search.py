from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import numpy as np

from .theorem_aware_evaluator import Parameters, TheoremAwarePaperPathEvaluator
from .flow140 import Flow140Model, FlowSolution


@dataclass
class Flow140Hit:
    batch_index: int
    sample_index: int
    flow_trial_index: int
    parameter_seed: int
    flow_seed: int
    params: Parameters
    theorem_eval: object
    flow_solution: FlowSolution

    def score(self):
        return self.flow_solution.margin_4D_equivalent


class RandomFlow140Search:
    """Random parameter search + randomized 140-rewrite architecture search.

    For every parameter point:
      1. theorem-aware G1..G12 evaluator runs;
      2. each flow trial draws 140 random rewrite preferences;
      3. the 578-variable LP projects them onto the exact feasible flow
         polytope with all unresolved frontiers fixed to zero;
      4. score is the TRUE theorem-aware terminal margin, not the perturbed
         LP objective.
    """

    TEMPERATURES = (0.0, 0.02, 0.1, 0.5, 2.0, 10.0)

    def __init__(
        self,
        evaluator: TheoremAwarePaperPathEvaluator,
        flow_model: Flow140Model,
        delta: float,
        epsilon: float = 1e-10,
        parameter_samples_per_batch: int = 12,
        flow_trials_per_parameter: int = 16,
        base_seed: int = 260605224,
        required_margin_4D: float = 1e-5,
    ):
        self.evaluator = evaluator
        self.flow_model = flow_model
        self.delta = float(delta)
        self.a = 2.0 - self.delta
        self.epsilon = float(epsilon)
        self.parameter_samples_per_batch = int(parameter_samples_per_batch)
        self.flow_trials_per_parameter = int(flow_trials_per_parameter)
        self.base_seed = int(base_seed)
        self.required_margin_4D = float(required_margin_4D)

    def _sample_parameters(self, rng) -> Parameters:
        alpha_lo = 1/18 + 2e-5
        alpha_hi = 1/12 - 2e-5

        if rng.random() < 0.70:
            alpha = float(np.clip(rng.normal(4/53, 0.006), alpha_lo, alpha_hi))
        else:
            alpha = float(rng.uniform(alpha_lo, alpha_hi))

        beta_lo = alpha + 3e-5
        beta_hi = 1/6 - 3e-5
        if rng.random() < 0.70:
            beta = float(np.clip(rng.normal(4/33, 0.014), beta_lo, beta_hi))
        else:
            beta = float(rng.uniform(beta_lo, beta_hi))

        middle = 1/3 - beta
        gamma_lo = max(1/4 + 3e-5, middle + 3e-5)
        gamma_hi = 1/3 - 3e-5

        if rng.random() < 0.70:
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

    def run_batch(self, batch_index: int):
        parameter_seed = self.base_seed + 1_000_003 * int(batch_index)
        prng = np.random.default_rng(parameter_seed)

        best: Optional[Flow140Hit] = None
        success: Optional[Flow140Hit] = None
        theorem_valid = 0
        feasible_flow_trials = 0

        for sample_index in range(self.parameter_samples_per_batch):
            params = self._sample_parameters(prng)
            tev = self.evaluator.evaluate(params)
            if not tev.valid:
                continue
            theorem_valid += 1

            for trial in range(self.flow_trials_per_parameter):
                flow_seed = (
                    self.base_seed
                    + 1000000007 * int(batch_index)
                    + 10007 * sample_index
                    + trial
                ) & ((1 << 63) - 1)
                frng = np.random.default_rng(flow_seed)

                preference = frng.normal(
                    size=len(self.flow_model.rewrite_names)
                )
                temperature = self.TEMPERATURES[
                    trial % len(self.TEMPERATURES)
                ]

                sol = self.flow_model.solve(
                    tev,
                    preference_vector=preference,
                    preference_temperature=temperature,
                )
                if not sol.success:
                    continue
                feasible_flow_trials += 1

                hit = Flow140Hit(
                    batch_index=batch_index,
                    sample_index=sample_index,
                    flow_trial_index=trial,
                    parameter_seed=parameter_seed,
                    flow_seed=flow_seed,
                    params=params,
                    theorem_eval=tev,
                    flow_solution=sol,
                )

                if best is None or hit.score() > best.score():
                    best = hit

                if sol.margin_4D_equivalent >= self.required_margin_4D:
                    if success is None or hit.score() > success.score():
                        success = hit

        return {
            "batch_index": batch_index,
            "parameter_seed": parameter_seed,
            "parameter_samples": self.parameter_samples_per_batch,
            "theorem_valid_parameter_samples": theorem_valid,
            "flow_trials": (
                self.parameter_samples_per_batch
                * self.flow_trials_per_parameter
            ),
            "feasible_flow_trials": feasible_flow_trials,
            "best": best,
            "success": success,
        }
