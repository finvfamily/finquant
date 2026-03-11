"""
finquant - 订单执行与资金管理模块

Broker 负责订单管理、资金管理、持仓管理
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import uuid
import pandas as pd


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"      # 市价单
    LIMIT = "LIMIT"        # 限价单


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"    # 待提交
    SUBMITTED = "SUBMITTED"  # 已提交
    FILLED = "FILLED"      # 已成交
    PARTIAL_FILLED = "PARTIAL_FILLED"  # 部分成交
    CANCELLED = "CANCELLED"  # 已取消
    REJECTED = "REJECTED"  # 已拒绝


@dataclass
class Order:
    """订单"""
    code: str
    action: str  # BUY / SELL
    volume: int
    price: float = 0  # 限价，0=市价
    order_type: OrderType = OrderType.MARKET
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: OrderStatus = OrderStatus.PENDING
    filled_volume: int = 0
    filled_price: float = 0
    commission: float = 0
    create_time: datetime = field(default_factory=datetime.now)

    def __repr__(self):
        return f"Order({self.order_id[:8]}, {self.action} {self.volume} {self.code}, status={self.status.value})"


@dataclass
class Position:
    """持仓"""
    code: str
    shares: int = 0       # 持仓数量
    cost: float = 0       # 总成本
    avg_cost: float = 0   # 平均成本
    _current_price: float = 0  # 当前价格
    open_date = None      # 开仓日期

    def set_price(self, price: float) -> None:
        """设置当前价格"""
        self._current_price = price

    @property
    def market_value(self) -> float:
        """市值 = 数量 * 当前价"""
        return self.shares * self._current_price

    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏 = (当前价 - 成本价) * 数量"""
        if self.shares == 0:
            return 0
        return (self._current_price - self.avg_cost) * self.shares


class Broker:
    """
    Broker 订单执行器

    职责：
    - 订单管理
    - 持仓管理
    - 资金管理
    - 订单执行
    """

    def __init__(
        self,
        initial_cash: float = 100000,
        commission_rate: float = 0.0003,
        slippage: float = 0,
        position_sizer: Callable = None,
    ):
        """
        Args:
            initial_cash: 初始资金
            commission_rate: 佣金费率
            slippage: 滑点比例
            position_sizer: 仓位计算函数 (broker, code, signal) -> volume
        """
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.slippage = slippage

        # 账户状态
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}  # code -> Position
        self.orders: List[Order] = []
        self.fills: List[Order] = []  # 成交记录

        # 回调
        self.position_sizer = position_sizer
        self.on_fill_callback: List[Callable] = []

    def get_position(self, code: str) -> Position:
        """获取持仓"""
        if code not in self.positions:
            self.positions[code] = Position(code=code)
        return self.positions[code]

    def get_total_assets(self, current_prices: Dict[str, float]) -> float:
        """计算总资产"""
        position_value = 0
        for code, pos in self.positions.items():
            if pos.shares > 0 and code in current_prices:
                position_value += pos.shares * current_prices[code]
        return self.cash + position_value

    def submit_order(self, code: str, action: str, volume: int,
                     price: float = 0, order_type: OrderType = OrderType.MARKET) -> Order:
        """
        提交订单

        Args:
            code: 股票代码
            action: BUY / SELL
            volume: 数量
            price: 价格（限价单）
            order_type: 订单类型

        Returns:
            Order 对象
        """
        order = Order(
            code=code,
            action=action,
            volume=volume,
            price=price,
            order_type=order_type,
        )

        # 初步验证
        if action == "BUY":
            # 买入需要足够资金
            estimated_cost = volume * (price if price > 0 else self._get_estimated_price(code, price))
            total_cost = estimated_cost * (1 + self.commission_rate)
            if total_cost > self.cash:
                order.status = OrderStatus.REJECTED
                return order

        self.orders.append(order)
        order.status = OrderStatus.SUBMITTED
        return order

    def execute_order(self, order: Order, bar_data: dict) -> Optional[Order]:
        """
        执行订单

        Args:
            order: 订单
            bar_data: 当前K线数据

        Returns:
            成交的订单（如果有）
        """
        if order.status != OrderStatus.SUBMITTED:
            return None

        # 获取成交价格
        if order.order_type == OrderType.MARKET:
            # 市价单：以开盘价或当前价成交
            fill_price = bar_data.get('close', bar_data.get('open', 0))
        else:
            # 限价单：检查是否触发
            if order.action == "BUY" and bar_data.get('low', 0) <= order.price:
                fill_price = order.price
            elif order.action == "SELL" and bar_data.get('high', 0) >= order.price:
                fill_price = order.price
            else:
                return None  # 未触发

        # 考虑滑点
        if order.action == "BUY":
            fill_price *= (1 + self.slippage)
        else:
            fill_price *= (1 - self.slippage)

        # 计算成交结果
        order.filled_volume = order.volume
        order.filled_price = fill_price
        order.commission = order.filled_volume * fill_price * self.commission_rate

        # 更新资金和持仓
        if order.action == "BUY":
            cost = order.filled_volume * fill_price + order.commission
            if cost > self.cash:
                # 资金不足，调整成交量
                available_volume = int(self.cash / (fill_price * (1 + self.commission_rate)) / 100) * 100
                if available_volume < 100:
                    order.status = OrderStatus.REJECTED
                    return order
                order.filled_volume = available_volume
                cost = order.filled_volume * fill_price + order.commission

            self.cash -= cost

            # 更新持仓
            pos = self.get_position(order.code)
            old_shares = pos.shares
            old_cost = pos.cost
            new_shares = old_shares + order.filled_volume
            new_cost = old_cost + order.filled_volume * fill_price

            # 首次买入时记录开仓日期
            if old_shares == 0:
                pos.open_date = bar_data.get('trade_date')

            pos.shares = new_shares
            pos.cost = new_cost
            pos.avg_cost = new_cost / new_shares if new_shares > 0 else 0

        else:  # SELL
            pos = self.get_position(order.code)
            if pos.shares < order.filled_volume:
                order.filled_volume = pos.shares

            proceeds = order.filled_volume * fill_price * (1 - self.commission_rate)
            order.commission = order.filled_volume * fill_price * self.commission_rate

            self.cash += proceeds
            pos.shares -= order.filled_volume
            pos.cost = pos.avg_cost * pos.shares

        order.status = OrderStatus.FILLED
        self.fills.append(order)

        # 触发回调
        for callback in self.on_fill_callback:
            callback(order)

        return order

    def get_pending_orders(self, code: str = None) -> List[Order]:
        """获取待成交订单"""
        pending = [o for o in self.orders if o.status == OrderStatus.SUBMITTED]
        if code:
            pending = [o for o in pending if o.code == code]
        return pending

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        for order in self.orders:
            if order.order_id == order_id and order.status == OrderStatus.SUBMITTED:
                order.status = OrderStatus.CANCELLED
                return True
        return False

    def cancel_all_orders(self, code: str = None) -> int:
        """取消所有订单"""
        count = 0
        for order in self.orders:
            if order.status == OrderStatus.SUBMITTED:
                if code is None or order.code == code:
                    order.status = OrderStatus.CANCELLED
                    count += 1
        return count

    def _get_estimated_price(self, code: str, fallback_price: float) -> float:
        """获取估计价格"""
        # 优先使用持仓成本价
        pos = self.get_position(code)
        if pos.shares > 0 and pos.avg_cost > 0:
            return pos.avg_cost
        return fallback_price

    def on_fill(self, callback: Callable) -> None:
        """注册成交回调"""
        self.on_fill_callback.append(callback)

    def get_equity_curve(self) -> pd.DataFrame:
        """获取权益曲线（需要外部注入价格数据）"""
        # 这个需要历史数据配合
        return pd.DataFrame()

    def reset(self) -> None:
        """重置账户"""
        self.cash = self.initial_cash
        self.positions.clear()
        self.orders.clear()
        self.fills.clear()


class Portfolio:
    """
    投资组合管理器

    负责多资产配置和再平衡
    """

    def __init__(self, broker: Broker, target_weights: Dict[str, float] = None):
        """
        Args:
            broker: Broker 实例
            target_weights: 目标权重 {code: weight}
        """
        self.broker = broker
        self.target_weights = target_weights or {}

    def rebalance(self, current_prices: Dict[str, float]) -> List[Order]:
        """
        再平衡组合

        Args:
            current_prices: 当前价格 {code: price}

        Returns:
            执行的订单列表
        """
        total_assets = self.broker.get_total_assets(current_prices)
        orders = []

        # 计算目标持仓
        for code, weight in self.target_weights.items():
            target_value = total_assets * weight
            current_pos = self.broker.get_position(code)
            current_value = current_pos.shares * current_prices.get(code, 0)

            diff_value = target_value - current_value

            if abs(diff_value) < 100:  # 忽略小额差异
                continue

            if diff_value > 0:
                # 买入
                volume = int(diff_value / current_prices.get(code, 1) / 100) * 100
                if volume > 0:
                    order = self.broker.submit_order(code, "BUY", volume)
                    orders.append(order)
            else:
                # 卖出
                volume = current_pos.shares
                if volume > 0:
                    order = self.broker.submit_order(code, "SELL", volume)
                    orders.append(order)

        return orders
