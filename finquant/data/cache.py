"""
finquant - 指标缓存模块

提供指标计算缓存，避免重复计算
"""

from typing import Dict, Callable, Any, List
import pandas as pd
import numpy as np
import hashlib
import json
from functools import wraps


class IndicatorCache:
    """
    指标缓存管理器

    功能：
    - 缓存指标计算结果
    - 支持按 key 失效
    - 支持 TTL（可选）
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._access_count: Dict[str, int] = {}

    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存 key"""
        # 简单实现：序列化参数
        key_data = {
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in kwargs.items()},
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Any:
        """获取缓存"""
        if key in self._cache:
            self._access_count[key] = self._access_count.get(key, 0) + 1
            return self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存"""
        self._cache[key] = value
        self._access_count[key] = 0

    def invalidate(self, key: str = None) -> None:
        """清除缓存"""
        if key:
            self._cache.pop(key, None)
            self._access_count.pop(key, None)
        else:
            self._cache.clear()
            self._access_count.clear()

    def get_stats(self) -> Dict:
        """获取缓存统计"""
        return {
            "size": len(self._cache),
            "total_access": sum(self._access_count.values()),
            "keys": list(self._cache.keys()),
        }


# 全局缓存实例
_global_cache = IndicatorCache()


def get_indicator_cache() -> IndicatorCache:
    """获取全局指标缓存"""
    return _global_cache


def cached_indicator(cache_key_func: Callable = None):
    """
    指标缓存装饰器

    Usage:
        @cached_indicator()
        def calculate_ma(data, period):
            return data['close'].rolling(period).mean()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存 key
            if cache_key_func:
                key = cache_key_func(*args, **kwargs)
            else:
                # 默认：使用函数名 + 参数
                key = f"{func.__name__}:{wrapper._make_key(*args, **kwargs)}"

            # 尝试从缓存获取
            cached = _global_cache.get(key)
            if cached is not None:
                return cached

            # 计算并缓存
            result = func(*args, **kwargs)
            _global_cache.set(key, result)
            return result

        # 绑定辅助方法
        wrapper._make_key = lambda *a, **kw: (
            f"{func.__name__}:{hashlib.md5(str((a, kw)).encode()).hexdigest()}"
        )
        wrapper.cache = _global_cache

        return wrapper

    return decorator


class IndicatorBuilder:
    """
    指标构建器

    提供常用技术指标的计算，支持缓存
    """

    @staticmethod
    @cached_indicator()
    def ma(close: pd.Series, period: int) -> pd.Series:
        """移动平均"""
        return close.rolling(period).mean()

    @staticmethod
    @cached_indicator()
    def ema(close: pd.Series, period: int) -> pd.Series:
        """指数移动平均"""
        return close.ewm(span=period, adjust=False).mean()

    @staticmethod
    @cached_indicator()
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """RSI 指标"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    @cached_indicator()
    def macd(
        close: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> pd.DataFrame:
        """MACD 指标"""
        exp1 = close.ewm(span=fast_period, adjust=False).mean()
        exp2 = close.ewm(span=slow_period, adjust=False).mean()

        macd = exp1 - exp2
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal

        return pd.DataFrame({
            "macd": macd,
            "signal": signal,
            "histogram": histogram,
        })

    @staticmethod
    @cached_indicator()
    def bollinger_bands(
        close: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> pd.DataFrame:
        """布林带"""
        ma = close.rolling(period).mean()
        std = close.rolling(period).std()

        return pd.DataFrame({
            "middle": ma,
            "upper": ma + std_dev * std,
            "lower": ma - std_dev * std,
        })

    @staticmethod
    @cached_indicator()
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """ATR 真实波动幅度"""
        high_low = high - low
        high_close = (high - close.shift()).abs()
        low_close = (low - close.shift()).abs()

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)

        return true_range.rolling(period).mean()

    @staticmethod
    @cached_indicator()
    def volume_profile(
        close: pd.Series,
        volume: pd.Series,
        bins: int = 20,
    ) -> pd.Series:
        """成交量加权平均价 (VWAP) 近似"""
        return (close * volume).rolling(20).sum() / volume.rolling(20).sum()

    @staticmethod
    def add_indicators(df: pd.DataFrame, indicator_config: Dict) -> pd.DataFrame:
        """
        批量添加指标

        Args:
            df: 包含 OHLCV 的 DataFrame
            indicator_config: 指标配置，如 {"ma": [5, 10, 20], "rsi": {"period": 14}}

        Returns:
            添加了指标的 DataFrame
        """
        result = df.copy()

        # MA
        if "ma" in indicator_config:
            periods = indicator_config["ma"]
            if isinstance(periods, int):
                periods = [periods]
            for p in periods:
                result[f"ma_{p}"] = IndicatorBuilder.ma(result["close"], p)

        # EMA
        if "ema" in indicator_config:
            periods = indicator_config["ema"]
            if isinstance(periods, int):
                periods = [periods]
            for p in periods:
                result[f"ema_{p}"] = IndicatorBuilder.ema(result["close"], p)

        # RSI
        if "rsi" in indicator_config:
            cfg = indicator_config["rsi"]
            period = cfg.get("period", 14) if isinstance(cfg, dict) else cfg
            result[f"rsi_{period}"] = IndicatorBuilder.rsi(result["close"], period)

        # MACD
        if "macd" in indicator_config:
            cfg = indicator_config["macd"]
            if isinstance(cfg, bool):
                cfg = {}
            macd_df = IndicatorBuilder.macd(
                result["close"],
                fast_period=cfg.get("fast_period", 12),
                slow_period=cfg.get("slow_period", 26),
                signal_period=cfg.get("signal_period", 9),
            )
            result = pd.concat([result, macd_df], axis=1)

        # Bollinger Bands
        if "boll" in indicator_config:
            cfg = indicator_config["boll"]
            period = cfg.get("period", 20) if isinstance(cfg, dict) else 20
            std_dev = cfg.get("std_dev", 2.0) if isinstance(cfg, dict) else 2.0

            boll_df = IndicatorBuilder.bollinger_bands(result["close"], period, std_dev)
            result = pd.concat([result, boll_df], axis=1)

        # ATR
        if "atr" in indicator_config:
            cfg = indicator_config["atr"]
            period = cfg.get("period", 14) if isinstance(cfg, dict) else 14
            result[f"atr_{period}"] = IndicatorBuilder.atr(
                result["high"], result["low"], result["close"], period
            )

        return result
