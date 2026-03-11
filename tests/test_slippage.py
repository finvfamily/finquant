"""
Tests for slippage models
"""

import pytest
import pandas as pd
from finquant.engine.core import (
    BacktestEngine,
    FixedSlippage,
    PercentageSlippage,
    VolumeSlippage,
)


class TestSlippageModels:
    """测试滑点模型"""

    def test_fixed_slippage_buy(self):
        """测试固定滑点 - 买入"""
        slippage = FixedSlippage(slippage=0.001)
        price = 100.0

        result = slippage.apply(price, 'buy')

        assert result == 100.1  # 100 * (1 + 0.001)

    def test_fixed_slippage_sell(self):
        """测试固定滑点 - 卖出"""
        slippage = FixedSlippage(slippage=0.001)
        price = 100.0

        result = slippage.apply(price, 'sell')

        assert result == 99.9  # 100 * (1 - 0.001)

    def test_percentage_slippage_buy(self):
        """测试比例滑点 - 买入"""
        slippage = PercentageSlippage(slippage_rate=0.002)
        price = 100.0

        result = slippage.apply(price, 'buy')

        assert result == 100.2

    def test_percentage_slippage_sell(self):
        """测试比例滑点 - 卖出"""
        slippage = PercentageSlippage(slippage_rate=0.002)
        price = 100.0

        result = slippage.apply(price, 'sell')

        assert result == 99.8

    def test_volume_slippage(self):
        """测试成交量滑点"""
        slippage = VolumeSlippage(base_slippage=0.0005, volume_factor=0.001)
        price = 100.0

        # 成交量较小
        result1 = slippage.apply(price, 'buy', volume=1000)
        # 成交量较大
        result2 = slippage.apply(price, 'buy', volume=100000)

        # 成交量越大，滑点越大，价格越高
        assert result2 > result1


class TestBacktestEngineSlippage:
    """测试 BacktestEngine 滑点集成"""

    def test_engine_with_fixed_slippage(self, sample_data, always_buy_strategy):
        """测试带固定滑点的回测引擎"""
        slippage = FixedSlippage(slippage=0.001)

        engine = BacktestEngine(
            initial_capital=100000,
            slippage_model=slippage,
            max_positions=1,
        )

        result = engine.run(sample_data, always_buy_strategy)

        # 检查是否有交易
        assert len(result.trades) > 0

        # 检查滑点是否被记录
        buy_trades = [t for t in result.trades if t['action'] == 'BUY']
        for trade in buy_trades:
            assert 'slippage' in trade
            assert trade['slippage'] > 0  # 买入时滑点为正

    def test_engine_without_slippage(self, sample_data, always_buy_strategy):
        """测试不带滑点的回测引擎"""
        engine = BacktestEngine(
            initial_capital=100000,
            slippage_model=None,
            max_positions=1,
        )

        result = engine.run(sample_data, always_buy_strategy)

        # 检查是否有交易
        assert len(result.trades) > 0

        # 检查滑点是否为0
        buy_trades = [t for t in result.trades if t['action'] == 'BUY']
        for trade in buy_trades:
            assert trade.get('slippage', 0) == 0


class TestVolumeLimit:
    """测试成交量限制"""

    def test_volume_limit_enabled(self, sample_data, always_buy_strategy):
        """测试启用成交量限制"""
        engine = BacktestEngine(
            initial_capital=1000000,  # 较大资金
            volume_limit=0.1,  # 最多买入10%成交量
            max_positions=1,
        )

        result = engine.run(sample_data, always_buy_strategy)

        # 验证回测能正常运行
        assert result.final_capital > 0

    def test_volume_limit_disabled(self, sample_data, always_buy_strategy):
        """测试禁用成交量限制"""
        engine = BacktestEngine(
            initial_capital=1000000,
            volume_limit=0,  # 禁用
            max_positions=1,
        )

        result = engine.run(sample_data, always_buy_strategy)

        # 验证回测能正常运行
        assert result.final_capital > 0
