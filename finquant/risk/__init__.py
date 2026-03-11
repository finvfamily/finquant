"""
finquant - 风控模块

包含风控管理器和执行精度
"""

from finquant.risk.manager import (
    RiskManager,
    RiskConfig,
    RiskState,
    RiskLevel,
    create_risk_manager,
)

from finquant.risk.execution import (
    OrderExecutor,
    SlippageModel,
    OrderType,
    FillPolicy,
    MarketCondition,
    create_executor,
    simple_backtest_with_slippage,
)

__all__ = [
    # 风控
    "RiskManager",
    "RiskConfig",
    "RiskState",
    "RiskLevel",
    "create_risk_manager",
    # 执行
    "OrderExecutor",
    "SlippageModel",
    "OrderType",
    "FillPolicy",
    "MarketCondition",
    "create_executor",
    "simple_backtest_with_slippage",
]
