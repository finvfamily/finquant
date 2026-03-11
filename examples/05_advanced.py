"""
finquant V2 - 多资产与可视化示例

演示多资产回测和可视化功能
"""

import pandas as pd


# ========== 示例1：多资产配置 ==========

def example_multi_asset():
    """多资产配置示例"""
    print("\n" + "="*60)
    print("示例1：多资产配置")
    print("="*60)

    from finquant.core import (
        MultiAssetEngine,
        AssetType,
        create_stock,
        create_futures,
        create_fund,
    )

    # 创建资产配置
    assets = [
        create_stock("SH600519", "茅台"),      # 股票
        create_stock("SH600000", "浦发"),      # 股票
        create_futures("IF", multiplier=300),   # 期货
        create_fund("110011", "易方达"),       # 基金
    ]

    print("资产配置:")
    for asset in assets:
        print(f"  {asset.code} - {asset.name}: {asset.asset_type}")

    # 创建多资产引擎
    engine = MultiAssetEngine(initial_capital=1000000)

    # 添加资产
    for asset in assets:
        engine.add_asset(asset)

    print(f"\n初始资金: {engine.initial_capital}")
    print(f"资产数量: {len(assets)}")


# ========== 示例2：股票组合 ==========

def example_stock_portfolio():
    """股票组合示例"""
    print("\n" + "="*60)
    print("示例2：股票组合")
    print("="*60)

    from finquant import get_kline, MAStrategy
    from finquant.core import MultiAssetEngine

    # 获取多只股票数据
    data = get_kline(
        codes=["SH600519", "SH600000", "SH600036"],
        start="2024-01-01",
        end="2025-01-01"
    )

    print(f"数据量: {len(data)} 行")

    # 创建组合策略
    strategy = MAStrategy(short_period=5, long_period=20)

    # 创建引擎
    engine = MultiAssetEngine(
        initial_capital=100000,
        max_positions=3,
    )

    # 添加策略
    engine.add_strategy(strategy)

    # 运行回测
    # result = engine.run(data)
    print("\n组合回测配置完成")


# ========== 示例3：结果可视化 ==========

def example_visualize():
    """结果可视化示例"""
    print("\n" + "="*60)
    print("示例3：结果可视化")
    print("="*60)

    from finquant import get_kline, MAStrategy
    from finquant.core import BacktestEngineV2, BacktestConfig
    from finquant.visualize import BacktestPlotter

    # 获取数据
    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")

    # 运行回测
    strategy = MAStrategy(short_period=5, long_period=20)
    engine = BacktestEngineV2(BacktestConfig(initial_capital=100000))
    engine.add_strategy(strategy)
    result = engine.run(data)

    # 创建可视化
    plotter = BacktestPlotter(result)

    # 输出摘要
    print("\n--- 摘要 ---")
    summary = plotter.summary()
    print(summary)

    # 输出权益曲线
    print("\n--- 权益曲线 ---")
    equity = plotter.equity()
    print(equity)

    # 输出回撤分析
    print("\n--- 回撤分析 ---")
    drawdown = plotter.drawdown()
    print(drawdown)

    # 输出收益分布
    print("\n--- 收益分布 ---")
    returns = plotter.returns()
    print(returns)


# ========== 示例4：策略对比可视化 ==========

def example_compare():
    """策略对比可视化"""
    print("\n" + "="*60)
    print("示例4：策略对比可视化")
    print("="*60)

    from finquant import get_kline, MAStrategy, RSIStrategy
    from finquant.core import BacktestEngineV2, BacktestConfig
    from finquant.visualize import compare_results

    # 获取数据
    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")

    # 策略列表
    strategies = [
        ("MA5-20", MAStrategy(short_period=5, long_period=20)),
        ("MA10-30", MAStrategy(short_period=10, long_period=30)),
        ("RSI", RSIStrategy(period=14, oversold=30, overbought=70)),
    ]

    results = []

    # 逐个回测
    for name, strategy in strategies:
        engine = BacktestEngineV2(BacktestConfig(initial_capital=100000))
        engine.add_strategy(strategy)
        result = engine.run(data)
        result.backtest_id = name
        results.append(result)

    # 对比结果
    comparison = compare_results(results, [s[0] for s in strategies])
    print(comparison)


# ========== 示例5：matplotlib 绘图 ==========

def example_matplotlib():
    """matplotlib 绘图示例"""
    print("\n" + "="*60)
    print("示例5：matplotlib 绘图")
    print("="*60)

    from finquant import get_kline, MAStrategy
    from finquant.core import BacktestEngineV2, BacktestConfig
    from finquant.visualize import BacktestPlotter

    # 获取数据
    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")

    # 运行回测
    strategy = MAStrategy(short_period=5, long_period=20)
    engine = BacktestEngineV2(BacktestConfig(initial_capital=100000))
    engine.add_strategy(strategy)
    result = engine.run(data)

    # 创建可视化
    plotter = BacktestPlotter(result)

    # 绘图 (需要 matplotlib)
    # plotter.plot(backend="matplotlib")
    # 图表已保存到 backtest_result.png

    print("matplotlib 绘图需要安装 matplotlib:")
    print("  pip install matplotlib")
    print("\n使用方法:")
    print("  plotter.plot(backend='matplotlib')")


# ========== 示例6：plotly 交互式图表 ==========

def example_plotly():
    """plotly 交互式图表示例"""
    print("\n" + "="*60)
    print("示例6：plotly 交互式图表")
    print("="*60)

    from finquant import get_kline, MAStrategy
    from finquant.core import BacktestEngineV2, BacktestConfig
    from finquant.visualize import BacktestPlotter

    # 获取数据
    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")

    # 运行回测
    strategy = MAStrategy(short_period=5, long_period=20)
    engine = BacktestEngineV2(BacktestConfig(initial_capital=100000))
    engine.add_strategy(strategy)
    result = engine.run(data)

    # 创建可视化
    plotter = BacktestPlotter(result)

    # 绘图 (需要 plotly)
    # plotter.plot(backend="plotly")
    # 图表已保存到 backtest_result.html

    print("plotly 绘图需要安装 plotly:")
    print("  pip install plotly")
    print("\n使用方法:")
    print("  plotter.plot(backend='plotly')")


# ========== 运行示例 ==========

if __name__ == "__main__":
    # 选择运行哪个示例
    example_visualize()

    # 其他示例
    # example_multi_asset()
    # example_stock_portfolio()
    # example_compare()
    # example_matplotlib()
    # example_plotly()
