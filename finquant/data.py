"""
finquant - 数据获取模块
使用 finshare 获取 K 线数据
"""

from datetime import date, datetime
from typing import List, Union
import pandas as pd


def ensure_full_code(code: str) -> str:
    """
    确保股票代码格式完整

    支持输入格式:
    - sz.159915 / sh.600519 (BaoStock格式) -> SZ159915 / SH600519
    - SZ159915 / SH600519 (标准格式) -> 保持不变
    - 159915 / 600519 (纯数字) -> 自动添加前缀

    返回格式: SH/SZ/BJ + 6位数字代码

    Args:
        code: 股票代码

    Returns:
        str: 完整格式的股票代码
    """
    if not code:
        return code

    code = code.strip()

    # 处理带点的格式 (如 sz.159915 / sh.600519)
    if "." in code:
        parts = code.split(".")
        if len(parts) == 2:
            market = parts[0].upper()
            num_code = parts[1]
            if market in ("SH", "SZ", "BJ", "HK", "US"):
                return f"{market}{num_code}"

    # 如果已经带有市场前缀且不含点，直接返回大写
    upper_code = code.upper()
    if upper_code.startswith(("SH", "SZ", "BJ", "HK", "US")):
        for prefix in ("SH", "SZ", "BJ", "HK", "US"):
            if upper_code.startswith(prefix):
                remaining = upper_code[len(prefix):]
                if remaining and remaining[0].isdigit():
                    return upper_code
                if remaining.startswith("."):
                    return f"{prefix}{remaining[1:]}"

    # 尝试根据数字判断市场
    clean_code = code.replace("SH", "").replace("SZ", "").replace("BJ", "").replace(".", "")
    if clean_code and clean_code[0].isdigit():
        first_digit = clean_code[0]
        if first_digit in ["6", "5"]:
            return f"SH{clean_code}"
        elif first_digit in ["0", "1", "2", "3"]:
            return f"SZ{clean_code}"
        elif first_digit == "9":
            if clean_code.startswith("90"):
                return f"SH{clean_code}"
            else:
                return f"BJ{clean_code}"

    return code  # 无法确定，返回原样


def get_kline(
    codes: Union[str, List[str]],
    start: Union[str, date] = None,
    end: Union[str, date] = None,
    adjust: str = None,
) -> pd.DataFrame:
    """
    获取 K 线数据

    Args:
        codes: 股票代码，如 "000001.SZ" 或 ["000001.SZ", "600000.SH"]
        start: 开始日期，如 "2024-01-01"
        end: 结束日期，如 "2024-12-31"
        adjust: 复权类型，None / "qfq"(前复权) / "hfq"(后复权)

    Returns:
        DataFrame: columns=[code, trade_date, open, high, low, close, volume]
    """
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
                adjust=adjust,
            )

            if df is not None and not df.empty:
                df = df.copy()
                # finshare 返回的 code 格式可能是 "SZ000001"，需要统一
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
            # finshare 使用 get_snapshot_data
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


def get_stock_info(code: str) -> dict:
    """
    获取股票基本信息

    Args:
        code: 股票代码

    Returns:
        dict: 股票信息
    """
    try:
        from finshare import get_data_manager
    except ImportError:
        raise ImportError("请安装 finshare: pip install finshare")

    manager = get_data_manager()
    # finshare 可能没有 get_stock_info，尝试其他方式
    try:
        return manager.get_stock_info(code)
    except AttributeError:
        # 如果没有该方法，返回基本信息
        return {"code": code}
