"""
finquant - 事件系统模块

提供事件驱动架构的核心组件
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime
import pandas as pd


class EventType(Enum):
    """事件类型"""
    # 数据事件
    BAR = "bar"              # 新K线
    TICK = "tick"            # tick数据

    # 交易事件
    SIGNAL = "signal"        # 交易信号
    ORDER = "order"          # 订单提交
    ORDER_PENDING = "order_pending"    # 订单待执行
    ORDER_REJECTED = "order_rejected" # 订单拒绝
    FILL = "fill"            # 成交
    TRADE = "trade"          # 交易完成（一笔完整的买卖）

    # 组合事件
    POSITION_OPEN = "position_open"   # 开仓
    POSITION_CLOSE = "position_close" # 平仓

    # 风控事件
    RISK_CHECK = "risk_check"        # 风控检查
    RISK_VIOLATION = "risk_violation" # 风控违规

    # 回测事件
    BACKTEST_START = "backtest_start"
    BACKTEST_END = "backtest_end"
    DAY_START = "day_start"
    DAY_END = "day_end"


@dataclass
class Event:
    """事件基类"""
    type: EventType
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""

    def __repr__(self):
        return f"Event({self.type.value}, source={self.source})"


@dataclass
class BarEvent(Event):
    """K线事件"""
    def __init__(self, bar_data: dict):
        super().__init__(EventType.BAR, bar_data)
        self.bar = bar_data

    @property
    def code(self) -> str:
        return self.bar.get('code', '')

    @property
    def close(self) -> float:
        return self.bar.get('close', 0)

    @property
    def open(self) -> float:
        return self.bar.get('open', 0)

    @property
    def high(self) -> float:
        return self.bar.get('high', 0)

    @property
    def low(self) -> float:
        return self.bar.get('low', 0)

    @property
    def volume(self) -> float:
        return self.bar.get('volume', 0)

    @property
    def trade_date(self):
        return self.bar.get('trade_date')


@dataclass
class SignalEvent(Event):
    """信号事件"""
    def __init__(self, code: str, signal: int, strength: float = 1.0):
        super().__init__(EventType.SIGNAL, {'code': code, 'signal': signal, 'strength': strength})
        self.code = code
        self.signal = signal  # 1: buy, -1: sell, 0: hold
        self.strength = strength


@dataclass
class OrderEvent(Event):
    """订单事件"""
    def __init__(
        self,
        code: str,
        action: str,  # BUY / SELL
        volume: int,
        price: float = 0,  # 0 = 市价单
        order_type: str = "MARKET",  # MARKET / LIMIT
    ):
        super().__init__(EventType.ORDER, {
            'code': code,
            'action': action,
            'volume': volume,
            'price': price,
            'order_type': order_type,
            'status': 'PENDING',
        })
        self.code = code
        self.action = action
        self.volume = volume
        self.price = price
        self.order_type = order_type
        self.order_id = None

    def __repr__(self):
        return f"Order({self.action} {self.volume} {self.code} @ {self.price})"


@dataclass
class FillEvent(Event):
    """成交事件"""
    def __init__(
        self,
        order_id: str,
        code: str,
        action: str,
        volume: int,
        price: float,
        commission: float = 0,
    ):
        super().__init__(EventType.FILL, {
            'order_id': order_id,
            'code': code,
            'action': action,
            'volume': volume,
            'price': price,
            'commission': commission,
        })
        self.order_id = order_id
        self.code = code
        self.action = action
        self.volume = volume
        self.price = price
        self.commission = commission


class EventBus:
    """
    事件总线

    负责事件的发布和订阅
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._event_queue: List[Event] = []
        self._history: List[Event] = []
        self._subscribers: Dict[str, List[EventType]] = {}  # 订阅者->订阅的事件

    def subscribe(self, event_type: EventType, handler: Callable, subscriber_name: str = None) -> None:
        """
        订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理函数，接收 Event 参数
            subscriber_name: 订阅者名称（用于调试）
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)

        if subscriber_name:
            if subscriber_name not in self._subscribers:
                self._subscribers[subscriber_name] = []
            self._subscribers[subscriber_name].append(event_type)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """取消订阅"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        """
        发布事件

        Args:
            event: 事件对象
        """
        # 记录历史
        self._history.append(event)

        # 放入队列（异步处理时使用）
        self._event_queue.append(event)

        # 同步分发
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    # 处理异常，避免影响其他处理器
                    print(f"事件处理错误: {e}")

    def clear_queue(self) -> None:
        """清空事件队列"""
        self._event_queue.clear()

    def get_history(self, event_type: EventType = None) -> List[Event]:
        """获取事件历史"""
        if event_type:
            return [e for e in self._history if e.type == event_type]
        return self._history.copy()

    def get_stats(self) -> Dict:
        """获取事件统计"""
        stats = {}
        for event_type in EventType:
            count = len([e for e in self._history if e.type == event_type])
            if count > 0:
                stats[event_type.value] = count
        return stats


class Observer(ABC):
    """
    观察者基类

    实现观察者模式的基类，可以订阅事件
    """

    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.event_bus: Optional[EventBus] = None

    def on_bar(self, event: BarEvent) -> Optional[SignalEvent]:
        """处理K线事件，返回信号事件（可选）"""
        return None

    def on_signal(self, event: SignalEvent) -> None:
        """处理信号事件"""
        pass

    def on_order(self, event: OrderEvent) -> None:
        """处理订单事件"""
        pass

    def on_fill(self, event: FillEvent) -> None:
        """处理成交事件"""
        pass

    def subscribe_to(self, event_bus: EventBus) -> None:
        """订阅事件总线"""
        self.event_bus = event_bus
        self._register_handlers(event_bus)

    def _register_handlers(self, event_bus: EventBus) -> None:
        """注册事件处理器（子类可覆盖）"""
        event_bus.subscribe(EventType.BAR, self._handle_bar)
        event_bus.subscribe(EventType.SIGNAL, self._handle_signal)
        event_bus.subscribe(EventType.ORDER, self._handle_order)
        event_bus.subscribe(EventType.FILL, self._handle_fill)

    def _handle_bar(self, event: Event) -> None:
        """处理K线事件"""
        bar_event = BarEvent(event.data)
        self.on_bar(bar_event)

    def _handle_signal(self, event: Event) -> None:
        """处理信号事件"""
        signal = SignalEvent(
            event.data.get('code', ''),
            event.data.get('signal', 0),
            event.data.get('strength', 1.0)
        )
        self.on_signal(signal)

    def _handle_order(self, event: Event) -> None:
        """处理订单事件"""
        order = OrderEvent(
            code=event.data.get('code', ''),
            action=event.data.get('action', ''),
            volume=event.data.get('volume', 0),
            price=event.data.get('price', 0),
            order_type=event.data.get('order_type', 'MARKET'),
        )
        order.order_id = event.data.get('order_id')
        self.on_order(order)

    def _handle_fill(self, event: Event) -> None:
        """处理成交事件"""
        fill = FillEvent(
            order_id=event.data.get('order_id', ''),
            code=event.data.get('code', ''),
            action=event.data.get('action', ''),
            volume=event.data.get('volume', 0),
            price=event.data.get('price', 0),
            commission=event.data.get('commission', 0),
        )
        self.on_fill(fill)


# 便捷函数
def create_bar_event(code: str, data: dict) -> BarEvent:
    """创建K线事件"""
    bar_data = {
        'code': code,
        'open': data.get('open', 0),
        'high': data.get('high', 0),
        'low': data.get('low', 0),
        'close': data.get('close', 0),
        'volume': data.get('volume', 0),
        'trade_date': data.get('trade_date'),
    }
    return BarEvent(bar_data)


def create_signal_event(code: str, signal: int, strength: float = 1.0) -> SignalEvent:
    """创建信号事件"""
    return SignalEvent(code, signal, strength)


def create_order_event(code: str, action: str, volume: int, price: float = 0) -> OrderEvent:
    """创建订单事件"""
    return OrderEvent(code, action, volume, price)


def create_fill_event(order: OrderEvent, price: float, commission: float) -> FillEvent:
    """创建成交事件"""
    return FillEvent(
        order_id=order.order_id or "",
        code=order.code,
        action=order.action,
        volume=order.volume,
        price=price,
        commission=commission,
    )
