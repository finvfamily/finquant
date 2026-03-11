"""
finquant - 券商适配器基类

定义券商接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class BrokerOrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"       # 待提交
    SUBMITTED = "SUBMITTED"   # 已提交
    FILLED = "FILLED"        # 已成交
    CANCELLED = "CANCELLED"  # 已撤销
    REJECTED = "REJECTED"    # 已拒绝


@dataclass
class BrokerOrder:
    """券商订单"""
    order_id: str
    broker_order_id: str = ""  # 券商订单号
    code: str = ""
    action: str = ""           # BUY/SELL
    quantity: int = 0          # 委托数量
    price: float = 0          # 委托价格
    filled_quantity: int = 0   # 成交数量
    avg_price: float = 0       # 成交均价
    status: BrokerOrderStatus = BrokerOrderStatus.PENDING
    message: str = ""          # 备注信息
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class BrokerPosition:
    """券商持仓"""
    code: str
    shares: int = 0
    avg_cost: float = 0
    current_price: float = 0
    market_value: float = 0
    profit: float = 0
    profit_ratio: float = 0


@dataclass
class BrokerAccount:
    """券商账户"""
    cash: float = 0
    market_value: float = 0
    total_assets: float = 0
    positions: List[BrokerPosition] = None

    def __post_init__(self):
        if self.positions is None:
            self.positions = []


class BrokerAdapter(ABC):
    """
    券商适配器基类

    定义券商接口规范
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化连接

        Returns:
            bool: 是否初始化成功
        """
        pass

    @abstractmethod
    def get_account(self) -> BrokerAccount:
        """
        获取账户信息

        Returns:
            BrokerAccount: 账户信息
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[BrokerPosition]:
        """
        获取持仓列表

        Returns:
            List[BrokerPosition]: 持仓列表
        """
        pass

    @abstractmethod
    def buy(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET"
    ) -> BrokerOrder:
        """
        买入

        Args:
            code: 股票代码
            quantity: 数量
            price: 价格，0=市价
            order_type: 订单类型

        Returns:
            BrokerOrder: 订单结果
        """
        pass

    @abstractmethod
    def sell(
        self,
        code: str,
        quantity: int,
        price: float = 0,
        order_type: str = "MARKET"
    ) -> BrokerOrder:
        """
        卖出

        Args:
            code: 股票代码
            quantity: 数量
            price: 价格，0=市价
            order_type: 订单类型

        Returns:
            BrokerOrder: 订单结果
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        撤销订单

        Args:
            order_id: 订单ID

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> BrokerOrderStatus:
        """
        获取订单状态

        Args:
            order_id: 订单ID

        Returns:
            BrokerOrderStatus: 订单状态
        """
        pass

    def is_available(self) -> bool:
        """检查是否可用"""
        return self._initialized


# ========== 模拟券商 ==========

class BacktestBroker(BrokerAdapter):
    """
    回测/模拟券商

    不实际下单，只记录
    """

    def __init__(self, initial_cash: float = 100000):
        super().__init__({"initial_cash": initial_cash})
        self._cash = initial_cash
        self._positions: Dict[str, Dict] = {}
        self._orders: Dict[str, BrokerOrder] = {}
        self._order_counter = 0

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def get_account(self) -> BrokerAccount:
        market_value = sum(p["shares"] * p["current_price"] for p in self._positions.values())
        return BrokerAccount(
            cash=self._cash,
            market_value=market_value,
            total_assets=self._cash + market_value,
            positions=[
                BrokerPosition(
                    code=code,
                    shares=data["shares"],
                    avg_cost=data["avg_cost"],
                    current_price=data["current_price"],
                    market_value=data["shares"] * data["current_price"],
                    profit=data["shares"] * (data["current_price"] - data["avg_cost"]),
                )
                for code, data in self._positions.items()
                if data["shares"] > 0
            ]
        )

    def get_positions(self) -> List[BrokerPosition]:
        return self.get_account().positions

    def buy(self, code: str, quantity: int, price: float = 0, order_type: str = "MARKET") -> BrokerOrder:
        self._order_counter += 1
        order_id = f"BT{self._order_counter:06d}"

        # 模拟成交
        filled_price = price if price > 0 else 10.0  # 假设成交价
        cost = quantity * filled_price * 1.001  # 考虑手续费

        if self._cash >= cost:
            self._cash -= cost

            if code not in self._positions:
                self._positions[code] = {"shares": 0, "avg_cost": 0, "current_price": filled_price}

            pos = self._positions[code]
            total_cost = pos["shares"] * pos["avg_cost"] + quantity * filled_price
            pos["shares"] += quantity
            pos["avg_cost"] = total_cost / pos["shares"] if pos["shares"] > 0 else 0

            order = BrokerOrder(
                order_id=order_id,
                broker_order_id=order_id,
                code=code,
                action="BUY",
                quantity=quantity,
                price=price,
                filled_quantity=quantity,
                avg_price=filled_price,
                status=BrokerOrderStatus.FILLED,
            )
        else:
            order = BrokerOrder(
                order_id=order_id,
                code=code,
                action="BUY",
                quantity=quantity,
                price=price,
                status=BrokerOrderStatus.REJECTED,
                message="资金不足",
            )

        self._orders[order_id] = order
        return order

    def sell(self, code: str, quantity: int, price: float = 0, order_type: str = "MARKET") -> BrokerOrder:
        self._order_counter += 1
        order_id = f"BT{self._order_counter:06d}"

        if code not in self._positions or self._positions[code]["shares"] < quantity:
            order = BrokerOrder(
                order_id=order_id,
                code=code,
                action="SELL",
                quantity=quantity,
                price=price,
                status=BrokerOrderStatus.REJECTED,
                message="持仓不足",
            )
        else:
            filled_price = price if price > 0 else 10.0
            revenue = quantity * filled_price * 0.999

            pos = self._positions[code]
            pos["shares"] -= quantity

            self._cash += revenue

            order = BrokerOrder(
                order_id=order_id,
                broker_order_id=order_id,
                code=code,
                action="SELL",
                quantity=quantity,
                price=price,
                filled_quantity=quantity,
                avg_price=filled_price,
                status=BrokerOrderStatus.FILLED,
            )

        self._orders[order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self._orders:
            order = self._orders[order_id]
            if order.status == BrokerOrderStatus.SUBMITTED:
                order.status = BrokerOrderStatus.CANCELLED
                return True
        return False

    def get_order_status(self, order_id: str) -> BrokerOrderStatus:
        if order_id in self._orders:
            return self._orders[order_id].status
        return BrokerOrderStatus.REJECTED


__all__ = [
    "BrokerOrderStatus",
    "BrokerOrder",
    "BrokerPosition",
    "BrokerAccount",
    "BrokerAdapter",
    "BacktestBroker",
]
