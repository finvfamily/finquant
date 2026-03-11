"""
finquant V2 - 基础示例

演示如何使用 finquant V2.0 进行量化回测
"""

import pandas as pd
from datetime import datetime, timedelta

# ========== 方式一：一行代码回测 ==========

def example_one_liner():
    """一行代码完成回测"""
    print("\n" + "="*60)
    print("方式一：一行代码回测")
    print("="*60)

    # 使用 bt 函数一行代码完成回测
    from finquant import bt

    result = bt(
        code="SH600519",      # 股票代码
        strategy="ma_cross",  # 策略名称
        short=5,              # 短期均线
        long=20,              # 长期均线
        start="2024-01-01",  # 开始日期
        end="2025-01-01",    # 结束日期
    )

    print(result.summary())


# ========== 方式二：API 回测 ==========

def example_api():
    """使用 API 进行回测"""
    print("\n" + "="*60)
    print("方式二：API 回测")
    print("="*60)

    from finquant import backtest, get_kline

    # 获取数据
    data = get_kline(
        codes=["SH600519"],
        start="2024-01-01",
        end="2025-01-01"
    )

    # 回测
    result = backtest(
        data=data,
        strategy="ma_cross",
        short=5,
        long=20,
        initial_capital=1000000
    )

    print(result.summary())


# ========== 方式三：引擎回测 ==========

def example_engine():
    """使用引擎进行回测"""
    print("\n" + "="*60)
    print("方式三：引擎回测")
    print("="*60)

    from finquant import get_kline, MAStrategy
    from finquant.core import BacktestEngineV2, BacktestConfig

    # 获取数据
    data = get_kline(
        codes=["SH600519", "SH600000"],
        start="2020-01-01",
        end="2026-01-01"
    )

    # 创建策略
    strategy = MAStrategy(short_period=5, long_period=20)

    # 创建配置
    config = BacktestConfig(
        initial_capital=100000,      # 初始资金
        commission_rate=0.0003,       # 手续费率
        slippage=0.001,              # 滑点
        max_positions=3,             # 最大持仓数
        max_single_position=0.3,     # 单票最大仓位
    )

    # 创建引擎
    engine = BacktestEngineV2(config)

    # 添加策略
    engine.add_strategy(strategy)

    # 运行回测
    result = engine.run(data)

    # 输出结果
    print("\n--- 回测结果 ---")
    print(f"初始资金: {result.initial_capital:,.2f}")
    print(f"最终资金: {result.final_capital:,.2f}")
    print(f"总收益率: {result.total_return*100:.2f}%")
    print(f"年化收益率: {result.annual_return*100:.2f}%")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"胜率: {result.win_rate*100:.2f}%")
    print(f"交易次数: {result.total_trades}")


# ========== 多策略比较 ==========

def example_compare():
    """多策略比较"""
    print("\n" + "="*60)
    print("多策略比较")
    print("="*60)

    from finquant import get_kline, MAStrategy, RSIStrategy
    from finquant.core import BacktestEngineV2, BacktestConfig
    from finquant.visualize import compare_results

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
    end_date = "2025-01-01"

    print(f"获取标的: {codes}")
    print(f"时间范围: {start_date} ~ {end_date}")

    # 增加初始资金
    initial_capital = 1000000  # 100万
    print(f"初始资金: {initial_capital:,}")

    data = get_kline(codes=codes, start=start_date, end=end_date)
    print(f"获取数据: {len(data)} 条")
    print(f"股票数量: {data['code'].nunique()}")
    print(f"日期范围: {data['trade_date'].min()} ~ {data['trade_date'].max()}")

    # 策略列表
    strategies = [
        ("MA5-20", MAStrategy(short_period=5, long_period=20)),
        ("MA10-30", MAStrategy(short_period=10, long_period=30)),
        ("RSI", RSIStrategy(period=14, oversold=30, overbought=70)),
    ]

    results = []

    # 逐个运行
    for name, strategy in strategies:
        config = BacktestConfig(initial_capital=100000)
        engine = BacktestEngineV2(config)
        engine.add_strategy(strategy)
        result = engine.run(data)
        result.backtest_id = name
        results.append(result)
        print(f"{name}: 收益率 {result.total_return*100:.2f}%")

    # 比较结果
    print(compare_results(results, [s[0] for s in strategies]))


# ========== 运行示例 ==========

if __name__ == "__main__":
    # 选择运行哪个示例
    example_engine()

    # 一行代码
    # example_one_liner()

    # API
    # example_api()

    # 多策略比较
    # example_compare()
