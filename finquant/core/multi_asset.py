"""
finquant - 多资产支持模块

支持股票、期货、期权、基金的组合回测
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import pandas as pd
import numpy as np


class AssetType(Enum):
    """资产类型"""
    STOCK = "stock"       # 股票
    FUTURES = "futures"   # 期货
    OPTIONS = "options"   # 期权
    FUND = "fund"         # 基金
    BOND = "bond"         # 债券


@dataclass
class AssetConfig:
    """资产配置"""
    code: str
    asset_type: AssetType
    name: str = ""
    # 期货特有
    multiplier: float = 1.0  # 合约乘数
    margin_ratio: float = 0.1  # 保证金比例
    # 期权特有
    strike_price: float = 0
    expiry_date: str = ""
    option_type: str = ""  # call/put
    # 基金特有
    nav: float = 0


class Position:
    """
    持仓（多资产版本）
    """

    def __init__(self, config: AssetConfig):
        self.config = config
        self.shares: float = 0  # 股票/基金数量
        self.avg_cost: float = 0  # 平均成本
        self.total_cost: float = 0  # 总成本

        # 期货特有
        self.future_position: int = 0  # 持仓手数
        self.long_position: int = 0  # 多头手数
        self.short_position: int = 0  # 空头手数
        self.settlement_price: float = 0  # 结算价

    @property
    def market_value(self) -> float:
        """市值"""
        return self.shares * self.avg_cost

    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return 0  # 需要当前价计算


class MultiAssetBroker:
    """
    多资产 Broker

    支持股票、期货、期权、基金的交易
    """

    def __init__(
        self,
        initial_cash: float = 100000,
        commission_rate: float = 0.0003,
        futures_commission: float = 0.0001,
    ):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_rate = commission_rate
        self.futures_commission = futures_commission

        # 持仓
        self.positions: Dict[str, Position] = {}

        # 资产配置
        self.asset_configs: Dict[str, AssetConfig] = {}

    def register_asset(self, config: AssetConfig) -> None:
        """注册资产"""
        self.asset_configs[config.code] = config
        if config.code not in self.positions:
            self.positions[config.code] = Position(config)

    def buy_stock(self, code: str, volume: int, price: float) -> bool:
        """买入股票"""
        if code not in self.asset_configs:
            return False

        cost = volume * price * (1 + self.commission_rate)
        if cost > self.cash:
            return False

        self.cash -= cost

        pos = self.positions.get(code)
        if pos is None:
            config = self.asset_configs[code]
            pos = Position(config)
            self.positions[code] = pos

        pos.shares += volume
        pos.total_cost += volume * price
        pos.avg_cost = pos.total_cost / pos.shares if pos.shares > 0 else 0

        return True

    def sell_stock(self, code: str, volume: int, price: float) -> bool:
        """卖出股票"""
        pos = self.positions.get(code)
        if pos is None or pos.shares < volume:
            return False

        proceeds = volume * price * (1 - self.commission_rate)
        self.cash += proceeds

        pos.shares -= volume
        pos.total_cost = pos.avg_cost * pos.shares

        return True

    def buy_futures(self, code: str, volume: int, price: float) -> bool:
        """买入期货（开多仓）"""
        config = self.asset_configs.get(code)
        if config is None:
            return False

        # 保证金 = 价格 * 手数 * 乘数 * 保证金比例
        required_margin = price * volume * config.multiplier * config.margin_ratio

        if required_margin > self.cash:
            return False

        self.cash -= required_margin

        pos = self.positions.get(code)
        if pos is None:
            pos = Position(config)
            self.positions[code] = pos

        pos.long_position += volume

        return True

    def sell_futures(self, code: str, volume: int, price: float) -> bool:
        """卖出期货（开空仓）"""
        config = self.asset_configs.get(code)
        if config is None:
            return False

        required_margin = price * volume * config.multiplier * config.margin_ratio

        if required_margin > self.cash:
            return False

        self.cash -= required_margin

        pos = self.positions.get(code)
        if pos is None:
            pos = Position(config)
            self.positions[code] = pos

        pos.short_position += volume

        return True

    def close_futures(self, code: str, volume: int, price: float) -> bool:
        """平仓期货"""
        pos = self.positions.get(code)
        if pos is None:
            return False

        config = pos.config

        # 释放保证金
        released_margin = price * volume * config.multiplier * config.margin_ratio

        # 计算盈亏
        if pos.long_position > 0:
            # 平多仓
            close_volume = min(volume, pos.long_position)
            pnl = (price - pos.settlement_price) * close_volume * config.multiplier
            pos.long_position -= close_volume
        elif pos.short_position > 0:
            # 平空仓
            close_volume = min(volume, pos.short_position)
            pnl = (pos.settlement_price - price) * close_volume * config.multiplier
            pos.short_position -= close_volume
        else:
            return False

        self.cash += released_margin + pnl

        return True

    def get_total_assets(self, prices: Dict[str, float]) -> float:
        """计算总资产"""
        total = self.cash

        for code, pos in self.positions.items():
            if code in prices:
                price = prices[code]

                if pos.config.asset_type == AssetType.STOCK:
                    total += pos.shares * price
                elif pos.config.asset_type == AssetType.FUTURES:
                    # 期货：持仓市值 + 保证金
                    config = pos.config
                    total += (pos.long_position - pos.short_position) * price * config.multiplier
                    # 加上占用保证金（简化计算）
                    total += (pos.long_position + pos.short_position) * price * config.multiplier * config.margin_ratio

        return total

    def get_position_value(self, prices: Dict[str, float]) -> float:
        """获取持仓市值"""
        value = 0
        for code, pos in self.positions.items():
            if code in prices:
                price = prices[code]
                if pos.config.asset_type == AssetType.STOCK:
                    value += pos.shares * price
                elif pos.config.asset_type == AssetType.FUTURES:
                    config = pos.config
                    value += (pos.long_position - pos.short_position) * price * config.multiplier
        return value


class MultiAssetEngine:
    """
    多资产回测引擎
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        commission_rate: float = 0.0003,
        futures_commission: float = 0.0001,
    ):
        self.broker = MultiAssetBroker(
            initial_cash=initial_capital,
            commission_rate=commission_rate,
            futures_commission=futures_commission,
        )

        self.data: Optional[pd.DataFrame] = None
        self.trade_dates: List = []

    def add_stock(self, code: str, name: str = "") -> None:
        """添加股票"""
        config = AssetConfig(
            code=code,
            asset_type=AssetType.STOCK,
            name=name or code,
        )
        self.broker.register_asset(config)

    def add_futures(self, code: str, multiplier: float = 1.0, margin_ratio: float = 0.1) -> None:
        """添加期货"""
        config = AssetConfig(
            code=code,
            asset_type=AssetType.FUTURES,
            multiplier=multiplier,
            margin_ratio=margin_ratio,
        )
        self.broker.register_asset(config)

    def add_fund(self, code: str, name: str = "") -> None:
        """添加基金"""
        config = AssetConfig(
            code=code,
            asset_type=AssetType.FUND,
            name=name or code,
        )
        self.broker.register_asset(config)

    def run(
        self,
        data: pd.DataFrame,
        strategies: Dict[str, Any],
        start_date: str = None,
        end_date: str = None,
    ) -> dict:
        """
        运行多资产回测

        Args:
            data: K线数据
            strategies: {code: strategy} 各资产的策略
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            回测结果
        """
        # 预处理数据
        df = data.copy()
        if start_date:
            df = df[df['trade_date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['trade_date'] <= pd.to_datetime(end_date)]

        self.data = df.sort_values(['trade_date', 'code'])
        self.trade_dates = sorted(df['trade_date'].unique())

        # 记录
        equity_curve = []

        for date in self.trade_dates:
            day_data = df[df['trade_date'] == date]

            # 获取当前价格
            prices = {row['code']: row['close'] for _, row in day_data.iterrows()}

            # 更新结算价
            for code, pos in self.broker.positions.items():
                if code in prices:
                    pos.settlement_price = prices[code]

            # 执行各资产策略
            for code, strategy in strategies.items():
                if code not in prices:
                    continue

                price = prices[code]
                asset_data = day_data[day_data['code'] == code]

                if asset_data.empty:
                    continue

                # 获取信号（简化版）
                signal = self._generate_signal(strategy, asset_data)

                if signal == 1:  # 买入
                    if code in self.broker.asset_configs:
                        config = self.broker.asset_configs[code]
                        if config.asset_type == AssetType.STOCK:
                            # 买入股票
                            amount = self.broker.cash * 0.8  # 80%仓位
                            volume = int(amount / price / 100) * 100
                            if volume > 0:
                                self.broker.buy_stock(code, volume, price)

                elif signal == -1:  # 卖出
                    if code in self.broker.positions:
                        pos = self.broker.positions[code]
                        if pos.config.asset_type == AssetType.STOCK and pos.shares > 0:
                            self.broker.sell_stock(code, pos.shares, price)

            # 记录当日资产
            total_assets = self.broker.get_total_assets(prices)
            equity_curve.append({
                'date': date,
                'cash': self.broker.cash,
                'position_value': self.broker.get_position_value(prices),
                'total_assets': total_assets,
            })

        return {
            'equity_curve': pd.DataFrame(equity_curve),
            'final_assets': equity_curve[-1]['total_assets'] if equity_curve else self.broker.initial_cash,
            'initial_capital': self.broker.initial_cash,
            'total_return': (equity_curve[-1]['total_assets'] / self.broker.initial_capital - 1) if equity_curve else 0,
        }

    def _generate_signal(self, strategy, data) -> int:
        """生成交易信号（简化版）"""
        # 实际应该调用策略的信号生成
        return 0


# ========== 便捷函数 ==========

def create_stock(code: str, name: str = "") -> AssetConfig:
    """创建股票配置"""
    return AssetConfig(code=code, asset_type=AssetType.STOCK, name=name or code)


def create_futures(code: str, multiplier: float = 1.0, margin_ratio: float = 0.1) -> AssetConfig:
    """创建期货配置"""
    return AssetConfig(
        code=code,
        asset_type=AssetType.FUTURES,
        multiplier=multiplier,
        margin_ratio=margin_ratio,
    )


def create_fund(code: str, name: str = "") -> AssetConfig:
    """创建基金配置"""
    return AssetConfig(code=code, asset_type=AssetType.FUND, name=name or code)


__all__ = [
    "AssetType",
    "AssetConfig",
    "Position",
    "MultiAssetBroker",
    "MultiAssetEngine",
    "create_stock",
    "create_futures",
    "create_fund",
]
