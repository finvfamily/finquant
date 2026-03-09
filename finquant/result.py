"""
finquant - 结果分析模块
"""

from typing import Dict, List
import pandas as pd
import numpy as np


class BacktestResult:
    """回测结果"""

    def __init__(self):
        self.backtest_id: str = ""
        self.start_date = None
        self.end_date = None
        self.initial_capital: float = 100000.0
        self.final_capital: float = 0.0
        self.total_return: float = 0.0
        self.annual_return: float = 0.0
        self.max_drawdown: float = 0.0
        self.sharpe_ratio: float = 0.0
        self.sortino_ratio: float = 0.0
        self.calmar_ratio: float = 0.0
        self.win_rate: float = 0.0
        self.total_trades: int = 0
        self.profit_trades: int = 0
        self.loss_trades: int = 0
        self.avg_profit: float = 0.0
        self.avg_loss: float = 0.0

        # 每日收益
        self.daily_returns: List[float] = []
        self.daily_equity: List[Dict] = []

        # 交易记录
        self.trades: List[Dict] = []

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "backtest_id": self.backtest_id,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "profit_trades": self.profit_trades,
            "loss_trades": self.loss_trades,
            "avg_profit": self.avg_profit,
            "avg_loss": self.avg_loss,
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        if not self.daily_equity:
            return pd.DataFrame()
        return pd.DataFrame(self.daily_equity)

    def summary(self) -> str:
        """输出回测摘要"""
        return f"""
========================================
          回测结果摘要
========================================
回测ID: {self.backtest_id}
回测期间: {self.start_date} ~ {self.end_date}
初始资金: {self.initial_capital:,.2f}
最终资金: {self.final_capital:,.2f}
总收益率: {self.total_return*100:.2f}%
年化收益率: {self.annual_return*100:.2f}%
最大回撤: {self.max_drawdown*100:.2f}%
夏普比率: {self.sharpe_ratio:.2f}
索提诺比率: {self.sortino_ratio:.2f}
卡玛比率: {self.calmar_ratio:.2f}
胜率: {self.win_rate*100:.2f}%
交易次数: {self.total_trades}
盈利交易: {self.profit_trades}
亏损交易: {self.loss_trades}
平均盈利: {self.avg_profit:,.2f}
平均亏损: {self.avg_loss:,.2f}
========================================
"""

    def get_trades_df(self) -> pd.DataFrame:
        """获取交易记录 DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)


def analyze_drawdown(equity_curve: List[float]) -> Dict:
    """
    分析回撤

    Args:
        equity_curve: 权益曲线

    Returns:
        dict: 回撤分析结果
    """
    if not equity_curve:
        return {}

    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak

    max_drawdown = np.min(drawdown)
    max_drawdown_idx = np.argmin(drawdown)

    # 找到最大回撤开始的位置
    peak_before_mdd = np.argmax(equity[:max_drawdown_idx]) if max_drawdown_idx > 0 else 0

    return {
        "max_drawdown": abs(max_drawdown),
        "max_drawdown_start": peak_before_mdd,
        "max_drawdown_end": max_drawdown_idx,
        "drawdown_duration": max_drawdown_idx - peak_before_mdd,
    }


def calculate_sortino_ratio(returns: List[float], target_return: float = 0.0) -> float:
    """
    计算索提诺比率

    Args:
        returns: 收益列表
        target_return: 目标收益（默认0）

    Returns:
        float: 索提诺比率
    """
    if not returns:
        return 0.0

    returns = np.array(returns)
    excess_returns = returns - target_return

    # 只考虑下行风险
    downside_returns = excess_returns[excess_returns < 0]

    if len(downside_returns) == 0:
        return 0.0

    downside_std = np.std(downside_returns)

    if downside_std == 0:
        return 0.0

    return np.mean(excess_returns) / downside_std * np.sqrt(252)


def calculate_calmar_ratio(total_return: float, max_drawdown: float) -> float:
    """
    计算卡玛比率

    Args:
        total_return: 总收益率
        max_drawdown: 最大回撤

    Returns:
        float: 卡玛比率
    """
    if max_drawdown == 0:
        return 0.0
    return total_return / max_drawdown


def compare_strategies(results: List[BacktestResult]) -> pd.DataFrame:
    """
    比较多个策略的回测结果

    Args:
        results: 回测结果列表

    Returns:
        DataFrame: 比较结果
    """
    data = []
    for r in results:
        data.append({
            "策略": r.backtest_id,
            "总收益": f"{r.total_return*100:.2f}%",
            "年化收益": f"{r.annual_return*100:.2f}%",
            "最大回撤": f"{r.max_drawdown*100:.2f}%",
            "夏普比率": f"{r.sharpe_ratio:.2f}",
            "胜率": f"{r.win_rate*100:.2f}%",
            "交易次数": r.total_trades,
        })

    return pd.DataFrame(data)
