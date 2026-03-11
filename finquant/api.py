"""
finquant - 极简 API

一行代码完成回测
"""

from typing import Union, List, Dict, Optional, Any
import pandas as pd

from finquant.core.engine import BacktestEngineV2, BacktestConfig
from finquant.strategy.base import Strategy, Action, Signal
from finquant.strategy import get_vectorized_strategy
from finquant.result import BacktestResult
from finquant.data import get_kline as _get_kline


# ========== 核心函数 ==========

def backtest(
    data: Union[str, pd.DataFrame],
    strategy: Union[str, Strategy, type],
    initial_capital: float = 100000,
    start: str = None,
    end: str = None,
    **kwargs
) -> BacktestResult:
    """
    一行代码完成回测

    Args:
        data: 数据
            - str: 股票代码，如 "SH600519"
            - DataFrame: K线数据
        strategy: 策略
            - str: 策略名称，如 "ma_cross", "rsi"
            - Strategy: 策略实例
            - type: 策略类
        initial_capital: 初始资金
        start: 开始日期
        end: 结束日期
        **kwargs: 策略参数

    Returns:
        BacktestResult: 回测结果

    Examples:
        # 代码 + 策略字符串
        result = backtest("SH600519", "ma_cross", short=5, long=20)

        # 数据 + 策略实例
        data = get_kline("SH600519", start="2020-01-01")
        result = backtest(data, MAStrategy(short=5, long=20))

        # 自定义策略
        result = backtest("SH600519", MyStrategy())
    """
    # 1. 处理数据
    if isinstance(data, str):
        # 股票代码，下载数据
        data = _get_kline(data, start=start, end=end)

    if data is None or data.empty:
        raise ValueError("数据为空")

    # 2. 处理策略
    # 先尝试创建策略，获取可能需要的参数
    known_params = {'short_period', 'long_period', 'period', 'oversold', 'overbought',
                   'fast_period', 'slow_period', 'signal_period', 'std_dev',
                   'short', 'long', 'ema_short', 'ema_long'}
    strategy_kwargs = {k: v for k, v in kwargs.items() if k in known_params}
    config_kwargs = {k: v for k, v in kwargs.items() if k not in known_params}

    if isinstance(strategy, str):
        # 策略名称字符串
        strategy = get_vectorized_strategy(strategy, **strategy_kwargs)
    elif isinstance(strategy, type):
        # 策略类
        strategy = strategy(**strategy_kwargs)
    elif not isinstance(strategy, Strategy):
        raise ValueError(f"无效的策略类型: {type(strategy)}")

    # 3. 运行回测
    config = BacktestConfig(
        initial_capital=initial_capital,
        **config_kwargs
    )
    engine = BacktestEngineV2(config)
    engine.add_strategy(strategy)

    return engine.run(data, start, end)


def compare(
    strategies: List[Union[str, Strategy, type]],
    data: Union[str, pd.DataFrame],
    initial_capital: float = 100000,
    start: str = None,
    end: str = None,
    **kwargs
) -> pd.DataFrame:
    """
    比较多个策略

    Args:
        strategies: 策略列表
        data: 数据
        initial_capital: 初始资金
        start: 开始日期
        end: 结束日期
        **kwargs: 策略参数（会被每个策略使用）

    Returns:
        DataFrame: 策略比较结果

    Examples:
        results = compare(
            ["ma_cross", "rsi", "macd"],
            "SH600519",
            start="2020-01-01"
        )
    """
    # 处理数据
    if isinstance(data, str):
        data = _get_kline(data, start=start, end=end)

    results = []

    for strat in strategies:
        try:
            result = backtest(data, strat, initial_capital, start, end, **kwargs)
            results.append({
                'strategy': str(strat),
                'return': result.total_return,
                'annual_return': result.annual_return,
                'sharpe': result.sharpe_ratio,
                'drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'trades': result.total_trades,
            })
        except Exception as e:
            print(f"策略 {strat} 回测失败: {e}")

    return pd.DataFrame(results)


def optimize(
    data: Union[str, pd.DataFrame],
    strategy: Union[str, type],
    params: Dict[str, Any],
    objective: str = "sharpe",
    method: str = "grid",
    n_iter: int = 50,
    **kwargs
) -> Dict:
    """
    参数优化

    Args:
        data: 数据
        strategy: 策略类或名称
        params: 参数范围
            - grid: {"param": [values]}
            - bayesian: {"param": (min, max)}
        objective: 优化目标 "sharpe", "return", "drawdown"
        method: "grid" 或 "bayesian"
        n_iter: 贝叶斯优化迭代次数

    Returns:
        优化结果

    Examples:
        best = optimize(
            "SH600519",
            "ma_cross",
            {"short": [5, 10, 15], "long": [20, 30, 40]},
            objective="sharpe"
        )
    """
    # 处理数据
    if isinstance(data, str):
        data = _get_kline(data, start=kwargs.get('start'), end=kwargs.get('end'))

    if method == "grid":
        return _grid_optimize(data, strategy, params, objective, **kwargs)
    elif method == "bayesian":
        return _bayesian_optimize(data, strategy, params, objective, n_iter, **kwargs)
    else:
        raise ValueError(f"Unknown method: {method}")


def _grid_optimize(data, strategy, params, objective, **kwargs):
    """网格搜索优化"""
    from itertools import product
    from finquant.engine_v2 import BacktestEngineV2, BacktestConfig
    from finquant.strategy import get_vectorized_strategy

    # 生成参数组合
    param_names = list(params.keys())
    param_values = list(params.values())
    combinations = list(product(*param_values))

    results = []

    for combo in combinations:
        param_dict = dict(zip(param_names, combo))

        # 创建策略
        if isinstance(strategy, str):
            strat = get_vectorized_strategy(strategy, **param_dict)
        else:
            strat = strategy(**param_dict)

        # 运行回测
        config = BacktestConfig(initial_capital=kwargs.get('initial_capital', 100000))
        engine = BacktestEngineV2(config)
        engine.add_strategy(strat)
        result = engine.run(data)

        # 记录结果
        row = param_dict.copy()
        row['return'] = result.total_return
        row['sharpe'] = result.sharpe_ratio
        row['drawdown'] = result.max_drawdown
        results.append(row)

    # 排序
    df = pd.DataFrame(results)

    if objective == "sharpe":
        df = df.sort_values('sharpe', ascending=False)
    elif objective == "return":
        df = df.sort_values('return', ascending=False)
    elif objective == "drawdown":
        df = df.sort_values('drawdown', ascending=True)

    return {
        'best_params': {k: v for k, v in df.iloc[0].items() if k not in ['return', 'sharpe', 'drawdown']},
        'best_score': df.iloc[0].get(objective, 0),
        'all_results': df,
    }


def _bayesian_optimize(data, strategy, params, objective, n_iter, **kwargs):
    """贝叶斯优化"""
    from finquant.optimize_v2 import BayesianOptimizer, BayesianConfig

    # 准备目标函数
    def objective_fn(p):
        # 创建策略
        if isinstance(strategy, str):
            strat = get_vectorized_strategy(strategy, **{k: int(v) if isinstance(v, float) and v == int(v) else v for k, v in p.items()})
        else:
            strat = strategy(**{k: int(v) if isinstance(v, float) and v == int(v) else v for k, v in p.items()})

        # 运行回测
        config = BacktestConfig(initial_capital=kwargs.get('initial_capital', 100000))
        engine = BacktestEngineV2(config)
        engine.add_strategy(strat)
        result = engine.run(data)

        if objective == "sharpe":
            return -result.sharpe_ratio  # 最小化
        elif objective == "return":
            return -result.total_return
        elif objective == "drawdown":
            return result.max_drawdown

        return -result.sharpe_ratio

    # 贝叶斯优化
    config = BayesianConfig(n_iter=n_iter)
    optimizer = BayesianOptimizer(params, config)
    best_params, best_score = optimizer.optimize(objective_fn)

    return {
        'best_params': {k: int(v) if isinstance(v, float) and v == int(v) else v for k, v in best_params.items()},
        'best_score': -best_score if objective in ['sharpe', 'return'] else best_score,
        'history': optimizer.get_history(),
    }


def quick_backtest(
    code: str,
    strategy: str = "ma_cross",
    start: str = "2020-01-01",
    end: str = None,
    capital: float = 100000,
    **strategy_params
) -> BacktestResult:
    """
    快速回测（最简接口）

    Args:
        code: 股票代码
        strategy: 策略名称
        start: 开始日期
        end: 结束日期
        capital: 初始资金
        **strategy_params: 策略参数

    Returns:
        BacktestResult

    Examples:
        result = quick_backtest("SH600519", "ma_cross", short=5, long=20)
    """
    return backtest(code, strategy, capital, start, end, **strategy_params)


# ========== 便捷别名 ==========

bt = backtest  # 短别名
compare_strats = compare  # 比较策略
opt = optimize  # 优化参数


__all__ = [
    "backtest",
    "bt",
    "compare",
    "compare_strats",
    "optimize",
    "opt",
    "quick_backtest",
]
