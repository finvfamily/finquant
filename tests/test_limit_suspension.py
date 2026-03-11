"""
Tests for limit up/down and suspension handling
"""

import pytest
import pandas as pd
from finquant.engine.core import BacktestEngine


class TestLimitUpDown:
    """测试涨跌停处理"""

    def test_limit_up_prevents_buy(self, limit_up_data):
        """测试涨停时禁止买入"""
        class BuyOnLimitUpStrategy:
            """尝试在涨停日买入的策略"""
            def generate_signals(self, data, code, current_date):
                return 1  # 始终买入

        engine = BacktestEngine(
            initial_capital=100000,
            limit_up_down=True,
            max_positions=1,
        )

        result = engine.run(limit_up_data, BuyOnLimitUpStrategy())

        # 找出涨停日
        limit_up_dates = limit_up_data[
            (limit_up_data['close'] - limit_up_data['pre_close']) / limit_up_data['pre_close'] >= 0.097
        ]['trade_date'].tolist()

        # 涨停日不应该有买入
        buy_trades_on_limit_up = [
            t for t in result.trades
            if t['action'] == 'BUY' and t['date'] in limit_up_dates
        ]

        assert len(buy_trades_on_limit_up) == 0

    def test_limit_down_allows_sell(self, limit_up_data):
        """测试跌停时允许卖出"""
        class SellStrategy:
            """始终卖出的策略"""
            def __init__(self):
                self.positions = set()

            def generate_signals(self, data, code, current_date):
                if code not in self.positions:
                    self.positions.add(code)
                    return 1  # 先买入
                return -1  # 然后卖出

        engine = BacktestEngine(
            initial_capital=100000,
            limit_up_down=True,
            max_positions=1,
        )

        result = engine.run(limit_up_data, SellStrategy())

        # 应该有卖出交易
        sell_trades = [t for t in result.trades if t['action'] == 'SELL']
        assert len(sell_trades) > 0

    def test_limit_up_disabled(self, limit_up_data):
        """测试禁用涨跌停限制"""
        class AlwaysBuyStrategy:
            def generate_signals(self, data, code, current_date):
                return 1

        engine = BacktestEngine(
            initial_capital=100000,
            limit_up_down=False,  # 禁用
            max_positions=1,
        )

        result = engine.run(limit_up_data, AlwaysBuyStrategy())

        # 禁用后应该有更多买入
        buy_trades = [t for t in result.trades if t['action'] == 'BUY']
        assert len(buy_trades) > 0


class TestSuspension:
    """测试停牌处理"""

    def test_suspended_prevents_trading(self, suspended_data):
        """测试停牌时禁止交易"""
        class TradeAlwaysStrategy:
            """始终交易的策略"""
            def __init__(self):
                self.has_position = False

            def generate_signals(self, data, code, current_date):
                if not self.has_position:
                    self.has_position = True
                    return 1  # 买入
                return -1  # 卖出

        engine = BacktestEngine(
            initial_capital=100000,
            suspended=True,
            max_positions=1,
        )

        result = engine.run(suspended_data, TradeAlwaysStrategy())

        # 停牌日不应该有交易
        suspended_dates = suspended_data[
            suspended_data.get('suspended', False) == True
        ]['trade_date'].tolist()

        trades_on_suspended = [
            t for t in result.trades
            if t['date'] in suspended_dates
        ]

        assert len(trades_on_suspended) == 0

    def test_suspension_disabled(self, suspended_data):
        """测试禁用停牌检查"""
        class AlwaysBuyStrategy:
            def generate_signals(self, data, code, current_date):
                return 1

        engine = BacktestEngine(
            initial_capital=100000,
            suspended=False,  # 禁用
            max_positions=1,
        )

        result = engine.run(suspended_data, AlwaysBuyStrategy())

        # 禁用后应该有买入
        buy_trades = [t for t in result.trades if t['action'] == 'BUY']
        assert len(buy_trades) > 0


class TestMarketStatus:
    """测试市场状态识别"""

    def test_is_limit_up(self):
        """测试涨停识别"""
        # 创建明确涨停的数据
        data = pd.DataFrame([
            {
                'code': 'AAPL',
                'trade_date': pd.Timestamp('2023-01-01'),
                'open': 10.0,
                'high': 11.0,
                'low': 9.8,
                'close': 10.97,  # 9.7% 涨幅
                'volume': 10000000,
                'pre_close': 10.0,
            }
        ])

        engine = BacktestEngine(
            initial_capital=100000,
            limit_up_down=True,
        )

        class DummyStrategy:
            def generate_signals(self, data, code, current_date):
                return 0

        engine.run(data, DummyStrategy())

        # 检查涨停识别
        assert len(engine._limit_up_codes) > 0

    def test_is_limit_down(self):
        """测试跌停识别"""
        data = pd.DataFrame([
            {
                'code': 'AAPL',
                'trade_date': pd.Timestamp('2023-01-01'),
                'open': 9.0,
                'high': 9.2,
                'low': 8.8,
                'close': 9.0,
                'volume': 10000000,
                'pre_close': 10.0,
            }
        ])

        engine = BacktestEngine(
            initial_capital=100000,
            limit_up_down=True,
        )

        class DummyStrategy:
            def generate_signals(self, data, code, current_date):
                return 0

        engine.run(data, DummyStrategy())

        # 跌停时应该能卖出
        assert 'AAPL' in engine._limit_down_codes

    def test_is_suspended(self):
        """测试停牌识别"""
        # 创建明确停牌的数据
        data = pd.DataFrame([
            {
                'code': 'AAPL',
                'trade_date': pd.Timestamp('2023-01-01'),
                'open': 10.0,
                'high': 10.0,
                'low': 10.0,
                'close': 10.0,
                'volume': 0,  # 成交量为0
                'pre_close': 10.0,
                'suspended': True,  # 明确标记为停牌
            }
        ])

        engine = BacktestEngine(
            initial_capital=100000,
            suspended=True,
        )

        class DummyStrategy:
            def generate_signals(self, data, code, current_date):
                return 0

        engine.run(data, DummyStrategy())

        # 检查停牌识别
        assert len(engine._suspended_codes) > 0
