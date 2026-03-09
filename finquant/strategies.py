"""
finquant - 策略模块
"""

from typing import Dict, List
import pandas as pd
import numpy as np


class BaseStrategy:
    """策略基类"""

    def __init__(self, params: Dict = None):
        self.params = params or {}

    def generate_signals(self, data: pd.DataFrame, code: str, current_date) -> int:
        """
        生成交易信号

        Args:
            data: 历史数据
            code: 股票代码
            current_date: 当前日期

        Returns:
            1: 买入
            0: 持有
            -1: 卖出
        """
        return 0


class MACrossStrategy(BaseStrategy):
    """
    均线交叉策略
    短均线上穿长均线买入，下穿卖出
    """

    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__({
            "short_period": short_period,
            "long_period": long_period,
        })
        self.short_period = short_period
        self.long_period = long_period

    def generate_signals(self, data: pd.DataFrame, code: str, current_date) -> int:
        # 获取该股票历史数据
        stock_data = data[(data["code"] == code) & (data["trade_date"] <= current_date)].copy()
        stock_data = stock_data.sort_values("trade_date")

        if len(stock_data) < self.long_period + 1:
            return 0

        # 计算均线
        stock_data["ma_short"] = stock_data["close"].rolling(self.short_period).mean()
        stock_data["ma_long"] = stock_data["close"].rolling(self.long_period).mean()

        # 获取最近两天的均线值
        last_ma_short = stock_data["ma_short"].iloc[-1]
        prev_ma_short = stock_data["ma_short"].iloc[-2]
        last_ma_long = stock_data["ma_long"].iloc[-1]
        prev_ma_long = stock_data["ma_long"].iloc[-2]

        # 金叉买入，死叉卖出
        if prev_ma_short <= prev_ma_long and last_ma_short > last_ma_long:
            return 1  # 买入
        elif prev_ma_short >= prev_ma_long and last_ma_short < last_ma_long:
            return -1  # 卖出

        return 0  # 持有


class RSIStrategy(BaseStrategy):
    """
    RSI 策略
    RSI < 30 超卖买入，RSI > 70 超买卖出
    """

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__({
            "period": period,
            "oversold": oversold,
            "overbought": overbought,
        })
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, data: pd.DataFrame, code: str, current_date) -> int:
        stock_data = data[(data["code"] == code) & (data["trade_date"] <= current_date)].copy()
        stock_data = stock_data.sort_values("trade_date")

        if len(stock_data) < self.period + 1:
            return 0

        # 计算 RSI
        delta = stock_data["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(self.period).mean()
        avg_loss = loss.rolling(self.period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        last_rsi = rsi.iloc[-1]

        if last_rsi < self.oversold:
            return 1  # 超卖买入
        elif last_rsi > self.overbought:
            return -1  # 超买卖出

        return 0


class MACDStrategy(BaseStrategy):
    """
    MACD 策略
    DIF 上穿 DEA 买入，下穿卖出
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ):
        super().__init__({
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
        })
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def generate_signals(self, data: pd.DataFrame, code: str, current_date) -> int:
        stock_data = data[(data["code"] == code) & (data["trade_date"] <= current_date)].copy()
        stock_data = stock_data.sort_values("trade_date")

        if len(stock_data) < self.slow_period + self.signal_period:
            return 0

        # 计算 MACD
        exp1 = stock_data["close"].ewm(span=self.fast_period, adjust=False).mean()
        exp2 = stock_data["close"].ewm(span=self.slow_period, adjust=False).mean()
        stock_data["macd"] = exp1 - exp2
        stock_data["signal"] = stock_data["macd"].ewm(span=self.signal_period, adjust=False).mean()

        last_macd = stock_data["macd"].iloc[-1]
        prev_macd = stock_data["macd"].iloc[-2]
        last_signal = stock_data["signal"].iloc[-1]
        prev_signal = stock_data["signal"].iloc[-2]

        # 金叉买入，死叉卖出
        if prev_macd <= prev_signal and last_macd > last_signal:
            return 1
        elif prev_macd >= prev_signal and last_macd < last_signal:
            return -1

        return 0


class BollStrategy(BaseStrategy):
    """
    布林带策略
    价格突破上轨买入，突破下轨卖出
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__({
            "period": period,
            "std_dev": std_dev,
        })
        self.period = period
        self.std_dev = std_dev

    def generate_signals(self, data: pd.DataFrame, code: str, current_date) -> int:
        stock_data = data[(data["code"] == code) & (data["trade_date"] <= current_date)].copy()
        stock_data = stock_data.sort_values("trade_date")

        if len(stock_data) < self.period + 1:
            return 0

        # 计算布林带
        stock_data["ma"] = stock_data["close"].rolling(self.period).mean()
        stock_data["std"] = stock_data["close"].rolling(self.period).std()
        stock_data["upper"] = stock_data["ma"] + self.std_dev * stock_data["std"]
        stock_data["lower"] = stock_data["ma"] - self.std_dev * stock_data["std"]

        last_close = stock_data["close"].iloc[-1]
        last_upper = stock_data["upper"].iloc[-1]
        last_lower = stock_data["lower"].iloc[-1]

        if last_close > last_upper:
            return 1
        elif last_close < last_lower:
            return -1

        return 0


class DualEMAStrategy(BaseStrategy):
    """
    双重指数移动平均线策略
    价格上穿 EMA 买入，下穿卖出
    """

    def __init__(self, short_period: int = 10, long_period: int = 30):
        super().__init__({
            "short_period": short_period,
            "long_period": long_period,
        })
        self.short_period = short_period
        self.long_period = long_period

    def generate_signals(self, data: pd.DataFrame, code: str, current_date) -> int:
        stock_data = data[(data["code"] == code) & (data["trade_date"] <= current_date)].copy()
        stock_data = stock_data.sort_values("trade_date")

        if len(stock_data) < self.long_period + 1:
            return 0

        # 计算 EMA
        stock_data["ema_short"] = stock_data["close"].ewm(span=self.short_period, adjust=False).mean()
        stock_data["ema_long"] = stock_data["close"].ewm(span=self.long_period, adjust=False).mean()

        last_ema_short = stock_data["ema_short"].iloc[-1]
        prev_ema_short = stock_data["ema_short"].iloc[-2]
        last_ema_long = stock_data["ema_long"].iloc[-1]
        prev_ema_long = stock_data["ema_long"].iloc[-2]

        if prev_ema_short <= prev_ema_long and last_ema_short > last_ema_long:
            return 1
        elif prev_ema_short >= prev_ema_long and last_ema_short < last_ema_long:
            return -1

        return 0


# 策略注册表
STRATEGY_REGISTRY = {
    "ma_cross": MACrossStrategy,
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "boll": BollStrategy,
    "dual_ema": DualEMAStrategy,
}


def get_strategy(strategy_name: str, **kwargs) -> BaseStrategy:
    """获取策略实例"""
    strategy_class = STRATEGY_REGISTRY.get(strategy_name)
    if not strategy_class:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    return strategy_class(**kwargs)
