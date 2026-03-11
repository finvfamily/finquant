"""
finquant - 量化研究实验室 (QuantLab)

统一的策略研究环境，整合因子研究和回测分析功能：
- 因子研究（IC分析、分组回测、相关性、合成）
- 策略回测
- 参数优化
- 绩效分析
- 策略对比
"""

from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np

from finquant.core import BacktestEngineV2, BacktestConfig


@dataclass
class LabConfig:
    """研究实验室配置"""
    name: str = "QuantLab"              # 实验室名称
    initial_capital: float = 1000000   # 初始资金
    benchmark: str = "SH510300"         # 基准代码
    risk_free_rate: float = 0.03        # 无风险利率


@dataclass
class FactorStudyResult:
    """因子研究结果"""
    factor_name: str
    ic_mean: float = 0
    ic_ir: float = 0
    rank_ic_mean: float = 0
    group_return: float = 0            # 分组收益
    long_short_return: float = 0       # 多空收益
    correlation: Dict[str, float] = field(default_factory=dict)
    weight: float = 0                  # 合成权重


@dataclass
class BacktestStudyResult:
    """回测研究结果"""
    strategy_name: str
    total_return: float = 0
    annual_return: float = 0
    sharpe_ratio: float = 0
    max_drawdown: float = 0
    win_rate: float = 0
    trades: int = 0
    daily_returns: pd.Series = None


class QuantLab:
    """
    量化研究实验室 (QuantLab)

    统一的策略研究入口，整合因子研究、回测分析、参数优化等功能

    使用示例:
        lab = QuantLab()

        # 1. 加载数据
        lab.load_data(codes, start_date, end_date)

        # 2. 计算因子
        lab.calculate_factors(['momentum_10', 'rsi_14'])

        # 3. 因子研究
        lab.study_factors()

        # 4. 策略回测
        lab.backtest(strategy)

        # 5. 参数优化
        lab.optimize(strategy_class, param_grid)

        # 6. 获取报告
        report = lab.get_report()
    """

    def __init__(self, config: LabConfig = None):
        """
        Args:
            config: 实验室配置
        """
        self.config = config or LabConfig()

        # 数据
        self.data: Optional[pd.DataFrame] = None
        self.factor_data: Dict[str, pd.Series] = {}

        # 研究结果
        self.factor_results: Dict[str, FactorStudyResult] = {}
        self.backtest_results: Dict[str, BacktestStudyResult] = {}
        self.optimize_results: Optional[pd.DataFrame] = None

        # 配置
        self.forward_return_days: int = 5  # 未来收益计算天数
        self.n_groups: int = 5              # 分组数量

    def load_data(
        self,
        codes: Union[str, List[str]],
        start: str = None,
        end: str = None,
        **kwargs
    ) -> 'QuantLab':
        """
        加载数据

        Args:
            codes: 股票代码
            start: 开始日期
            end: 结束日期
            **kwargs: 其他参数传递给 get_kline

        Returns:
            self
        """
        from finquant import get_kline

        if isinstance(codes, str):
            codes = [codes]

        self.data = get_kline(codes, start=start, end=end, **kwargs)

        # 计算未来收益
        self._calculate_forward_returns()

        print(f"[QuantLab] 加载数据: {len(self.data)} 条, {len(codes)} 只股票")
        print(f"[QuantLab] 时间范围: {self.data['trade_date'].min()} ~ {self.data['trade_date'].max()}")

        return self

    def _calculate_forward_returns(self) -> None:
        """计算未来收益"""
        if self.data is None:
            return

        # 按股票计算未来收益
        result = []
        for code, group in self.data.groupby('code'):
            group = group.sort_values('trade_date')
            group['forward_return'] = group['close'].shift(-self.forward_return_days) / group['close'] - 1
            result.append(group)

        self.data = pd.concat(result, ignore_index=True)

    def calculate_factor(
        self,
        name: str,
        func: Callable,
        **params
    ) -> 'QuantLab':
        """
        计算自定义因子

        Args:
            name: 因子名称
            func: 因子计算函数，接收DataFrame，返回因子Series
            **params: 函数参数

        Returns:
            self
        """
        if self.data is None:
            raise ValueError("请先调用 load_data() 加载数据")

        print(f"[QuantLab] 计算因子: {name}")

        # 按股票计算
        result = []
        for code, group in self.data.groupby('code'):
            group = group.sort_values('trade_date')
            factor_values = func(group, **params)
            group[name] = factor_values
            result.append(group)

        self.data = pd.concat(result, ignore_index=True)
        self.factor_data[name] = self.data[name]

        return self

    def add_factor_from_library(
        self,
        factor_name: str,
        periods: List[int] = None,
    ) -> 'QuantLab':
        """
        从因子库添加因子

        Args:
            factor_name: 因子名称 (如 'momentum', 'rsi', 'ma')
            periods: 周期列表 (如 [5, 10, 20])

        Returns:
            self
        """
        from finquant.data.factors import FactorLibrary

        if self.data is None:
            raise ValueError("请先调用 load_data() 加载数据")

        if periods is None:
            periods = [10]  # 默认

        print(f"[QuantLab] 从因子库添加因子: {factor_name}")

        # 获取因子函数
        if not hasattr(FactorLibrary, factor_name):
            raise ValueError(f"因子库中没有因子: {factor_name}")

        factor_func = getattr(FactorLibrary, factor_name)

        # 按股票计算
        result = []
        for code, group in self.data.groupby('code'):
            group = group.sort_values('trade_date')

            for period in periods:
                col_name = f"{factor_name}_{period}"
                group[col_name] = factor_func(group['close'], period)
                self.factor_data[col_name] = group[col_name]

            result.append(group)

        self.data = pd.concat(result, ignore_index=True)

        return self

    def calculate_factors(
        self,
        factor_names: List[str] = None,
    ) -> 'QuantLab':
        """
        批量计算技术因子

        Args:
            factor_names: 因子名称列表

        Returns:
            self
        """
        if factor_names is None:
            # 默认计算常用因子
            factor_names = ['momentum', 'rsi', 'ma', 'volatility', 'volume_ratio']

        for factor_name in factor_names:
            if factor_name == 'momentum':
                self.add_factor_from_library('momentum', [5, 10, 20])
            elif factor_name == 'rsi':
                self.add_factor_from_library('rsi', [6, 12, 24])
            elif factor_name == 'ma':
                self.add_factor_from_library('ma', [5, 10, 20, 60])
            elif factor_name == 'volatility':
                self.add_factor_from_library('volatility', [10, 20])
            elif factor_name == 'volume_ratio':
                self.add_factor_from_library('volume_ratio', [10, 20])
            elif factor_name == 'ma_bias':
                self.add_factor_from_library('ma_bias', [10, 20])

        return self

    def study_factors(
        self,
        factor_cols: List[str] = None,
    ) -> Dict[str, FactorStudyResult]:
        """
        因子研究

        Args:
            factor_cols: 因子列列表，默认使用所有计算的因子

        Returns:
            因子研究结果字典
        """
        from finquant.research import FactorICAnalyzer, GroupICAnalyzer, FactorCorrelation

        if self.data is None:
            raise ValueError("请先加载数据")

        if factor_cols is None:
            factor_cols = list(self.factor_data.keys())

        print(f"[QuantLab] 因子研究: {len(factor_cols)} 个因子")
        print("-" * 60)

        # 1. IC分析
        print("  [1/3] IC分析...")
        ic_analyzer = FactorICAnalyzer()
        ic_results = ic_analyzer.analyze(
            self.data, factor_cols, forward_return_col='forward_return'
        )

        # 2. 分组回测
        print("  [2/3] 分组回测...")
        group_analyzer = GroupICAnalyzer(n_groups=self.n_groups)

        # 3. 相关性分析
        print("  [3/3] 相关性分析...")
        corr_analyzer = FactorCorrelation(threshold=0.8)
        corr_results = corr_analyzer.analyze(self.data, factor_cols)

        # 整合结果
        self.factor_results = {}

        # 检查ic_results是否有数据
        if ic_results.empty:
            print("  警告: 因子研究数据不足，请确保数据足够长")
            return self.factor_results

        for factor in factor_cols:
            result = FactorStudyResult(factor_name=factor)

            # IC结果
            ic_row = ic_results[ic_results['factor'] == factor]
            if not ic_row.empty:
                result.ic_mean = float(ic_row['ic_mean'].values[0])
                result.ic_ir = float(ic_row['ic_ir'].values[0])
                result.rank_ic_mean = float(ic_row['rank_ic_mean'].values[0])

            # 分组结果
            ls_return = group_analyzer.calculate_long_short_return(
                self.data, factor, 'forward_return'
            )
            if ls_return:
                result.long_short_return = ls_return.get('long_short_return', 0)

            # 相关性
            if corr_results.high_corr_pairs:
                high_corr = [p for p in corr_results.high_corr_pairs if p['factor1'] == factor or p['factor2'] == factor]
                for p in high_corr:
                    other = p['factor2'] if p['factor1'] == factor else p['factor1']
                    result.correlation[other] = p['correlation']

            self.factor_results[factor] = result

        # 打印结果
        self._print_factor_results()

        return self.factor_results

    def _print_factor_results(self) -> None:
        """打印因子研究结果"""
        print("\n因子研究结果:")
        print("-" * 80)
        print(f"{'因子':<20} {'IC均值':>10} {'IC_IR':>10} {'多空收益':>12} {'评级':>6}")
        print("-" * 80)

        for name, result in self.factor_results.items():
            # 评级
            if result.ic_ir > 0.5:
                rating = 'A+'
            elif result.ic_ir > 0.3:
                rating = 'A'
            elif result.ic_ir > 0.1:
                rating = 'B'
            else:
                rating = 'C'

            print(f"{name:<20} {result.ic_mean:>10.4f} {result.ic_ir:>10.4f} "
                  f"{result.long_short_return:>12.2%} {rating:>6}")

    def backtest(
        self,
        strategy,
        name: str = None,
        **kwargs
    ) -> BacktestStudyResult:
        """
        策略回测

        Args:
            strategy: 策略实例
            name: 策略名称
            **kwargs: 回测配置

        Returns:
            回测结果
        """
        from finquant import BacktestEngineV2, BacktestConfig

        if self.data is None:
            raise ValueError("请先加载数据")

        strategy_name = name or strategy.__class__.__name__

        print(f"[QuantLab] 回测策略: {strategy_name}")

        # 运行回测
        engine = BacktestEngineV2(
            BacktestConfig(initial_capital=self.config.initial_capital, **kwargs)
        )
        engine.add_strategy(strategy)

        # 获取日期范围
        start_date = str(self.data['trade_date'].min())[:10]
        end_date = str(self.data['trade_date'].max())[:10]

        result = engine.run(self.data, start_date, end_date)

        # 保存结果
        study_result = BacktestStudyResult(
            strategy_name=strategy_name,
            total_return=result.total_return,
            annual_return=result.annual_return,
            sharpe_ratio=result.sharpe_ratio,
            max_drawdown=result.max_drawdown,
            win_rate=result.win_rate,
            trades=result.total_trades,
        )

        self.backtest_results[strategy_name] = study_result

        # 打印结果
        print(f"\n回测结果: {strategy_name}")
        print(f"  总收益: {result.total_return:.2%}")
        print(f"  年化收益: {result.annual_return:.2%}")
        print(f"  夏普比率: {result.sharpe_ratio:.2f}")
        print(f"  最大回撤: {result.max_drawdown:.2%}")
        print(f"  胜率: {result.win_rate:.2%}")

        return study_result

    def optimize(
        self,
        strategy_class,
        param_grid: Dict[str, List],
        objective: str = "sharpe_ratio",
        method: str = "grid",
    ) -> pd.DataFrame:
        """
        参数优化

        Args:
            strategy_class: 策略类
            param_grid: 参数网格
            objective: 优化目标
            method: 优化方法 "grid" 或 "bayesian"

        Returns:
            优化结果
        """
        from finquant.optimize import GridSearchOptimizer, BayesianOptimizer, BayesianConfig

        if self.data is None:
            raise ValueError("请先加载数据")

        print(f"[QuantLab] 参数优化: {strategy_class.__name__}")
        print(f"  参数网格: {param_grid}")
        print(f"  优化目标: {objective}")

        if method == "grid":
            optimizer = GridSearchOptimizer(
                data=self.data,
                strategy_class=strategy_class,
                param_grid=param_grid,
            )
            optimizer.optimize(objective=objective, verbose=False)

            # 获取结果
            results = optimizer.results_

            # 转换为DataFrame
            df = pd.DataFrame(results)

        elif method == "bayesian":
            # 贝叶斯优化
            config = BayesianConfig(n_iter=20)

            # 构建参数边界
            param_bounds = {}
            for param, values in param_grid.items():
                param_bounds[param] = (min(values), max(values))

            optimizer = BayesianOptimizer(param_bounds, config)

            # 目标函数
            def objective_fn(params):
                strategy = strategy_class(**params)
                engine = BacktestEngineV2(BacktestConfig(initial_capital=self.config.initial_capital))
                engine.add_strategy(strategy)

                try:
                    result = engine.run(self.data)
                    if objective == "sharpe_ratio":
                        return result.sharpe_ratio
                    elif objective == "total_return":
                        return result.total_return
                    else:
                        return result.sharpe_ratio
                except:
                    return -999

            best_params, best_score = optimizer.optimize(objective_fn, maximize=True, verbose=False)

            # 获取历史
            df = optimizer.get_history()

            print(f"  最优参数: {best_params}")
            print(f"  最优分数: {best_score:.4f}")

        else:
            raise ValueError(f"Unknown method: {method}")

        self.optimize_results = df

        # 打印Top5
        if not df.empty:
            print(f"\nTop 5 结果:")
            top5 = df.nlargest(5, 'score') if 'score' in df.columns else df.head(5)
            print(top5.to_string(index=False))

        return df

    def compare_strategies(self) -> pd.DataFrame:
        """
        策略对比

        Returns:
            对比结果表格
        """
        if not self.backtest_results:
            return pd.DataFrame()

        rows = []
        for name, result in self.backtest_results.items():
            rows.append({
                '策略': name,
                '总收益': result.total_return,
                '年化收益': result.annual_return,
                '夏普比率': result.sharpe_ratio,
                '最大回撤': result.max_drawdown,
                '胜率': result.win_rate,
                '交易次数': result.trades,
            })

        df = pd.DataFrame(rows)

        print("\n策略对比:")
        print(df.to_string(index=False))

        return df

    def get_report(self) -> Dict[str, Any]:
        """
        获取研究报告

        Returns:
            包含所有研究结果的字典
        """
        report = {
            'config': self.config,
            'data_info': {
                'n_records': len(self.data) if self.data is not None else 0,
                'n_stocks': self.data['code'].nunique() if self.data is not None else 0,
                'date_range': (
                    str(self.data['trade_date'].min()) if self.data is not None else None,
                    str(self.data['trade_date'].max()) if self.data is not None else None,
                ),
            },
            'factor_results': {
                name: {
                    'ic_mean': r.ic_mean,
                    'ic_ir': r.ic_ir,
                    'long_short_return': r.long_short_return,
                }
                for name, r in self.factor_results.items()
            },
            'backtest_results': {
                name: {
                    'total_return': r.total_return,
                    'annual_return': r.annual_return,
                    'sharpe_ratio': r.sharpe_ratio,
                    'max_drawdown': r.max_drawdown,
                }
                for name, r in self.backtest_results.items()
            },
            'optimize_results': self.optimize_results,
        }

        return report

    def save_report(self, path: str) -> None:
        """
        保存研究报告

        Args:
            path: 保存路径
        """
        import json

        report = self.get_report()

        # 转换日期
        if report['data_info']['date_range']:
            report['data_info']['date_range'] = [
                str(d)[:10] if d else None
                for d in report['data_info']['date_range']
            ]

        # 保存为JSON
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"[QuantLab] 报告已保存: {path}")


# ========== 便捷函数 ==========


def create_lab(name: str = "QuantLab", **kwargs) -> QuantLab:
    """
    创建量化研究实验室

    Args:
        name: 实验室名称
        **kwargs: 配置参数

    Returns:
        QuantLab实例
    """
    config = LabConfig(name=name, **kwargs)
    return QuantLab(config)


__all__ = [
    "LabConfig",
    "FactorStudyResult",
    "BacktestStudyResult",
    "QuantLab",
    "create_lab",
]
