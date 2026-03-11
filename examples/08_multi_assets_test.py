"""
finquant V2 - 多品类全量测试

测试不同类型的标的：
- ETF: 510300(沪深300ETF), 512880(证券ETF)
- LOF: 161039(易方达创业板)
- 主板: 600519(茅台), 600036(招商银行)
- 创业板: 300750(宁德时代), 300059(东方财富)
- 科创板: 688981(中芯国际), 688111(华大基因)
"""

import time
from datetime import datetime, timedelta


def test_multi_assets():
    """多品类标的测试"""
    print("\n" + "="*70)
    print(" finquant V2 多品类全量测试")
    print("="*70)

    # ========== Step 1: 数据获取 ==========
    print("\n" + "-"*50)
    print("Step 1: 获取多品类数据")
    print("-"*50)

    from finquant import get_kline

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

    print(f"\n获取数据: {len(data)} 条")
    print(f"标的数量: {data['code'].nunique()}")
    print(f"日期范围: {data['trade_date'].min()} ~ {data['trade_date'].max()}")

    # 统计各类标的
    print("\n标的统计:")
    for code in codes:
        code_data = data[data['code'] == code]
        if not code_data.empty:
            price = code_data['close'].iloc[-1]
            print(f"  {code}: {len(code_data)} 条, 现价 {price:.2f}")

    # ========== Step 2: 策略 ==========
    print("\n" + "-"*50)
    print("Step 2: 创建双均线策略")
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
            history = bar.history('close', self.long_period + 1)
            if len(history) < self.long_period:
                return None

            ma_short = history.rolling(self.short_period).mean().iloc[-1]
            ma_long = history.rolling(self.long_period).mean().iloc[-1]
            ma_short_prev = history.rolling(self.short_period).mean().iloc[-2]
            ma_long_prev = history.rolling(self.long_period).mean().iloc[-2]

            if ma_short_prev <= ma_long_prev and ma_short > ma_long:
                return Signal(
                    action=Action.BUY,
                    code=bar.code,
                    strength=1.0,
                    price=bar.close,
                    reason=f"MA{self.short_period}上穿MA{self.long_period}"
                )

            if ma_short_prev >= ma_long_prev and ma_short < ma_long:
                return Signal(
                    action=Action.SELL,
                    code=bar.code,
                    strength=1.0,
                    price=bar.close,
                    reason=f"MA{self.short_period}下穿MA{self.long_period}"
                )

            return None

    strategy = DualMAStrategy(short_period=5, long_period=20)
    print(f"策略: {strategy.name}")
    print(f"参数: {strategy.params}")

    # ========== Step 3: 回测 ==========
    print("\n" + "-"*50)
    print("Step 3: 运行回测")
    print("-"*50)

    from finquant.core import BacktestEngineV2, BacktestConfig

    # 增加初始资金到100万
    config = BacktestConfig(
        initial_capital=initial_capital,  # 100万
        commission_rate=0.0003,     # 万三手续费
        slippage=0.001,              # 千一滑点
        max_positions=5,             # 最多5只持仓
        max_single_position=0.3,     # 单票最多30%
    )

    engine = BacktestEngineV2(config)
    engine.add_strategy(strategy)

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

    # 交易记录按标的统计
    if result.trades:
        print(f"\n=== 交易记录 (共{len(result.trades)}笔) ===")

        # 按标的统计
        trade_by_code = {}
        for trade in result.trades:
            code = trade.get('code', 'UNKNOWN')
            if code not in trade_by_code:
                trade_by_code[code] = []
            trade_by_code[code].append(trade)

        print("\n按标的统计:")
        total_realized = 0
        for code, trades in sorted(trade_by_code.items()):
            buy_count = sum(1 for t in trades if t.get('action') == 'BUY')
            sell_count = sum(1 for t in trades if t.get('action') == 'SELL')
            # 计算已实现盈亏
            profits = [t.get('profit', 0) for t in trades if t.get('action') == 'SELL']
            total_profit = sum(profits)
            total_realized += total_profit
            print(f"  {code}: 买入{buy_count}次, 卖出{sell_count}次, 盈亏 {total_profit:+.2f}")

        # 计算未实现盈亏（最终持仓）
        last_date = engine.trade_dates[-1] if engine.trade_dates else None
        unrealized_total = 0
        if last_date:
            last_day_data = engine.data[engine.data['trade_date'] == last_date]
            last_prices = {row['code']: row['close'] for _, row in last_day_data.iterrows()}

            print("\n最终持仓未实现盈亏:")
            for code, pos in engine.broker.positions.items():
                if pos.shares > 0:
                    current_price = last_prices.get(code, 0)
                    unrealized = (current_price - pos.avg_cost) * pos.shares
                    unrealized_total += unrealized
                    open_date_str = ""
                    if pos.open_date:
                        if hasattr(pos.open_date, 'strftime'):
                            open_date_str = pos.open_date.strftime('%Y-%m-%d')
                        else:
                            open_date_str = str(pos.open_date)[:10]
                    print(f"  {code}: {pos.shares}股, 开仓 {open_date_str}, 成本{pos.avg_cost:.2f}, 现价{current_price:.2f}, 盈亏 {unrealized:+.2f}")

        print(f"\n已实现盈亏合计: {total_realized:+.2f}")
        print(f"未实现盈亏合计: {unrealized_total:+.2f}")
        print(f"总盈亏: {total_realized + unrealized_total:+.2f}")

    # 最终持仓
    print("\n=== 最终持仓 ===")
    # 获取最后一天的价格
    last_date = engine.trade_dates[-1] if engine.trade_dates else None
    if last_date:
        last_day_data = engine.data[engine.data['trade_date'] == last_date]
        last_prices = {row['code']: row['close'] for _, row in last_day_data.iterrows()}

        for code, pos in engine.broker.positions.items():
            if pos.shares > 0:
                # 设置当前价格
                current_price = last_prices.get(code, 0)
                pos.set_price(current_price)
                unrealized_pnl = pos.unrealized_pnl
                # 格式化开仓日期
                open_date_str = ""
                if pos.open_date:
                    if hasattr(pos.open_date, 'strftime'):
                        open_date_str = pos.open_date.strftime('%Y-%m-%d')
                    else:
                        open_date_str = str(pos.open_date)[:10]
                print(f"  {code}: {pos.shares}股, 开仓 {open_date_str}, 成本 {pos.avg_cost:.2f}, 现价 {current_price:.2f}, 现值 {pos.market_value:.2f}, 盈亏 {unrealized_pnl:+.2f}")

    # ========== Step 5: 可视化 ==========
    print("\n" + "-"*50)
    print("Step 5: 可视化")
    print("-"*50)

    from finquant.visualize import BacktestPlotter

    plotter = BacktestPlotter(result)
    print("\n" + plotter.summary())

    # ========== 完成 ==========
    print("\n" + "="*70)
    print(" 测试完成!")
    print("="*70)

    print(f"""
多品类测试总结:
- 初始资金: {initial_capital:,}
- 标的数量: {len(codes)}
- 标的类型: ETF({2}), LOF({1}), 主板({2}), 创业板({2}), 科创板({2})
- 交易次数: {result.total_trades}
- 总收益: {result.total_return*100:.2f}%
""")


def test_etf_only():
    """仅ETF测试"""
    print("\n" + "="*70)
    print(" 仅ETF测试")
    print("="*70)

    from finquant import get_kline
    from finquant.strategy.base import Strategy, Signal, Action, Bar
    from finquant.core import BacktestEngineV2, BacktestConfig

    # ETF 标的
    codes = [
        "SH510300",  # 沪深300ETF
        "SH512880",  # 证券ETF
        "SH513050",  # 消费ETF
        "SH512690",  # 医药ETF
    ]

    data = get_kline(codes=codes, start="2024-01-01", end="2025-01-01")
    print(f"获取 {len(codes)} 只ETF数据: {len(data)} 条")

    class DualMAStrategy(Strategy):
        def __init__(self, short=5, long=20):
            super().__init__("DualMA")
            self.short = short
            self.long = long

        def on_bar(self, bar: Bar) -> Signal:
            history = bar.history('close', self.long + 1)
            if len(history) < self.long:
                return None

            ma_short = history.rolling(self.short).mean().iloc[-1]
            ma_long = history.rolling(self.long).mean().iloc[-1]
            ma_short_prev = history.rolling(self.short).mean().iloc[-2]
            ma_long_prev = history.rolling(self.long).mean().iloc[-2]

            if ma_short_prev <= ma_long_prev and ma_short > ma_long:
                return Signal(action=Action.BUY, code=bar.code, strength=1.0)

            if ma_short_prev >= ma_long_prev and ma_short < ma_long:
                return Signal(action=Action.SELL, code=bar.code, strength=1.0)

            return None

    engine = BacktestEngineV2(BacktestConfig(initial_capital=1000000))
    engine.add_strategy(DualMAStrategy(5, 20))
    result = engine.run(data)

    print(f"\n=== ETF回测结果 ===")
    print(f"收益率: {result.total_return*100:.2f}%")
    print(f"交易次数: {result.total_trades}")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")


# ========== 运行测试 ==========

if __name__ == "__main__":
    # 多品类全量测试
    test_multi_assets()

    # 仅ETF测试
    # test_etf_only()
