"""
finquant - 信号模块

定义交易信号
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class Action(Enum):
    """交易动作"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"      # 市价单
    LIMIT = "LIMIT"        # 限价单
    STOP = "STOP"          # 止损单
    STOP_LIMIT = "STOP_LIMIT"  # 止损限价单


class SignalType(Enum):
    """信号类型"""
    ENTRY = "ENTRY"        # 入场
    EXIT = "EXIT"          # 出场
    ADJUST = "ADJUST"      # 调整


@dataclass
class Signal:
    """
    交易信号

    策略生成的买卖信号，包含完整交易信息
    """
    action: Action              # 交易动作
    code: str                  # 股票代码

    # 可选字段
    strength: float = 1.0      # 信号强度 0-1
    price: float = 0          # 指定价格，0=市价
    quantity: int = 0         # 数量，0=自动计算
    order_type: OrderType = OrderType.MARKET  # 订单类型
    signal_type: SignalType = SignalType.ENTRY  # 信号类型

    # 说明
    reason: str = ""           # 信号原因
    tags: Dict[str, Any] = field(default_factory=dict)  # 自定义标签

    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.quantity < 0:
            raise ValueError("quantity must be >= 0")
        if not 0 <= self.strength <= 1:
            raise ValueError("strength must be between 0 and 1")

    @property
    def is_buy(self) -> bool:
        return self.action == Action.BUY

    @property
    def is_sell(self) -> bool:
        return self.action == Action.SELL

    @property
    def is_market(self) -> bool:
        return self.order_type == OrderType.MARKET

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "action": self.action.value,
            "code": self.code,
            "strength": self.strength,
            "price": self.price,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "signal_type": self.signal_type.value,
            "reason": self.reason,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Signal":
        """从字典创建"""
        return cls(
            action=Action(data.get("action", "BUY")),
            code=data["code"],
            strength=data.get("strength", 1.0),
            price=data.get("price", 0),
            quantity=data.get("quantity", 0),
            order_type=OrderType(data.get("order_type", "MARKET")),
            signal_type=SignalType(data.get("signal_type", "ENTRY")),
            reason=data.get("reason", ""),
            tags=data.get("tags", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
        )

    def __repr__(self):
        return f"Signal({self.action.value} {self.code} @ {self.price or '市价'} qty={self.quantity} reason={self.reason})"


# ========== 便捷函数 ==========

def buy_signal(
    code: str,
    strength: float = 1.0,
    price: float = 0,
    quantity: int = 0,
    reason: str = "",
    **tags
) -> Signal:
    """创建买入信号"""
    return Signal(
        action=Action.BUY,
        code=code,
        strength=strength,
        price=price,
        quantity=quantity,
        reason=reason,
        signal_type=SignalType.ENTRY,
        tags=tags,
    )


def sell_signal(
    code: str,
    strength: float = 1.0,
    price: float = 0,
    quantity: int = 0,
    reason: str = "",
    **tags
) -> Signal:
    """创建卖出信号"""
    return Signal(
        action=Action.SELL,
        code=code,
        strength=strength,
        price=price,
        quantity=quantity,
        reason=reason,
        signal_type=SignalType.EXIT,
        tags=tags,
    )


def hold_signal(
    code: str = "",
    reason: str = "",
    **tags
) -> Signal:
    """创建持有信号"""
    return Signal(
        action=Action.HOLD,
        code=code,
        strength=0,
        reason=reason,
        tags=tags,
    )


__all__ = [
    "Action",
    "OrderType",
    "SignalType",
    "Signal",
    "buy_signal",
    "sell_signal",
    "hold_signal",
]
