"""
finquant V2 - 优化示例

演示如何使用参数优化功能
"""

import pandas as pd


# ========== 示例1：贝叶斯优化 ==========

def example_bayesian():
    """贝叶斯优化示例"""
    print("\n" + "="*60)
    print("示例1：贝叶斯优化")
    print("="*60)

    from finquant import get_kline
    from finquant.strategy import MAStrategy
    from finquant.optimize import BayesianOptimizer, BayesianConfig

    # 多品类标的
    codes = [
        # ETF
        "SH510300",  # 沪深300ETF
        "SH512880",  # 证券ETF
        # LOF
        "SH161039",  # 易方达创业板LOF
        # 主板
        "SH600519",  # 茅台
        "SH600036",  # 招商银行
        # 创业板
        "SZ300750",  # 宁德时代
        "SZ300059",  # 东方财富
        # 科创板
        "SH688981",  # 中芯国际
        "SH688111",  # 华大基因
    ]

    start_date = "2024-01-01"
    end_date = "2024-11-01"

    print(f"获取标的: {codes}")
    print(f"时间范围: {start_date} ~ {end_date}")

    # 增加初始资金
    initial_capital = 1000000  # 100万
    print(f"初始资金: {initial_capital:,}")

    data = get_kline(codes=codes, start=start_date, end=end_date)

    print(f"获取数据: {len(data)} 条")
    print(f"股票数量: {data['code'].nunique()}")
    print(f"日期范围: {data['trade_date'].min()} ~ {data['trade_date'].max()}")

    # 定义目标函数
    from finquant.core import BacktestEngineV2, BacktestConfig

    def objective(params):
        """目标函数：最大化夏普比率"""
        short = int(params['short_period'])
        long = int(params['long_period'])

        if short >= long:
            return -999  # 无效参数

        strategy = MAStrategy(short_period=short, long_period=long)
        engine = BacktestEngineV2(BacktestConfig(initial_capital=1000000))
        engine.add_strategy(strategy)

        try:
            result = engine.run(data)
            return result.sharpe_ratio if result.sharpe_ratio > 0 else -1
        except:
            return -1

    # 创建优化器
    config = BayesianConfig(
        n_iter=20,               # 迭代次数
        n_initial_points=5,      # 初始点数
        acquisition="ei",        # 采集函数
    )

    optimizer = BayesianOptimizer(
        param_bounds={
            'short_period': (3, 20),
            'long_period': (20, 60),
        },
        config=config,
    )

    # 运行优化
    best_params, best_score = optimizer.optimize(
        objective_fn=objective,
        maximize=True,
        verbose=True,
    )

    print(f"\n最优参数: {best_params}")
    print(f"最优夏普比率: {best_score:.4f}")


# ========== 示例2：Walk-Forward 优化 ==========

def example_walkforward():
    """Walk-Forward 优化示例"""
    print("\n" + "="*60)
    print("示例2：Walk-Forward 优化")
    print("="*60)

    from finquant import get_kline
    from finquant.strategy import MAStrategy
    from finquant.optimize import WalkForwardOptimizer, WalkForwardConfig

    # 获取数据
    data = get_kline(["SH600519"], start="2023-01-01", end="2025-01-01")
    print(f"数据量: {len(data)} 行")

    # 参数网格
    param_grid = {
        "short_period": [3, 5, 7, 10],
        "long_period": [20, 30, 40],
    }

    # 创建优化器
    config = WalkForwardConfig(
        train_days=252,     # 1年训练
        test_days=63,      # 3个月测试
        step_days=21,      # 每月滚动
    )

    optimizer = WalkForwardOptimizer(
        train_days=252,
        test_days=63,
        step_days=21,
    )

    # 运行优化
    results = optimizer.optimize(
        data=data,
        strategy_class=MAStrategy,
        param_grid=param_grid,
        objective="sharpe_ratio",
        verbose=True,
    )

    print(f"\nWalk-Forward 结果:")
    print(results.to_string())


# ========== 示例3：敏感性分析 ==========

def example_sensitivity():
    """敏感性分析示例"""
    print("\n" + "="*60)
    print("示例3：敏感性分析")
    print("="*60)

    from finquant import get_kline
    from finquant.strategy import MAStrategy
    from finquant.optimize import SensitivityAnalyzer

    # 获取数据
    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")
    print(f"数据量: {len(data)} 行")

    # 基础参数
    base_params = {
        "short_period": 5,
        "long_period": 20,
    }

    # 创建分析器
    analyzer = SensitivityAnalyzer()

    # 分析 short_period 参数
    print("\n分析 short_period 参数:")
    results = analyzer.analyze(
        data=data,
        strategy_class=MAStrategy,
        base_params=base_params,
        param_name="short_period",
        range_pct=0.5,  # 范围 ±50%
        n_points=5,
    )

    print(results.to_string())

    # 分析 long_period 参数
    print("\n分析 long_period 参数:")
    results = analyzer.analyze(
        data=data,
        strategy_class=MAStrategy,
        base_params=base_params,
        param_name="long_period",
        range_pct=0.5,
        n_points=5,
    )

    print(results.to_string())


# ========== 示例4：二维敏感性分析 ==========

def example_2d_sensitivity():
    """二维敏感性分析示例"""
    print("\n" + "="*60)
    print("示例4：二维敏感性分析")
    print("="*60)

    from finquant import get_kline
    from finquant.strategy import MAStrategy
    from finquant.optimize import SensitivityAnalyzer

    # 获取数据
    data = get_kline(["SH600519"], start="2024-01-01", end="2025-01-01")
    print(f"数据量: {len(data)} 行")

    # 基础参数
    base_params = {
        "short_period": 5,
        "long_period": 20,
    }

    # 创建分析器
    analyzer = SensitivityAnalyzer()

    # 二维分析
    print("\n二维敏感性分析 (short_period vs long_period):")
    results = analyzer.analyze_2d(
        data=data,
        strategy_class=MAStrategy,
        base_params=base_params,
        param1="short_period",
        param2="long_period",
        n_points=5,
    )

    print(results.to_string())


# ========== 示例5：参数稳定性评估 ==========

def example_stability():
    """参数稳定性评估示例"""
    print("\n" + "="*60)
    print("示例5：参数稳定性评估")
    print("="*60)

    from finquant import get_kline
    from finquant.strategy import MAStrategy
    from finquant.optimize import WalkForwardOptimizer, ParameterStability

    # 获取数据
    data = get_kline(["SH600519"], start="2023-01-01", end="2025-01-01")

    # 参数网格
    param_grid = {
        "short_period": [3, 5, 7],
        "long_period": [20, 30],
    }

    # Walk-Forward 优化
    optimizer = WalkForwardOptimizer(
        train_days=180,
        test_days=60,
        step_days=30,
    )

    results = optimizer.optimize(
        data=data,
        strategy_class=MAStrategy,
        param_grid=param_grid,
        verbose=False,
    )

    print("Walk-Forward 结果:")
    print(results.to_string())

    # 评估稳定性
    stability = ParameterStability.evaluate(results)

    print("\n稳定性评估:")
    print(f"  平均收益: {stability['mean_return']*100:.2f}%")
    print(f"  收益波动: {stability['std_return']*100:.2f}%")
    print(f"  变异系数: {stability['return_cv']:.2f}")
    print(f"  平均夏普: {stability['mean_sharpe']:.2f}")
    print(f"  胜率: {stability['win_rate']*100:.2f}%")
    print(f"  稳定性得分: {stability['stability_score']:.2f}")


# ========== 运行示例 ==========

if __name__ == "__main__":
    # 选择运行哪个示例
    # example_bayesian()
    # example_walkforward()
    # example_sensitivity()
    # example_2d_sensitivity()
    example_stability()
