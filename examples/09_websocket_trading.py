"""
finquant - WebSocket 实盘券商示例

演示如何使用 WebSocket 券商适配器进行实盘交易
"""

import json
import time

from finquant.trading.broker import (
    BrokerConfig,
    WsBroker,
    ConnectionState,
    BrokerAccount,
    BrokerOrder,
)


# ========== 示例1：创建 WebSocket 券商 ==========

def example_create_ws_broker():
    """创建 WebSocket 券商"""
    print("\n" + "="*60)
    print("示例1：创建 WebSocket 券商")
    print("="*60)

    from finquant.trading.broker import create_ws_broker

    # 方式1: 使用便捷函数
    broker = create_ws_broker(
        ws_url="wss://example.com/ws",
        account_id="123456",
        password="password",
        timeout=30,
        max_reconnect=5,
    )

    print(f"券商类型: {type(broker).__name__}")
    print(f"配置: ws_url={broker.config.ws_url}")


# ========== 示例2：继承自定义券商 ==========

class MyBroker(WsBroker):
    """
    自定义券商 - 需要实现具体的接口

    示例：实现东方财富/同花顺等券商接口
    """

    def __init__(self, config: BrokerConfig):
        super().__init__(config)

    async def _authenticate(self) -> bool:
        """鉴权实现"""
        # 发送鉴权消息
        auth_msg = {
            "type": "login",
            "data": {
                "account_id": self.config.account_id,
                "password": self.config.password,
            }
        }
        await self._ws.send(json.dumps(auth_msg))

        # 等待鉴权结果
        return True

    async def _send_order(self, order, order_type: str):
        """发送订单实现"""
        msg = {
            "type": "order",
            "data": {
                "order_id": order.order_id,
                "code": order.code,
                "action": order.action,
                "quantity": order.quantity,
                "price": order.price,
                "order_type": order_type,
            }
        }
        await self._ws.send(json.dumps(json.dumps(msg)))
        return {"broker_order_id": f"B{order.order_id}"}

    async def _query_account(self):
        """查询账户"""
        # 发送查询请求
        await self._ws.send(json.dumps({
            "type": "query_account",
            "data": {}
        }))
        # 实际实现需要等待回调
        return BrokerAccount(cash=100000, market_value=0, total_assets=100000)


def example_custom_broker():
    """自定义券商"""
    print("\n" + "="*60)
    print("示例2：自定义券商")
    print("="*60)

    from finquant.trading.broker import BrokerConfig, BrokerAccount
    import json

    # 创建自定义券商
    config = BrokerConfig(
        ws_url="wss://example.com/ws",
        account_id="123456",
        password="password",
    )
    broker = MyBroker(config)

    print(f"自定义券商: {type(broker).__name__}")
    print("需要实现的方法:")
    print("  - _authenticate(): 鉴权")
    print("  - _send_order(): 发送订单")
    print("  - _cancel_order(): 撤销订单")
    print("  - _query_account(): 查询账户")
    print("  - _query_positions(): 查询持仓")


# ========== 示例3：实盘交易流程 ==========

def example_live_trading():
    """实盘交易流程"""
    print("\n" + "="*60)
    print("示例3：实盘交易流程")
    print("="*60)

    # 创建模拟券商（不连接真实WebSocket）
    broker = WsBroker(BrokerConfig(
        ws_url="wss://mock.example.com/ws",
    ))

    # 设置回调
    def on_order_update(order):
        print(f"订单更新: {order.order_id} - {order.status.value}")

    def on_quote_update(code, price):
        print(f"行情更新: {code} = {price}")

    def on_state_change(state: ConnectionState):
        print(f"连接状态: {state.value}")

    broker.on_order_update = on_order_update
    broker.on_quote_update = on_quote_update
    broker.on_connection_state = on_state_change

    # 初始化（这里会启动连接线程）
    # broker.initialize()

    # 注意: 模拟模式下不会真正连接
    print("注意: 需要配置真实 WebSocket URL 才能实盘交易")
    print("\n配置示例:")
    print("""
    # 方式1: 代码配置
    broker = WsBroker(BrokerConfig(
        ws_url="wss://your-broker.com/ws",
        account_id="your_account",
        password="your_password",
    ))

    # 方式2: 继承实现
    class MyBroker(WsBroker):
        async def _authenticate(self):
            # 实现鉴权逻辑
            pass
        async def _send_order(self, order, order_type):
            # 实现下单逻辑
            pass
    """)


# ========== 示例4：对接具体券商 ==========

def example_broker_implementation():
    """券商对接示例"""
    print("\n" + "="*60)
    print("示例4：券商对接示例")
    print("="*60)

    print("""
常见券商 WebSocket 接口实现思路:

1. 东方财富 WebSocket
   - URL: wss://quote.eastmoney.com/ws
   - 鉴权: 需要 account_token
   - 特点: 行情免费, 交易需要开户

2. 同花顺 WebSocket
   - URL: wss://openapi.ttstock.cn/ws
   - 鉴权: 需要 app_id + secret
   - 特点: 需申请API权限

3. 恒生电子 HTS API
   - 需要联系券商获取
   - 特点: 机构用户为主

4. 替代方案: 券商官方 API
   - 华泰: quant.xinguanyao.com
   - 银河: 量化通
   - 中信: 信e投

实现步骤:
1. 继承 WsBroker
2. 实现 _authenticate() 鉴权
3. 实现 _send_order() 下单
4. 实现 _query_account() 查询账户
5. 实现 _query_positions() 查询持仓
6. 处理 _handle_message() 接收消息回调
    """)


# ========== 示例5：信号转实盘 ==========

def example_signal_to_trading():
    """信号转实盘"""
    print("\n" + "="*60)
    print("示例5：信号转实盘")
    print("="*60)

    from finquant import (
        Signal, Action, OrderType,
        buy_signal, sell_signal,
        SignalBus,
    )

    # 1. 创建券商（模拟）
    broker = WsBroker(BrokerConfig(ws_url="wss://mock.example.com/ws"))

    # 2. 创建信号处理器
    def signal_to_order(signal: Signal, context: dict):
        """将信号转换为订单"""
        print(f"收到信号: {signal.action.value} {signal.code}")

        if signal.action == Action.BUY:
            # 计算买入数量
            account = broker.get_account()
            # 简单策略: 每次买入可用资金的 10%
            quantity = int(account.cash * 0.1 / signal.price / 100) * 100

            if quantity > 0:
                order = broker.buy(
                    code=signal.code,
                    quantity=quantity,
                    price=signal.price,
                    order_type=signal.order_type.value,
                )
                print(f"  -> 下单: {order.order_id}")

        elif signal.action == Action.SELL:
            # 获取持仓
            positions = broker.get_positions()
            for pos in positions:
                if pos.code == signal.code and pos.shares > 0:
                    order = broker.sell(
                        code=signal.code,
                        quantity=pos.shares,
                        price=signal.price,
                        order_type=signal.order_type.value,
                    )
                    print(f"  -> 下单: {order.order_id}")
                    break

    # 3. 创建信号总线并订阅
    bus = SignalBus()
    bus.subscribe(signal_to_order)

    # 4. 发布信号测试
    print("\n发布买入信号:")
    bus.publish(buy_signal(code="SH600519", price=1500, reason="MA金叉"))

    print("\n发布卖出信号:")
    bus.publish(sell_signal(code="SH600519", reason="MA死叉"))


# ========== 运行示例 ==========

if __name__ == "__main__":
    example_create_ws_broker()
    example_custom_broker()
    example_live_trading()
    example_broker_implementation()
    example_signal_to_trading()
