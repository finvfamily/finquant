"""
finquant - 数据模块 V2

支持：
- 分钟线数据 (5min/15min/30min/60min)
- 数据缓存
- 因子数据集成
- 多资产数据 (期货/基金)
"""

from datetime import date, datetime
from typing import List, Union, Dict, Optional, Callable
from pathlib import Path
import pandas as pd
import numpy as np
import hashlib
import json
import time
from functools import lru_cache


# ========== 全局数据加载器（带缓存） ==========

# 默认启用缓存，TTL 3600秒（1小时）
_default_loader: Optional["DataLoader"] = None


def _get_default_loader() -> "DataLoader":
    """获取默认数据加载器（带缓存）"""
    global _default_loader
    if _default_loader is None:
        # 使用全局缓存实例
        _default_loader = DataLoader(use_cache=True, cache_ttl=3600)
        _default_loader._cache = _global_cache  # 复用全局缓存
    return _default_loader


# ========== 数据源 ==========

def get_kline(
    codes: Union[str, List[str]],
    start: Union[str, date] = None,
    end: Union[str, date] = None,
    adjust: str = None,
    period: str = "daily",
    lookback: int = 1000,
) -> pd.DataFrame:
    """
    获取 K 线数据

    Args:
        codes: 股票代码，如 "000001.SZ" 或 ["000001.SZ", "600000.SH"]
        start: 开始日期，如 "2024-01-01"
        end: 结束日期，如 "2024-12-31"
        adjust: 复权类型，None / "qfq"(前复权) / "hfq"(后复权)
        period: 周期
            - "daily": 日线
            - "weekly": 周线
            - "monthly": 月线
            - "5min": 5分钟线
            - "15min": 15分钟线
            - "30min": 30分钟线
            - "60min": 60分钟线
            - "1min": 1分钟线
        lookback: 预取历史天数（默认1000天），用于策略计算技术指标。
            会自动获取 start 之前 lookback 天的数据用于计算指标，
            但返回的数据从 start 开始

    Returns:
        DataFrame: columns=[code, trade_date, open, high, low, close, volume]

    Note:
        默认启用缓存，TTL 为 1 小时。如需禁用缓存或调整 TTL，
        可使用 DataLoader 类手动创建实例。
    """
    # 使用带缓存的 DataLoader
    loader = _get_default_loader()
    return loader.get_kline(codes, start, end, period, adjust, lookback)


# ========== 内部函数：直接从 finshare 获取（无缓存） ==========

def _get_kline_no_cache(
    codes: Union[str, List[str]],
    start: Union[str, date] = None,
    end: Union[str, date] = None,
    adjust: str = None,
    period: str = "daily",
) -> pd.DataFrame:
    """直接从 finshare 获取数据，不使用缓存"""
    try:
        from finshare import get_data_manager
    except ImportError:
        raise ImportError("请安装 finshare: pip install finshare")

    # 确保 codes 是列表
    if isinstance(codes, str):
        codes = [codes]

    # 处理日期格式
    if isinstance(start, date):
        start = start.strftime("%Y-%m-%d")
    if isinstance(end, date):
        end = end.strftime("%Y-%m-%d")


    all_data = []
    manager = get_data_manager()

    for code in codes:
        try:
            # finshare API: get_historical_data(code, start, end, period, adjust)
            df = manager.get_historical_data(
                code,
                start=start,
                end=end,
                period=period,
                adjust=adjust,
            )

            if df is not None and not df.empty:
                df = df.copy()
                all_data.append(df)

        except Exception as e:
            print(f"获取 {code} 数据失败: {e}")
            continue

    if not all_data:
        return pd.DataFrame()

    # 合并数据
    result = pd.concat(all_data, ignore_index=True)

    # finshare 列名映射
    column_mapping = {
        "open_price": "open",
        "high_price": "high",
        "low_price": "low",
        "close_price": "close",
    }

    result = result.rename(columns=column_mapping)

    # 确保必需列存在
    required_cols = ["code", "trade_date", "open", "high", "low", "close", "volume"]
    for col in required_cols:
        if col not in result.columns:
            raise ValueError(f"Missing column: {col}")

    # 转换日期
    if not pd.api.types.is_datetime64_any_dtype(result["trade_date"]):
        result["trade_date"] = pd.to_datetime(result["trade_date"])

    # 排序
    result = result.sort_values(["code", "trade_date"])

    return result


def get_realtime_quote(codes: Union[str, List[str]]) -> pd.DataFrame:
    """
    获取实时行情

    Args:
        codes: 股票代码

    Returns:
        DataFrame: 实时行情数据
    """
    try:
        from finshare import get_data_manager
    except ImportError:
        raise ImportError("请安装 finshare: pip install finshare")

    if isinstance(codes, str):
        codes = [codes]

    manager = get_data_manager()

    all_data = []
    for code in codes:
        try:
            df = manager.get_snapshot_data(code)
            if df is not None and not df.empty:
                df["code"] = code
                all_data.append(df)
        except Exception as e:
            print(f"获取 {code} 实时行情失败: {e}")
            continue

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


# ========== 数据缓存 ==========

class DataCache:
    """
    数据缓存层

    功能：
    - 本地文件缓存（持久化）
    - 内存缓存（加速）
    - TTL 支持
    - 缓存统计
    """

    def __init__(self, max_size: int = 100, cache_dir: str = None):
        """
        Args:
            max_size: 最大缓存条目数
            cache_dir: 缓存目录，默认 ~/.finquant/cache
        """
        import os
        from pathlib import Path

        # 默认缓存目录
        if cache_dir is None:
            home = Path.home()
            cache_dir = home / ".finquant" / "cache"

        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存
        self._memory_cache: Dict[str, dict] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self._cache_dir / f"{key}.parquet"

    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存 key"""
        key_data = {
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in kwargs.items()},
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """获取缓存（先从内存，再从本地文件）"""
        # 先检查内存缓存
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            # 检查 TTL
            if time.time() - entry["timestamp"] < entry["ttl"]:
                self._hits += 1
                return entry["data"]
            else:
                # TTL 过期，删除
                del self._memory_cache[key]

        # 检查本地文件缓存
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                # 检查文件创建时间
                file_age = time.time() - cache_path.stat().st_mtime
                # 从文件名获取 TTL（默认 1 小时）
                ttl = 3600

                if file_age < ttl:
                    df = pd.read_parquet(cache_path)
                    # 存入内存缓存
                    self._memory_cache[key] = {
                        "data": df,
                        "timestamp": time.time(),
                        "ttl": ttl,
                    }
                    self._hits += 1
                    return df
                else:
                    # 过期，删除文件
                    cache_path.unlink()
            except Exception:
                pass

        self._misses += 1
        return None

    def set(self, key: str, data: pd.DataFrame, ttl: int = 3600) -> None:
        """设置缓存（同时存入内存和本地文件）"""
        # 如果内存缓存已满，删除最老的
        if len(self._memory_cache) >= self._max_size:
            oldest_key = min(self._memory_cache.keys(), key=lambda k: self._memory_cache[k]["timestamp"])
            del self._memory_cache[oldest_key]

        # 存入内存缓存
        self._memory_cache[key] = {
            "data": data.copy(),
            "timestamp": time.time(),
            "ttl": ttl,
        }

        # 存入本地文件
        try:
            cache_path = self._get_cache_path(key)
            data.to_parquet(cache_path, index=False)
        except Exception as e:
            print(f"警告: 缓存写入失败: {e}")

    def invalidate(self, key: str = None) -> None:
        """清除缓存"""
        if key:
            self._memory_cache.pop(key, None)
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
        else:
            self._memory_cache.clear()
            # 清除所有缓存文件
            for f in self._cache_dir.glob("*.parquet"):
                f.unlink()

    def get_stats(self) -> dict:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        # 统计本地文件数
        local_files = len(list(self._cache_dir.glob("*.parquet")))
        return {
            "size": len(self._memory_cache),
            "local_files": local_files,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


# 全局缓存实例
_global_cache = DataCache()


def get_data_cache() -> DataCache:
    """获取全局数据缓存"""
    return _global_cache


def cached_data(ttl: int = 3600):
    """
    数据缓存装饰器

    Args:
        ttl: 缓存时间（秒）

    Usage:
        @cached_data(ttl=1800)
        def get_data(code, start, end):
            return finshare.get_kline(code, start, end)
    """
    cache = DataCache()

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 生成缓存 key
            key = f"{func.__name__}:{hashlib.md5(str((args, kwargs)).encode()).hexdigest()}"

            # 尝试从缓存获取
            cached = cache.get(key)
            if cached is not None:
                return cached

            # 调用原函数
            result = func(*args, **kwargs)

            # 存入缓存
            if isinstance(result, pd.DataFrame):
                cache.set(key, result, ttl)

            return result

        wrapper.cache = cache
        return wrapper

    return decorator


# ========== 数据加载器 ==========

class DataLoader:
    """
    统一数据加载器

    支持：
    - 自动缓存
    - 批量获取
    - 多数据源
    """

    def __init__(self, use_cache: bool = True, cache_ttl: int = 3600):
        """
        Args:
            use_cache: 是否使用缓存
            cache_ttl: 缓存时间（秒）
        """
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self._cache = DataCache() if use_cache else None

    def get_kline(
        self,
        codes: Union[str, List[str]],
        start: str = None,
        end: str = None,
        period: str = "daily",
        adjust: str = None,
        lookback: int = 0,
    ) -> pd.DataFrame:
        """获取 K 线数据（带缓存）

        Args:
            codes: 股票代码
            start: 开始日期
            end: 结束日期
            period: 周期
            adjust: 复权类型
            lookback: 预取历史天数，用于策略计算技术指标
        """
        # 如果有 lookback，调整 start 日期
        actual_start = start
        if lookback > 0 and start:
            from datetime import timedelta
            start_dt = pd.to_datetime(start) - timedelta(days=lookback + 30)
            actual_start = start_dt.strftime("%Y-%m-%d")

        # 确保 codes 是列表
        if isinstance(codes, str):
            codes = [codes]

        # 生成缓存 key（使用简化 key，不含日期范围）
        base_cache_key = self._make_cache_key("kline", codes, period, adjust)

        # 尝试从缓存获取并检查是否需要更新
        if self._cache:
            cached = self._cache.get(base_cache_key)
            if cached is not None and not cached.empty:
                # 检查缓存数据是否覆盖请求的日期范围
                cached = cached.copy()
                cached_dates = cached['trade_date']

                # 解析请求的日期范围
                req_start = pd.to_datetime(start) if start else None
                req_end = pd.to_datetime(end) if end else None

                # 获取缓存数据的日期范围
                cached_start = cached_dates.min()
                cached_end = cached_dates.max()

                # 检查是否需要更新
                need_update = False
                new_end = req_end

                # 计算日期差距（天）
                days_diff = None
                if req_end is not None:
                    days_diff = (req_end - cached_end).days

                # 检查 start：只关心是否缺少前面的数据（容差5天）
                start_diff = None
                if req_start is not None:
                    start_diff = (cached_start - req_start).days

                # 决定是否需要更新
                # 1. end 日期差距 > 3天需要更新
                # 2. start 缺少超过 5天需要更新
                if req_end is not None and cached_end < req_end and (days_diff is None or days_diff > 3):
                    need_update = True
                    print(f"[缓存] {codes[0]} 缓存到 {cached_end}，需要更新到 {req_end} (差距{days_diff}天)")
                elif req_start is not None and start_diff > 5:
                    need_update = True
                    print(f"[缓存] {codes[0]} 缓存从 {cached_start} 开始，需要从 {req_start} 开始 (缺少{start_diff}天)")
                else:
                    print(f"[缓存] {codes[0]} 缓存 {cached_start.date()}~{cached_end.date()}, 请求 {req_start.date()}~{req_end.date()}, 可用")

                if not need_update:
                    # 缓存数据足够，筛选返回
                    result = cached
                    if req_start is not None:
                        result = result[result['trade_date'] >= req_start]
                    if req_end is not None:
                        result = result[result['trade_date'] <= req_end]

                    codes_str = ','.join(codes)
                    print(f"[命中缓存] {codes_str} {start}~{end}: {len(result)} 条 (共{len(cached)}条缓存)")
                    return result

                # 需要更新：获取新数据并合并（只在需要更新且差距>3天时）
                if need_update and req_end is not None and cached_end < req_end and days_diff > 3:
                    # 从缓存的结束日期+1天开始获取
                    from datetime import timedelta
                    fetch_start = (cached_end + timedelta(days=1)).strftime("%Y-%m-%d")
                    fetch_end = req_end.strftime("%Y-%m-%d") if hasattr(req_end, 'strftime') else str(req_end)[:10]

                    codes_str = ','.join(codes)
                    print(f"[增量] {codes_str} {fetch_start}~{fetch_end}: 获取新数据...")

                    # 获取新数据
                    new_data = _get_kline_no_cache(codes, fetch_start, fetch_end, adjust, period)

                    if not new_data.empty:
                        # 合并缓存数据和新数据，去重
                        cached = cached[~cached['trade_date'].isin(new_data['trade_date'])]
                        combined = pd.concat([cached, new_data], ignore_index=True)
                        combined = combined.sort_values(['code', 'trade_date'])

                        # 更新缓存
                        self._cache.set(base_cache_key, combined, self.cache_ttl)

                        # 返回请求范围的数据
                        result = combined
                        if req_start is not None:
                            result = result[result['trade_date'] >= req_start]
                        if req_end is not None:
                            result = result[result['trade_date'] <= req_end]

                        print(f"[更新] {codes_str} {start}~{end}: {len(result)} 条 (缓存已更新)")
                        return result
                    else:
                        # 没有新数据，返回缓存
                        result = cached
                        if req_start is not None:
                            result = result[result['trade_date'] >= req_start]
                        if req_end is not None:
                            result = result[result['trade_date'] <= req_end]
                        codes_str = ','.join(codes)
                        print(f"[无新数据] {codes_str} {start}~{end}: 返回缓存 {len(result)} 条")
                        return result
                else:
                    # 不需要更新，直接返回缓存
                    pass

        # 从 finshare 获取
        codes_str = ','.join(codes) if isinstance(codes, list) else codes
        print(f"[网络] {codes_str} {start}~{end}: 请求网络...")
        data = _get_kline_no_cache(codes, actual_start, end, adjust, period)

        # 如果有 lookback，筛选回实际需要的日期范围
        if lookback > 0 and start:
            data = data[data['trade_date'] >= pd.to_datetime(start)]

        # 存入缓存
        if self._cache and not data.empty:
            self._cache.set(base_cache_key, data, self.cache_ttl)

        return data

    def get_minute_kline(
        self,
        codes: Union[str, List[str]],
        start: str = None,
        end: str = None,
        period: str = "5min",
    ) -> pd.DataFrame:
        """获取分钟线数据"""
        return self.get_kline(codes, start, end, period=period)

    def get_future_kline(
        self,
        codes: Union[str, List[str]],
        start: str = None,
        end: str = None,
    ) -> pd.DataFrame:
        """获取期货 K 线数据"""
        try:
            from finshare import get_future_kline
        except ImportError:
            raise ImportError("请安装 finshare: pip install finshare")

        if isinstance(codes, str):
            codes = [codes]

        all_data = []
        for code in codes:
            data = get_future_kline(code, start, end)
            if data:
                df = pd.DataFrame([{
                    'code': code,
                    'trade_date': d.get('trade_date'),
                    'open': d.get('open'),
                    'high': d.get('high'),
                    'low': d.get('low'),
                    'close': d.get('close'),
                    'volume': d.get('volume'),
                } for d in data])
                all_data.append(df)

        if not all_data:
            return pd.DataFrame()

        return pd.concat(all_data, ignore_index=True)

    def get_fund_nav(
        self,
        codes: Union[str, List[str]],
        start: str = None,
        end: str = None,
    ) -> pd.DataFrame:
        """获取基金净值数据"""
        try:
            from finshare import get_fund_nav
        except ImportError:
            raise ImportError("请安装 finshare: pip install finshare")

        if isinstance(codes, str):
            codes = [codes]

        all_data = []
        for code in codes:
            data = get_fund_nav(code, start, end)
            if data:
                df = pd.DataFrame([{
                    'code': code,
                    'trade_date': d.get('nav_date'),
                    'nav': d.get('nav'),
                    'acc_nav': d.get('acc_nav'),
                } for d in data])
                all_data.append(df)

        if not all_data:
            return pd.DataFrame()

        return pd.concat(all_data, ignore_index=True)

    def invalidate_cache(self, key: str = None) -> None:
        """清除缓存"""
        if self._cache:
            self._cache.invalidate(key)

    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        if self._cache:
            return self._cache.get_stats()
        return {}

    def _make_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存 key"""
        key_data = {
            "prefix": prefix,
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in kwargs.items()},
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()


# ========== 因子数据 ==========

class FactorLoader:
    """
    因子数据加载器

    集成 finshare 的因子数据
    """

    @staticmethod
    def get_money_flow(code: str, start: str = None, end: str = None) -> pd.DataFrame:
        """获取资金流向数据"""
        try:
            from finshare import get_money_flow
        except ImportError:
            raise ImportError("请安装 finshare: pip install finshare")

        data = get_money_flow(code)
        if data is not None:
            return data
        return pd.DataFrame()

    @staticmethod
    def get_lhb(start: str = None, end: str = None) -> pd.DataFrame:
        """获取龙虎榜数据"""
        try:
            from finshare import get_lhb
        except ImportError:
            raise ImportError("请安装 finshare: pip install finshare")

        data = get_lhb(start, end)
        if data is not None:
            return data
        return pd.DataFrame()

    @staticmethod
    def get_margin(code: str = None) -> pd.DataFrame:
        """获取融资融券数据"""
        try:
            from finshare import get_margin
        except ImportError:
            raise ImportError("请安装 finshare: pip install finshare")

        data = get_margin(code)
        if data is not None:
            return data
        return pd.DataFrame()

    @staticmethod
    def get_financial(
        code: str,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, pd.DataFrame]:
        """获取财务数据"""
        try:
            from finshare import get_income, get_balance, get_cashflow
        except ImportError:
            raise ImportError("请安装 finshare: pip install finshare")

        return {
            "income": get_income(code, start_date, end_date) or pd.DataFrame(),
            "balance": get_balance(code, start_date, end_date) or pd.DataFrame(),
            "cashflow": get_cashflow(code, start_date, end_date) or pd.DataFrame(),
        }


def add_factor(data: pd.DataFrame, factor_name: str, code: str = None) -> pd.DataFrame:
    """
    往数据中添加因子

    Args:
        data: K线数据
        factor_name: 因子名称
            - "money_flow": 资金流向
            - "margin": 融资融券
        code: 股票代码（可选）

    Returns:
        添加了因子的 DataFrame
    """
    if factor_name == "money_flow":
        if code:
            mf = FactorLoader.get_money_flow(code)
            if not mf.empty:
                # 合并到主数据
                data = data.merge(
                    mf[['trade_date', 'net_inflow', 'net_inflow_rate']],
                    on='trade_date',
                    how='left',
                )
        return data

    elif factor_name == "margin":
        if code:
            margin = FactorLoader.get_margin(code)
            if not margin.empty:
                data = data.merge(
                    margin[['trade_date', 'margin_balance', 'short_balance']],
                    on='trade_date',
                    how='left',
                )
        return data

    else:
        raise ValueError(f"Unknown factor: {factor_name}")


# ========== 便捷函数 ==========

__all__ = [
    # 数据获取
    "get_kline",
    "get_realtime_quote",
    # 缓存
    "DataCache",
    "get_data_cache",
    "cached_data",
    # 加载器
    "DataLoader",
    "FactorLoader",
    "add_factor",
]
