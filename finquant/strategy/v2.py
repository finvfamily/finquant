"""
finquant - 策略接口模块 (V2)

事件驱动架构下的策略接口
支持独立单元测试
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np

# 从 base 导入公共类（确保使用同一个 Action enum）
from finquant.strategy.base import Action, Bar, Strategy

# Signal 需要 code 字段，从 base 导入后需要确保有 code 字段
from finquant.strategy.base import Signal as BaseSignal


@dataclass
class Signal(BaseSignal):
    """交易信号（带 code 字段）"""

    def __repr__(self):
        return f"Signal({self.action.name}, {self.code}, strength={self.strength})"


class Strategy(ABC):
    """
    策略基类（事件驱动版）

    与旧版区别：
    - 基于事件驱动，可以订阅不同类型的事件
    - 可以独立于引擎进行单元测试
    - 返回 Signal 对象而非简单的 int
    """

    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.params: Dict = {}

        # 持仓状态（可选，由引擎维护）
        self._position: Dict[str, int] = {}  # code -> shares

    @property
    def position(self) -> Dict[str, int]:
        """获取当前持仓"""
        return self._position.copy()

    def update_position(self, code: str, shares: int) -> None:
        """更新持仓状态"""
        self._position[code] = shares

    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """
        收到K线时调用（核心方法）

        Args:
            bar: K线数据

        Returns:
            Signal 对象或 None（不交易）
        """
        return None

    def on_trade(self, code: str, action: Action, shares: int, price: float) -> None:
        """
        成交时调用

        Args:
            code: 股票代码
            action: 买入/卖出
            shares: 成交数量
            price: 成交价格
        """
        pass

    def on_day_start(self, date) -> None:
        """交易日开始时调用"""
        pass

    def on_day_end(self, date) -> None:
        """交易日结束时调用"""
        pass

    def get_params(self) -> Dict:
        """获取策略参数"""
        return self.params.copy()

    def set_params(self, **params) -> None:
        """设置策略参数"""
        self.params.update(params)


class CompositeStrategy(Strategy):
    """
    组合策略

    组合多个子策略的信号
    """

    def __init__(self, strategies: List[Strategy], combine_method: str = "vote"):
        """
        Args:
            strategies: 子策略列表
            combine_method: 信号组合方式
                - "vote": 投票（多数获胜）
                - "avg": 平均信号强度
                - "first": 第一个非 HOLD 信号
        """
        super().__init__("CompositeStrategy")
        self.strategies = strategies
        self.combine_method = combine_method

    def on_bar(self, bar: Bar) -> Optional[Signal]:
        # 获取所有子策略信号
        signals = []
        for strategy in self.strategies:
            signal = strategy.on_bar(bar)
            if signal:
                signals.append(signal)

        if not signals:
            return None

        # 组合信号
        if self.combine_method == "vote":
            return self._combine_vote(signals)
        elif self.combine_method == "avg":
            return self._combine_avg(signals)
        else:
            return signals[0]

    def _combine_vote(self, signals: List[Signal]) -> Signal:
        """投票组合"""
        buy_count = sum(1 for s in signals if s.action == Action.BUY)
        sell_count = sum(1 for s in signals if s.action == Action.SELL)
        hold_count = sum(1 for s in signals if s.action == Action.HOLD)

        if buy_count > sell_count and buy_count > hold_count:
            return Signal(Action.BUY, strength=buy_count / len(signals))
        elif sell_count > buy_count and sell_count > hold_count:
            return Signal(Action.SELL, strength=sell_count / len(signals))
        else:
            return Signal(Action.HOLD)

    def _combine_avg(self, signals: List[Signal]) -> Signal:
        """平均组合"""
        avg_strength = np.mean([s.strength for s in signals])

        buy_signals = [s for s in signals if s.action == Action.BUY]
        sell_signals = [s for s in signals if s.action == Action.SELL]

        if len(buy_signals) > len(sell_signals):
            return Signal(Action.BUY, avg_strength)
        elif len(sell_signals) > len(buy_signals):
            return Signal(Action.SELL, avg_strength)
        else:
            return Signal(Action.HOLD)


# 策略注册表（用于工厂模式）
_STRATEGY_REGISTRY: Dict[str, type] = {}


def register_strategy(name: str):
    """策略注册装饰器"""
    def decorator(cls):
        _STRATEGY_REGISTRY[name] = cls
        return cls
    return decorator


def create_strategy(name: str, **params) -> Strategy:
    """创建策略实例"""
    if name not in _STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy: {name}")
    return _STRATEGY_REGISTRY[name](**params)


# 向量化策略别名（兼容 API）
def get_vectorized_strategy(strategy_name: str, **kwargs):
    """获取向量化策略实例（兼容接口）"""
    return create_strategy(strategy_name, **kwargs)


# 便捷函数：创建买入/卖出信号
def buy_signal(code: str = "", strength: float = 1.0, price: float = 0, reason: str = "") -> Signal:
    """创建买入信号"""
    return Signal(Action.BUY, code, strength, price, reason)


def sell_signal(code: str = "", strength: float = 1.0, price: float = 0, reason: str = "") -> Signal:
    """创建卖出信号"""
    return Signal(Action.SELL, code, strength, price, reason)


def hold_signal(code: str = "", strength: float = 0, reason: str = "") -> Signal:
    """创建持有信号"""
    return Signal(Action.HOLD, code, strength, 0, reason)


# 从 V1 策略迁移的示例
class MAStrategy(Strategy):
    """均线交叉策略（V2版）"""

    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__("MAStrategy")
        self.short_period = short_period
        self.long_period = long_period
        self.params = {"short_period": short_period, "long_period": long_period}

    def on_bar(self, bar: Bar) -> Optional[Signal]:
        # 获取历史数据
        history = bar.history('close', self.long_period + 1)

        if len(history) < self.long_period + 1:
            return None

        # 计算均线
        ma_short = history.tail(self.short_period).mean()
        ma_long = history.tail(self.long_period).mean()

        # 前一根K线的均线
        prev_history = bar.history('close', self.long_period + 2).iloc[:-1]
        prev_ma_short = prev_history.tail(self.short_period).mean()
        prev_ma_long = prev_history.tail(self.long_period).mean()

        # 金叉买入
        if prev_ma_short <= prev_ma_long and ma_short > ma_long:
            return buy_signal(bar.code, reason=f"MA金叉: short={ma_short:.2f}, long={ma_long:.2f}")

        # 死叉卖出
        if prev_ma_short >= prev_ma_long and ma_short < ma_long:
            return sell_signal(bar.code, reason=f"MA死叉: short={ma_short:.2f}, long={ma_long:.2f}")

        return hold_signal(bar.code)


class RSIStrategy(Strategy):
    """RSI 策略（V2版）"""

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__("RSIStrategy")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.params = {"period": period, "oversold": oversold, "overbought": overbought}

    def on_bar(self, bar: Bar) -> Optional[Signal]:
        history = bar.history('close', self.period + 1)

        if len(history) < self.period + 1:
            return None

        # 计算 RSI
        delta = history.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.tail(self.period).mean()
        avg_loss = loss.tail(self.period).mean()

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # 超卖买入
        if rsi < self.oversold:
            return buy_signal(bar.code, reason=f"RSI超卖: {rsi:.2f}")

        # 超买卖出
        if rsi > self.overbought:
            return sell_signal(bar.code, reason=f"RSI超买: {rsi:.2f}")

        return hold_signal(bar.code)


# 注册策略
register_strategy("ma_cross")(MAStrategy)
register_strategy("rsi")(RSIStrategy)
