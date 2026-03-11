"""
finquant - 数据模块

包含数据加载、缓存、因子计算、指标缓存
"""

from finquant.data.loader import (
    get_kline,
    get_realtime_quote,
    DataLoader,
    FactorLoader,
    add_factor,
    _get_default_loader,
)

from finquant.data.loader import (
    DataCache,
    get_data_cache,
    cached_data,
)

from finquant.data.cache import (
    # 指标缓存
    IndicatorCache,
    IndicatorBuilder,
    get_indicator_cache,
    cached_indicator,
)

from finquant.data.factors import (
    FactorLibrary,
    FACTOR_REGISTRY,
    get_factor,
)

__all__ = [
    # 加载器
    "get_kline",
    "get_realtime_quote",
    "DataLoader",
    "FactorLoader",
    "add_factor",
    # 数据缓存
    "DataCache",
    "get_data_cache",
    "cached_data",
    # 指标缓存
    "IndicatorCache",
    "IndicatorBuilder",
    "get_indicator_cache",
    "cached_indicator",
    # 因子
    "FactorLibrary",
    "FACTOR_REGISTRY",
    "get_factor",
]
