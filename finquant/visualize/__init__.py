"""
finquant - 可视化模块

提供回测结果可视化功能
"""

from typing import List
import pandas as pd
import numpy as np


# ========== 文本可视化 ==========

def plot_text_equity(result) -> str:
    """文本版权益曲线"""
    if not result.daily_equity:
        return "无数据"

    df = pd.DataFrame(result.daily_equity)

    # 采样显示
    n = len(df)
    if n > 20:
        step = n // 20
        df_plot = df.iloc[::step]
    else:
        df_plot = df

    lines = ["\n========== 权益曲线 =========="]
    lines.append(f"{'日期':<12} {'现金':>12} {'持仓':>12} {'总资产':>12}")
    lines.append("-" * 52)

    for _, row in df_plot.iterrows():
        date = str(row.get('date', ''))[:10]
        cash = row.get('cash', 0)
        pos_value = row.get('position_value', 0)
        total = row.get('total_assets', 0)
        lines.append(f"{date:<12} {cash:>12,.0f} {pos_value:>12,.0f} {total:>12,.0f}")

    return "\n".join(lines)


def plot_text_drawdown(result) -> str:
    """文本版回撤曲线"""
    if not result.daily_equity:
        return "无数据"

    df = pd.DataFrame(result.daily_equity)
    equity = df['total_assets'].values
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak * 100

    # 找最大回撤
    max_dd = drawdown.min()
    max_dd_idx = np.argmin(drawdown)

    lines = ["\n========== 回撤分析 =========="]
    lines.append(f"最大回撤: {max_dd:.2f}%")
    lines.append(f"回撤开始: {df.iloc[max_dd_idx-1].get('date', '') if max_dd_idx > 0 else 'N/A'}")
    lines.append(f"回撤最低: {df.iloc[max_dd_idx].get('date', '')}")

    # 回撤分布
    dd_ranges = [
        (0, 5, "0-5%"),
        (5, 10, "5-10%"),
        (10, 20, "10-20%"),
        (20, 50, "20-50%"),
        (50, 100, "50%+"),
    ]

    lines.append("\n回撤分布:")
    for lo, hi, label in dd_ranges:
        count = np.sum((drawdown >= -hi) & (drawdown < -lo))
        pct = count / len(drawdown) * 100 if len(drawdown) > 0 else 0
        bar = "█" * int(pct / 2)
        lines.append(f"  {label:>8}: {bar} {pct:.1f}%")

    return "\n".join(lines)


def plot_text_returns(result) -> str:
    """文本版收益分布"""
    if not result.daily_equity:
        return "无数据"

    df = pd.DataFrame(result.daily_equity)
    returns = df['total_assets'].pct_change().dropna() * 100

    lines = ["\n========== 收益分布 =========="]
    lines.append(f"交易日数: {len(returns)}")
    lines.append(f"上涨天数: {(returns > 0).sum()} ({(returns > 0).mean()*100:.1f}%)")
    lines.append(f"下跌天数: {(returns < 0).sum()} ({(returns < 0).mean()*100:.1f}%)")
    lines.append(f"平均收益: {returns.mean():.2f}%")
    lines.append(f"收益标准差: {returns.std():.2f}%")
    lines.append(f"最大单日: {returns.max():.2f}%")
    lines.append(f"最大亏损: {returns.min():.2f}%")

    # 收益分布
    ranges = [
        (-100, -5, "< -5%"),
        (-5, -2, "-5% ~ -2%"),
        (-2, 0, "-2% ~ 0%"),
        (0, 2, "0% ~ 2%"),
        (2, 5, "2% ~ 5%"),
        (5, 100, "> 5%"),
    ]

    lines.append("\n收益分布:")
    for lo, hi, label in ranges:
        if lo < 0:
            count = np.sum((returns >= lo) & (returns < hi))
        else:
            count = np.sum((returns > lo) & (returns <= hi))
        pct = count / len(returns) * 100 if len(returns) > 0 else 0
        bar = "█" * int(pct / 2)
        lines.append(f"  {label:>12}: {bar} {pct:.1f}%")

    return "\n".join(lines)


def plot_text_trades(result) -> str:
    """文本版交易记录"""
    if not result.trades:
        return "无交易记录"

    lines = ["\n========== 交易记录 =========="]
    lines.append(f"{'日期':<12} {'代码':<10} {'方向':>6} {'价格':>10} {'数量':>8}")
    lines.append("-" * 50)

    for trade in result.trades[:20]:  # 只显示前20笔
        date = str(trade.get('date', ''))[:10]
        code = trade.get('code', '')
        action = trade.get('action', '')
        price = trade.get('price', 0)
        shares = trade.get('shares', 0)
        lines.append(f"{date:<12} {code:<10} {action:>6} {price:>10,.2f} {shares:>8}")

    if len(result.trades) > 20:
        lines.append(f"... 还有 {len(result.trades) - 20} 笔交易")

    return "\n".join(lines)


def plot_text_summary(result) -> str:
    """文本版摘要"""
    lines = [
        "╔════════════════════════════════════════╗",
        "║          回测结果摘要                  ║",
        "╠════════════════════════════════════════╣",
        f"║ 初始资金:  {result.initial_capital:>15,.2f}  ║",
        f"║ 最终资金:  {result.final_capital:>15,.2f}  ║",
        f"║ 总收益:    {result.total_return*100:>15,.2f}%  ║",
        f"║ 年化收益:  {result.annual_return*100:>15,.2f}%  ║",
        f"║ 夏普比率:  {result.sharpe_ratio:>15,.2f}  ║",
        f"║ 最大回撤:  {result.max_drawdown*100:>15,.2f}%  ║",
        f"║ 胜率:      {result.win_rate*100:>15,.2f}%  ║",
        f"║ 交易次数: {result.total_trades:>15}  ║",
        "╚════════════════════════════════════════╝",
    ]
    return "\n".join(lines)


# ========== 主类 ==========

class BacktestPlotter:
    """
    回测结果可视化

    支持文本和 matplotlib 可视化
    """

    def __init__(self, result):
        self.result = result

    def summary(self) -> str:
        """输出摘要"""
        return plot_text_summary(self.result)

    def equity(self) -> str:
        """输出权益曲线"""
        return plot_text_equity(self.result)

    def drawdown(self) -> str:
        """输出回撤分析"""
        return plot_text_drawdown(self.result)

    def returns(self) -> str:
        """输出收益分布"""
        return plot_text_returns(self.result)

    def trades(self) -> str:
        """输出交易记录"""
        return plot_text_trades(self.result)

    def all(self) -> str:
        """输出完整报告"""
        return "\n".join([
            self.summary(),
            self.equity(),
            self.drawdown(),
            self.returns(),
            self.trades(),
        ])

    # matplotlib 可视化（可选）
    def plot(self, backend: str = "matplotlib"):
        """绘图"""
        try:
            if backend == "matplotlib":
                self._plot_matplotlib()
            elif backend == "plotly":
                self._plot_plotly()
            else:
                raise ValueError(f"Unknown backend: {backend}")
        except ImportError:
            print("请安装 matplotlib: pip install matplotlib")
            print("使用文本可视化: print(backtest.all())")

    def _plot_matplotlib(self):
        """matplotlib 绘图"""
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')

        df = pd.DataFrame(self.result.daily_equity)

        fig, axes = plt.subplots(2, 2, figsize=(12, 8))

        # 权益曲线
        axes[0, 0].plot(df['total_assets'])
        axes[0, 0].set_title('权益曲线')
        axes[0, 0].set_xlabel('交易日')
        axes[0, 0].set_ylabel('资产')
        axes[0, 0].grid(True)

        # 回撤曲线
        equity = df['total_assets'].values
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak * 100
        axes[0, 1].fill_between(range(len(drawdown)), drawdown, 0)
        axes[0, 1].set_title('回撤')
        axes[0, 1].set_xlabel('交易日')
        axes[0, 1].set_ylabel('回撤 %')

        # 收益分布
        returns = df['total_assets'].pct_change().dropna() * 100
        axes[1, 0].hist(returns, bins=30, edgecolor='black')
        axes[1, 0].set_title('收益分布')
        axes[1, 0].set_xlabel('日收益率 %')
        axes[1, 0].set_ylabel('频次')

        # 买卖点
        if self.result.trades:
            dates = [t['date'] for t in self.result.trades]
            prices = [t['price'] for t in self.result.trades]
            colors = ['green' if t['action'] == 'BUY' else 'red' for t in self.result.trades]
            axes[1, 1].scatter(range(len(dates)), prices, c=colors, s=10)
            axes[1, 1].set_title('交易点位')
            axes[1, 1].set_xlabel('交易序号')
            axes[1, 1].set_ylabel('价格')

        plt.tight_layout()
        plt.savefig('backtest_result.png', dpi=150)
        print("图表已保存到: backtest_result.png")

    def _plot_plotly(self):
        """plotly 绘图"""
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            raise ImportError("请安装 plotly: pip install plotly")

        df = pd.DataFrame(self.result.daily_equity)

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['权益曲线', '回撤', '收益分布', '交易点位']
        )

        # 权益曲线
        fig.add_trace(
            go.Scatter(y=df['total_assets'], name='资产'),
            row=1, col=1
        )

        # 回撤
        equity = df['total_assets'].values
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak * 100
        fig.add_trace(
            go.Scatter(y=drawdown, fill='tozeroy', name='回撤'),
            row=1, col=2
        )

        # 收益分布
        returns = df['total_assets'].pct_change().dropna() * 100
        fig.add_trace(
            go.Histogram(x=returns, name='收益'),
            row=2, col=1
        )

        # 买卖点
        if self.result.trades:
            buys = [(i, t['price']) for i, t in enumerate(self.result.trades) if t['action'] == 'BUY']
            sells = [(i, t['price']) for i, t in enumerate(self.result.trades) if t['action'] == 'SELL']
            if buys:
                fig.add_trace(
                    go.Scatter(x=[b[0] for b in buys], y=[b[1] for b in buys],
                              mode='markers', marker=dict(color='green', symbol='triangle-up'),
                              name='买入'),
                    row=2, col=2
                )
            if sells:
                fig.add_trace(
                    go.Scatter(x=[s[0] for s in sells], y=[s[1] for s in sells],
                              mode='markers', marker=dict(color='red', symbol='triangle-down'),
                              name='卖出'),
                    row=2, col=2
                )

        fig.update_layout(height=600, showlegend=True)
        fig.write_html('backtest_result.html')
        print("交互式图表已保存到: backtest_result.html")


# ========== 便捷函数 ==========

def plot(result, backend: str = "text"):
    """
    可视化回测结果

    Args:
        result: BacktestResult
        backend: "text", "matplotlib", 或 "plotly"

    Returns:
        文本返回字符串，图表保存文件
    """
    plotter = BacktestPlotter(result)

    if backend == "text":
        return plotter.all()
    else:
        plotter.plot(backend)


def compare_results(results: List, names: List[str] = None) -> str:
    """
    对比多个回测结果

    Args:
        results: BacktestResult 列表
        names: 名称列表

    Returns:
        对比表格
    """
    if names is None:
        names = [f"策略{i+1}" for i in range(len(results))]

    lines = ["\n========== 策略对比 =========="]
    lines.append(f"{'名称':<12} {'总收益':>10} {'年化':>10} {'夏普':>8} {'回撤':>10} {'胜率':>8}")
    lines.append("-" * 62)

    for name, result in zip(names, results):
        lines.append(
            f"{name:<12} "
            f"{result.total_return*100:>9.2f}% "
            f"{result.annual_return*100:>9.2f}% "
            f"{result.sharpe_ratio:>8.2f} "
            f"{result.max_drawdown*100:>9.2f}% "
            f"{result.win_rate*100:>7.2f}%"
        )

    return "\n".join(lines)


__all__ = [
    "BacktestPlotter",
    "plot",
    "compare_results",
    "plot_text_summary",
    "plot_text_equity",
    "plot_text_drawdown",
    "plot_text_returns",
    "plot_text_trades",
]
