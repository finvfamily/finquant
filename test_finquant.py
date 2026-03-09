"""
finquant - 量化回测测试脚本
"""

from datetime import date, timedelta
from finquant.data import get_kline, ensure_full_code
from finquant.strategies import MACrossStrategy, RSIStrategy, MACDStrategy
from finquant.engine import BacktestEngine


def test_ensure_full_code():
    """测试股票代码格式化"""
    print("=" * 50)
    print("测试1: 股票代码格式化")
    print("=" * 50)

    test_codes = [
        "000001",
        "600000",
        "159915",
        "000001.SZ",
        "600000.SH",
        "sh.600000",
        "sz.000001",
    ]

    for code in test_codes:
        full_code = ensure_full_code(code)
        print(f"  {code} -> {full_code}")


def test_data_fetch():
    """测试数据获取"""
    print("\n" + "=" * 50)
    print("测试2: 数据获取")
    print("=" * 50)

    # 使用短码，finshare 会自动转换为完整代码
    codes = ["000001", "600000"]
    start_date = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    print(f"获取数据: {codes}")
    print(f"时间范围: {start_date} ~ {end_date}")

    data = get_kline(codes, start=start_date, end=end_date)
    print(f"获取到 {len(data)} 条数据")
    print(f"\n数据预览:")
    print(data.head())
    print(f"\n股票列表: {data['code'].unique().tolist()}")

    return data


def test_ma_cross_strategy(data):
    """测试均线交叉策略"""
    print("\n" + "=" * 50)
    print("测试3: 均线交叉策略")
    print("=" * 50)

    # 创建策略
    strategy = MACrossStrategy(short_period=5, long_period=20)

    # 创建回测引擎
    engine = BacktestEngine(initial_capital=100000, commission_rate=0.0003)

    # 获取回测日期范围
    start_date = data["trade_date"].min().strftime("%Y-%m-%d")
    end_date = data["trade_date"].max().strftime("%Y-%m-%d")

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
        print(f"共 {len(trades_df)} 笔交易")
        print("最近5笔交易:")
        print(trades_df.tail(5).to_string(index=False))

    return result


def test_rsi_strategy(data):
    """测试RSI策略"""
    print("\n" + "=" * 50)
    print("测试4: RSI策略")
    print("=" * 50)

    strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    engine = BacktestEngine(initial_capital=100000)

    start_date = data["trade_date"].min().strftime("%Y-%m-%d")
    end_date = data["trade_date"].max().strftime("%Y-%m-%d")

    result = engine.run(data, strategy, start_date, end_date)

    print(f"总收益: {result.total_return*100:.2f}%")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"交易次数: {result.total_trades}")

    return result


def test_macd_strategy(data):
    """测试MACD策略"""
    print("\n" + "=" * 50)
    print("测试5: MACD策略")
    print("=" * 50)

    strategy = MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
    engine = BacktestEngine(initial_capital=100000)

    start_date = data["trade_date"].min().strftime("%Y-%m-%d")
    end_date = data["trade_date"].max().strftime("%Y-%m-%d")

    result = engine.run(data, strategy, start_date, end_date)

    print(f"总收益: {result.total_return*100:.2f}%")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"交易次数: {result.total_trades}")

    return result


def test_compare_strategies(data):
    """测试多策略比较"""
    print("\n" + "=" * 50)
    print("测试6: 多策略比较")
    print("=" * 50)

    # 定义策略
    strategies = {
        "MA交叉(5-20)": MACrossStrategy(short_period=5, long_period=20),
        "MA交叉(10-30)": MACrossStrategy(short_period=10, long_period=30),
        "RSI策略": RSIStrategy(period=14, oversold=30, overbought=70),
        "MACD策略": MACDStrategy(fast_period=12, slow_period=26, signal_period=9),
    }

    start_date = data["trade_date"].min().strftime("%Y-%m-%d")
    end_date = data["trade_date"].max().strftime("%Y-%m-%d")

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
        print(f"  最大回撤: {result.max_drawdown*100:.2f}%")

    # 比较结果
    print("\n" + "=" * 50)
    print("策略比较结果")
    print("=" * 50)

    from finquant.result import compare_strategies
    comparison = compare_strategies(results)
    print(comparison.to_string(index=False))


def test_custom_strategy(data):
    """测试自定义策略"""
    print("\n" + "=" * 50)
    print("测试7: 自定义策略")
    print("=" * 50)

    from finquant.strategies import BaseStrategy
    import pandas as pd

    class BreakoutStrategy(BaseStrategy):
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
    strategy = BreakoutStrategy()
    engine = BacktestEngine(initial_capital=100000)

    start_date = data["trade_date"].min().strftime("%Y-%m-%d")
    end_date = data["trade_date"].max().strftime("%Y-%m-%d")

    result = engine.run(data, strategy, start_date, end_date)

    print(result.summary())

    return result


if __name__ == "__main__":
    # 测试1: 股票代码格式化
    test_ensure_full_code()

    # 测试2: 获取数据
    data = test_data_fetch()

    if data.empty:
        print("数据获取失败，退出测试")
        exit(1)

    # 测试3: 均线交叉策略
    test_ma_cross_strategy(data)

    # 测试4: RSI策略
    test_rsi_strategy(data)

    # 测试5: MACD策略
    test_macd_strategy(data)

    # 测试6: 多策略比较
    test_compare_strategies(data)

    # 测试7: 自定义策略
    test_custom_strategy(data)

    print("\n" + "=" * 50)
    print("所有测试完成!")
    print("=" * 50)
