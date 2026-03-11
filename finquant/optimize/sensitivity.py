"""
finquant - 敏感性分析模块
"""

from typing import Dict
import numpy as np
import pandas as pd


class SensitivityAnalyzer:
    """
    参数敏感性分析
    """

    def __init__(self):
        pass

    def analyze(
        self,
        data: pd.DataFrame,
        strategy_class,
        base_params: Dict,
        param_name: str,
        range_pct: float = 0.5,
        n_points: int = 11,
    ) -> pd.DataFrame:
        """
        分析单个参数的敏感性

        Args:
            data: K线数据
            strategy_class: 策略类
            base_params: 基础参数
            param_name: 要分析的参数名
            range_pct: 参数范围百分比
            n_points: 采样点数

        Returns:
            敏感性分析结果
        """
        from finquant.core.engine import BacktestEngineV2 as BacktestEngine

        base_value = base_params[param_name]
        lo = base_value * (1 - range_pct)
        hi = base_value * (1 + range_pct)

        # 生成参数值
        if param_name in ['period', 'short', 'long', 'fast', 'slow']:
            # 整数参数
            values = [int(v) for v in np.linspace(lo, hi, n_points)]
        else:
            values = np.linspace(lo, hi, n_points)

        results = []

        for v in values:
            params = base_params.copy()
            params[param_name] = v

            # 运行回测
            engine = BacktestEngine()
            result = engine.run(data, strategy_class(**params))

            results.append({
                'param_value': v,
                'return': result.total_return,
                'sharpe': result.sharpe_ratio,
                'drawdown': result.max_drawdown,
                'trades': result.total_trades,
            })

        return pd.DataFrame(results)

    def analyze_2d(
        self,
        data: pd.DataFrame,
        strategy_class,
        base_params: Dict,
        param1: str,
        param2: str,
        n_points: int = 10,
    ) -> pd.DataFrame:
        """
        二维敏感性分析（参数网格）

        Args:
            data: K线数据
            strategy_class: 策略类
            base_params: 基础参数
            param1: 参数1名
            param2: 参数2名
            n_points: 每个参数的点数

        Returns:
            二维敏感性结果
        """
        from finquant.core.engine import BacktestEngineV2 as BacktestEngine

        results = []

        # 参数1范围
        v1_base = base_params[param1]
        v1_lo = v1_base * 0.5
        v1_hi = v1_base * 1.5
        v1_values = [int(v) for v in np.linspace(v1_lo, v1_hi, n_points)]

        # 参数2范围
        v2_base = base_params[param2]
        v2_lo = v2_base * 0.5
        v2_hi = v2_base * 1.5
        v2_values = [int(v) for v in np.linspace(v2_lo, v2_hi, n_points)]

        for v1 in v1_values:
            for v2 in v2_values:
                params = base_params.copy()
                params[param1] = v1
                params[param2] = v2

                engine = BacktestEngine()
                result = engine.run(data, strategy_class(**params))

                results.append({
                    param1: v1,
                    param2: v2,
                    'return': result.total_return,
                    'sharpe': result.sharpe_ratio,
                })

        return pd.DataFrame(results)


# ========== 参数稳定性评估 ==========

class ParameterStability:
    """
    参数稳定性评估
    """

    @staticmethod
    def evaluate(wf_results: pd.DataFrame) -> dict:
        """
        评估参数稳定性

        Args:
            wf_results: Walk-Forward 结果

        Returns:
            稳定性评估指标
        """
        import numpy as np

        if wf_results.empty:
            return {}

        # 提取测试收益
        test_returns = wf_results['test_return'].values
        test_sharpes = wf_results['test_sharpe'].values

        # 计算稳定性指标
        return {
            # 收益稳定性
            'mean_return': np.mean(test_returns),
            'std_return': np.std(test_returns),
            'return_cv': np.std(test_returns) / np.mean(test_returns) if np.mean(test_returns) != 0 else 0,

            # 夏普稳定性
            'mean_sharpe': np.mean(test_sharpes),
            'std_sharpe': np.std(test_sharpes),

            # 胜率（正收益轮次比例）
            'win_rate': np.sum(test_returns > 0) / len(test_returns),

            # 稳定性得分 (0-1)
            'stability_score': 1 - min(1, np.std(test_returns) / (abs(np.mean(test_returns)) + 0.001)),
        }


__all__ = [
    "SensitivityAnalyzer",
    "ParameterStability",
]
