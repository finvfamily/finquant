"""
finquant V2 - 自定义策略示例

演示如何创建自定义策略
"""

import pandas as pd
import numpy as np
from datetime import datetime

# ========== 示例1：基础策略 ==========

def example_basic_strategy():
    """基础自定义策略"""
    print("\n" + "="*60)
    print("示例1：基础自定义策略")
    print("="*60)

    from finquant import get_kline
    from finquant.strategy.base import Strategy, Signal, Action, Bar

    class BreakoutStrategy(Strategy):
        """价格突破20日高点买入，跌破20日低点卖出"""

        def __init__(self, period: int = 20):
            super().__init__("BreakoutStrategy")
            self.period = period
            self.params = {"period": period}

        def on_bar(self, bar: Bar) -> Signal:
            # 获取历史数据
            history = bar.history('close', self.period + 1)
            if len(history) < self.period:
                return None

            current = history.iloc[-1]
            high_20 = history.rolling(20).max().iloc[-1]
            low_20 = history.rolling(20).min().iloc[-1]

            # 突破高点买入
            if current > high_20:
                return Signal(
                    action=Action.BUY,
                    strength=1.0,
                    price=bar.close,
                    reason=f"突破20日高点 {high_20:.2f}"
                )

            # 跌破低点卖出
            if current < low_20:
                return Signal(
                    action=Action.SELL,
                    strength=1.0,
                    price=bar.close,
                    reason=f"跌破20日低点 {low_20:.2f}"
                )

            return None

    # 回测
    from finquant.core import BacktestEngineV2, BacktestConfig

    # 多品类标的
    codes = [
        # ETF
        "SH510300",  # 沪深300ETF
        "SH512880",  # 证券ETF
        # LOF
        "SH161039",  # 易方达创业板LOF
        # 主板
        "SH600519",  # 茅台
        "SH600036",  # 招商银行
        # 创业板
        "SZ300750",  # 宁德时代
        "SZ300059",  # 东方财富
        # 科创板
        "SH688981",  # 中芯国际
        "SH688111",  # 华大基因
    ]

    start_date = "2024-01-01"
    end_date = "2024-11-01"
    print(f"获取标的: {codes}")
    print(f"时间范围: {start_date} ~ {end_date}")

    # 增加初始资金
    initial_capital = 1000000  # 100万
    print(f"初始资金: {initial_capital:,}")

    data = get_kline(codes=codes, start=start_date, end=end_date)

    print(f"获取数据: {len(data)} 条")
    print(f"股票数量: {data['code'].nunique()}")
    print(f"日期范围: {data['trade_date'].min()} ~ {data['trade_date'].max()}")

    engine = BacktestEngineV2(BacktestConfig(initial_capital=1000000))
    engine.add_strategy(BreakoutStrategy(period=20))
    result = engine.run(data)

    print(f"收益率: {result.total_return*100:.2f}%")
    print(f"交易次数: {result.total_trades}")


# ========== 示例2：双均线策略 ==========

def example_ma_strategy():
    """双均线策略"""
    print("\n" + "="*60)
    print("示例2：双均线策略")
    print("="*60)

    from finquant import get_kline
    from finquant.strategy.base import Strategy, Signal, Action, Bar

    class DualMAStrategy(Strategy):
        """双均线策略：MA5 上穿 MA20 买入，下穿卖出"""

        def __init__(self, short: int = 5, long: int = 20):
            super().__init__("DualMA")
            self.short = short
            self.long = long
            self.params = {"short": short, "long": long}

        def on_bar(self, bar: Bar) -> Signal:
            history = bar.history('close', self.long + 1)
            if len(history) < self.long:
                return None

            # 计算均线
            ma_short = history.rolling(self.short).mean().iloc[-1]
            ma_long = history.rolling(self.long).mean().iloc[-1]
            ma_short_prev = history.rolling(self.short).mean().iloc[-2]
            ma_long_prev = history.rolling(self.long).mean().iloc[-2]

            # 金叉买入
            if ma_short_prev <= ma_long_prev and ma_short > ma_long:
                return Signal(
                    action=Action.BUY,
                    strength=1.0,
                    reason=f"MA{self.short}上穿MA{self.long}"
                )

            # 死叉卖出
            if ma_short_prev >= ma_long_prev and ma_short < ma_long:
                return Signal(
                    action=Action.SELL,
                    strength=1.0,
                    reason=f"MA{self.short}下穿MA{self.long}"
                )

            return None

    # 回测
    from finquant.core import BacktestEngineV2, BacktestConfig

    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")

    engine = BacktestEngineV2(BacktestConfig(initial_capital=100000))
    engine.add_strategy(DualMAStrategy(short=5, long=20))
    result = engine.run(data)

    print(f"收益率: {result.total_return*100:.2f}%")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"交易次数: {result.total_trades}")


# ========== 示例3：RSI 策略 ==========

def example_rsi_strategy():
    """RSI 策略"""
    print("\n" + "="*60)
    print("示例3：RSI 策略")
    print("="*60)

    from finquant import get_kline
    from finquant.strategy.base import Strategy, Signal, Action, Bar

    class RSIStrategy(Strategy):
        """RSI 策略：RSI < 30 买入，RSI > 70 卖出"""

        def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
            super().__init__("RSI")
            self.period = period
            self.oversold = oversold
            self.overbought = overbought
            self.params = {"period": period, "oversold": oversold, "overbought": overbought}

        def on_bar(self, bar: Bar) -> Signal:
            history = bar.history('close', self.period + 1)
            if len(history) < self.period:
                return None

            # 计算 RSI
            delta = history.diff()
            gain = delta.where(delta > 0, 0)
            loss = (-delta).where(delta < 0, 0)

            avg_gain = gain.rolling(self.period).mean().iloc[-1]
            avg_loss = loss.rolling(self.period).mean().iloc[-1]

            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            # 超卖买入
            if rsi < self.oversold:
                return Signal(
                    action=Action.BUY,
                    strength=(self.oversold - rsi) / self.oversold,
                    reason=f"RSI超卖 {rsi:.1f}"
                )

            # 超买卖出
            if rsi > self.overbought:
                return Signal(
                    action=Action.SELL,
                    strength=(rsi - self.overbought) / (100 - self.overbought),
                    reason=f"RSI超买 {rsi:.1f}"
                )

            return None

    # 回测
    from finquant.core import BacktestEngineV2, BacktestConfig

    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")

    engine = BacktestEngineV2(BacktestConfig(initial_capital=100000))
    engine.add_strategy(RSIStrategy(period=14, oversold=30, overbought=70))
    result = engine.run(data)

    print(f"收益率: {result.total_return*100:.2f}%")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"交易次数: {result.total_trades}")


# ========== 示例4：布林带策略 ==========

def example_boll_strategy():
    """布林带策略"""
    print("\n" + "="*60)
    print("示例4：布林带策略")
    print("="*60)

    from finquant import get_kline
    from finquant.strategy.base import Strategy, Signal, Action, Bar

    class BollStrategy(Strategy):
        """布林带策略：价格突破上轨买入，突破下轨卖出"""

        def __init__(self, period: int = 20, std_dev: float = 2.0):
            super().__init__("Boll")
            self.period = period
            self.std_dev = std_dev
            self.params = {"period": period, "std_dev": std_dev}

        def on_bar(self, bar: Bar) -> Signal:
            history = bar.history('close', self.period + 1)
            if len(history) < self.period:
                return None

            # 计算布林带
            ma = history.rolling(self.period).mean().iloc[-1]
            std = history.rolling(self.period).std().iloc[-1]
            upper = ma + self.std_dev * std
            lower = ma - self.std_dev * std

            current = history.iloc[-1]

            # 突破上轨买入
            if current > upper:
                return Signal(
                    action=Action.BUY,
                    strength=1.0,
                    reason=f"突破上轨 {upper:.2f}"
                )

            # 突破下轨卖出
            if current < lower:
                return Signal(
                    action=Action.SELL,
                    strength=1.0,
                    reason=f"突破下轨 {lower:.2f}"
                )

            return None

    # 回测
    from finquant.core import BacktestEngineV2, BacktestConfig

    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")

    engine = BacktestEngineV2(BacktestConfig(initial_capital=100000))
    engine.add_strategy(BollStrategy(period=20, std_dev=2.0))
    result = engine.run(data)

    print(f"收益率: {result.total_return*100:.2f}%")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"交易次数: {result.total_trades}")


# ========== 示例5：成交量策略 ==========

def example_volume_strategy():
    """成交量策略"""
    print("\n" + "="*60)
    print("示例5：成交量策略")
    print("="*60)

    from finquant import get_kline
    from finquant.strategy.base import Strategy, Signal, Action, Bar

    class VolumeStrategy(Strategy):
        """成交量策略：放量上涨买入，放量下跌卖出"""

        def __init__(self, period: int = 20, volume_mult: float = 1.5):
            super().__init__("Volume")
            self.period = period
            self.volume_mult = volume_mult
            self.params = {"period": period, "volume_mult": volume_mult}

        def on_bar(self, bar: Bar) -> Signal:
            history = bar.history('close', self.period + 1)
            volume_history = bar.history('volume', self.period + 1)

            if len(history) < self.period:
                return None

            # 计算平均成交量
            avg_volume = volume_history.rolling(self.period).mean().iloc[-1]
            current_volume = volume_history.iloc[-1]

            # 计算价格变化
            price_change = (history.iloc[-1] - history.iloc[-2]) / history.iloc[-2]

            # 放量上涨买入
            if current_volume > avg_volume * self.volume_mult and price_change > 0.01:
                return Signal(
                    action=Action.BUY,
                    strength=min(price_change * 10, 1.0),
                    reason=f"放量上涨 {current_volume/avg_volume:.1f}倍"
                )

            # 放量下跌卖出
            if current_volume > avg_volume * self.volume_mult and price_change < -0.01:
                return Signal(
                    action=Action.SELL,
                    strength=min(abs(price_change) * 10, 1.0),
                    reason=f"放量下跌 {current_volume/avg_volume:.1f}倍"
                )

            return None

    # 回测
    from finquant.core import BacktestEngineV2, BacktestConfig

    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")

    engine = BacktestEngineV2(BacktestConfig(initial_capital=100000))
    engine.add_strategy(VolumeStrategy(period=20, volume_mult=1.5))
    result = engine.run(data)

    print(f"收益率: {result.total_return*100:.2f}%")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"交易次数: {result.total_trades}")


# ========== 运行示例 ==========

if __name__ == "__main__":
    # 选择运行哪个示例
    example_ma_strategy()

    # 其他示例
    # example_basic_strategy()
    # example_rsi_strategy()
    # example_boll_strategy()
    # example_volume_strategy()
