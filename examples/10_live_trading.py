"""
finquant - 实盘交易示例

演示如何使用东方财富行情接口和模拟实盘券商
"""

import time


# ========== 示例1：获取实时行情 ==========

def example_realtime_quote():
    """获取实时行情"""
    print("\n" + "="*60)
    print("示例1：获取实时行情 (东方财富)")
    print("="*60)

    from finquant import get_realtime_quote

    # 获取行情
    codes = ["SH600519", "SZ000001", "SH000001"]
    quotes = get_realtime_quote(codes)

    print(f"\n行情数据:")
    for code, data in quotes.items():
        print(f"\n{code} ({data.get('name')}):")
        print(f"  当前价: {data.get('price')}")
        print(f"  涨跌: {data.get('change')} ({data.get('change_pct')}%)")
        print(f"  成交量: {data.get('volume')}")
        print(f"  成交额: {data.get('amount')}")
        print(f"  最高: {data.get('high')}, 最低: {data.get('low')}")
        print(f"  买一: {data.get('bid')}, 卖一: {data.get('ask')}")


# ========== 示例2：模拟实盘券商 ==========

def example_simulated_broker():
    """模拟实盘券商"""
    print("\n" + "="*60)
    print("示例2：模拟实盘券商")
    print("="*60)

    from finquant import (
        create_simulated_broker,
        get_realtime_quote,
    )

    # 创建券商 (初始资金 10万)
    broker = create_simulated_broker(initial_cash=100000)

    # 初始化
    broker.initialize()

    # 等待行情获取
    time.sleep(1)

    print(f"\n初始账户:")
    account = broker.get_account()
    print(f"  现金: {account.cash:.2f}")
    print(f"  持仓市值: {account.market_value:.2f}")
    print(f"  总资产: {account.total_assets:.2f}")

    # 获取贵州茅台行情
    code = "SH600519"
    quotes = get_realtime_quote([code])
    if code in quotes:
        price = quotes[code].get("price", 0)
        print(f"\n当前 {code} 价格: {price}")

        # 买入 (100股 * 1400 = 140000 > 100000，资金不足)
        # 改为买入10股
        print(f"\n--- 买入 {code} 10股 ---")
        order = broker.buy(code, 10, price=price)
        print(f"订单ID: {order.order_id}")
        print(f"状态: {order.status.value}")
        print(f"成交价: {order.avg_price}")

        # 查看持仓
        account = broker.get_account()
        print(f"\n账户信息:")
        print(f"  现金: {account.cash:.2f}")
        print(f"  持仓数: {len(account.positions)}")

        for pos in account.positions:
            print(f"\n  {pos.code}:")
            print(f"    股数: {pos.shares}")
            print(f"    成本: {pos.avg_cost:.2f}")
            print(f"    当前价: {pos.current_price:.2f}")
            print(f"    市值: {pos.market_value:.2f}")
            print(f"    盈亏: {pos.profit:.2f} ({pos.profit_ratio*100:.2f}%)")

        # 卖出
        print(f"\n--- 卖出 {code} 5股 ---")
        order = broker.sell(code, 5, price=price)
        print(f"订单ID: {order.order_id}")
        print(f"状态: {order.status.value}")

    # 关闭
    broker.close()


# ========== 示例3：信号转实盘 ==========

def example_signal_trading():
    """信号转实盘交易"""
    print("\n" + "="*60)
    print("示例3：信号转实盘交易")
    print("="*60)

    from finquant import (
        Signal, Action, OrderType,
        buy_signal, sell_signal,
        SignalBus,
        create_simulated_broker,
        get_realtime_quote,
    )

    # 创建券商
    broker = create_simulated_broker(initial_cash=100000)
    broker.initialize()
    time.sleep(1)

    # 信号处理器
    def signal_to_order(signal: Signal, context: dict):
        """将信号转换为订单"""
        print(f"\n收到信号: {signal.action.value} {signal.code}")

        # 获取当前价格
        quotes = get_realtime_quote([signal.code])
        price = quotes.get(signal.code, {}).get("price", 0)

        if signal.action == Action.BUY:
            # 简单策略: 买入可用资金的 20%
            account = broker.get_account()
            quantity = int(account.cash * 0.2 / price / 100) * 100

            if quantity > 0:
                order = broker.buy(signal.code, quantity, price=price)
                print(f"  -> 买入: {order.quantity}股 @ {order.avg_price}")
            else:
                print(f"  -> 资金不足")

        elif signal.action == Action.SELL:
            # 卖出全部
            positions = broker.get_positions()
            for pos in positions:
                if pos.code == signal.code and pos.shares > 0:
                    order = broker.sell(signal.code, pos.shares, price=price)
                    print(f"  -> 卖出: {order.quantity}股 @ {order.avg_price}")
                    break

    # 创建信号总线
    bus = SignalBus()
    bus.subscribe(signal_to_order)

    # 发布信号
    print("\n--- 测试买入信号 ---")
    bus.publish(buy_signal(code="SH600519", reason="MA金叉"))

    time.sleep(1)

    print("\n--- 测试卖出信号 ---")
    bus.publish(sell_signal(code="SH600519", reason="MA死叉"))

    # 查看最终账户
    account = broker.get_account()
    print(f"\n--- 最终账户 ---")
    print(f"现金: {account.cash:.2f}")
    print(f"持仓市值: {account.market_value:.2f}")
    print(f"总资产: {account.total_assets:.2f}")

    broker.close()


# ========== 示例4：持续运行实盘 ==========

def example_continuous_trading():
    """持续运行实盘"""
    print("\n" + "="*60)
    print("示例4：持续运行实盘 (按 Ctrl+C 停止)")
    print("="*60)

    import signal
    import sys

    from finquant import (
        create_simulated_broker,
        get_realtime_quote,
    )

    # 创建券商
    broker = create_simulated_broker(initial_cash=100000)
    broker.initialize()

    # 关注的股票
    watch_codes = ["SH600519", "SZ000001", "SH000001"]

    print(f"关注股票: {watch_codes}")
    print("按 Ctrl+C 停止\n")

    running = True

    def signal_handler(sig, frame):
        nonlocal running
        print("\n\n正在停止...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while running:
            # 获取行情
            quotes = get_realtime_quote(watch_codes)

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 行情:")
            for code in watch_codes:
                if code in quotes:
                    q = quotes[code]
                    print(f"  {code}: {q.get('price')} ({q.get('change_pct')}%)")

            # 检查持仓
            account = broker.get_account()
            print(f"\n账户: 现金 {account.cash:.2f}, 持仓 {account.market_value:.2f}, 总计 {account.total_assets:.2f}")

            # 每10秒更新一次
            for _ in range(10):
                if not running:
                    break
                time.sleep(1)

    except KeyboardInterrupt:
        pass

    broker.close()
    print("\n已停止")


# ========== 运行示例 ==========

if __name__ == "__main__":
    from datetime import datetime

    print("="*60)
    print("finquant 实盘交易示例")
    print("="*60)

    example_realtime_quote()
    example_simulated_broker()
    example_signal_trading()

    # 持续运行示例 (可选)
    # example_continuous_trading()
