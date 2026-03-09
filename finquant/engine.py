"""
finquant - 轻量级量化回测引擎
纯 Python 脚本，无需服务端和数据缓存
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Callable
import pandas as pd
import numpy as np

# 从 result 模块导入 BacktestResult
from finquant.result import BacktestResult


class PositionSizer:
    """仓位控制器基类"""

    def calculate_size(self, engine: 'BacktestEngine', code: str, signal: int, price: float) -> float:
        """
        计算买入仓位比例 (0.0 - 1.0)

        Args:
            engine: 回测引擎
            code: 股票代码
            signal: 信号强度 (1=买入, -1=卖出, 0=持有)
            price: 当前价格

        Returns:
            float: 仓位比例 (0.0-1.0)
        """
        raise NotImplementedError


class FixedPositionSizer(PositionSizer):
    """固定仓位比例"""

    def __init__(self, position_ratio: float = 0.8):
        """
        Args:
            position_ratio: 仓位比例 (0.0-1.0)，默认 80%
        """
        self.position_ratio = max(0.0, min(1.0, position_ratio))

    def calculate_size(self, engine: 'BacktestEngine', code: str, signal: int, price: float) -> float:
        return self.position_ratio if signal == 1 else 0.0


class DynamicPositionSizer(PositionSizer):
    """动态仓位 - 根据信号强度调整仓位"""

    def __init__(self, base_ratio: float = 0.5, max_ratio: float = 1.0):
        """
        Args:
            base_ratio: 基础仓位比例
            max_ratio: 最大仓位比例
        """
        self.base_ratio = base_ratio
        self.max_ratio = max_ratio

    def calculate_size(self, engine: 'BacktestEngine', code: str, signal: int, price: float) -> float:
        # 根据信号强度计算仓位
        # signal 为 1 时使用基础仓位，为 -1 时清仓
        if signal == 1:
            return self.base_ratio
        elif signal == -1:
            return 0.0
        return engine.get_position_ratio(code)


class PyramidPositionSizer(PositionSizer):
    """金字塔仓位 - 浮盈越多，仓位越大"""

    def __init__(self, base_ratio: float = 0.2, max_ratio: float = 1.0, step: float = 0.1):
        """
        Args:
            base_ratio: 基础仓位比例
            max_ratio: 最大仓位比例
            step: 每次加仓比例
        """
        self.base_ratio = base_ratio
        self.max_ratio = max_ratio
        self.step = step

    def calculate_size(self, engine: 'BacktestEngine', code: str, signal: int, price: float) -> float:
        if signal != 1:
            return 0.0

        # 获取当前持仓
        pos = engine.positions.get(code, {"shares": 0})
        if pos["shares"] == 0:
            return self.base_ratio

        # 根据持仓盈亏调整仓位
        cost = pos["cost"] / pos["shares"] if pos["shares"] > 0 else price
        profit_ratio = (price - cost) / cost if cost > 0 else 0

        # 浮盈越多，仓位越大
        levels = int(profit_ratio / self.step)  # 每 10% 浮盈加一层
        ratio = min(self.base_ratio + levels * self.step, self.max_ratio)

        return ratio


class CounterPyramidPositionSizer(PositionSizer):
    """倒金字塔仓位 - 浮亏越多，仓位越小"""

    def __init__(self, base_ratio: float = 0.8, min_ratio: float = 0.1):
        """
        Args:
            base_ratio: 基础仓位比例
            min_ratio: 最小仓位比例
        """
        self.base_ratio = base_ratio
        self.min_ratio = min_ratio

    def calculate_size(self, engine: 'BacktestEngine', code: str, signal: int, price: float) -> float:
        if signal != 1:
            return 0.0

        pos = engine.positions.get(code, {"shares": 0})
        if pos["shares"] == 0:
            return self.base_ratio

        # 根据持仓盈亏调整仓位
        cost = pos["cost"] / pos["shares"] if pos["shares"] > 0 else price
        profit_ratio = (price - cost) / cost if cost > 0 else 0

        # 浮亏越多，仓位越小
        if profit_ratio < 0:
            ratio = self.base_ratio * (1 + profit_ratio)  # 亏损 10% 则仓位减少 10%
            ratio = max(ratio, self.min_ratio)
        else:
            ratio = self.base_ratio

        return ratio


class ATRPositionSizer(PositionSizer):
    """ATR 仓位 - 根据波动率调整仓位"""

    def __init__(self, risk_ratio: float = 0.02, atr_period: int = 14):
        """
        Args:
            risk_ratio: 风险比例 (每次交易风险金额占比)
            atr_period: ATR 周期
        """
        self.risk_ratio = risk_ratio
        self.atr_period = atr_period
        self.atr_cache: Dict[str, float] = {}

    def calculate_size(self, engine: 'BacktestEngine', code: str, signal: int, price: float) -> float:
        if signal != 1:
            return 0.0

        # 尝试从缓存获取 ATR
        atr = self.atr_cache.get(code)
        if atr is None:
            # 需要从历史数据计算 ATR（简化版本）
            return 0.5  # 默认半仓

        # 根据 ATR 计算仓位
        # 风险金额 = 总资产 * risk_ratio
        # 仓位 = 风险金额 / (价格 * ATR倍数)
        total_assets = engine.get_total_assets()
        risk_amount = total_assets * self.risk_ratio

        # 假设止损为 2 倍 ATR
        stop_loss = atr * 2
        shares = risk_amount / stop_loss

        # 转换为仓位比例
        position_value = shares * price
        ratio = position_value / total_assets

        return min(ratio, 1.0)


class BacktestEngine:
    """
    轻量级回测引擎

    使用 finshare 获取数据，纯 Python 脚本，无需缓存
    支持多种仓位控制策略
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        position_sizer: PositionSizer = None,
        max_positions: int = 5,
        max_single_position: float = 0.3,
    ):
        """
        初始化回测引擎

        Args:
            initial_capital: 初始资金
            commission_rate: 佣金费率（默认万三）
            position_sizer: 仓位控制器，默认固定 80% 仓位
            max_positions: 最大持仓股票数，默认 5 只
            max_single_position: 单只股票最大仓位比例，默认 30%
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate

        # 仓位控制
        self.position_sizer = position_sizer or FixedPositionSizer(0.8)
        self.max_positions = max_positions
        self.max_single_position = max_single_position

        # 账户状态
        self.cash = initial_capital
        self.positions: Dict[str, Dict] = {}  # {code: {"shares": x, "cost": y}}
        self.history: List[Dict] = []  # 每日历史

    def get_total_assets(self) -> float:
        """获取总资产"""
        return self.cash + self.get_position_value()

    def get_position_value(self) -> float:
        """获取持仓市值"""
        # 需要外部传入当前价格，这里简化返回最近记录
        if self.history:
            return self.history[-1].get("position_value", 0)
        return 0

    def get_position_ratio(self, code: str) -> float:
        """获取指定股票的持仓比例"""
        total_assets = self.get_total_assets()
        if total_assets == 0:
            return 0

        pos = self.positions.get(code, {"shares": 0})
        if pos["shares"] == 0:
            return 0

        # 需要外部传入价格计算市值
        return 0  # 简化

    def can_buy(self, code: str) -> bool:
        """是否可以买入"""
        # 检查持仓数量限制
        current_positions = sum(1 for p in self.positions.values() if p["shares"] > 0)
        if current_positions >= self.max_positions:
            return False

        # 检查单票仓位限制
        # (需要在买入时检查)
        return True

    def run(
        self,
        data: pd.DataFrame,
        strategy,
        start_date: date = None,
        end_date: date = None,
    ) -> BacktestResult:
        """
        运行回测

        Args:
            data: K线数据，columns=[code, trade_date, open, high, low, close, volume]
            strategy: 策略实例，需实现 generate_signals(df, current_date) -> signal
            start_date: 回测开始日期
            end_date: 回测结束日期

        Returns:
            BacktestResult: 回测结果
        """
        # 筛选日期范围
        if start_date:
            data = data[data["trade_date"] >= pd.to_datetime(start_date)]
        if end_date:
            data = data[data["trade_date"] <= pd.to_datetime(end_date)]

        # 获取交易日列表
        trade_dates = sorted(data["trade_date"].unique())

        # 初始化结果
        result = BacktestResult()
        result.backtest_id = f"bt_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result.start_date = trade_dates[0] if trade_dates else start_date
        result.end_date = trade_dates[-1] if trade_dates else end_date
        result.initial_capital = self.initial_capital

        # 重置账户
        self.cash = self.initial_capital
        self.positions = {}
        self.history = []

        # 逐日回测
        for i, current_date in enumerate(trade_dates):
            # 获取当日数据
            day_data = data[data["trade_date"] == current_date]

            # 获取当前各股票价格
            current_prices = {}
            for _, row in day_data.iterrows():
                current_prices[row["code"]] = row["close"]

            # 获取持仓市值
            total_position_value = 0
            for code, pos in self.positions.items():
                if pos["shares"] > 0 and code in current_prices:
                    total_position_value += pos["shares"] * current_prices[code]

            # 记录当日资产
            total_assets = self.cash + total_position_value
            self.history.append({
                "date": current_date,
                "cash": self.cash,
                "position_value": total_position_value,
                "total_assets": total_assets,
            })

            # 获取各股票信号并执行交易
            for _, row in day_data.iterrows():
                code = row["code"]
                current_price = row["close"]

                # 生成信号
                signal = strategy.generate_signals(data, code, current_date)

                if signal == 1:  # 买入
                    # 使用仓位控制器计算仓位
                    position_ratio = self.position_sizer.calculate_size(self, code, signal, current_price)

                    # 检查是否超过单票最大仓位
                    current_position_value = self.positions.get(code, {"shares": 0})["shares"] * current_price
                    total_assets = self.cash + total_position_value
                    current_ratio = current_position_value / total_assets if total_assets > 0 else 0

                    if current_ratio >= self.max_single_position:
                        continue  # 超过单票最大仓位，不买入

                    # 检查持仓数量限制
                    current_positions = sum(1 for p in self.positions.values() if p["shares"] > 0)
                    if current_positions >= self.max_positions and code not in self.positions:
                        continue  # 超过最大持仓数，且不是加仓

                    # 计算买入金额
                    buy_amount = total_assets * position_ratio
                    shares = int(buy_amount / current_price / 100) * 100  # 整手

                    if shares > 0:
                        cost = shares * current_price * (1 + self.commission_rate)
                        if cost <= self.cash:
                            self.cash -= cost

                            if code not in self.positions:
                                self.positions[code] = {"shares": 0, "cost": 0}

                            old_shares = self.positions[code]["shares"]
                            old_cost = self.positions[code]["cost"]
                            new_shares = old_shares + shares
                            new_cost = old_cost + shares * current_price
                            self.positions[code] = {"shares": new_shares, "cost": new_cost}

                            result.trades.append({
                                "date": current_date,
                                "code": code,
                                "action": "BUY",
                                "price": current_price,
                                "shares": shares,
                                "amount": cost,
                            })

                elif signal == -1:  # 卖出
                    pos = self.positions.get(code, {"shares": 0})
                    if pos["shares"] > 0:
                        shares = pos["shares"]
                        proceeds = shares * current_price * (1 - self.commission_rate)

                        result.trades.append({
                            "date": current_date,
                            "code": code,
                            "action": "SELL",
                            "price": current_price,
                            "shares": shares,
                            "amount": proceeds,
                            "profit": proceeds - pos["cost"],
                        })

                        self.cash += proceeds
                        self.positions[code]["shares"] = 0
                        self.positions[code]["cost"] = 0

        # 计算最终资产
        final_day_data = data[data["trade_date"] == trade_dates[-1]]
        final_position_value = 0
        for code, pos in self.positions.items():
            if pos["shares"] > 0:
                code_data = final_day_data[final_day_data["code"] == code]
                if not code_data.empty:
                    current_price = code_data.iloc[0]["close"]
                    final_position_value += pos["shares"] * current_price

        result.final_capital = self.cash + final_position_value

        # 计算统计指标
        self._calculate_stats(result, trade_dates)

        return result

    def _calculate_stats(self, result: BacktestResult, trade_dates: List):
        """计算统计指标"""
        # 总收益率
        result.total_return = (result.final_capital - result.initial_capital) / result.initial_capital

        # 年化收益率
        days = len(trade_dates)
        years = days / 252
        if years > 0:
            result.annual_return = (1 + result.total_return) ** (1 / years) - 1

        # 计算最大回撤
        equity_curve = [h["total_assets"] for h in self.history]
        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown = max_dd

        # 计算夏普比率
        if len(equity_curve) > 1:
            returns = np.diff(equity_curve) / equity_curve[:-1]
            if len(returns) > 0 and returns.std() > 0:
                result.sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)

        # 交易统计
        result.total_trades = len(result.trades)
        sells = [t for t in result.trades if t["action"] == "SELL"]
        if sells:
            profits = [t.get("profit", 0) for t in sells]
            result.profit_trades = len([p for p in profits if p > 0])
            result.loss_trades = len([p for p in profits if p <= 0])
            result.win_rate = result.profit_trades / len(sells) if sells else 0


class PortfolioRebalance:
    """
    投资组合再平衡策略
    定期调整各股票持仓比例
    """

    def __init__(self, target_weights: Dict[str, float]):
        """
        Args:
            target_weights: 目标权重 {code: weight}, sum should be 1.0
        """
        self.target_weights = target_weights

    def rebalance(
        self,
        engine: BacktestEngine,
        current_date,
        current_prices: Dict[str, float],
    ):
        """执行再平衡"""
        # 计算当前总资产
        total_assets = engine.cash
        for code, pos in engine.positions.items():
            if pos["shares"] > 0 and code in current_prices:
                total_assets += pos["shares"] * current_prices[code]

        # 调整各股票持仓
        for code, weight in self.target_weights.items():
            target_value = total_assets * weight

            if code not in engine.positions:
                engine.positions[code] = {"shares": 0, "cost": 0}

            current_value = engine.positions[code]["shares"] * current_prices.get(code, 0)

            # 买入或卖出
            if target_value > current_value:
                # 买入
                buy_amount = target_value - current_value
                shares = int(buy_amount / current_prices[code] / 100) * 100
                if shares > 0:
                    cost = shares * current_prices[code] * (1 + engine.commission_rate)
                    if cost <= engine.cash:
                        engine.cash -= cost
                        engine.positions[code]["shares"] += shares
                        engine.positions[code]["cost"] += shares * current_prices[code]
            elif target_value < current_value:
                # 卖出
                sell_value = current_value - target_value
                shares = int(sell_value / current_prices[code] / 100) * 100
                if shares > 0 and engine.positions[code]["shares"] >= shares:
                    proceeds = shares * current_prices[code] * (1 - engine.commission_rate)
                    engine.cash += proceeds
                    engine.positions[code]["shares"] -= shares
                    engine.positions[code]["cost"] -= shares * current_prices[code]
