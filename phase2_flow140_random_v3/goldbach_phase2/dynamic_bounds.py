"""Compatibility shim for v1 imports.

New code should import from theorem_aware_evaluator.
"""
from .theorem_aware_evaluator import (
    Parameters as DynamicParameters,
    EvaluationResult as DynamicEvaluation,
    TheoremAwarePaperPathEvaluator as PaperPathDynamicEvaluator,
)
