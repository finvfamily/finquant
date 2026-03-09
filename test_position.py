"""
finquant - 仓位控制测试脚本
"""

from datetime import date, timedelta
from finquant.data import get_kline
from finquant.strategies import MACrossStrategy
from finquant.engine import (
    BacktestEngine,
    FixedPositionSizer,
    DynamicPositionSizer,
    PyramidPositionSizer,
    CounterPyramidPositionSizer,
)


def test_position_sizers():
    """测试不同仓位控制器"""
    print("=" * 60)
    print("仓位控制测试")
    print("=" * 60)

    # 获取数据
    codes = ["000001", "600000"]
    start_date = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = date.today().strftime("%Y-%m-%d")

    print(f"获取数据: {codes}")
    data = get_kline(codes, start=start_date, end=end_date)
    print(f"获取到 {len(data)} 条数据\n")

    start = data["trade_date"].min().strftime("%Y-%m-%d")
    end = data["trade_date"].max().strftime("%Y-%m-%d")

    # 定义策略
    strategy = MACrossStrategy(short_period=5, long_period=20)

    # 测试不同仓位控制
    results = []

    # 1. 固定仓位 50%
    print("-" * 40)
    print("测试1: 固定仓位 50%")
    engine = BacktestEngine(
        initial_capital=100000,
        position_sizer=FixedPositionSizer(0.5),
        max_positions=3,
        max_single_position=0.3,
    )
    result = engine.run(data, strategy, start, end)
    result.backtest_id = "固定50%"
    results.append(result)
    print(f"  总收益: {result.total_return*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  交易次数: {result.total_trades}")

    # 2. 固定仓位 80%
    print("-" * 40)
    print("测试2: 固定仓位 80%")
    engine = BacktestEngine(
        initial_capital=100000,
        position_sizer=FixedPositionSizer(0.8),
        max_positions=3,
        max_single_position=0.3,
    )
    result = engine.run(data, strategy, start, end)
    result.backtest_id = "固定80%"
    results.append(result)
    print(f"  总收益: {result.total_return*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  交易次数: {result.total_trades}")

    # 3. 动态仓位
    print("-" * 40)
    print("测试3: 动态仓位")
    engine = BacktestEngine(
        initial_capital=100000,
        position_sizer=DynamicPositionSizer(base_ratio=0.5, max_ratio=1.0),
        max_positions=3,
        max_single_position=0.3,
    )
    result = engine.run(data, strategy, start, end)
    result.backtest_id = "动态仓位"
    results.append(result)
    print(f"  总收益: {result.total_return*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  交易次数: {result.total_trades}")

    # 4. 金字塔仓位
    print("-" * 40)
    print("测试4: 金字塔仓位")
    engine = BacktestEngine(
        initial_capital=100000,
        position_sizer=PyramidPositionSizer(base_ratio=0.2, max_ratio=1.0, step=0.1),
        max_positions=3,
        max_single_position=0.3,
    )
    result = engine.run(data, strategy, start, end)
    result.backtest_id = "金字塔仓位"
    results.append(result)
    print(f"  总收益: {result.total_return*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  交易次数: {result.total_trades}")

    # 5. 倒金字塔仓位
    print("-" * 40)
    print("测试5: 倒金字塔仓位")
    engine = BacktestEngine(
        initial_capital=100000,
        position_sizer=CounterPyramidPositionSizer(base_ratio=0.8, min_ratio=0.1),
        max_positions=3,
        max_single_position=0.3,
    )
    result = engine.run(data, strategy, start, end)
    result.backtest_id = "倒金字塔"
    results.append(result)
    print(f"  总收益: {result.total_return*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  交易次数: {result.total_trades}")

    # 6. 不同持仓数量限制
    print("-" * 40)
    print("测试6: 最多持仓1只股票")
    engine = BacktestEngine(
        initial_capital=100000,
        position_sizer=FixedPositionSizer(0.8),
        max_positions=1,
        max_single_position=0.8,
    )
    result = engine.run(data, strategy, start, end)
    result.backtest_id = "持仓1只"
    results.append(result)
    print(f"  总收益: {result.total_return*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  交易次数: {result.total_trades}")

    # 汇总比较
    print("\n" + "=" * 60)
    print("仓位控制策略比较")
    print("=" * 60)
    print(f"{'策略':<15} {'总收益':>10} {'夏普比率':>10} {'交易次数':>10}")
    print("-" * 60)
    for r in results:
        print(f"{r.backtest_id:<15} {r.total_return*100:>9.2f}% {r.sharpe_ratio:>10.2f} {r.total_trades:>10}")


if __name__ == "__main__":
    test_position_sizers()
