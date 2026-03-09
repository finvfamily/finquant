"""
finquant - 参数优化模块
"""

from typing import Dict, List, Callable
import pandas as pd
from itertools import product
from finquant.engine import BacktestEngine
from finquant.strategies import BaseStrategy


class GridSearchOptimizer:
    """
    网格搜索参数优化器
    """

    def __init__(
        self,
        data: pd.DataFrame,
        strategy_class: type,
        param_grid: Dict[str, List],
        start_date: str = None,
        end_date: str = None,
        initial_capital: float = 100000,
    ):
        """
        Args:
            data: K线数据
            strategy_class: 策略类
            param_grid: 参数网格，如 {"short_period": [5, 10], "long_period": [20, 30]}
            start_date: 回测开始日期
            end_date: 回测结束日期
            initial_capital: 初始资金
        """
        self.data = data
        self.strategy_class = strategy_class
        self.param_grid = param_grid
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital

        # 生成参数组合
        self.param_combinations = list(product(*param_grid.values()))
        self.param_names = list(param_grid.keys())

    def optimize(self, objective: str = "sharpe_ratio") -> pd.DataFrame:
        """
        运行参数优化

        Args:
            objective: 优化目标，"sharpe_ratio" / "total_return" / "win_rate"

        Returns:
            DataFrame: 优化结果
        """
        results = []

        total = len(self.param_combinations)
        print(f"开始网格搜索，共 {total} 组参数...")

        for i, params in enumerate(self.param_combinations):
            param_dict = dict(zip(self.param_names, params))

            # 创建策略实例
            strategy = self.strategy_class(**param_dict)

            # 运行回测
            engine = BacktestEngine(initial_capital=self.initial_capital)
            result = engine.run(
                data=self.data,
                strategy=strategy,
                start_date=self.start_date,
                end_date=self.end_date,
            )

            # 获取目标值
            if objective == "sharpe_ratio":
                score = result.sharpe_ratio
            elif objective == "total_return":
                score = result.total_return
            elif objective == "win_rate":
                score = result.win_rate
            else:
                score = result.sharpe_ratio

            # 记录结果
            row = param_dict.copy()
            row["total_return"] = result.total_return
            row["annual_return"] = result.annual_return
            row["max_drawdown"] = result.max_drawdown
            row["sharpe_ratio"] = result.sharpe_ratio
            row["win_rate"] = result.win_rate
            row["total_trades"] = result.total_trades
            row["score"] = score

            results.append(row)

            print(f"  [{i+1}/{total}] {param_dict} -> 得分: {score:.4f}")

        # 转换为 DataFrame
        df = pd.DataFrame(results)

        # 按得分排序
        df = df.sort_values("score", ascending=False)

        return df

    def get_best_params(self, objective: str = "sharpe_ratio") -> Dict:
        """获取最佳参数"""
        df = self.optimize(objective)
        if df.empty:
            return {}

        best = df.iloc[0]
        return {k: v for k, v in best.items() if k not in [
            "total_return", "annual_return", "max_drawdown",
            "sharpe_ratio", "win_rate", "total_trades", "score"
        ]}


def walk_forward_optimization(
    data: pd.DataFrame,
    strategy_class: type,
    default_params: Dict,
    train_period: int = 252,
    test_period: int = 63,
    step: int = 21,
) -> List[Dict]:
    """
    walk-forward 参数优化

    Args:
        data: K线数据
        strategy_class: 策略类
        default_params: 默认参数
        train_period: 训练集天数
        test_period: 测试集天数
        step: 滚动步长

    Returns:
        list: 每轮优化结果
    """
    from datetime import timedelta

    results = []

    dates = sorted(data["trade_date"].unique())
    n = len(dates)

    start_idx = 0

    while start_idx + train_period + test_period <= n:
        # 划分训练集和测试集
        train_end = start_idx + train_period
        test_end = min(train_end + test_period, n)

        train_start_date = dates[start_idx]
        train_end_date = dates[train_end - 1]
        test_start_date = dates[train_end]
        test_end_date = dates[test_end - 1]

        # 训练集优化
        train_data = data[
            (data["trade_date"] >= train_start_date) &
            (data["trade_date"] <= train_end_date)
        ]

        optimizer = GridSearchOptimizer(
            data=train_data,
            strategy_class=strategy_class,
            param_grid={
                "short_period": [5, 10, 15],
                "long_period": [20, 30, 40],
            },
            start_date=train_start_date.strftime("%Y-%m-%d") if hasattr(train_start_date, 'strftime') else str(train_start_date),
            end_date=train_end_date.strftime("%Y-%m-%d") if hasattr(train_end_date, 'strftime') else str(train_end_date),
        )

        best_params = optimizer.get_best_params()

        # 测试集验证
        test_data = data[
            (data["trade_date"] >= test_start_date) &
            (data["trade_date"] <= test_end_date)
        ]

        strategy = strategy_class(**best_params)
        engine = BacktestEngine()
        result = engine.run(test_data, strategy)

        results.append({
            "train_period": f"{train_start_date} ~ {train_end_date}",
            "test_period": f"{test_start_date} ~ {test_end_date}",
            "best_params": best_params,
            "test_return": result.total_return,
            "test_sharpe": result.sharpe_ratio,
        })

        # 滚动
        start_idx += step

    return results
