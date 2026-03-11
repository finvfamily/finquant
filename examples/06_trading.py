"""
finquant V2 - 交易信号示例

演示如何使用信号系统进行实盘接入
"""

import time


# ========== 示例1：基础信号系统 ==========

def example_basic_signal():
    """基础信号系统"""
    print("\n" + "="*60)
    print("示例1：基础信号系统")
    print("="*60)

    from finquant import (
        Signal, Action, OrderType,
        buy_signal, sell_signal, hold_signal,
        SignalBus,
    )

    # 创建信号
    signal = buy_signal(
        code="SH600519",
        price=1500,
        quantity=100,
        reason="MA5上穿MA20"
    )

    print(f"\n创建信号: {signal}")
    print(f"  代码: {signal.code}")
    print(f"  动作: {signal.action.value}")
    print(f"  价格: {signal.price}")
    print(f"  数量: {signal.quantity}")
    print(f"  原因: {signal.reason}")

    # 信号转字典
    print(f"\n转字典: {signal.to_dict()}")


# ========== 示例2：信号总线 ==========

def example_signal_bus():
    """信号总线"""
    print("\n" + "="*60)
    print("示例2：信号总线")
    print("="*60)

    from finquant import (
        SignalBus, Action,
        signal_filter_by_action,
        signal_deduplicate,
    )
    from finquant.trading.signal import buy_signal, sell_signal

    # 创建信号总线
    bus = SignalBus()

    # 添加处理器
    received_signals = []

    def handler(signal, context):
        received_signals.append(signal)
        print(f"收到信号: {signal.action.value} {signal.code}")

    bus.subscribe(handler)

    # 添加过滤器
    bus.add_filter(signal_filter_by_action(["BUY"]))  # 只接收买入信号
    bus.add_filter(signal_deduplicate(window_seconds=60))  # 60秒内不重复

    # 发布信号
    print("\n发布买入信号:")
    bus.publish(buy_signal(code="SH600519", reason="金叉1"))

    print("\n发布卖出信号 (会被过滤):")
    bus.publish(sell_signal(code="SH600519", reason="死叉"))

    print("\n发布重复买入信号 (60秒内去重):")
    bus.publish(buy_signal(code="SH600519", reason="金叉2"))

    print(f"\n收到信号数: {len(received_signals)}")


# ========== 示例3：信号发布器 ==========

def example_publisher():
    """信号发布器"""
    print("\n" + "="*60)
    print("示例3：信号发布器")
    print("="*60)

    from finquant import (
        SignalPublisher, ConsoleHandler,
        buy_signal, sell_signal,
    )

    # 创建发布器
    publisher = SignalPublisher()

    # 添加控制台处理器
    publisher.add_handler(ConsoleHandler(verbose=True))

    # 发布信号
    publisher.publish(
        buy_signal(code="SH600519", price=1500, reason="MA金叉")
    )

    publisher.publish(
        sell_signal(code="SH600519", reason="MA死叉")
    )


# ========== 示例4：Webhook 推送 ==========

def example_webhook():
    """Webhook 推送"""
    print("\n" + "="*60)
    print("示例4：Webhook 推送")
    print("="*60)

    from finquant import SignalPublisher, WebhookHandler, buy_signal

    # 创建发布器
    publisher = SignalPublisher()

    # 添加 Webhook 处理器
    # publisher.add_handler(WebhookHandler(
    #     url="https://oapi.dingtalk.com/robot/send?access_token=xxx"
    # ))

    # 注意: 需要真实的 webhook URL 才能测试
    print("Webhook 处理器已配置 (需要真实 URL 才能测试)")
    print("用法:")
    print("""
    publisher = SignalPublisher()
    publisher.add_handler(WebhookHandler(
        url="https://oapi.dingtalk.com/robot/send?access_token=你的token"
    ))
    publisher.publish(buy_signal(code="SH600519", reason="买入"))
    """)


# ========== 示例5：账户管理 ==========

def example_portfolio():
    """账户管理"""
    print("\n" + "="*60)
    print("示例5：账户管理")
    print("="*60)

    from finquant import Portfolio

    # 创建账户
    portfolio = Portfolio(initial_capital=1000000, commission_rate=0.0003)

    print(f"初始资金: {portfolio.initial_capital}")
    print(f"可用现金: {portfolio.get_available_cash()}")

    # 买入
    print("\n--- 买入 SH600519 ---")
    order = portfolio.submit_order("SH600519", "BUY", 1000, price=10.0)
    print(f"订单: {order.code} {order.action} {order.quantity} @ {order.price}")
    print(f"订单状态: {order.status.value}")
    print(f"剩余现金: {portfolio.cash:.2f}")

    # 持仓
    pos = portfolio.get_position("SH600519")
    print(f"持仓: {pos.shares}股, 成本: {pos.avg_cost:.2f}")

    # 卖出
    print("\n--- 卖出 SH600519 ---")
    order = portfolio.submit_order("SH600519", "SELL", 500, price=11.0)
    print(f"订单: {order.code} {order.action} {order.quantity} @ {order.price}")

    # 统计
    print("\n--- 账户统计 ---")
    stats = portfolio.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")


# ========== 示例6：券商适配器 ==========

def example_broker():
    """券商适配器"""
    print("\n" + "="*60)
    print("示例6：券商适配器")
    print("="*60)

    from finquant import BacktestBroker

    # 创建模拟券商
    broker = BacktestBroker(initial_cash=100000)
    broker.initialize()

    print(f"券商初始化: {broker.is_available()}")

    # 买入
    print("\n--- 买入 ---")
    order = broker.buy("SH600519", 1000, price=10.0)
    print(f"订单ID: {order.order_id}")
    print(f"状态: {order.status.value}")
    print(f"成交价: {order.avg_price}")

    # 获取账户
    account = broker.get_account()
    print(f"\n账户现金: {account.cash:.2f}")
    print(f"持仓市值: {account.market_value:.2f}")
    print(f"总资产: {account.total_assets:.2f}")


# ========== 示例7：完整工作流 ==========

def example_full_workflow():
    """完整工作流"""
    print("\n" + "="*60)
    print("示例7：完整工作流")
    print("="*60)

    from finquant import (
        Strategy, Signal, Action, Bar,
        Portfolio,
        SignalBus, SignalPublisher, ConsoleHandler,
        BacktestBroker,
        BacktestEngineV2, BacktestConfig,
        MAStrategy,
    )

    # 1. 创建账户
    portfolio = Portfolio(initial_capital=100000)

    # 2. 创建信号总线
    bus = SignalBus()

    # 3. 创建发布器
    publisher = SignalPublisher()
    publisher.add_handler(ConsoleHandler())

    # 4. 连接信号总线到发布器
    def signal_to_publisher(signal, context):
        publisher.publish(signal, context)

    bus.subscribe(signal_to_publisher)

    # 5. 创建模拟券商
    broker = BacktestBroker(initial_cash=100000)
    broker.initialize()

    print("\n完整工作流配置完成!")
    print("  - 账户: Portfolio")
    print("  - 信号总线: SignalBus")
    print("  - 信号发布: SignalPublisher")
    print("  - 券商: BacktestBroker")

    # 实际使用时连接到引擎
    # engine = BacktestEngineV2(BacktestConfig())
    # engine.set_signal_bus(bus)
    # engine.set_portfolio(portfolio)


# ========== 运行示例 ==========

if __name__ == "__main__":
    example_basic_signal()
    example_signal_bus()
    example_publisher()
    example_webhook()
    example_portfolio()
    example_broker()
    example_full_workflow()
