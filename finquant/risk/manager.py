"""
finquant - 风控模块

提供完整的风控功能：
- 仓位管理
- 止损/止盈
- 最大回撤控制
- 风险监控
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskConfig:
    """风控配置"""
    # 仓位控制
    max_position: float = 0.3       # 单票最大仓位比例
    max_total_position: float = 0.9  # 总仓位上限
    min_cash_ratio: float = 0.1     # 最低现金比例

    # 止损止盈
    stop_loss: float = 0.05         # 止损比例 (5%)
    take_profit: float = 0.15        # 止盈比例 (15%)
    trailing_stop: float = 0.03      # 跟踪止损 (3%)

    # 回撤控制
    max_drawdown: float = 0.2        # 最大回撤限制 (20%)
    max_daily_loss: float = 0.05     # 单日最大亏损 (5%)

    # 交易限制
    max_trades_per_day: int = 10    # 单日最大交易次数
    max_trades_per_stock: int = 3    # 单票单日最大交易次数
    min_trade_interval: int = 5     # 最小交易间隔(分钟)

    # 杠杆
    allow_leverage: bool = False     # 是否允许杠杆
    max_leverage: float = 1.0        # 最大杠杆倍数


@dataclass
class RiskState:
    """风控状态"""
    risk_level: RiskLevel = RiskLevel.LOW
    peak_equity: float = 0
    current_drawdown: float = 0
    daily_pnl: float = 0
    daily_trades: int = 0
    stock_trades: Dict[str, int] = field(default_factory=dict)
    last_trade_time: Dict[str, datetime] = field(default_factory=dict)
    stop_loss_triggered: bool = False
    take_profit_triggered: bool = False
    max_drawdown_triggered: bool = False


class RiskManager:
    """
    风控管理器

    功能：
    - 交易前检查
    - 交易后风控
    - 止损/止盈
    - 回撤控制
    """

    def __init__(self, config: RiskConfig = None):
        """
        Args:
            config: 风控配置
        """
        self.config = config or RiskConfig()
        self.state = RiskState()
        self._callbacks: List[Callable] = []

    def reset(self) -> None:
        """重置风控状态"""
        self.state = RiskState()

    # ========== 交易前检查 ==========

    def pre_trade_check(
        self,
        code: str,
        action: str,
        volume: int,
        price: float,
        total_assets: float,
        current_position_value: float = 0,
    ) -> Tuple[bool, str]:
        """
        交易前风控检查

        Args:
            code: 股票代码
            action: BUY/SELL
            volume: 数量
            price: 价格
            total_assets: 总资产
            current_position_value: 当前持仓市值

        Returns:
            (通过检查, 原因)
        """
        # 检查风险等级
        if self.state.risk_level == RiskLevel.CRITICAL:
            return False, "风控已触发，市场关闭"

        # 检查单日交易次数
        if self.state.daily_trades >= self.config.max_trades_per_day:
            return False, f"单日交易次数超限 ({self.config.max_trades_per_day})"

        # 检查单票交易次数
        stock_trades = self.state.stock_trades.get(code, 0)
        if stock_trades >= self.config.max_trades_per_stock:
            return False, f"单票交易次数超限 ({self.config.max_trades_per_stock})"

        # 买入检查
        if action.upper() == "BUY":
            # 检查总仓位
            proposed_value = volume * price
            new_position_value = current_position_value + proposed_value
            position_ratio = new_position_value / total_assets

            if position_ratio > self.config.max_position:
                return False, f"单票仓位超限 ({position_ratio:.1%} > {self.config.max_position:.1%})"

            # 检查总仓位
            total_position_ratio = (current_position_value + proposed_value) / total_assets
            if total_position_ratio > self.config.max_total_position:
                return False, f"总仓位超限 ({total_position_ratio:.1%} > {self.config.max_total_position:.1%})"

            # 检查现金：买入需要资金 = 买入金额 + 预留现金
            required_cash = proposed_value + total_assets * self.config.min_cash_ratio
            available_cash = total_assets - current_position_value
            if required_cash > available_cash:
                return False, f"现金不足 (需要{required_cash:.0f}, 可用{available_cash:.0f})"

            # 检查杠杆
            if self.config.allow_leverage:
                leverage = proposed_value / total_assets
                if leverage > self.config.max_leverage:
                    return False, f"杠杆超限 ({leverage:.1f}x > {self.config.max_leverage:.1f}x)"

        return True, ""

    # ========== 交易后检查 ==========

    def post_trade_check(
        self,
        code: str,
        action: str,
        volume: int,
        price: float,
    ) -> None:
        """
        交易后更新状态
        """
        self.state.daily_trades += 1

        # 更新单票交易次数
        if code not in self.state.stock_trades:
            self.state.stock_trades[code] = 0
        self.state.stock_trades[code] += 1

        # 记录交易时间
        self.state.last_trade_time[code] = datetime.now()

    # ========== 持仓风控 ==========

    def check_positions(
        self,
        positions: Dict[str, dict],
        current_prices: Dict[str, float],
        total_assets: float,
    ) -> List[dict]:
        """
        检查所有持仓

        Args:
            positions: 持仓 {code: {shares, cost, ...}}
            current_prices: 当前价格
            total_assets: 总资产

        Returns:
            需要触发的交易列表
        """
        triggers = []

        for code, pos in positions.items():
            if pos.get('shares', 0) <= 0:
                continue

            if code not in current_prices:
                continue

            shares = pos['shares']
            cost = pos.get('cost', 0)
            avg_cost = cost / shares if shares > 0 else 0
            current_price = current_prices[code]

            # 计算涨跌幅
            pnl_ratio = (current_price - avg_cost) / avg_cost if avg_cost > 0 else 0

            # 止损检查
            if self.config.stop_loss > 0 and pnl_ratio <= -self.config.stop_loss:
                if not self.state.stop_loss_triggered:
                    triggers.append({
                        'code': code,
                        'action': 'SELL',
                        'reason': f'止损: {pnl_ratio:.1%}',
                        'shares': shares,
                    })
                    self.state.stop_loss_triggered = True

            # 止盈检查
            if self.config.take_profit > 0 and pnl_ratio >= self.config.take_profit:
                if not self.state.take_profit_triggered:
                    triggers.append({
                        'code': code,
                        'action': 'SELL',
                        'reason': f'止盈: {pnl_ratio:.1%}',
                        'shares': shares,
                    })
                    self.state.take_profit_triggered = True

        return triggers

    # ========== 回撤控制 ==========

    def check_drawdown(self, current_equity: float) -> Tuple[bool, str]:
        """
        检查回撤

        Args:
            current_equity: 当前权益

        Returns:
            (是否触发, 原因)
        """
        # 更新峰值
        if current_equity > self.state.peak_equity:
            self.state.peak_equity = current_equity
            self.state.current_drawdown = 0
            return True, ""

        # 计算回撤
        if self.state.peak_equity > 0:
            self.state.current_drawdown = (self.state.peak_equity - current_equity) / self.state.peak_equity

        # 检查回撤限制
        if self.state.current_drawdown >= self.config.max_drawdown:
            if not self.state.max_drawdown_triggered:
                self.state.max_drawdown_triggered = True
                return False, f"最大回撤触发: {self.state.current_drawdown:.1%}"

        return True, ""

    # ========== 单日亏损检查 ==========

    def check_daily_loss(self, daily_pnl: float, initial_capital: float) -> bool:
        """
        检查单日亏损

        Args:
            daily_pnl: 当日盈亏
            initial_capital: 初始资金

        Returns:
            是否允许交易
        """
        daily_loss_ratio = abs(daily_pnl) / initial_capital if daily_pnl < 0 else 0

        if daily_loss_ratio >= self.config.max_daily_loss:
            return False

        return True

    # ========== 风险等级更新 ==========

    def update_risk_level(self) -> RiskLevel:
        """根据状态更新风险等级"""
        if self.state.max_drawdown_triggered:
            self.state.risk_level = RiskLevel.CRITICAL
        elif self.state.current_drawdown > self.config.max_drawdown * 0.8:
            self.state.risk_level = RiskLevel.HIGH
        elif self.state.current_drawdown > self.config.max_drawdown * 0.5:
            self.state.risk_level = RiskLevel.MEDIUM
        else:
            self.state.risk_level = RiskLevel.LOW

        return self.state.risk_level

    # ========== 回调 ==========

    def on_risk_event(self, callback: Callable) -> None:
        """注册风控事件回调"""
        self._callbacks.append(callback)

    def _notify_risk_event(self, event: dict) -> None:
        """通知风控事件"""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"风控回调错误: {e}")

    # ========== 统计 ==========

    def get_risk_stats(self) -> dict:
        """获取风控统计"""
        return {
            'risk_level': self.state.risk_level.value,
            'peak_equity': self.state.peak_equity,
            'current_drawdown': self.state.current_drawdown,
            'daily_trades': self.state.daily_trades,
            'stock_trades': self.state.stock_trades,
            'stop_loss_triggered': self.state.stop_loss_triggered,
            'take_profit_triggered': self.state.take_profit_triggered,
            'max_drawdown_triggered': self.state.max_drawdown_triggered,
        }


# ========== 便捷函数 ==========

def create_risk_manager(
    max_position: float = 0.3,
    stop_loss: float = 0.05,
    take_profit: float = 0.15,
    max_drawdown: float = 0.2,
    **kwargs
) -> RiskManager:
    """
    创建风控管理器（便捷函数）

    Args:
        max_position: 单票最大仓位
        stop_loss: 止损比例
        take_profit: 止盈比例
        max_drawdown: 最大回撤

    Returns:
        RiskManager
    """
    config = RiskConfig(
        max_position=max_position,
        stop_loss=stop_loss,
        take_profit=take_profit,
        max_drawdown=max_drawdown,
        **kwargs
    )
    return RiskManager(config)


__all__ = [
    "RiskLevel",
    "RiskConfig",
    "RiskState",
    "RiskManager",
    "create_risk_manager",
]
