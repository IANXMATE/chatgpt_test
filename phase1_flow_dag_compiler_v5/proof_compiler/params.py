from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List
import sympy as sp

alpha, beta, gamma, tau = sp.symbols("alpha beta gamma tau", real=True)
PARAM_SYMBOLS = (alpha, beta, gamma, tau)


def parse_number(x):
    if isinstance(x, (int, float)):
        return float(x)
    x = str(x).strip()
    if "/" in x:
        return float(Fraction(x))
    return float(x)


@dataclass(frozen=True)
class ReferencePoint:
    a: float = 1.9
    alpha: float = 4/53
    beta: float = 4/33
    gamma: float = 3/11
    epsilon: float = 1e-10

    @property
    def tau(self) -> float:
        return (self.a - 1.0) / self.a - self.epsilon

    def subs(self) -> Dict[sp.Symbol, float]:
        return {
            alpha: self.alpha,
            beta: self.beta,
            gamma: self.gamma,
            tau: self.tau,
        }

    def as_dict(self):
        return {
            "a": self.a,
            "alpha": self.alpha,
            "beta": self.beta,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "tau": self.tau,
        }


@dataclass(frozen=True)
class ParameterDomain:
    """Linear relaxation of Proposition 4.3 parameter conditions.

    The exact relation tau=(a-1)/a-epsilon is deliberately left for Stage 2.
    For Phase 1 reachability, tau is retained as an independent parameter
    satisfying the consequences needed by Proposition 4.3.

    A tiny positive strict_margin models strict inequalities conservatively.
    """
    strict_margin: float = 1e-6

    def inequalities(self) -> List[sp.Expr]:
        e = sp.Float(self.strict_margin)
        # Convention: every expression is <= 0.
        return [
            sp.Rational(1,18) + e - alpha,       # alpha > 1/18
            alpha + e - beta,                    # alpha < beta
            2*beta + e - sp.Rational(1,3),      # beta < (1-3 beta)/3
            sp.Rational(1,3) - beta + e - gamma,# (1-3 beta)/3 < gamma
            gamma + e - sp.Rational(1,3),       # gamma < 1/3
            sp.Rational(1,3) + e - tau,          # tau > 1/3
            tau + e - sp.Rational(1,2),          # tau < 1/2
        ]

    def as_strings(self):
        return [str(sp.expand(x)) + " <= 0" for x in self.inequalities()]
