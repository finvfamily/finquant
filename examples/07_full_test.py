"""
finquant V2 - 完整使用流程测试

模拟真实用户使用回测系统的完整流程
"""

import time
from datetime import datetime, timedelta


def test_full_workflow():
    """
    完整使用流程测试

    模拟真实用户的使用步骤：
    1. 数据获取
    2. 策略开发
    3. 回测运行
    4. 结果分析
    5. 参数优化
    6. 信号输出
    """
    print("\n" + "="*70)
    print(" finquant V2 完整使用流程测试")
    print("="*70)

    # ========== Step 1: 数据获取 ==========
    print("\n" + "-"*50)
    print("Step 1: 获取数据")
    print("-"*50)

    from finquant import get_kline

    # 获取多只股票数据
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

    print(f"获取股票: {codes}")
    print(f"时间范围: {start_date} ~ {end_date}")

    data = get_kline(codes=codes, start=start_date, end=end_date)

    print(f"获取数据: {len(data)} 条")
    print(f"股票数量: {data['code'].nunique()}")
    print(f"日期范围: {data['trade_date'].min()} ~ {data['trade_date'].max()}")

    # ========== Step 2: 策略开发 ==========
    print("\n" + "-"*50)
    print("Step 2: 创建策略")
    print("-"*50)

    from finquant.strategy.base import Strategy, Signal, Action, Bar

    class DualMAStrategy(Strategy):
        """双均线策略"""

        def __init__(self, short_period: int = 5, long_period: int = 20):
            super().__init__("DualMA")
            self.short_period = short_period
            self.long_period = long_period
            self.params = {"short": short_period, "long": long_period}

        def on_bar(self, bar: Bar) -> Signal:
            # 获取历史数据
            history = bar.history('close', self.long_period + 1)
            if len(history) < self.long_period + 1:
                return None

            # 计算均线
            ma_short = history.rolling(self.short_period).mean().iloc[-1]
            ma_long = history.rolling(self.long_period).mean().iloc[-1]
            ma_short_prev = history.rolling(self.short_period).mean().iloc[-2]
            ma_long_prev = history.rolling(self.long_period).mean().iloc[-2]

            # 金叉买入
            if ma_short_prev <= ma_long_prev and ma_short > ma_long:
                return Signal(
                    action=Action.BUY,
                    code=bar.code,
                    strength=1.0,
                    price=bar.close,
                    reason=f"MA{self.short_period}上穿MA{self.long_period}"
                )

            # 死叉卖出
            if ma_short_prev >= ma_long_prev and ma_short < ma_long:
                return Signal(
                    action=Action.SELL,
                    code=bar.code,
                    strength=1.0,
                    price=bar.close,
                    reason=f"MA{self.short_period}下穿MA{self.long_period}"
                )

            return None

    # 创建策略实例
    strategy = DualMAStrategy(short_period=5, long_period=20)

    print(f"策略: {strategy.name}")
    print(f"参数: {strategy.params}")

    # ========== Step 3: 回测运行 ==========
    print("\n" + "-"*50)
    print("Step 3: 运行回测")
    print("-"*50)

    from finquant.core import BacktestEngineV2, BacktestConfig

    # 创建配置
    config = BacktestConfig(
        initial_capital=1000000,      # 初始资金 100万
        commission_rate=0.0003,     # 万三手续费
        slippage=0.001,            # 千一滑点
        max_positions=3,           # 最多3只持仓
        max_single_position=0.3,   # 单票最多30%
    )

    # 创建引擎
    engine = BacktestEngineV2(config)

    # 添加策略
    engine.add_strategy(strategy)

    # 运行回测
    print("运行回测中...")
    start_time = time.time()
    result = engine.run(data)
    elapsed = time.time() - start_time

    print(f"回测完成! 耗时: {elapsed:.2f}秒")

    # ========== Step 4: 结果分析 ==========
    print("\n" + "-"*50)
    print("Step 4: 结果分析")
    print("-"*50)

    print("\n=== 回测结果 ===")
    print(f"初始资金:     {result.initial_capital:>12,.2f}")
    print(f"最终资金:     {result.final_capital:>12,.2f}")
    print(f"总收益率:     {result.total_return*100:>11.2f}%")
    print(f"年化收益率:   {result.annual_return*100:>11.2f}%")
    print(f"夏普比率:     {result.sharpe_ratio:>12.2f}")
    print(f"最大回撤:     {result.max_drawdown*100:>11.2f}%")
    print(f"胜率:         {result.win_rate*100:>11.2f}%")
    print(f"交易次数:     {result.total_trades:>12d}")

    # 权益曲线
    if result.daily_equity:
        print("\n=== 权益曲线 (前5天) ===")
        import pandas as pd
        equity_df = pd.DataFrame(result.daily_equity)
        print(equity_df.head())

    # 交易记录
    if result.trades:
        print(f"\n=== 交易记录 (共{len(result.trades)}笔) ===")
        for i, trade in enumerate(result.trades[:5]):
            print(f"  {i+1}. {trade}")
        if len(result.trades) > 5:
            print(f"  ... 还有 {len(result.trades)-5} 笔")

    # ========== Step 5: 可视化 ==========
    print("\n" + "-"*50)
    print("Step 5: 可视化")
    print("-"*50)

    from finquant.visualize import BacktestPlotter

    plotter = BacktestPlotter(result)

    print("\n--- 摘要 ---")
    print(plotter.summary())

    # ========== Step 6: 多策略比较 ==========
    print("\n" + "-"*50)
    print("Step 6: 多策略比较")
    print("-"*50)

    # 创建不同参数的策略
    strategies = [
        ("MA(5,20)", DualMAStrategy(5, 20)),
        ("MA(10,30)", DualMAStrategy(10, 30)),
        ("MA(20,60)", DualMAStrategy(20, 60)),
    ]

    results = []

    for name, strat in strategies:
        engine = BacktestEngineV2(BacktestConfig(initial_capital=100000))
        engine.add_strategy(strat)
        r = engine.run(data)
        r.backtest_id = name
        results.append(r)
        print(f"{name}: 收益率 {r.total_return*100:.2f}%, 夏普 {r.sharpe_ratio:.2f}")

    from finquant.visualize import compare_results

    print("\n=== 策略对比 ===")
    print(compare_results(results, [s[0] for s in strategies]))

    # ========== Step 7: 参数优化 ==========
    print("\n" + "-"*50)
    print("Step 7: 参数优化")
    print("-"*50)

    from finquant.optimize import BayesianOptimizer, BayesianConfig

    def objective(params):
        """目标函数：最大化夏普比率"""
        short = int(params['short_period'])
        long = int(params['long_period'])

        if short >= long:
            return -999

        strat = DualMAStrategy(short_period=short, long_period=long)
        eng = BacktestEngineV2(BacktestConfig(initial_capital=100000))
        eng.add_strategy(strat)

        try:
            r = eng.run(data)
            return r.sharpe_ratio if r.sharpe_ratio > 0 else -1
        except:
            return -1

    # 贝叶斯优化
    config = BayesianConfig(n_iter=10)
    optimizer = BayesianOptimizer(
        param_bounds={
            'short_period': (3, 15),
            'long_period': (20, 60),
        },
        config=config,
    )

    print("运行贝叶斯优化 (10次迭代)...")
    best_params, best_score = optimizer.optimize(objective, maximize=True, verbose=False)

    print(f"\n最优参数: {best_params}")
    print(f"最优夏普: {best_score:.4f}")

    # ========== Step 8: 信号输出 ==========
    print("\n" + "-"*50)
    print("Step 8: 信号输出")
    print("-"*50)

    from finquant import (
        SignalPublisher, ConsoleHandler,
        buy_signal, sell_signal,
    )

    # 创建发布器
    publisher = SignalPublisher()
    publisher.add_handler(ConsoleHandler(verbose=True))

    # 模拟信号
    print("\n模拟信号输出:")

    # 买入信号
    signal = buy_signal(
        code="SH600519",
        price=1500,
        quantity=100,
        reason="MA5上穿MA20"
    )
    publisher.publish(signal, {"source": "backtest"})

    # 卖出信号
    signal = sell_signal(
        code="SH600519",
        reason="MA5下穿MA20"
    )
    publisher.publish(signal, {"source": "backtest"})

    # ========== Step 9: 账户管理 ==========
    print("\n" + "-"*50)
    print("Step 9: 账户管理")
    print("-"*50)

    from finquant import Portfolio

    # 创建账户
    portfolio = Portfolio(initial_capital=100000, commission_rate=0.0003)

    # 买入
    print("\n--- 买入交易 ---")
    order = portfolio.submit_order("SH600519", "BUY", 1000, price=10.0)
    print(f"买入 1000股 @ 10.0")
    print(f"订单状态: {order.status.value}")
    print(f"剩余现金: {portfolio.cash:.2f}")

    # 卖出
    print("\n--- 卖出交易 ---")
    order = portfolio.submit_order("SH600519", "SELL", 500, price=11.0)
    print(f"卖出 500股 @ 11.0")
    print(f"订单状态: {order.status.value}")
    print(f"剩余现金: {portfolio.cash:.2f}")

    # 统计
    print("\n--- 账户统计 ---")
    stats = portfolio.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # ========== 完成 ==========
    print("\n" + "="*70)
    print(" 测试完成!")
    print("="*70)

    print("""
使用流程总结:
1. get_kline() 获取数据
2. 开发 Strategy 子类
3. BacktestEngineV2 运行回测
4. 查看 result 结果
5. BacktestPlotter 可视化
6. 多策略比较
7. 参数优化 (BayesianOptimizer)
8. SignalPublisher 信号输出
9. Portfolio 账户管理
""")


def test_strategy_templates():
    """
    常用策略模板测试
    """
    print("\n" + "="*70)
    print(" 常用策略模板")
    print("="*70)

    from finquant.strategy.base import Strategy, Signal, Action, Bar

    # ========== 模板1: 突破策略 ==========
    print("\n--- 模板1: 突破策略 ---")

    class BreakoutStrategy(Strategy):
        """价格突破20日高点买入"""

        def __init__(self, period: int = 20):
            super().__init__("Breakout")
            self.period = period

        def on_bar(self, bar: Bar) -> Signal:
            history = bar.history('close', self.period + 1)
            if len(history) < self.period:
                return None

            high_20 = history.rolling(20).max().iloc[-1]
            if bar.close > high_20:
                return Signal(Action.BUY, code=bar.code, reason="突破20日高点")

            return None

    # ========== 模板2: RSI策略 ==========
    print("--- 模板2: RSI策略 ---")

    class RSIStrategy(Strategy):
        """RSI超卖买入，超买卖出"""

        def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
            super().__init__("RSI")
            self.period = period
            self.oversold = oversold
            self.overbought = overbought

        def on_bar(self, bar: Bar) -> Signal:
            history = bar.history('close', self.period + 1)
            if len(history) < self.period:
                return None

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

            if rsi < self.oversold:
                return Signal(Action.BUY, code=bar.code, reason=f"RSI超卖{rsi:.0f}")
            if rsi > self.overbought:
                return Signal(Action.SELL, code=bar.code, reason=f"RSI超买{rsi:.0f}")

            return None

    # ========== 模板3: 布林带策略 ==========
    print("--- 模板3: 布林带策略 ---")

    class BollStrategy(Strategy):
        """布林带突破策略"""

        def __init__(self, period: int = 20, std_dev: float = 2.0):
            super().__init__("Boll")
            self.period = period
            self.std_dev = std_dev

        def on_bar(self, bar: Bar) -> Signal:
            history = bar.history('close', self.period + 1)
            if len(history) < self.period:
                return None

            ma = history.rolling(self.period).mean().iloc[-1]
            std = history.rolling(self.period).std().iloc[-1]
            upper = ma + self.std_dev * std
            lower = ma - self.std_dev * std

            if bar.close > upper:
                return Signal(Action.BUY, code=bar.code, reason=f"突破上轨{upper:.2f}")
            if bar.close < lower:
                return Signal(Action.SELL, code=bar.code, reason=f"突破下轨{lower:.2f}")

            return None

    # ========== 模板4: 成交量策略 ==========
    print("--- 模板4: 成交量策略 ---")

    class VolumeStrategy(Strategy):
        """放量突破策略"""

        def __init__(self, period: int = 20, volume_mult: float = 1.5):
            super().__init__("Volume")
            self.period = period
            self.volume_mult = volume_mult

        def on_bar(self, bar: Bar) -> Signal:
            history = bar.history('close', self.period + 1)
            volume_history = bar.history('volume', self.period + 1)

            if len(history) < self.period:
                return None

            avg_volume = volume_history.rolling(self.period).mean().iloc[-1]
            price_change = (history.iloc[-1] - history.iloc[-2]) / history.iloc[-2]

            if bar.volume > avg_volume * self.volume_mult and price_change > 0.02:
                return Signal(Action.BUY, code=bar.code, reason="放量上涨")
            if bar.volume > avg_volume * self.volume_mult and price_change < -0.02:
                return Signal(Action.SELL, code=bar.code, reason="放量下跌")

            return None

    print("""
策略模板已创建:
- BreakoutStrategy: 突破策略
- RSIStrategy: RSI策略
- BollStrategy: 布林带策略
- VolumeStrategy: 成交量策略

用户只需继承 Strategy 类，实现 on_bar 方法即可!
""")


def test_api_usage():
    """
    简洁 API 测试
    """
    print("\n" + "="*70)
    print(" 简洁 API 测试")
    print("="*70)

    # 方式一: 一行代码回测
    print("\n--- 方式一: bt() ---")

    from finquant import bt

    # 需要先安装 finshare 并获取数据
    # result = bt("SH600519", "ma_cross", short=5, long=20)
    # print(result.summary())

    print("bt() API 需要数据源支持")

    # 方式二: backtest()
    print("\n--- 方式二: backtest() ---")

    from finquant import backtest, get_kline

    print("backtest() API 使用方式:")
    print("""
    data = get_kline(["SH600519"], start="2024-01-01")
    result = backtest(data, "ma_cross", short=5, long=20)
    print(result.summary())
    """)


# ========== 运行测试 ==========

if __name__ == "__main__":
    # 选择运行哪个测试
    test_full_workflow()

    # 策略模板
    # test_strategy_templates()

    # API 测试
    # test_api_usage()
