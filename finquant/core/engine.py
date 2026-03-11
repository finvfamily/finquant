"""
finquant - 事件驱动回测引擎 (V2)

支持：
- 事件驱动架构
- 多策略组合
- 插件式 Observer
- 详细的回测数据记录
"""

from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np

from finquant.core.event import (
    EventBus, Event, EventType,
    BarEvent, SignalEvent, OrderEvent, FillEvent,
)
from finquant.core.broker import Broker, Order, OrderStatus
from finquant.strategy.base import Strategy, Signal, Action, Bar
from finquant.result import BacktestResult


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 100000
    commission_rate: float = 0.0003
    slippage: float = 0
    max_positions: int = 5
    max_single_position: float = 0.3


class BacktestEngineV2:
    """
    事件驱动回测引擎 V2

    架构：
    DataFeed -> EventBus -> Strategy -> Broker -> Execution
                         |
                         v
                   Observers (指标/风控/分析)

    特点：
    - 完全事件驱动
    - 策略与引擎解耦
    - 支持多策略组合
    - 支持插件式扩展
    """

    def __init__(self, config: BacktestConfig = None):
        """
        Args:
            config: 回测配置
        """
        self.config = config or BacktestConfig()

        # 核心组件
        self.event_bus = EventBus()
        self.broker = Broker(
            initial_cash=self.config.initial_capital,
            commission_rate=self.config.commission_rate,
            slippage=self.config.slippage,
        )

        # 策略和观察者
        self.strategies: List[Strategy] = []
        self.observers: List[Any] = []

        # 数据
        self.data: Optional[pd.DataFrame] = None
        self.trade_dates: List = []

        # 回测结果
        self.result: Optional[BacktestResult] = None

        # 注册事件处理器
        self._register_handlers()

    def add_strategy(self, strategy: Strategy) -> None:
        """添加策略"""
        self.strategies.append(strategy)
        # 策略订阅事件
        self.event_bus.subscribe(EventType.BAR, self._strategy_on_bar(strategy))

    def add_observer(self, observer) -> None:
        """添加观察者"""
        self.observers.append(observer)
        observer.subscribe_to(self.event_bus)

    def run(
        self,
        data: pd.DataFrame,
        start_date: str = None,
        end_date: str = None,
    ) -> BacktestResult:
        """
        运行回测

        Args:
            data: K线数据
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            BacktestResult: 回测结果
        """
        # 预处理数据
        self.data = self._prepare_data(data, start_date, end_date)
        self.trade_dates = sorted(self.data['trade_date'].unique())

        # 初始化结果
        self.result = self._init_result()

        # 发送回测开始事件
        self.event_bus.publish(Event(EventType.BACKTEST_START, {}))

        # 逐日回测
        self._run_backtest()

        # 发送回测结束事件
        self.event_bus.publish(Event(EventType.BACKTEST_END, {}))

        # 计算统计指标
        self._calculate_stats()

        return self.result

    def _prepare_data(self, data: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
        """预处理数据"""
        df = data.copy()

        # 日期过滤
        if start_date:
            df = df[df['trade_date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['trade_date'] <= pd.to_datetime(end_date)]

        # 确保必要列
        required = ['code', 'trade_date', 'open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        return df.sort_values(['trade_date', 'code'])

    def _init_result(self) -> BacktestResult:
        """初始化结果"""
        result = BacktestResult()
        result.backtest_id = f"bt_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result.start_date = self.trade_dates[0] if self.trade_dates else None
        result.end_date = self.trade_dates[-1] if self.trade_dates else None
        result.initial_capital = self.config.initial_capital
        return result

    def _register_handlers(self) -> None:
        """注册事件处理器"""
        # 信号 -> 订单
        self.event_bus.subscribe(EventType.SIGNAL, self._handle_signal)

        # 订单 -> 成交
        self.event_bus.subscribe(EventType.ORDER, self._handle_order)

    def _strategy_on_bar(self, strategy: Strategy):
        """创建策略的 BAR 事件处理器"""
        def handler(event: Event):
            bar_event = BarEvent(event.data)
            bar = self._create_bar(bar_event)

            # 注入历史数据到 bar
            bar._history_data = self._get_history_data(bar.code, bar.trade_date)

            # 策略生成信号
            signal = strategy.on_bar(bar)

            if signal and signal.action != Action.HOLD:
                # 发布信号事件
                self.event_bus.publish(SignalEvent(
                    code=bar.code,
                    signal=1 if signal.action == Action.BUY else -1,
                    strength=signal.strength,
                ))

        return handler

    def _create_bar(self, bar_event: BarEvent) -> Bar:
        """创建 Bar 对象"""
        return Bar(
            code=bar_event.code,
            trade_date=bar_event.trade_date,
            open=bar_event.open,
            high=bar_event.high,
            low=bar_event.low,
            close=bar_event.close,
            volume=bar_event.volume,
        )

    def _get_history_data(self, code: str, current_date, lookback: int = 100) -> pd.DataFrame:
        """获取历史数据（包含当前bar）"""
        df = self.data[
            (self.data['code'] == code) &
            (self.data['trade_date'] <= current_date)
        ]
        return df.tail(lookback)

    def _get_price_on_date(self, code: str, date) -> float:
        """获取指定日期的收盘价"""
        # 统一日期类型
        target_date = pd.to_datetime(date)
        row = self.data[
            (self.data['code'] == code) &
            (self.data['trade_date'] == target_date)
        ]
        if not row.empty:
            return float(row.iloc[0]['close'])

        # 如果精确日期没找到，找最近的交易日
        if row.empty:
            past_data = self.data[
                (self.data['code'] == code) &
                (self.data['trade_date'] <= target_date)
            ]
            if not past_data.empty:
                return float(past_data.iloc[-1]['close'])
        return 0

    def _handle_signal(self, event: Event) -> None:
        """处理信号事件"""
        code = event.data.get('code')
        signal_value = event.data.get('signal', 0)

        if signal_value == 0:
            return

        # 获取当前价格
        current_date = self._current_date
        bar_data = self.data[
            (self.data['code'] == code) &
            (self.data['trade_date'] == current_date)
        ]

        if bar_data.empty:
            return

        bar_data = bar_data.iloc[0]
        current_price = bar_data['close']

        # 获取持仓
        position = self.broker.get_position(code)
        current_shares = position.shares

        # 生成订单
        if signal_value == 1 and current_shares == 0:
            # 买入
            if self._can_buy(code, current_price):
                # 计算买入数量 - 使用可用现金，不能超过
                available_cash = self.broker.cash
                # 预留手续费
                max_amount = available_cash / (1 + self.config.commission_rate)

                # A股默认100股起买
                min_lot = 100
                # 计算可买入的股数（100股倍数）
                volume = int(max_amount / current_price / min_lot) * min_lot

                # 不足最小起买量则不买入
                if volume >= min_lot:
                    order = self.broker.submit_order(code, "BUY", volume, current_price)
                    self.event_bus.publish(OrderEvent(
                        code=code,
                        action="BUY",
                        volume=volume,
                        price=current_price,
                    ))

        elif signal_value == -1 and current_shares > 0:
            order = self.broker.submit_order(code, "SELL", current_shares, current_price)
            self.event_bus.publish(OrderEvent(
                code=code,
                action="SELL",
                volume=current_shares,
                price=current_price,
            ))

    def _handle_order(self, event: Event) -> None:
        """处理订单事件"""
        # 这里简化处理，实际应该根据订单创建和执行
        pass

    def _can_buy(self, code: str, price: float) -> bool:
        """检查是否可以买入"""
        # 检查持仓数量限制
        current_positions = sum(
            1 for p in self.broker.positions.values()
            if p.shares > 0
        )
        if current_positions >= self.config.max_positions:
            return False

        return True

    def _run_backtest(self) -> None:
        """执行回测"""
        # 按日期分组处理
        for date in self.trade_dates:
            self._current_date = date

            # 发送日期开始事件
            self.event_bus.publish(Event(EventType.DAY_START, {'date': date}))

            # 获取当日数据
            day_data = self.data[self.data['trade_date'] == date]

            # 构建价格映射
            current_prices = {}
            for _, row in day_data.iterrows():
                current_prices[row['code']] = row['close']

            # 处理每只股票（先处理交易，再记录资产）
            for _, row in day_data.iterrows():
                # 发布 BAR 事件
                bar_data = {
                    'code': row['code'],
                    'trade_date': row['trade_date'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume'],
                }
                self.event_bus.publish(Event(EventType.BAR, bar_data))

                # 处理待成交订单
                self._process_pending_orders(bar_data)

            # 发送日期结束事件
            self.event_bus.publish(Event(EventType.DAY_END, {'date': date}))

            # 记录当日资产（交易后）
            total_assets = self.broker.get_total_assets(current_prices)
            self.result.daily_equity.append({
                'date': date,
                'cash': self.broker.cash,
                'position_value': total_assets - self.broker.cash,
                'total_assets': total_assets,
            })

        # 计算最终资产
        if self.trade_dates:
            last_date = self.trade_dates[-1]
            last_data = self.data[self.data['trade_date'] == last_date]
            prices = {row['code']: row['close'] for _, row in last_data.iterrows()}
            self.result.final_capital = self.broker.get_total_assets(prices)

            # 记录最终持仓（不添加到 equity 里，避免计算错误）
            # positions 已在上面的循环中记录

    def _process_pending_orders(self, bar_data: dict) -> None:
        """处理待成交订单"""
        pending = self.broker.get_pending_orders(bar_data['code'])

        for order in pending:
            filled = self.broker.execute_order(order, bar_data)
            if filled:
                # 计算总资产（使用当日各股票的收盘价）
                current_date = bar_data['trade_date']
                total_assets = self.broker.cash
                for pos_code, pos in self.broker.positions.items():
                    if pos.shares > 0:
                        # 获取该持仓股票当日的收盘价
                        pos_price = self._get_price_on_date(pos_code, current_date)
                        if pos_price > 0:
                            total_assets += pos.shares * pos_price

                # 打印交易日志
                trade_date = bar_data['trade_date'].strftime('%Y-%m-%d') if hasattr(bar_data['trade_date'], 'strftime') else str(bar_data['trade_date'])

                if order.action == "BUY":
                    cost = order.filled_volume * order.filled_price + order.commission
                    print(f"[买入] {trade_date} | {order.code} | "
                          f"数量:{order.filled_volume} | 价格:{order.filled_price:.2f} | "
                          f"成本:{cost:.2f}(手续费:{order.commission:.2f}) | "
                          f"剩余现金:{self.broker.cash:.2f} | 总资产:{total_assets:.2f}")
                else:  # SELL
                    proceeds = order.filled_volume * order.filled_price - order.commission
                    profit = self._calculate_trade_profit(order)
                    profit_pct = profit / (order.filled_volume * order.filled_price) * 100 if order.filled_volume > 0 else 0
                    print(f"[卖出] {trade_date} | {order.code} | "
                          f"数量:{order.filled_volume} | 价格:{order.filled_price:.2f} | "
                          f"卖出额:{order.filled_volume * order.filled_price:.2f} | 手续费:{order.commission:.2f} | "
                          f"收益:{profit:+.2f}({profit_pct:+.2f}%) | "
                          f"剩余现金:{self.broker.cash:.2f} | 总资产:{total_assets:.2f}")

                # 记录交易
                self.result.trades.append({
                    'date': bar_data['trade_date'],
                    'code': order.code,
                    'action': order.action,
                    'price': order.filled_price,
                    'shares': order.filled_volume,
                    'amount': order.filled_volume * order.filled_price,
                    'commission': order.commission,
                    'profit': profit if order.action == "SELL" else 0,
                })

    def _calculate_trade_profit(self, order: Order) -> float:
        """计算交易盈亏"""
        if order.action != "SELL":
            return 0

        pos = self.broker.get_position(order.code)
        # 简化：使用平均成本计算
        return (order.filled_price - pos.avg_cost) * order.filled_volume

    def _calculate_stats(self) -> None:
        """计算统计指标"""
        if not self.result:
            return

        # 总收益率
        self.result.total_return = (
            self.result.final_capital - self.result.initial_capital
        ) / self.result.initial_capital

        # 年化收益率
        if self.result.start_date and self.result.end_date:
            days = (self.result.end_date - self.result.start_date).days
            years = days / 252
            if years > 0:
                self.result.annual_return = (1 + self.result.total_return) ** (1 / years) - 1

        # 计算最大回撤
        if self.result.daily_equity:
            equity_curve = [e['total_assets'] for e in self.result.daily_equity]
            peak = equity_curve[0]
            max_dd = 0
            for eq in equity_curve:
                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak
                if dd > max_dd:
                    max_dd = dd
            self.result.max_drawdown = max_dd

        # 计算夏普比率
        if self.result.daily_equity:
            equity_curve = [e['total_assets'] for e in self.result.daily_equity]
            if len(equity_curve) > 1:
                returns = []
                for i in range(1, len(equity_curve)):
                    ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                    returns.append(ret)

                if returns:
                    mean_return = np.mean(returns)
                    std_return = np.std(returns)
                    if std_return > 0:
                        # 假设无风险利率为0，年化夏普比率
                        self.result.sharpe_ratio = (mean_return / std_return) * np.sqrt(252)

        # 交易统计
        self.result.total_trades = len(self.result.trades)
        sells = [t for t in self.result.trades if t['action'] == 'SELL']
        if sells:
            profits = [t.get('profit', 0) for t in sells]
            self.result.profit_trades = len([p for p in profits if p > 0])
            self.result.loss_trades = len([p for p in profits if p <= 0])
            self.result.win_rate = self.result.profit_trades / len(sells) if sells else 0

    def get_event_stats(self) -> Dict:
        """获取事件统计"""
        return self.event_bus.get_stats()


# 便捷函数
def backtest(
    data: pd.DataFrame,
    strategy: Strategy,
    initial_capital: float = 100000,
    **kwargs
) -> BacktestResult:
    """
    快速回测函数

    Args:
        data: K线数据
        strategy: 策略实例
        initial_capital: 初始资金
        **kwargs: 其他配置

    Returns:
        BacktestResult
    """
    config = BacktestConfig(initial_capital=initial_capital, **kwargs)
    engine = BacktestEngineV2(config)
    engine.add_strategy(strategy)
    return engine.run(data)
