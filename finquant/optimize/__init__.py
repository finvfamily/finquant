"""
finquant - 优化模块

包含贝叶斯优化、Walk-Forward、敏感性分析
"""

from finquant.optimize.bayesian import (
    BayesianOptimizer,
    BayesianConfig,
    bayesian_optimize,
)

from finquant.optimize.walkforward import (
    WalkForwardOptimizer,
    WalkForwardConfig,
    walk_forward_optimize,
    GridSearchOptimizer,
)

from finquant.optimize.sensitivity import (
    SensitivityAnalyzer,
    ParameterStability,
)

__all__ = [
    # 贝叶斯
    "BayesianOptimizer",
    "BayesianConfig",
    "bayesian_optimize",
    # Walk-Forward
    "WalkForwardOptimizer",
    "WalkForwardConfig",
    "walk_forward_optimize",
    "GridSearchOptimizer",
    # 敏感性
    "SensitivityAnalyzer",
    "ParameterStability",
]
