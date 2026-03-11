"""
finquant V2 - 风控示例

演示如何使用风控功能
"""

import pandas as pd


# ========== 示例1：基础风控 ==========

def example_basic_risk():
    """基础风控示例"""
    print("\n" + "="*60)
    print("示例1：基础风控")
    print("="*60)

    from finquant import get_kline, MAStrategy
    from finquant.core import BacktestEngineV2, BacktestConfig
    from finquant.risk import RiskManager, RiskConfig, RiskLevel, create_risk_manager

    # 创建风控配置
    config = RiskConfig(
        stop_loss=0.05,        # 5% 止损
        take_profit=0.15,     # 15% 止盈
        max_drawdown=0.20,    # 20% 最大回撤
    )

    # 创建风控管理器
    risk_mgr = create_risk_manager(config)

    print(f"止损: {config.stop_loss*100}%")
    print(f"止盈: {config.take_profit*100}%")
    print(f"最大回撤: {config.max_drawdown*100}%")

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

    # 创建策略和引擎
    strategy = MAStrategy(short_period=5, long_period=20)
    engine_config = BacktestConfig(initial_capital=1000000)
    engine = BacktestEngineV2(engine_config)

    # 添加风控观察者
    engine.add_observer(risk_mgr)

    # 添加策略
    engine.add_strategy(strategy)

    # 运行回测
    result = engine.run(data)

    print(f"\n回测结果:")
    print(f"收益率: {result.total_return*100:.2f}%")
    print(f"最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"交易次数: {result.total_trades}")


# ========== 示例2：高级风控 ==========

def example_advanced_risk():
    """高级风控示例"""
    print("\n" + "="*60)
    print("示例2：高级风控")
    print("="*60)

    from finquant import get_kline, MAStrategy
    from finquant.core import BacktestEngineV2, BacktestConfig
    from finquant.risk import (
        RiskManager, RiskConfig, RiskLevel,
        create_risk_manager, OrderExecutor
    )

    # 创建高级风控配置
    config = RiskConfig(
        stop_loss=0.03,           # 3% 止损
        take_profit=0.10,        # 10% 止盈
        max_drawdown=0.15,      # 15% 最大回撤
        max_position=3,          # 最多3只持仓
        max_single_position=0.3, # 单票最多30%
        trailing_stop=0.05,      # 5% 追踪止损
    )

    # 创建风控管理器
    risk_mgr = create_risk_manager(config)

    # 创建订单执行器
    executor = OrderExecutor(
        slippage_model="fixed",
        slippage_rate=0.001,
        fill_policy="full",
    )

    print("风控配置:")
    print(f"  止损: {config.stop_loss*100}%")
    print(f"  止盈: {config.take_profit*100}%")
    print(f"  追踪止损: {config.trailing_stop*100}%")
    print(f"  最大持仓: {config.max_position}")
    print(f"  单票仓位: {config.max_single_position*100}%")


# ========== 示例3：仓位管理 ==========

def example_position_sizing():
    """仓位管理示例"""
    print("\n" + "="*60)
    print("示例3：仓位管理")
    print("="*60)

    from finquant import get_kline, MAStrategy
    from finquant.core import BacktestEngineV2, BacktestConfig

    # 方式1：固定仓位
    print("\n--- 固定半仓 ---")
    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")

    config = BacktestConfig(
        initial_capital=100000,
        max_positions=2,
        max_single_position=0.5,  # 单票最多50%
    )

    engine = BacktestEngineV2(config)
    engine.add_strategy(MAStrategy(short=5, long=20))
    result = engine.run(data)

    print(f"收益率: {result.total_return*100:.2f}%")
    print(f"最大回撤: {result.max_drawdown*100:.2f}%")

    # 方式2：动态仓位
    print("\n--- 动态仓位 ---")
    # 根据信号强度调整仓位
    # 实际使用时需要在策略中实现


# ========== 示例4：执行精度 ==========

def example_execution():
    """执行精度示例"""
    print("\n" + "="*60)
    print("示例4：执行精度")
    print("="*60)

    from finquant.risk import (
        OrderExecutor,
        SlippageModel,
        FillPolicy,
        MarketCondition,
        create_executor,
    )

    # 创建滑点模型
    print("\n滑点模型:")
    print(f"  NONE: {SlippageModel.NONE}")
    print(f"  FIXED: {SlippageModel.FIXED}")
    print(f"  VOLUME_BASED: {SlippageModel.VOLUME_BASED}")
    print(f"  VOLATILITY_BASED: {SlippageModel.VOLATILITY_BASED}")

    # 创建执行器
    executor = create_executor(
        slippage_model=SlippageModel.FIXED,
        slippage_rate=0.001,
        fill_policy=FillPolicy.PARTIAL,
    )

    print(f"\n执行器配置:")
    print(f"  滑点: {executor.slippage_model}")
    print(f"  成交策略: {executor.fill_policy}")

    # 计算滑点
    market = MarketCondition(
        bid_price=10.00,
        ask_price=10.01,
        volume=1000000,
    )

    buy_price = executor.calculate_price(10.00, "BUY", market)
    sell_price = executor.calculate_price(10.01, "SELL", market)

    print(f"\n滑点计算:")
    print(f"  买入价格: 10.00 -> {buy_price:.4f}")
    print(f"  卖出价格: 10.01 -> {sell_price:.4f}")


# ========== 运行示例 ==========

if __name__ == "__main__":
    # 选择运行哪个示例
    example_basic_risk()

    # 其他示例
    # example_advanced_risk()
    # example_position_sizing()
    # example_execution()
