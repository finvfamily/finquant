"""
finquant - 账户/组合管理

管理持仓、现金、订单
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"      # 待提交
    SUBMITTED = "SUBMITTED"  # 已提交
    FILLED = "FILLED"       # 已成交
    PARTIAL_FILLED = "PARTIAL_FILLED"  # 部分成交
    CANCELLED = "CANCELLED" # 已取消
    REJECTED = "REJECTED"   # 已拒绝


@dataclass
class Position:
    """持仓"""
    code: str
    shares: int = 0           # 持仓数量
    avg_cost: float = 0       # 平均成本
    current_price: float = 0  # 当前价格
    realized_pnl: float = 0   # 已实现盈亏

    @property
    def market_value(self) -> float:
        """市值"""
        return self.shares * self.current_price

    @property
    def cost(self) -> float:
        """持仓成本"""
        return self.shares * self.avg_cost

    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return self.market_value - self.cost

    @property
    def pnl_percent(self) -> float:
        """盈亏比例"""
        if self.cost == 0:
            return 0
        return self.unrealized_pnl / self.cost


@dataclass
class Order:
    """订单"""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    code: str = ""
    action: str = ""         # BUY/SELL
    quantity: int = 0        # 委托数量
    price: float = 0        # 委托价格，0=市价
    filled: int = 0        # 已成交数量
    avg_price: float = 0    # 成交均价
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    @property
    def is_pending(self) -> bool:
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]


class Portfolio:
    """
    账户/组合管理

    管理现金、持仓、订单
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        commission_rate: float = 0.0003,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate

        # 持仓
        self.positions: Dict[str, Position] = {}

        # 订单
        self.orders: List[Order] = []

        # 历史
        self.equity_curve: List[Dict] = []

        # 统计
        self.total_trades = 0
        self.winning_trades = 0

    # ========== 持仓管理 ==========

    def get_position(self, code: str) -> Position:
        """获取持仓"""
        if code not in self.positions:
            self.positions[code] = Position(code=code)
        return self.positions[code]

    def get_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions

    def has_position(self, code: str) -> bool:
        """是否有持仓"""
        return code in self.positions and self.positions[code].shares > 0

    # ========== 现金管理 ==========

    def get_available_cash(self) -> float:
        """可用现金"""
        return self.cash

    def get_total_equity(self, prices: Dict[str, float] = None) -> float:
        """总权益 = 现金 + 市值"""
        market_value = 0
        if prices:
            for code, pos in self.positions.items():
                pos.current_price = prices.get(code, pos.current_price)
                market_value += pos.market_value
        return self.cash + market_value

    # ========== 订单管理 ==========

    def create_order(self, code: str, action: str, quantity: int, price: float = 0) -> Order:
        """创建订单"""
        order = Order(
            code=code,
            action=action.upper(),
            quantity=quantity,
            price=price,
        )
        self.orders.append(order)
        return order

    def submit_order(self, code: str, action: str, quantity: int, price: float = 0) -> Order:
        """提交订单（简化的市价单逻辑）"""
        order = self.create_order(code, action, quantity, price)

        # 模拟成交
        filled_price = price if price > 0 else 0  # 回测中假设成交价

        if action.upper() == "BUY":
            # 检查现金
            cost = quantity * filled_price * (1 + self.commission_rate)
            if self.cash >= cost:
                self.cash -= cost
                pos = self.get_position(code)
                pos.shares += quantity
                pos.avg_cost = (pos.avg_cost * (pos.shares - quantity) + filled_price * quantity) / pos.shares if pos.shares > 0 else 0
                order.status = OrderStatus.FILLED
                order.filled = quantity
                order.avg_price = filled_price
                self.total_trades += 1
            else:
                order.status = OrderStatus.REJECTED
        else:  # SELL
            pos = self.get_position(code)
            if pos.shares >= quantity:
                revenue = quantity * filled_price * (1 - self.commission_rate)
                self.cash += revenue
                pos.shares -= quantity
                pos.realized_pnl += revenue - quantity * pos.avg_cost
                order.status = OrderStatus.FILLED
                order.filled = quantity
                order.avg_price = filled_price
                if revenue - quantity * pos.avg_cost > 0:
                    self.winning_trades += 1
                self.total_trades += 1
            else:
                order.status = OrderStatus.REJECTED

        order.updated_at = datetime.now()
        return order

    def get_orders(self, status: OrderStatus = None) -> List[Order]:
        """获取订单列表"""
        if status:
            return [o for o in self.orders if o.status == status]
        return self.orders

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        for order in self.orders:
            if order.order_id == order_id and order.is_pending:
                order.status = OrderStatus.CANCELLED
                return True
        return False

    # ========== 风控检查 ==========

    def can_buy(self, code: str, price: float, quantity: int) -> bool:
        """是否可以买入"""
        if price <= 0 or quantity <= 0:
            return False
        cost = price * quantity * (1 + self.commission_rate)
        return self.cash >= cost

    def can_sell(self, code: str, quantity: int) -> bool:
        """是否可以卖出"""
        pos = self.get_position(code)
        return pos.shares >= quantity

    # ========== 统计 ==========

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_value = self.get_total_equity()
        total_return = (total_value - self.initial_capital) / self.initial_capital

        return {
            "initial_capital": self.initial_capital,
            "current_capital": total_value,
            "cash": self.cash,
            "total_return": total_return,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "win_rate": self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
            "position_count": len([p for p in self.positions.values() if p.shares > 0]),
        }

    def record_equity(self, prices: Dict[str, float] = None):
        """记录权益曲线"""
        self.equity_curve.append({
            "timestamp": datetime.now(),
            "total_equity": self.get_total_equity(prices),
            "cash": self.cash,
        })

    def __repr__(self):
        return f"Portfolio(cash={self.cash:.2f}, positions={len(self.positions)})"


__all__ = [
    "OrderStatus",
    "Position",
    "Order",
    "Portfolio",
]
