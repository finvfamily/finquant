"""
Tests for analysis module
"""

import pytest
import pandas as pd
import numpy as np
from finquant.analysis.result import (
    BacktestResult,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_omega_ratio,
    calculate_volatility,
    calculate_downside_volatility,
)


class TestRiskIndicators:
    """测试风险指标计算"""

    def test_sharpe_ratio(self):
        """测试夏普比率"""
        returns = pd.Series([0.01, -0.005, 0.015, 0.02, -0.01])

        sharpe = calculate_sharpe_ratio(returns)

        assert isinstance(sharpe, float)

    def test_sharpe_ratio_zero_std(self):
        """测试标准差为0的情况"""
        returns = pd.Series([0.01, 0.01, 0.01, 0.01])

        sharpe = calculate_sharpe_ratio(returns)

        assert sharpe == 0.0

    def test_sortino_ratio(self):
        """测试索提诺比率"""
        returns = pd.Series([0.01, -0.005, 0.015, 0.02, -0.01])

        sortino = calculate_sortino_ratio(returns)

        assert isinstance(sortino, float)

    def test_calmar_ratio(self):
        """测试卡玛比率"""
        total_return = 0.5
        max_drawdown = 0.2

        calmar = calculate_calmar_ratio(total_return, max_drawdown)

        assert calmar == 2.5

    def test_calmar_ratio_zero_drawdown(self):
        """测试最大回撤为0的情况"""
        total_return = 0.5
        max_drawdown = 0.0

        calmar = calculate_calmar_ratio(total_return, max_drawdown)

        assert calmar == 0.0

    def test_omega_ratio(self):
        """测试Omega比率"""
        returns = pd.Series([0.01, -0.005, 0.015, 0.02, -0.01])

        omega = calculate_omega_ratio(returns)

        assert isinstance(omega, float)
        assert omega > 0

    def test_omega_ratio_all_positive(self):
        """测试全部正收益的情况"""
        returns = pd.Series([0.01, 0.02, 0.015, 0.03, 0.025])

        omega = calculate_omega_ratio(returns)

        assert omega == float('inf')

    def test_volatility(self):
        """测试波动率"""
        returns = pd.Series([0.01, -0.005, 0.015, 0.02, -0.01])

        vol = calculate_volatility(returns)

        assert isinstance(vol, float)
        assert vol >= 0

    def test_downside_volatility(self):
        """测试下行波动率"""
        returns = pd.Series([0.01, -0.005, 0.015, 0.02, -0.01])

        downside_vol = calculate_downside_volatility(returns)

        assert isinstance(downside_vol, float)
        assert downside_vol >= 0


class TestBacktestResult:
    """测试回测结果类"""

    def test_backtest_result_creation(self):
        """测试创建回测结果"""
        result = BacktestResult()

        assert result.backtest_id == ""
        assert result.total_return == 0.0
        assert result.sharpe_ratio == 0.0

    def test_backtest_result_to_dict(self):
        """测试转换为字典"""
        result = BacktestResult()
        result.backtest_id = "test_001"
        result.total_return = 0.1

        result_dict = result.to_dict()

        assert result_dict['backtest_id'] == 'test_001'
        assert result_dict['total_return'] == 0.1
        assert 'omega_ratio' in result_dict

    def test_backtest_result_summary(self):
        """测试摘要输出"""
        result = BacktestResult()
        result.backtest_id = "test_001"
        result.start_date = "2023-01-01"
        result.end_date = "2023-12-31"
        result.initial_capital = 100000
        result.final_capital = 110000
        result.total_return = 0.1
        result.annual_return = 0.1
        result.sharpe_ratio = 1.5
        result.omega_ratio = 2.0

        summary = result.summary()

        assert 'test_001' in summary
        assert '10.00%' in summary
        assert 'Omega比率' in summary

    def test_get_returns_series(self):
        """测试获取收益率序列"""
        result = BacktestResult()
        result.daily_returns = [0.01, -0.005, 0.015]

        returns = result.get_returns_series()

        assert len(returns) == 3

    def test_get_trades_df(self):
        """测试获取交易记录"""
        result = BacktestResult()
        result.trades = [
            {'date': '2023-01-01', 'code': 'AAPL', 'action': 'BUY', 'price': 100},
            {'date': '2023-01-02', 'code': 'AAPL', 'action': 'SELL', 'price': 105},
        ]

        trades_df = result.get_trades_df()

        assert len(trades_df) == 2
        assert 'action' in trades_df.columns
