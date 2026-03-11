"""
finquant - 订单执行精度模块

提供真实的市场模拟：
- 滑点模型
- 部分成交模拟
- 流动性影响
- 价格冲击
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from enum import Enum
import numpy as np
import pandas as pd


class SlippageModel(Enum):
    """滑点模型"""
    NONE = "none"           # 无滑点
    FIXED = "fixed"         # 固定滑点
    VOLUME_BASED = "volume_based"  # 基于成交量
    VOLATILITY_BASED = "volatility_based"  # 基于波动率


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"        # 市价单
    LIMIT = "limit"          # 限价单
    STOP = "stop"            # 止损单
    STOP_LIMIT = "stop_limit"  # 止损限价单


class FillPolicy(Enum):
    """成交策略"""
    FULL = "full"           # 全部成交
    PARTIAL = "partial"     # 部分成交
    PARTICLE = "particle"   # 粒子成交（更精细）


@dataclass
class MarketCondition:
    """市场条件"""
    bid_price: float = 0     # 买一价
    ask_price: float = 0     # 卖一价
    bid_volume: float = 0   # 买一量
    ask_volume: float = 0    # 卖一量
    spread: float = 0        # 买卖价差
    spread_ratio: float = 0  # 价差比例
    volume: float = 0        # 成交量
    turnover: float = 0     # 成交额
    volatility: float = 0   # 波动率

    @property
    def mid_price(self) -> float:
        """中间价"""
        return (self.bid_price + self.ask_price) / 2 if self.bid_price and self.ask_price else 0

    @property
    def market_impact_coef(self) -> float:
        """市场冲击系数（简化）"""
        # 成交量越大，冲击越小
        if self.volume <= 0:
            return 0.1
        return min(0.1, 1.0 / np.sqrt(self.volume / 1e6))


class OrderExecutor:
    """
    订单执行器

    功能：
    - 滑点计算
    - 部分成交模拟
    - 流动性影响
    - 价格冲击
    """

    def __init__(
        self,
        slippage_model: SlippageModel = SlippageModel.VOLUME_BASED,
        default_slippage: float = 0.001,
        fill_policy: FillPolicy = FillPolicy.PARTIAL,
        max_fill_ratio: float = 0.1,
    ):
        """
        Args:
            slippage_model: 滑点模型
            default_slippage: 默认滑点比例
            fill_policy: 成交策略
            max_fill_ratio: 最大成交比例（相对于成交量）
        """
        self.slippage_model = slippage_model
        self.default_slippage = default_slippage
        self.fill_policy = fill_policy
        self.max_fill_ratio = max_fill_ratio

    def calculate_slippage(
        self,
        direction: str,  # BUY / SELL
        price: float,
        volume: int,
        market_condition: MarketCondition = None,
    ) -> float:
        """
        计算滑点

        Args:
            direction: 买入/卖出
            price: 价格
            volume: 数量
            market_condition: 市场条件

        Returns:
            滑点后的价格
        """
        if self.slippage_model == SlippageModel.NONE:
            return price

        if self.slippage_model == SlippageModel.FIXED:
            slippage = self.default_slippage
            return price * (1 + slippage) if direction == "BUY" else price * (1 - slippage)

        if self.slippage_model == SlippageModel.VOLUME_BASED and market_condition:
            # 基于成交量计算滑点
            # 订单量占成交量的比例
            volume_ratio = volume / market_condition.volume if market_condition.volume > 0 else 0

            # 滑点 = 基础滑点 * (1 + 订单占比)
            slippage = self.default_slippage * (1 + volume_ratio * 10)

            return price * (1 + slippage) if direction == "BUY" else price * (1 - slippage)

        if self.slippage_model == SlippageModel.VOLATILITY_BASED and market_condition:
            # 基于波动率计算滑点
            volatility = market_condition.volatility
            slippage = self.default_slippage * (1 + volatility)

            return price * (1 + slippage) if direction == "BUY" else price * (1 - slippoint)

        return price

    def calculate_market_impact(
        self,
        direction: str,
        volume: int,
        price: float,
        market_condition: MarketCondition = None,
    ) -> float:
        """
        计算市场冲击

        大额订单会导致价格向不利方向移动

        Args:
            direction: 买入/卖出
            volume: 数量
            price: 当前价格
            market_condition: 市场条件

        Returns:
            冲击后的价格调整
        """
        if market_condition is None:
            return 0

        # 计算订单金额占成交额的比例
        order_value = volume * price
        if market_condition.turnover > 0:
            turnover_ratio = order_value / market_condition.turnover
        else:
            turnover_ratio = 0

        # 冲击系数（简化模型）
        impact_coef = market_condition.market_impact_coef

        # 冲击 = 订单占比 * 冲击系数 * 价格
        impact = turnover_ratio * impact_coef * price

        # 买入推高价格，卖出压低价格
        if direction == "BUY":
            return impact
        else:
            return -impact

    def calculate_partial_fill(
        self,
        volume: int,
        market_condition: MarketCondition,
    ) -> Tuple[int, float]:
        """
        计算部分成交

        Args:
            volume: 订单数量
            market_condition: 市场条件

        Returns:
            (实际成交数量, 成交比例)
        """
        if self.fill_policy == FillPolicy.FULL:
            return volume, 1.0

        if market_condition is None:
            return volume, 1.0

        # 可成交数量 = min(订单数量, 卖一/买一量 * 比例)
        if market_condition.ask_volume > 0:
            available = market_condition.ask_volume
        else:
            available = market_condition.volume * self.max_fill_ratio

        # 限制成交比例
        max_volume = int(volume * self.max_fill_ratio)
        filled_volume = min(volume, available, max_volume)

        # 确保整手
        filled_volume = int(filled_volume / 100) * 100

        fill_ratio = filled_volume / volume if volume > 0 else 0

        return filled_volume, fill_ratio

    def execute(
        self,
        direction: str,
        volume: int,
        price: float,
        market_condition: MarketCondition = None,
    ) -> dict:
        """
        执行订单

        Args:
            direction: 买入/卖出
            volume: 数量
            price: 价格
            market_condition: 市场条件

        Returns:
            执行结果 {
                'filled_volume': 成交数量,
                'fill_ratio': 成交比例,
                'fill_price': 成交价格,
                'commission': 手续费,
                'slippage': 滑点,
                'market_impact': 市场冲击,
            }
        """
        # 计算滑点
        slippage_price = self.calculate_slippage(direction, price, volume, market_condition)

        # 计算市场冲击
        impact = self.calculate_market_impact(direction, volume, price, market_condition)

        # 最终成交价
        if direction == "BUY":
            final_price = slippage_price + impact
        else:
            final_price = slippage_price - impact

        # 计算部分成交
        filled_volume, fill_ratio = self.calculate_partial_fill(volume, market_condition)

        # 计算手续费（简化）
        commission = filled_volume * final_price * 0.0003

        return {
            'filled_volume': filled_volume,
            'fill_ratio': fill_ratio,
            'fill_price': final_price,
            'commission': commission,
            'slippage': abs(final_price - price),
            'market_impact': abs(impact),
            'direction': direction,
            'original_volume': volume,
        }

    def simulate_execution(
        self,
        order_list: list,
        price_series: pd.Series,
        volume_series: pd.Series = None,
    ) -> pd.DataFrame:
        """
        批量模拟订单执行

        Args:
            order_list: 订单列表 [{'date', 'direction', 'volume', 'price'}]
            price_series: 价格序列
            volume_series: 成交量序列

        Returns:
            执行结果 DataFrame
        """
        results = []

        for order in order_list:
            date = order['date']
            direction = order['direction']
            volume = order['volume']
            price = order.get('price', 0)

            # 获取当日市场条件
            mc = None
            if volume_series is not None and date in volume_series:
                mc = MarketCondition(
                    volume=volume_series.get(date, 0),
                    volatility=0.02,  # 简化
                )

            # 如果没有指定价格，使用收盘价
            if price == 0 and date in price_series:
                price = price_series[date]

            # 执行
            result = self.execute(direction, volume, price, mc)
            result['date'] = date
            results.append(result)

        return pd.DataFrame(results)


# ========== 便捷函数 ==========

def create_executor(
    slippage_model: str = "volume_based",
    slippage_rate: float = 0.001,
    fill_policy: str = "partial",
) -> OrderExecutor:
    """
    创建订单执行器

    Args:
        slippage_model: 滑点模型 (none/fixed/volume_based/volatility_based)
        slippage_rate: 滑点比例
        fill_policy: 成交策略 (full/partial)

    Returns:
        OrderExecutor
    """
    model_map = {
        "none": SlippageModel.NONE,
        "fixed": SlippageModel.FIXED,
        "volume_based": SlippageModel.VOLUME_BASED,
        "volatility_based": SlippageModel.VOLATILITY_BASED,
    }

    fill_map = {
        "full": FillPolicy.FULL,
        "partial": FillPolicy.PARTIAL,
    }

    return OrderExecutor(
        slippage_model=model_map.get(slippage_model, SlippageModel.VOLUME_BASED),
        default_slippage=slippage_rate,
        fill_policy=fill_map.get(fill_policy, FillPolicy.PARTIAL),
    )


# ========== 简单模拟函数 ==========

def simple_backtest_with_slippage(
    data: pd.DataFrame,
    signals: pd.DataFrame,
    initial_capital: float = 100000,
    slippage_rate: float = 0.001,
) -> dict:
    """
    简单回测（带滑点）

    Args:
        data: K线数据
        signals: 信号 DataFrame ['date', 'code', 'signal']
        initial_capital: 初始资金
        slippage_rate: 滑点比例

    Returns:
        回测结果
    """
    executor = create_executor(slippage_model="fixed", slippage_rate=slippage_rate)

    cash = initial_capital
    position = 0
    trades = []

    for _, signal in signals.iterrows():
        date = signal['date']
        code = signal['code']
        action = signal['signal']

        # 获取价格
        price_data = data[(data['date'] == date) & (data['code'] == code)]
        if price_data.empty:
            continue

        price = price_data.iloc[0]['close']

        if action == 1 and position == 0:  # 买入
            result = executor.execute("BUY", 100, price)
            cost = result['filled_volume'] * result['fill_price'] + result['commission']
            if cost <= cash:
                cash -= cost
                position = result['filled_volume']
                trades.append({
                    'date': date,
                    'action': 'BUY',
                    'price': result['fill_price'],
                    'volume': result['filled_volume'],
                    'slippage': result['slippage'],
                })

        elif action == -1 and position > 0:  # 卖出
            result = executor.execute("SELL", position, price)
            proceeds = result['filled_volume'] * result['fill_price'] - result['commission']
            cash += proceeds
            trades.append({
                'date': date,
                'action': 'SELL',
                'price': result['fill_price'],
                'volume': result['filled_volume'],
                'slippage': result['slippage'],
            })
            position = 0

    # 最终资产
    final_value = cash + position * data.iloc[-1]['close']

    return {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': (final_value - initial_capital) / initial_capital,
        'trades': pd.DataFrame(trades),
    }


__all__ = [
    "SlippageModel",
    "OrderType",
    "FillPolicy",
    "MarketCondition",
    "OrderExecutor",
    "create_executor",
    "simple_backtest_with_slippage",
]
