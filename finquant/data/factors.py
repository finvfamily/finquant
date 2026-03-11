"""
finquant - 因子库模块

提供常用技术因子和基本面因子
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from functools import lru_cache


class FactorLibrary:
    """
    因子库

    提供 20+ 常用因子
    """

    # ========== 动量因子 ==========

    @staticmethod
    def momentum(close: pd.Series, period: int = 20) -> pd.Series:
        """
        动量因子

        过去 period 天的收益率

        Returns:
            Series: 动量因子值
        """
        return close / close.shift(period) - 1

    @staticmethod
    def roc(close: pd.Series, period: int = 12) -> pd.Series:
        """
        ROC 变动率指标

        (当前价格 - N日前价格) / N日前价格 * 100
        """
        return (close - close.shift(period)) / close.shift(period) * 100

    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """
        RSI 相对强弱指标

        Returns:
            Series: RSI 值 (0-100)
        """
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # ========== 趋势因子 ==========

    @staticmethod
    def ma(close: pd.Series, period: int = 20) -> pd.Series:
        """简单移动平均"""
        return close.rolling(period).mean()

    @staticmethod
    def ema(close: pd.Series, period: int = 12) -> pd.Series:
        """指数移动平均"""
        return close.ewm(span=period, adjust=False).mean()

    @staticmethod
    def ma_bias(close: pd.Series, period: int = 20) -> pd.Series:
        """
        均线偏离率

        (当前价格 - MA) / MA * 100
        """
        ma = close.rolling(period).mean()
        return (close - ma) / ma * 100

    @staticmethod
    def dual_ema_ratio(close: pd.Series, short_period: int = 10, long_period: int = 30) -> pd.Series:
        """
        双 EMA 比率

        EMA(短期) / EMA(长期)
        """
        ema_short = close.ewm(span=short_period, adjust=False).mean()
        ema_long = close.ewm(span=long_period, adjust=False).mean()
        return ema_short / ema_long

    # ========== 波动率因子 ==========

    @staticmethod
    def volatility(close: pd.Series, period: int = 20) -> pd.Series:
        """
        波动率因子

        Returns: 日收益率的标准差年化
        """
        returns = close.pct_change()
        return returns.rolling(period).std() * np.sqrt(252)

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        ATR 真实波动幅度均值
        """
        high_low = high - low
        high_close = (high - close.shift()).abs()
        low_close = (low - close.shift()).abs()

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)

        return true_range.rolling(period).mean()

    @staticmethod
    def bollinger_width(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
        """
        布林带宽度

        (上轨 - 下轨) / 中轨
        """
        ma = close.rolling(period).mean()
        std = close.rolling(period).std()

        upper = ma + std_dev * std
        lower = ma - std_dev * std

        return (upper - lower) / ma

    # ========== 成交量因子 ==========

    @staticmethod
    def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        """
        量比

        当前成交量 / 20日平均成交量
        """
        avg_volume = volume.rolling(period).mean()
        return volume / avg_volume

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        OBV 能量潮
        """
        sign = np.sign(close.diff())
        return (sign * volume).cumsum()

    @staticmethod
    def vwap(close: pd.Series, volume: pd.Series, period: int = 20) -> pd.Series:
        """
        VWAP 成交量加权平均价
        """
        return (close * volume).rolling(period).sum() / volume.rolling(period).sum()

    @staticmethod
    def money_flow(close: pd.Series, volume: pd.Series, period: int = 20) -> pd.Series:
        """
        资金流向（简化版）

        收盘价 * 成交量 的移动平均
        """
        return (close * volume).rolling(period).sum()

    # ========== 价值因子 ==========

    @staticmethod
    def pe_ratio(close: pd.Series, earnings: pd.Series) -> pd.Series:
        """
        市盈率（简化）

        需要传入 earnings 数据
        """
        return close / earnings

    @staticmethod
    def pb_ratio(close: pd.Series, book_value: pd.Series) -> pd.Series:
        """
        市净率（简化）

        需要传入 book_value 数据
        """
        return close / book_value

    @staticmethod
    def ps_ratio(close: pd.Series, revenue: pd.Series) -> pd.Series:
        """
        市销率（简化）
        """
        return close / revenue

    # ========== 成长因子 ==========

    @staticmethod
    def revenue_growth(revenue: pd.Series, period: int = 4) -> pd.Series:
        """
        营收增长率

        过去 period 期的营收变化
        """
        return revenue.pct_change(period)

    @staticmethod
    def earnings_growth(earnings: pd.Series, period: int = 4) -> pd.Series:
        """
        盈利增长率
        """
        return earnings.pct_change(period)

    # ========== 质量因子 ==========

    @staticmethod
    def roe(net_income: pd.Series, equity: pd.Series) -> pd.Series:
        """
        ROE 净资产收益率
        """
        return net_income / equity * 100

    @staticmethod
    def roa(net_income: pd.Series, assets: pd.Series) -> pd.Series:
        """
        ROA 总资产收益率
        """
        return net_income / assets * 100

    @staticmethod
    def gross_margin(revenue: pd.Series, gross_profit: pd.Series) -> pd.Series:
        """
        毛利率
        """
        return gross_profit / revenue * 100

    # ========== 风险因子 ==========

    @staticmethod
    def beta(returns: pd.Series, market_returns: pd.Series, period: int = 60) -> pd.Series:
        """
        Beta 贝塔系数
        """
        covariance = returns.rolling(period).cov(market_returns)
        variance = market_returns.rolling(period).var()
        return covariance / variance

    @staticmethod
    def sharpe(returns: pd.Series, period: int = 252) -> pd.Series:
        """
        夏普比率
        """
        return np.sqrt(period) * returns.mean() / returns.std()

    @staticmethod
    def sortino(returns: pd.Series, period: int = 252) -> pd.Series:
        """
        索提诺比率

        只考虑下行风险
        """
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std()

        if downside_std == 0:
            return pd.Series(0, index=returns.index)

        return np.sqrt(period) * returns.mean() / downside_std

    @staticmethod
    def max_drawdown(close: pd.Series, period: int = 60) -> pd.Series:
        """
        最大回撤
        """
        rolling_max = close.rolling(period, min_periods=1).max()
        drawdown = (close - rolling_max) / rolling_max
        return drawdown.min(axis=0)

    # ========== 组合因子 ==========

    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        往数据中添加所有常用技术指标

        Args:
            df: 包含 OHLCV 的 DataFrame

        Returns:
            添加了指标的 DataFrame
        """
        result = df.copy()

        # 动量
        result['momentum_5'] = FactorLibrary.momentum(result['close'], 5)
        result['momentum_10'] = FactorLibrary.momentum(result['close'], 10)
        result['momentum_20'] = FactorLibrary.momentum(result['close'], 20)
        result['momentum_60'] = FactorLibrary.momentum(result['close'], 60)

        # RSI
        result['rsi_6'] = FactorLibrary.rsi(result['close'], 6)
        result['rsi_12'] = FactorLibrary.rsi(result['close'], 12)
        result['rsi_24'] = FactorLibrary.rsi(result['close'], 24)

        # 均线
        result['ma_5'] = FactorLibrary.ma(result['close'], 5)
        result['ma_10'] = FactorLibrary.ma(result['close'], 10)
        result['ma_20'] = FactorLibrary.ma(result['close'], 20)
        result['ma_60'] = FactorLibrary.ma(result['close'], 60)

        # EMA
        result['ema_12'] = FactorLibrary.ema(result['close'], 12)
        result['ema_26'] = FactorLibrary.ema(result['close'], 26)

        # 均线偏离
        result['ma_bias_20'] = FactorLibrary.ma_bias(result['close'], 20)

        # 波动率
        result['volatility_20'] = FactorLibrary.volatility(result['close'], 20)

        # ATR
        result['atr_14'] = FactorLibrary.atr(result['high'], result['low'], result['close'], 14)

        # 成交量
        result['volume_ratio_20'] = FactorLibrary.volume_ratio(result['volume'], 20)

        # OBV
        result['obv'] = FactorLibrary.obv(result['close'], result['volume'])

        return result


# 注册表
FACTOR_REGISTRY: Dict[str, callable] = {
    # 动量
    "momentum": FactorLibrary.momentum,
    "roc": FactorLibrary.roc,
    "rsi": FactorLibrary.rsi,
    # 趋势
    "ma": FactorLibrary.ma,
    "ema": FactorLibrary.ema,
    "ma_bias": FactorLibrary.ma_bias,
    "dual_ema_ratio": FactorLibrary.dual_ema_ratio,
    # 波动率
    "volatility": FactorLibrary.volatility,
    "atr": FactorLibrary.atr,
    "bollinger_width": FactorLibrary.bollinger_width,
    # 成交量
    "volume_ratio": FactorLibrary.volume_ratio,
    "obv": FactorLibrary.obv,
    "vwap": FactorLibrary.vwap,
    "money_flow": FactorLibrary.money_flow,
    # 风险
    "sharpe": FactorLibrary.sharpe,
    "sortino": FactorLibrary.sortino,
    "max_drawdown": FactorLibrary.max_drawdown,
    "beta": FactorLibrary.beta,
}


def get_factor(name: str, **params):
    """
    获取因子函数

    Args:
        name: 因子名称
        **params: 因子参数

    Returns:
        因子函数
    """
    if name not in FACTOR_REGISTRY:
        raise ValueError(f"Unknown factor: {name}")
    return FACTOR_REGISTRY[name]


__all__ = [
    "FactorLibrary",
    "FACTOR_REGISTRY",
    "get_factor",
]
