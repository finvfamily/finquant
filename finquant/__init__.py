"""
finquant - 轻量级量化回测工具

纯 Python 脚本，无需服务端和数据缓存
使用 finshare 获取实时数据
"""

__version__ = "0.1.0"
__author__ = "MeepoQuant"

from finquant.engine import (
    BacktestEngine,
    PortfolioRebalance,
    # 仓位控制器
    PositionSizer,
    FixedPositionSizer,
    DynamicPositionSizer,
    PyramidPositionSizer,
    CounterPyramidPositionSizer,
    ATRPositionSizer,
)
from finquant.strategies import (
    BaseStrategy,
    MACrossStrategy,
    RSIStrategy,
    MACDStrategy,
    BollStrategy,
    DualEMAStrategy,
    get_strategy,
)
from finquant.data import get_kline, get_realtime_quote, ensure_full_code
from finquant.result import BacktestResult, compare_strategies

__all__ = [
    "BacktestEngine",
    "PortfolioRebalance",
    # 仓位控制器
    "PositionSizer",
    "FixedPositionSizer",
    "DynamicPositionSizer",
    "PyramidPositionSizer",
    "CounterPyramidPositionSizer",
    "ATRPositionSizer",
    # 策略
    "BaseStrategy",
    "MACrossStrategy",
    "RSIStrategy",
    "MACDStrategy",
    "BollStrategy",
    "DualEMAStrategy",
    "get_strategy",
    # 数据
    "get_kline",
    "get_realtime_quote",
    "ensure_full_code",
    # 结果
    "BacktestResult",
    "compare_strategies",
]
