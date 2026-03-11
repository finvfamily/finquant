"""
Tests for risk management module
"""

import pytest
from finquant.engine.risk import RiskManager, ATRCalculator, calculate_atr


class TestRiskManager:
    """测试风控管理器"""

    def test_stop_loss_triggered(self):
        """测试止损触发"""
        risk_mgr = RiskManager(stop_loss=0.05)

        risk_mgr.on_open_position('AAPL', 100.0)

        # 亏损达到5%触发止损
        assert risk_mgr.check_stop_loss('AAPL', 94.9) == True

        # 亏损未达到5%不触发
        assert risk_mgr.check_stop_loss('AAPL', 95.1) == False

    def test_stop_profit_triggered(self):
        """测试止盈触发"""
        risk_mgr = RiskManager(stop_profit=0.15)

        risk_mgr.on_open_position('AAPL', 100.0)

        # 盈利达到15%触发止盈
        assert risk_mgr.check_stop_profit('AAPL', 115.1) == True

        # 盈利未达到15%不触发
        assert risk_mgr.check_stop_profit('AAPL', 114.9) == False

    def test_trailing_stop_triggered(self):
        """测试跟踪止损触发"""
        risk_mgr = RiskManager(trailing_stop=0.1)

        risk_mgr.on_open_position('AAPL', 100.0)
        risk_mgr.on_price_update('AAPL', 120.0)  # 涨到120

        # 从最高点回撤10%触发
        assert risk_mgr.check_trailing_stop('AAPL', 108.0) == True

        # 未达到10%不触发
        assert risk_mgr.check_trailing_stop('AAPL', 109.0) == False

    def test_atr_stop_triggered(self):
        """测试ATR止损触发"""
        risk_mgr = RiskManager(atr_stop_multiplier=2.0)

        risk_mgr.on_open_position('AAPL', 100.0)

        # 价格跌破 100 - 2*2 = 96 触发
        assert risk_mgr.check_atr_stop('AAPL', 95.0, atr=2.5) == True

        # 未跌破不触发
        assert risk_mgr.check_atr_stop('AAPL', 97.0, atr=2.5) == False

    def test_max_drawdown_triggered(self):
        """测试最大回撤触发"""
        risk_mgr = RiskManager(max_drawdown=0.15)  # 设置15%阈值

        risk_mgr.on_assets_update(100000)
        risk_mgr.on_assets_update(110000)
        risk_mgr.on_assets_update(90000)

        # 从110000回撤到90000，约18%，超过15%阈值
        assert risk_mgr.check_max_drawdown(90000) == True

    def test_should_close_position(self):
        """测试综合平仓判断"""
        risk_mgr = RiskManager(
            stop_loss=0.05,
            stop_profit=0.15,
            trailing_stop=0.1,
        )

        risk_mgr.on_open_position('AAPL', 100.0)

        # 止损触发
        assert risk_mgr.should_close_position('AAPL', 94.0) == True

        # 恢复后更新
        risk_mgr.on_price_update('AAPL', 110.0)

        # 止盈触发
        assert risk_mgr.should_close_position('AAPL', 116.0) == True

    def test_position_info(self):
        """测试获取持仓信息"""
        risk_mgr = RiskManager(
            stop_loss=0.05,
            stop_profit=0.15,
        )

        risk_mgr.on_open_position('AAPL', 100.0)
        risk_mgr.on_price_update('AAPL', 110.0)

        info = risk_mgr.get_position_info('AAPL', 105.0)

        assert info['entry_price'] == 100.0
        assert info['peak_price'] == 110.0
        assert info['profit_ratio'] == 0.05  # 5%
        assert info['stop_loss'] == -0.05

    def test_on_close_position(self):
        """测试平仓时清理状态"""
        risk_mgr = RiskManager(stop_loss=0.05)

        risk_mgr.on_open_position('AAPL', 100.0)
        risk_mgr.on_price_update('AAPL', 110.0)

        risk_mgr.on_close_position('AAPL')

        # 状态应该被清理
        assert 'AAPL' not in risk_mgr._entry_prices
        assert 'AAPL' not in risk_mgr._peak_prices


class TestATRCalculator:
    """测试ATR计算器"""

    def test_atr_calculation(self):
        """测试ATR计算"""
        calculator = ATRCalculator(period=14)

        # 添加数据
        highs = [110, 115, 112, 118, 120]
        lows = [100, 105, 102, 108, 110]
        closes = [105, 110, 108, 115, 112]

        for h, l, c in zip(highs, lows, closes):
            calculator.update(h, l, c)

        atr = calculator.get_atr()

        # ATR应该大于0
        assert atr is None or atr >= 0  # 数据不足14条时返回None

    def test_atr_with_sufficient_data(self):
        """测试足够数据的ATR计算"""
        calculator = ATRCalculator(period=3)

        # 添加足够的数据
        for i in range(10):
            high = 100 + i + 2
            low = 100 + i - 1
            close = 100 + i
            calculator.update(high, low, close)

        atr = calculator.get_atr()

        assert atr is not None
        assert atr > 0


class TestCalculateATR:
    """测试ATR计算函数"""

    def test_calculate_atr(self):
        """测试ATR计算"""
        highs = [110, 115, 112, 118, 120]
        lows = [100, 105, 102, 108, 110]
        closes = [105, 110, 108, 115, 112]

        atr = calculate_atr(highs, lows, closes, period=3)

        assert atr >= 0

    def test_calculate_atr_insufficient_data(self):
        """测试数据不足时ATR为0"""
        highs = [110]
        lows = [100]
        closes = [105]

        atr = calculate_atr(highs, lows, closes, period=14)

        assert atr == 0.0
