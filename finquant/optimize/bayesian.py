"""
finquant - 贝叶斯优化模块

提供高斯过程代理模型 + 采集函数
"""

from typing import Dict, List, Callable, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.stats import norm
import random


# ========== 贝叶斯优化 ==========

@dataclass
class BayesianConfig:
    """贝叶斯优化配置"""
    n_iter: int = 50          # 迭代次数
    n_initial_points: int = 10  # 初始随机采样点数
    acquisition: str = "ei"   # 采集函数: "ei", "ucb", "poi"
    kappa: float = 2.0        # UCB 参数
    xi: float = 0.0          # EI 参数
    random_state: int = 42


class BayesianOptimizer:
    """
    贝叶斯参数优化

    使用高斯过程代理模型 + 采集函数
    """

    def __init__(self, param_bounds: Dict[str, Tuple[float, float]], config: BayesianConfig = None):
        """
        Args:
            param_bounds: 参数边界 {"param_name": (min, max)}
            config: 配置
        """
        self.param_bounds = param_bounds
        self.config = config or BayesianConfig()

        # 存储观测数据
        self.X: List[List[float]] = []
        self.y: List[float] = []

        # 参数名称列表
        self.param_names = list(param_bounds.keys())

        # 随机种子
        random.seed(self.config.random_state)
        np.random.seed(self.config.random_state)

    def _random_sample(self) -> Dict[str, float]:
        """随机采样参数"""
        return {
            name: random.uniform(lo, hi)
            for name, (lo, hi) in self.param_bounds.items()
        }

    def _to_array(self, params: Dict[str, float]) -> np.ndarray:
        """转换为数组"""
        return np.array([params[name] for name in self.param_names])

    def _to_dict(self, arr: np.ndarray) -> Dict[str, float]:
        """转换为字典"""
        return {name: arr[i] for i, name in enumerate(self.param_names)}

    def _gp_predict(self, X_train: np.ndarray, y_train: np.ndarray, X_pred: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        高斯过程预测（简化版）

        Returns:
            (mean, std)
        """
        n_train = len(X_train)
        n_pred = len(X_pred)

        if n_train == 0:
            return np.zeros(n_pred), np.ones(n_pred)

        # 计算核矩阵
        # 使用 RBF 核
        length_scale = 1.0
        sigma_f = 1.0

        # 训练点之间的距离
        dist = np.zeros((n_train, n_train))
        for i in range(n_train):
            for j in range(n_train):
                dist[i, j] = np.sum(((X_train[i] - X_train[j]) / length_scale) ** 2)

        K = sigma_f ** 2 * np.exp(-0.5 * dist) + np.eye(n_train) * 1e-6

        # 预测点的核
        K_star = np.zeros((n_pred, n_train))
        for i in range(n_pred):
            for j in range(n_train):
                K_star[i, j] = sigma_f ** 2 * np.exp(
                    -0.5 * np.sum(((X_pred[i] - X_train[j]) / length_scale) ** 2)
                )

        # 预测
        K_inv = np.linalg.inv(K)
        mu = K_star @ K_inv @ y_train
        cov = sigma_f ** 2 - K_star @ K_inv @ K_star.T
        std = np.sqrt(np.diag(cov))
        std = np.maximum(std, 1e-6)  # 防止零方差

        return mu, std

    def _acquisition(self, mu: np.ndarray, std: np.ndarray, y_best: float) -> np.ndarray:
        """计算采集函数值"""
        if self.config.acquisition == "ei":
            # Expected Improvement
            z = (mu - y_best - self.config.xi) / std
            ei = (mu - y_best - self.config.xi) * norm.cdf(z) + std * norm.pdf(z)
            ei[std == 0] = 0
            return ei

        elif self.config.acquisition == "ucb":
            # Upper Confidence Bound
            return mu + self.config.kappa * std

        elif self.config.acquisition == "poi":
            # Probability of Improvement
            z = (mu - y_best - self.config.xi) / std
            poi = norm.cdf(z)
            poi[std == 0] = 0
            return poi

        return np.zeros_like(mu)

    def suggest_next(self) -> Dict[str, float]:
        """建议下一个采样点"""
        if len(self.X) < self.config.n_initial_points:
            # 随机采样
            return self._random_sample()

        # 高斯过程预测
        X_train = np.array(self.X)
        y_train = np.array(self.y)

        # 生成候选点
        n_candidates = 1000
        candidates = np.zeros((n_candidates, len(self.param_names)))
        for i, (name, (lo, hi)) in enumerate(self.param_bounds.items()):
            candidates[:, i] = np.random.uniform(lo, hi, n_candidates)

        # 预测
        mu, std = self._gp_predict(X_train, y_train, candidates)

        # 采集函数
        y_best = min(self.y) if self.config.acquisition == "ei" else max(self.y)
        acq_values = self._acquisition(mu, std, y_best)

        # 选择最大值
        best_idx = np.argmax(acq_values)

        return self._to_dict(candidates[best_idx])

    def observe(self, params: Dict[str, float], score: float) -> None:
        """记录观测结果"""
        self.X.append(self._to_array(params))
        self.y.append(score)

    def optimize(
        self,
        objective_fn: Callable[[Dict[str, float]], float],
        maximize: bool = False,
        verbose: bool = True,
    ) -> Tuple[Dict[str, float], float]:
        """
        执行优化

        Args:
            objective_fn: 目标函数，输入参数字典，返回分数
            maximize: 是否最大化
            verbose: 是否打印进度

        Returns:
            (最优参数, 最优分数)
        """
        if not maximize:
            # 转换为最小化问题
            original_fn = objective_fn
            objective_fn = lambda params: -original_fn(params)

        if verbose:
            print(f"贝叶斯优化: {len(self.param_bounds)} 个参数, {self.config.n_iter} 次迭代")

        # 初始采样
        for i in range(self.config.n_initial_points):
            params = self._random_sample()
            score = objective_fn(params)
            self.observe(params, score)

            if verbose:
                print(f"  初始 {i+1}/{self.config.n_initial_points}: {params} -> {score:.4f}")

        # 迭代优化
        for i in range(self.config.n_iter):
            # 建议下一个点
            params = self.suggest_next()
            score = objective_fn(params)
            self.observe(params, score)

            if verbose:
                best_score = min(self.y)
                best_params = self._to_dict(self.X[np.argmin(self.y)])
                print(f"  迭代 {i+1}/{self.config.n_iter}: {params} -> {score:.4f} (best: {best_score:.4f})")

        # 返回结果
        best_idx = np.argmin(self.y)
        best_params = self._to_dict(self.X[best_idx])
        best_score = self.y[best_idx]

        if not maximize:
            best_score = -best_score

        if verbose:
            print(f"最优参数: {best_params}")
            print(f"最优分数: {best_score:.4f}")

        return best_params, best_score

    def get_history(self) -> pd.DataFrame:
        """获取优化历史"""
        data = []
        for i, (x, y) in enumerate(zip(self.X, self.y)):
            row = {name: x[i] for i, name in enumerate(self.param_names)}
            row['score'] = y
            row['iteration'] = i
            data.append(row)

        return pd.DataFrame(data)


# ========== 便捷函数 ==========

def bayesian_optimize(
    param_bounds: Dict[str, Tuple[float, float]],
    objective_fn: Callable,
    n_iter: int = 50,
    maximize: bool = False,
) -> Tuple[Dict[str, float], float]:
    """
    贝叶斯优化便捷函数

    Args:
        param_bounds: 参数边界
        objective_fn: 目标函数
        n_iter: 迭代次数
        maximize: 是否最大化

    Returns:
        (最优参数, 最优分数)
    """
    config = BayesianConfig(n_iter=n_iter)
    optimizer = BayesianOptimizer(param_bounds, config)
    return optimizer.optimize(objective_fn, maximize)


__all__ = [
    "BayesianConfig",
    "BayesianOptimizer",
    "bayesian_optimize",
]
