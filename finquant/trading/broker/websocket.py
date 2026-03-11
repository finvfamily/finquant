"""
finquant - WebSocket 券商适配器

通用 WebSocket 券商适配器，支持对接多个券商接口
"""

import asyncio
import json
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Awaitable
from urllib.parse import urljoin

import websockets
from websockets.client import WebSocketClientProtocol

from .base import (
    BrokerAdapter,
    BrokerAccount,
    BrokerOrder,
    BrokerOrderStatus,
    BrokerPosition,
)

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    AUTHENTICATED = "AUTHENTICATED"
    ERROR = "ERROR"


@dataclass
class WsMessage:
    """WebSocket 消息"""
    type: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BrokerConfig:
    """券商配置"""
    # 连接配置
    ws_url: str = ""                    # WebSocket URL
    rest_url: str = ""                   # REST API URL (可选)
    timeout: int = 30                    # 超时时间(秒)

    # 鉴权配置
    account_id: str = ""                 # 账户ID
    password: str = ""                   # 密码/Token
    token: str = ""                      # 认证Token

    # 行情配置
    subscribe_quotes: bool = True        # 是否订阅行情
    quote_interval: int = 3              # 行情推送间隔(秒)

    # 重连配置
    max_reconnect: int = 5               # 最大重连次数
    reconnect_interval: int = 5           # 重连间隔(秒)

    # 调试
    debug: bool = False                  # 调试模式


class WsBroker(BrokerAdapter):
    """
    WebSocket 通用券商适配器

    使用方式:
    1. 继承并实现 _send_order, _cancel_order, _query_account, _query_positions 方法
    2. 或使用默认实现（模拟模式）
    """

    def __init__(self, config: BrokerConfig):
        super().__init__(config)
        self.config = config
        self._state = ConnectionState.DISCONNECTED
        self._ws: Optional[WebSocketClientProtocol] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # 订单相关
        self._pending_orders: Dict[str, BrokerOrder] = {}
        self._order_callbacks: Dict[str, Callable] = {}

        # 缓存
        self._cached_account: Optional[BrokerAccount] = None
        self._cached_positions: List[BrokerPosition] = []
        self._quotes: Dict[str, float] = {}  # 实时行情 {code: price}

        # 回调
        self.on_order_update: Optional[Callable[[BrokerOrder], None]] = None
        self.on_quote_update: Optional[Callable[[str, float], None]] = None
        self.on_connection_state: Optional[Callable[[ConnectionState], None]] = None

    # ========== 连接管理 ==========

    def initialize(self) -> bool:
        """初始化连接"""
        try:
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False

    def _run_loop(self):
        """运行异步事件循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_loop())
        self._loop.close()

    async def _connect_loop(self):
        """连接循环"""
        reconnect_count = 0

        while self._running:
            try:
                self._update_state(ConnectionState.CONNECTING)
                logger.info(f"正在连接 {self.config.ws_url}...")

                async with websockets.connect(
                    self.config.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    self._update_state(ConnectionState.CONNECTED)
                    logger.info("WebSocket 连接成功")

                    # 鉴权
                    if not await self._authenticate():
                        logger.error("鉴权失败")
                        self._update_state(ConnectionState.ERROR)
                        await asyncio.sleep(self.config.reconnect_interval)
                        continue

                    self._update_state(ConnectionState.AUTHENTICATED)
                    reconnect_count = 0

                    # 订阅行情
                    if self.config.subscribe_quotes:
                        await self._subscribe_quotes()

                    # 处理消息
                    await self._receive_messages()

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"连接关闭: {e}")
            except Exception as e:
                logger.error(f"连接错误: {e}")
                self._update_state(ConnectionState.ERROR)

            reconnect_count += 1
            if reconnect_count > self.config.max_reconnect:
                logger.error("达到最大重连次数，停止重连")
                break

            if self._running:
                await asyncio.sleep(self.config.reconnect_interval)

        self._update_state(ConnectionState.DISCONNECTED)

    async def _authenticate(self) -> bool:
        """鉴权 - 子类可重写"""
        # 默认实现：直接返回成功
        return True

    async def _subscribe_quotes(self):
        """订阅行情 - 子类可重写"""
        pass

    def _update_state(self, state: ConnectionState):
        """更新连接状态"""
        self._state = state
        if self.on_connection_state:
            self.on_connection_state(state)

    # ========== 消息处理 ==========

    async def _receive_messages(self):
        """接收消息"""
        async for message in self._ws:
            if not self._running:
                break

            try:
                await self._handle_message(message)
            except Exception as e:
                logger.error(f"处理消息失败: {e}")

    async def _handle_message(self, raw_message: str):
        """处理消息 - 子类可重写"""
        if self.config.debug:
            logger.debug(f"收到消息: {raw_message}")

        try:
            msg = json.loads(raw_message)
            msg_type = msg.get("type", "")

            if msg_type == "order_update":
                await self._handle_order_update(msg.get("data", {}))
            elif msg_type == "quote":
                await self._handle_quote(msg.get("data", {}))
            elif msg_type == "account":
                await self._handle_account(msg.get("data", {}))
            else:
                self._handle_custom_message(msg)

        except json.JSONDecodeError:
            logger.warning(f"非JSON消息: {raw_message}")

    async def _handle_order_update(self, data: Dict):
        """处理订单更新"""
        order_id = data.get("order_id", "")
        if order_id in self._pending_orders:
            order = self._pending_orders[order_id]
            order.filled_quantity = data.get("filled_quantity", 0)
            order.avg_price = data.get("avg_price", 0)
            order.status = BrokerOrderStatus(data.get("status", "PENDING"))
            order.updated_at = datetime.now()

            if self.on_order_update:
                self.on_order_update(order)

    async def _handle_quote(self, data: Dict):
        """处理行情"""
        code = data.get("code", "")
        price = data.get("price", 0)
        if code and price > 0:
            self._quotes[code] = price
            if self.on_quote_update:
                self.on_quote_update(code, price)

    def _handle_custom_message(self, msg: Dict):
        """处理自定义消息 - 子类可重写"""
        pass

    # ========== 订单操作 ==========

    def buy(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET"
    ) -> BrokerOrder:
        """买入"""
        order = BrokerOrder(
            order_id=self._generate_order_id(),
            code=code,
            action="BUY",
            quantity=quantity,
            price=price,
            status=BrokerOrderStatus.PENDING,
        )
        self._pending_orders[order.order_id] = order

        asyncio.run_coroutine_threadsafe(
            self._send_order_async(order, order_type),
            self._loop
        )
        return order

    def sell(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET"
    ) -> BrokerOrder:
        """卖出"""
        order = BrokerOrder(
            order_id=self._generate_order_id(),
            code=code,
            action="SELL",
            quantity=quantity,
            price=price,
            status=BrokerOrderStatus.PENDING,
        )
        self._pending_orders[order.order_id] = order

        asyncio.run_coroutine_threadsafe(
            self._send_order_async(order, order_type),
            self._loop
        )
        return order

    async def _send_order_async(self, order: BrokerOrder, order_type: str):
        """发送订单"""
        try:
            order.status = BrokerOrderStatus.SUBMITTED

            # 子类实现实际发送
            result = await self._send_order(order, order_type)

            if result:
                order.broker_order_id = result.get("broker_order_id", order.order_id)
                order.status = BrokerOrderStatus.SUBMITTED
            else:
                order.status = BrokerOrderStatus.REJECTED
                order.message = "发送失败"

        except Exception as e:
            logger.error(f"发送订单失败: {e}")
            order.status = BrokerOrderStatus.REJECTED
            order.message = str(e)

    async def _send_order(self, order: BrokerOrder, order_type: str) -> Optional[Dict]:
        """发送订单 - 子类重写"""
        # 默认实现：模拟成交
        await asyncio.sleep(0.1)
        order.status = BrokerOrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_price = order.price if order.price > 0 else self._quotes.get(order.code, 10.0)
        return {"broker_order_id": order.order_id}

    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        if order_id not in self._pending_orders:
            return False

        order = self._pending_orders[order_id]
        if order.status not in [BrokerOrderStatus.PENDING, BrokerOrderStatus.SUBMITTED]:
            return False

        asyncio.run_coroutine_threadsafe(
            self._cancel_order_async(order_id),
            self._loop
        )
        return True

    async def _cancel_order_async(self, order_id: str):
        """异步撤销订单"""
        try:
            result = await self._cancel_order(order_id)
            if result:
                self._pending_orders[order_id].status = BrokerOrderStatus.CANCELLED
        except Exception as e:
            logger.error(f"撤销订单失败: {e}")

    async def _cancel_order(self, order_id: str) -> bool:
        """撤销订单 - 子类重写"""
        return True

    def get_order_status(self, order_id: str) -> BrokerOrderStatus:
        """获取订单状态"""
        if order_id in self._pending_orders:
            return self._pending_orders[order_id].status
        return BrokerOrderStatus.REJECTED

    # ========== 账户操作 ==========

    def get_account(self) -> BrokerAccount:
        """获取账户信息"""
        # 先尝试异步获取
        if self._loop and self._state == ConnectionState.AUTHENTICATED:
            future = asyncio.run_coroutine_threadsafe(
                self._query_account_async(),
                self._loop
            )
            try:
                account = future.result(timeout=5)
                self._cached_account = account
                return account
            except Exception as e:
                logger.warning(f"异步获取账户失败，使用缓存: {e}")

        # 返回缓存
        if self._cached_account:
            return self._cached_account

        return BrokerAccount()

    async def _query_account_async(self) -> BrokerAccount:
        """异步查询账户"""
        return await self._query_account()

    async def _query_account(self) -> BrokerAccount:
        """查询账户 - 子类重写"""
        # 默认实现
        return BrokerAccount(
            cash=100000,
            market_value=0,
            total_assets=100000,
            positions=[]
        )

    def get_positions(self) -> List[BrokerPosition]:
        """获取持仓列表"""
        if self._loop and self._state == ConnectionState.AUTHENTICATED:
            future = asyncio.run_coroutine_threadsafe(
                self._query_positions_async(),
                self._loop
            )
            try:
                positions = future.result(timeout=5)
                self._cached_positions = positions
                return positions
            except Exception as e:
                logger.warning(f"异步获取持仓失败，使用缓存: {e}")

        return self._cached_positions

    async def _query_positions_async(self) -> List[BrokerPosition]:
        """异步查询持仓"""
        return await self._query_positions()

    async def _query_positions(self) -> List[BrokerPosition]:
        """查询持仓 - 子类重写"""
        return []

    # ========== 行情 ==========

    def get_quote(self, code: str) -> Optional[float]:
        """获取实时行情"""
        return self._quotes.get(code)

    def get_all_quotes(self) -> Dict[str, float]:
        """获取所有行情"""
        return self._quotes.copy()

    # ========== 工具方法 ==========

    def _generate_order_id(self) -> str:
        """生成订单ID"""
        import time
        return f"ORDER{int(time.time() * 1000)}"

    def is_available(self) -> bool:
        """检查是否可用"""
        return self._initialized and self._state == ConnectionState.AUTHENTICATED

    def close(self):
        """关闭连接"""
        self._running = False
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._ws.close() if self._ws else asyncio.sleep(0),
                self._loop
            )


# ========== 便捷函数 ==========

def create_ws_broker(
    ws_url: str,
    account_id: str = "",
    password: str = "",
    **kwargs
) -> WsBroker:
    """创建 WebSocket 券商"""
    config = BrokerConfig(
        ws_url=ws_url,
        account_id=account_id,
        password=password,
        **kwargs
    )
    return WsBroker(config)


__all__ = [
    "BrokerConfig",
    "WsBroker",
    "ConnectionState",
    "create_ws_broker",
]
