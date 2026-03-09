"""
finquant - 量化回测示例
"""

from datetime import date, timedelta
from finquant.data import get_kline
from finquant.strategies import MACrossStrategy, RSIStrategy, MACDStrategy, get_strategy
from finquant.engine import BacktestEngine


def example_ma_cross():
    """均线交叉策略示例"""
    print("=" * 50)
    print("均线交叉策略回测示例")
    print("=" * 50)

    # 获取数据
    codes = ["000001.SZ", "600000.SH"]
    start_date = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    print(f"获取数据: {codes}")
    print(f"时间范围: {start_date} ~ {end_date}")

    data = get_kline(codes, start=start_date, end=end_date)
    print(f"获取到 {len(data)} 条数据")

    # 创建策略
    strategy = MACrossStrategy(short_period=5, long_period=20)

    # 创建回测引擎
    engine = BacktestEngine(initial_capital=100000, commission_rate=0.0003)

    # 运行回测
    result = engine.run(
        data=data,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
    )

    # 输出结果
    print(result.summary())

    # 输出交易记录
    trades_df = result.get_trades_df()
    if not trades_df.empty:
        print("最近10笔交易:")
        print(trades_df.tail(10))


def example_multi_strategy():
    """多策略比较示例"""
    print("=" * 50)
    print("多策略比较示例")
    print("=" * 50)

    # 获取数据
    codes = ["000001.SZ"]
    start_date = (date.today() - timedelta(days=730)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    data = get_kline(codes, start=start_date, end=end_date)

    # 定义策略
    strategies = {
        "MA交叉(5-20)": MACrossStrategy(short_period=5, long_period=20),
        "MA交叉(10-30)": MACrossStrategy(short_period=10, long_period=30),
        "RSI策略": RSIStrategy(period=14, oversold=30, overbought=70),
        "MACD策略": MACDStrategy(fast_period=12, slow_period=26, signal_period=9),
    }

    results = []

    # 逐个运行策略
    for name, strategy in strategies.items():
        print(f"\n运行策略: {name}")

        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(data, strategy, start_date, end_date)
        result.backtest_id = name
        results.append(result)

        print(f"  总收益: {result.total_return*100:.2f}%")
        print(f"  夏普比率: {result.sharpe_ratio:.2f}")

    # 比较结果
    print("\n" + "=" * 50)
    print("策略比较结果")
    print("=" * 50)

    from finquant.result import compare_strategies
    comparison = compare_strategies(results)
    print(comparison.to_string(index=False))


def example_custom_strategy():
    """自定义策略示例"""
    print("=" * 50)
    print("自定义策略示例")
    print("=" * 50)

    from finquant.strategies import BaseStrategy
    import pandas as pd

    class MyStrategy(BaseStrategy):
        """自定义策略：价格突破20日高点买入，跌破20日低点卖出"""

        def __init__(self):
            super().__init__({"period": 20})

        def generate_signals(self, data: pd.DataFrame, code: str, current_date):
            stock_data = data[(data["code"] == code) & (data["trade_date"] <= current_date)].copy()
            stock_data = stock_data.sort_values("trade_date")

            if len(stock_data) < 21:
                return 0

            # 计算20日高低点
            stock_data["high20"] = stock_data["high"].rolling(20).max()
            stock_data["low20"] = stock_data["low"].rolling(20).min()

            last_close = stock_data["close"].iloc[-1]
            last_high = stock_data["high20"].iloc[-1]
            last_low = stock_data["low20"].iloc[-1]

            if last_close > last_high:
                return 1
            elif last_close < last_low:
                return -1

            return 0

    # 运行自定义策略
    codes = ["000001.SZ"]
    start_date = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    data = get_kline(codes, start=start_date, end=end_date)

    strategy = MyStrategy()
    engine = BacktestEngine(initial_capital=100000)
    result = engine.run(data, strategy, start_date, end_date)

    print(result.summary())


if __name__ == "__main__":
    # 运行示例
    example_ma_cross()

    # 多策略比较
    # example_multi_strategy()

    # 自定义策略
    # example_custom_strategy()
