"""
finquant - Walk-Forward 优化模块
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import pandas as pd
import itertools


@dataclass
class WalkForwardConfig:
    """Walk-Forward 配置"""
    train_days: int = 252      # 训练集天数 (1年)
    test_days: int = 63        # 测试集天数 (3个月)
    step_days: int = 21        # 滚动步长 (1个月)
    rebalance: bool = True     # 是否再平衡


class GridSearchOptimizer:
    """网格搜索优化器"""

    def __init__(
        self,
        data: pd.DataFrame,
        strategy_class,
        param_grid: Dict[str, List],
        start_date: str = None,
        end_date: str = None,
    ):
        self.data = data
        self.strategy_class = strategy_class
        self.param_grid = param_grid
        self.start_date = start_date
        self.end_date = end_date
        self.results_ = []
        self.best_params_ = None
        self.best_score_ = float('-inf')

    def optimize(self, objective: str = "sharpe_ratio", verbose: bool = True):
        """执行网格搜索"""
        from finquant import BacktestEngineV2, BacktestConfig
        import pandas as pd

        # 过滤数据
        data = self.data
        if self.start_date:
            data = data[data['trade_date'] >= pd.to_datetime(self.start_date)]
        if self.end_date:
            data = data[data['trade_date'] <= pd.to_datetime(self.end_date)]

        # 生成参数组合
        keys = list(self.param_grid.keys())
        values = list(self.param_grid.values())
        combinations = list(itertools.product(*values))

        if verbose:
            print(f"网格搜索: {len(combinations)} 个参数组合")

        for combo in combinations:
            params = dict(zip(keys, combo))

            # 创建策略
            strategy = self.strategy_class(**params)

            # 运行回测
            engine = BacktestEngineV2(BacktestConfig(initial_capital=100000))
            engine.add_strategy(strategy)

            try:
                result = engine.run(data)

                # 获取目标值
                if objective == "sharpe_ratio":
                    score = result.sharpe_ratio
                elif objective == "total_return":
                    score = result.total_return
                elif objective == "win_rate":
                    score = result.win_rate
                else:
                    score = result.sharpe_ratio

                self.results_.append({
                    "params": params,
                    "score": score,
                    "return": result.total_return,
                    "sharpe": result.sharpe_ratio,
                    "trades": result.total_trades,
                })

                if score > self.best_score_:
                    self.best_score_ = score
                    self.best_params_ = params

                if verbose:
                    print(f"  {params} -> {objective}: {score:.4f}")

            except Exception as e:
                if verbose:
                    print(f"  {params} -> 错误: {e}")

        return self

    def get_best_params(self, objective: str = "sharpe_ratio"):
        """获取最优参数"""
        if self.best_params_ is None:
            self.optimize(objective)
        return self.best_params_


class WalkForwardOptimizer:
    """
    Walk-Forward 参数优化

    避免过拟合的经典方法
    """

    def __init__(
        self,
        train_days: int = 252,
        test_days: int = 63,
        step_days: int = 21,
    ):
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days

    def optimize(
        self,
        data: pd.DataFrame,
        strategy_class,
        param_grid: Dict[str, List],
        objective: str = "sharpe_ratio",
        verbose: bool = True,
    ) -> pd.DataFrame:
        """
        执行 Walk-Forward 优化

        Args:
            data: K线数据
            strategy_class: 策略类
            param_grid: 参数网格
            objective: 优化目标
            verbose: 是否打印

        Returns:
            每轮的结果 DataFrame
        """
        from finquant.optimize import GridSearchOptimizer

        # 获取交易日
        if 'trade_date' not in data.columns:
            raise ValueError("data must have 'trade_date' column")

        dates = sorted(data['trade_date'].unique())
        n = len(dates)

        results = []
        start_idx = 0

        round_num = 0

        while start_idx + self.train_days + self.test_days <= n:
            round_num += 1

            # 划分数据集
            train_end = start_idx + self.train_days
            test_end = min(train_end + self.test_days, n)

            train_start_date = dates[start_idx]
            train_end_date = dates[train_end - 1]
            test_start_date = dates[train_end]
            test_end_date = dates[test_end - 1]

            if verbose:
                print(f"\n=== Round {round_num} ===")
                print(f"训练集: {train_start_date} ~ {train_end_date}")
                print(f"测试集: {test_start_date} ~ {test_end_date}")

            # 训练集优化
            train_data = data[
                (data['trade_date'] >= train_start_date) &
                (data['trade_date'] <= train_end_date)
            ]

            if train_data.empty:
                start_idx += self.step_days
                continue

            optimizer = GridSearchOptimizer(
                data=train_data,
                strategy_class=strategy_class,
                param_grid=param_grid,
                start_date=str(train_start_date)[:10],
                end_date=str(train_end_date)[:10],
            )

            best_params = optimizer.get_best_params(objective)

            if verbose:
                print(f"最优参数: {best_params}")

            # 测试集验证
            test_data = data[
                (data['trade_date'] >= test_start_date) &
                (data['trade_date'] <= test_end_date)
            ]

            if test_data.empty:
                start_idx += self.step_days
                continue

            # 运行测试
            from finquant.core.engine import BacktestEngineV2 as BacktestEngine
            strategy = strategy_class(**best_params)
            engine = BacktestEngine()
            engine.add_strategy(strategy)
            result = engine.run(test_data)

            # 记录结果
            results.append({
                'round': round_num,
                'train_start': train_start_date,
                'train_end': train_end_date,
                'test_start': test_start_date,
                'test_end': test_end_date,
                'best_params': best_params,
                'test_return': result.total_return,
                'test_sharpe': result.sharpe_ratio,
                'test_drawdown': result.max_drawdown,
                'test_trades': result.total_trades,
            })

            if verbose:
                print(f"测试收益: {result.total_return:.2%}")
                print(f"测试夏普: {result.sharpe_ratio:.2f}")

            # 滚动
            start_idx += self.step_days

        return pd.DataFrame(results)


def walk_forward_optimize(
    data: pd.DataFrame,
    strategy_class,
    param_grid: Dict[str, List],
    train_days: int = 252,
    test_days: int = 63,
    step_days: int = 21,
) -> pd.DataFrame:
    """
    Walk-Forward 优化便捷函数
    """
    optimizer = WalkForwardOptimizer(train_days, test_days, step_days)
    return optimizer.optimize(data, strategy_class, param_grid)


__all__ = [
    "WalkForwardConfig",
    "WalkForwardOptimizer",
    "walk_forward_optimize",
]
