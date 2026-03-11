"""
pytest configuration and fixtures
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_data():
    """
    生成示例K线数据
    """
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    dates = [d for d in dates if d.weekday() < 5]  # 只保留工作日

    data = []
    base_price = 10.0

    for date in dates:
        # 模拟股票 AAPL
        price = base_price * (1 + np.random.randn() * 0.02)
        volume = np.random.randint(1000000, 10000000)
        pre_close = base_price

        data.append({
            'code': 'AAPL',
            'trade_date': date,
            'open': price * 0.99,
            'high': price * 1.02,
            'low': price * 0.98,
            'close': price,
            'volume': volume,
            'pre_close': pre_close,
        })

        base_price = price

    return pd.DataFrame(data)


@pytest.fixture
def multi_stock_data():
    """
    生成多只股票的K线数据
    """
    dates = pd.date_range(start='2023-01-01', end='2023-06-30', freq='D')
    dates = [d for d in dates if d.weekday() < 5]

    codes = ['AAPL', 'GOOGL', 'MSFT']
    data = []

    for code in codes:
        base_price = 10.0 + np.random.rand() * 90
        for date in dates:
            price = base_price * (1 + np.random.randn() * 0.02)
            volume = np.random.randint(1000000, 10000000)

            data.append({
                'code': code,
                'trade_date': date,
                'open': price * 0.99,
                'high': price * 1.02,
                'low': price * 0.98,
                'close': price,
                'volume': volume,
                'pre_close': base_price,
            })

            base_price = price

    return pd.DataFrame(data)


@pytest.fixture
def limit_up_data():
    """
    生成包含涨停的数据
    """
    dates = pd.date_range(start='2023-01-01', end='2023-01-10', freq='D')
    dates = [d for d in dates if d.weekday() < 5]

    data = []
    pre_close = 10.0

    for i, date in enumerate(dates):
        if i == 5:  # 第6天涨停
            close = pre_close * 1.097  # 约10%涨幅
        else:
            close = pre_close * (1 + np.random.randn() * 0.02)

        data.append({
            'code': 'AAPL',
            'trade_date': date,
            'open': close * 0.99,
            'high': close * 1.02,
            'low': close * 0.98,
            'close': close,
            'volume': 10000000,
            'pre_close': pre_close,
        })

        pre_close = close

    return pd.DataFrame(data)


@pytest.fixture
def suspended_data():
    """
    生成包含停牌的数据
    """
    dates = pd.date_range(start='2023-01-01', end='2023-01-10', freq='D')
    dates = [d for d in dates if d.weekday() < 5]

    data = []
    for i, date in enumerate(dates):
        if i == 5:  # 第6天停牌
            volume = 0
            suspended = True
            close = 10.0  # 停牌时价格不变
        else:
            volume = 10000000
            suspended = False
            close = 10.0 * (1 + np.random.randn() * 0.02)

        data.append({
            'code': 'AAPL',
            'trade_date': date,
            'open': close,
            'high': close,
            'low': close,
            'close': close,
            'volume': volume,
            'pre_close': 10.0,
            'suspended': suspended,
        })

    return pd.DataFrame(data)


@pytest.fixture
def simple_strategy():
    """
    简单的测试策略：每天买入，第二天卖出
    """
    class SimpleStrategy:
        def __init__(self):
            self.holdings = {}

        def generate_signals(self, data, code, current_date):
            if code not in self.holdings:
                self.holdings[code] = False

            if not self.holdings.get(code, False):
                self.holdings[code] = True
                return 1  # 买入
            else:
                self.holdings[code] = False
                return -1  # 卖出

    return SimpleStrategy()


@pytest.fixture
def always_buy_strategy():
    """
    始终买入的策略
    """
    class AlwaysBuyStrategy:
        def generate_signals(self, data, code, current_date):
            return 1

    return AlwaysBuyStrategy()


@pytest.fixture
def always_sell_strategy():
    """
    始终卖出的策略
    """
    class AlwaysSellStrategy:
        def generate_signals(self, data, code, current_date):
            return -1

    return AlwaysSellStrategy()
