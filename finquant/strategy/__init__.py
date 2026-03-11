"""
finquant - 策略模块

包含策略基类和各种策略实现
"""

from finquant.strategy.base import (
    Strategy,
    Signal,
    Action,
    Bar,
    buy_signal,
    sell_signal,
    hold_signal,
)

from finquant.strategy.composite import (
    CompositeStrategy,
)

from finquant.strategy.v2 import (
    MAStrategy,
    RSIStrategy,
    get_vectorized_strategy,
    create_strategy,
)

__all__ = [
    # 基础
    "Strategy",
    "Signal",
    "Action",
    "Bar",
    "buy_signal",
    "sell_signal",
    "hold_signal",
    # 策略实现
    "MAStrategy",
    "RSIStrategy",
    "get_vectorized_strategy",
    "create_strategy",
    # 组合策略
    "CompositeStrategy",
]
