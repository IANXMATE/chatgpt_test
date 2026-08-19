from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import numpy as np

from .theorem_aware_evaluator import Parameters
from .compiled_flow import CompiledFlow140Model


@dataclass
class FrontierHit:
    batch_index: int
    sample_index: int
    parameter_seed: int
    params: Parameters
    theorem_eval: object
    compile_result: object
    flow_solution: object
    reachable_rewrite_count: int

    def score(self):
        return self.flow_solution.margin_4D_equivalent


class RandomFrontierCompiledSearch:
    """Random parameter search; flow subproblem is solved exactly by LP."""

    def __init__(
        self,
        evaluator,
        compiler,
        flow_blueprint,
        delta: float,
        epsilon: float = 1e-10,
        parameter_samples_per_batch: int = 4,
        base_seed: int = 260605224,
        required_margin_4D: float = 1e-5,
    ):
        self.evaluator = evaluator
        self.compiler = compiler
        self.flow = flow_blueprint
        self.delta = float(delta)
        self.a = 2.0 - self.delta
        self.epsilon = float(epsilon)
        self.parameter_samples_per_batch = int(parameter_samples_per_batch)
        self.base_seed = int(base_seed)
        self.required_margin_4D = float(required_margin_4D)

    def _sample_parameters(self, rng) -> Parameters:
        alpha_lo = 1/18 + 2e-5
        alpha_hi = 1/12 - 2e-5

        if rng.random() < 0.72:
            alpha = float(np.clip(rng.normal(4/53, 0.006), alpha_lo, alpha_hi))
        else:
            alpha = float(rng.uniform(alpha_lo, alpha_hi))

        beta_lo = alpha + 3e-5
        beta_hi = 1/6 - 3e-5
        if rng.random() < 0.72:
            beta = float(np.clip(rng.normal(4/33, 0.014), beta_lo, beta_hi))
        else:
            beta = float(rng.uniform(beta_lo, beta_hi))

        middle = 1/3 - beta
        gamma_lo = max(1/4 + 3e-5, middle + 3e-5)
        gamma_hi = 1/3 - 3e-5

        if rng.random() < 0.72:
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
        seed = self.base_seed + 1000003 * int(batch_index)
        rng = np.random.default_rng(seed)

        best: Optional[FrontierHit] = None
        success: Optional[FrontierHit] = None
        theorem_valid = 0
        compiled_flow_feasible = 0

        for sample_index in range(self.parameter_samples_per_batch):
            p = self._sample_parameters(rng)
            tev = self.evaluator.evaluate(p)
            if not tev.valid:
                continue
            theorem_valid += 1

            cres = self.compiler.compile(p)
            cmodel = CompiledFlow140Model(
                self.flow,
                cres.terminals,
                allow_g16_paper_bridge=True,
            )
            reachable, _ = cmodel.certifiably_reachable_rewrites()

            # Fixed-parameter proof-flow optimization is linear, so solve it
            # exactly rather than wasting time randomly sampling 140 flows.
            sol = cmodel.solve(tev)
            if not sol.success:
                continue
            compiled_flow_feasible += 1

            hit = FrontierHit(
                batch_index=batch_index,
                sample_index=sample_index,
                parameter_seed=seed,
                params=p,
                theorem_eval=tev,
                compile_result=cres,
                flow_solution=sol,
                reachable_rewrite_count=len(reachable),
            )

            if best is None or hit.score() > best.score():
                best = hit
            if sol.margin_4D_equivalent >= self.required_margin_4D:
                if success is None or hit.score() > success.score():
                    success = hit

        return {
            "batch_index": batch_index,
            "parameter_seed": seed,
            "parameter_samples": self.parameter_samples_per_batch,
            "theorem_valid_parameter_samples": theorem_valid,
            "compiled_flow_feasible": compiled_flow_feasible,
            "best": best,
            "success": success,
        }
