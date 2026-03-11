"""
finquant - 性能基准测试

对比 V1 和 V2 向量化策略的性能
"""

import time
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# V1 策略（旧版本）
from finquant.strategies import MACrossStrategy as MACrossStrategyV1

# V2 策略（新版本）
from finquant.strategies_v2 import MAStrategy as MAStrategyV2


def generate_mock_data(
    codes: list,
    start_date: str,
    end_date: str,
    initial_price: float = 100.0,
) -> pd.DataFrame:
    """
    生成模拟 K 线数据

    Args:
        codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        initial_price: 初始价格
    """
    # 生成日期
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    dates = pd.date_range(start, end, freq='B')  # 工作日

    all_data = []

    for code in codes:
        # 生成随机价格序列
        np.random.seed(hash(code) % 10000)
        n = len(dates)

        # 模拟价格波动
        returns = np.random.normal(0.001, 0.02, n)
        prices = initial_price * np.exp(np.cumsum(returns))

        # 生成 OHLCV
        for i, date in enumerate(dates):
            close = prices[i]
            open_price = prices[i - 1] if i > 0 else close * (1 + np.random.uniform(-0.01, 0.01))
            high = max(open_price, close) * (1 + abs(np.random.uniform(0, 0.02)))
            low = min(open_price, close) * (1 - abs(np.random.uniform(0, 0.02)))
            volume = np.random.randint(1000000, 10000000)

            all_data.append({
                'code': code,
                'trade_date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
            })

    df = pd.DataFrame(all_data)
    return df


def run_v1_backtest(data: pd.DataFrame, strategy, code: str) -> dict:
    """
    V1 风格回测（模拟旧版逐日计算）
    """
    trade_dates = sorted(data['trade_date'].unique())
    trades = []
    cash = 100000
    position = 0
    cost = 0

    for i, current_date in enumerate(trade_dates):
        # 模拟 V1 的逐行计算方式
        stock_data = data[(data['code'] == code) & (data['trade_date'] <= current_date)].copy()
        stock_data = stock_data.sort_values('trade_date')

        if len(stock_data) < 21:
            continue

        # 每次重新计算指标（V1 方式）
        stock_data['ma_short'] = stock_data['close'].rolling(5).mean()
        stock_data['ma_long'] = stock_data['close'].rolling(20).mean()

        if len(stock_data) < 2:
            continue

        last_ma_short = stock_data['ma_short'].iloc[-1]
        prev_ma_short = stock_data['ma_short'].iloc[-2]
        last_ma_long = stock_data['ma_long'].iloc[-1]
        prev_ma_long = stock_data['ma_long'].iloc[-2]

        current_price = stock_data['close'].iloc[-1]

        # 金叉买入
        if prev_ma_short <= prev_ma_long and last_ma_short > last_ma_long:
            if position == 0 and cash > current_price * 100:
                shares = int(cash / current_price / 100) * 100
                cost = shares * current_price * 1.0003
                if cost <= cash:
                    cash -= cost
                    position = shares
                    trades.append({'action': 'BUY', 'price': current_price, 'shares': shares})

        # 死叉卖出
        elif prev_ma_short >= prev_ma_long and last_ma_short < last_ma_long:
            if position > 0:
                proceeds = position * current_price * 0.9997
                cash += proceeds
                trades.append({'action': 'SELL', 'price': current_price, 'shares': position})
                position = 0

    # 计算最终资产
    final_price = data[(data['code'] == code) & (data['trade_date'] == trade_dates[-1])]['close'].iloc[0]
    final_value = cash + position * final_price

    return {
        'final_value': final_value,
        'trades': len(trades),
    }


def run_v2_backtest(data: pd.DataFrame, strategy, code: str) -> dict:
    """
    V2 向量化回测（批量获取信号）
    """
    trade_dates = sorted(data['trade_date'].unique())
    trades = []
    cash = 100000
    position = 0
    cost = 0

    # 预计算所有指标 + 批量获取信号
    strategy.precompute(data)
    all_signals = strategy.get_all_signals(data)

    # 过滤该股票的信号
    code_signals = all_signals[all_signals['code'] == code].copy()
    code_signals = code_signals.sort_values('trade_date')

    # 快速查找价格
    price_map = data[data['code'] == code].set_index('trade_date')['close'].to_dict()

    for _, row in code_signals.iterrows():
        current_date = row['trade_date']
        signal = row['signal']
        current_price = price_map.get(current_date)

        if current_price is None or signal == 0:
            continue

        # 买入
        if signal == 1:
            if position == 0 and cash > current_price * 100:
                shares = int(cash / current_price / 100) * 100
                cost = shares * current_price * 1.0003
                if cost <= cash:
                    cash -= cost
                    position = shares
                    trades.append({'action': 'BUY', 'price': current_price, 'shares': shares})

        # 卖出
        elif signal == -1:
            if position > 0:
                proceeds = position * current_price * 0.9997
                cash += proceeds
                trades.append({'action': 'SELL', 'price': current_price, 'shares': position})
                position = 0

    # 计算最终资产
    final_price = data[(data['code'] == code) & (data['trade_date'] == trade_dates[-1])]['close'].iloc[0]
    final_value = cash + position * final_price

    return {
        'final_value': final_value,
        'trades': len(trades),
    }


def run_performance_test(
    codes: list = None,
    start_date: str = "2020-01-01",
    end_date: str = "2024-12-31",
    n_runs: int = 3,
) -> dict:
    """
    运行性能对比测试
    """
    if codes is None:
        codes = ['SH600519', 'SH000001', 'SZ000001']

    print(f"\n{'='*60}")
    print(f"finquant 性能对比测试")
    print(f"{'='*60}")
    print(f"股票数量: {len(codes)}")
    print(f"时间范围: {start_date} ~ {end_date}")

    # 生成测试数据
    print(f"\n生成测试数据...")
    data = generate_mock_data(codes, start_date, end_date)
    print(f"数据量: {len(data)} 行")

    # 测试代码
    test_code = codes[0]

    # ===== V1 测试 =====
    print(f"\n--- V1 (旧版逐行计算) ---")
    strategy_v1 = MACrossStrategyV1(short_period=5, long_period=20)

    v1_times = []
    for i in range(n_runs):
        start = time.time()
        result_v1 = run_v1_backtest(data, strategy_v1, test_code)
        elapsed = time.time() - start
        v1_times.append(elapsed)
        print(f"  运行 {i+1}: {elapsed:.3f}s | 交易: {result_v1['trades']} | 最终价值: {result_v1['final_value']:,.0f}")

    v1_avg_time = np.mean(v1_times)

    # ===== V2 测试 =====
    print(f"\n--- V2 (向量化预计算) ---")
    strategy_v2 = MAStrategyV2(short_period=5, long_period=20)

    v2_times = []
    for i in range(n_runs):
        start = time.time()
        result_v2 = run_v2_backtest(data, strategy_v2, test_code)
        elapsed = time.time() - start
        v2_times.append(elapsed)
        print(f"  运行 {i+1}: {elapsed:.3f}s | 交易: {result_v2['trades']} | 最终价值: {result_v2['final_value']:,.0f}")

    v2_avg_time = np.mean(v2_times)

    # ===== 结果对比 =====
    print(f"\n{'='*60}")
    print(f"性能对比结果")
    print(f"{'='*60}")
    print(f"V1 平均耗时: {v1_avg_time:.3f}s")
    print(f"V2 平均耗时: {v2_avg_time:.3f}s")
    print(f"性能提升: {v1_avg_time / v2_avg_time:.1f}x")

    # 结果一致性检查
    print(f"\n--- 结果一致性 ---")
    print(f"V1 最终价值: {result_v1['final_value']:,.2f}")
    print(f"V2 最终价值: {result_v2['final_value']:,.2f}")
    print(f"V1 交易次数: {result_v1['trades']}")
    print(f"V2 交易次数: {result_v2['trades']}")

    diff_value = abs(result_v1['final_value'] - result_v2['final_value'])
    diff_pct = diff_value / result_v1['final_value'] * 100
    print(f"价值差异: {diff_value:,.2f} ({diff_pct:.4f}%)")

    if diff_value < 1:  # 差异小于1元视为一致
        print("✓ 结果一致性: PASS")
        consistent = True
    else:
        print("✗ 结果一致性: FAIL")
        consistent = False

    return {
        'v1_time': v1_avg_time,
        'v2_time': v2_avg_time,
        'speedup': v1_avg_time / v2_avg_time,
        'v1_result': result_v1,
        'v2_result': result_v2,
        'consistent': consistent,
    }


def run_scalability_test():
    """
    扩展性测试：测试不同数据量下的性能
    """
    print(f"\n{'='*60}")
    print(f"扩展性测试")
    print(f"{'='*60}")

    test_configs = [
        (["SH600519"], "2023-01-01", "2024-12-31", "单股票1年"),
        (["SH600519"], "2020-01-01", "2024-12-31", "单股票5年"),
        (["SH600519", "SH000001"], "2020-01-01", "2024-12-31", "2股票5年"),
        (["SH600519", "SH000001", "SZ000001"], "2020-01-01", "2024-12-31", "3股票5年"),
    ]

    results = []

    for codes, start, end, label in test_configs:
        data = generate_mock_data(codes, start, end)
        print(f"\n{label}: {len(data)} 行数据")

        # V1
        strategy_v1 = MACrossStrategyV1()
        start_time = time.time()
        result_v1 = run_v1_backtest(data, strategy_v1, codes[0])
        v1_time = time.time() - start_time

        # V2
        strategy_v2 = MAStrategyV2()
        start_time = time.time()
        result_v2 = run_v2_backtest(data, strategy_v2, codes[0])
        v2_time = time.time() - start_time

        speedup = v1_time / v2_time

        print(f"  V1: {v1_time:.3f}s | V2: {v2_time:.3f}s | 提升: {speedup:.1f}x")

        results.append({
            'label': label,
            'rows': len(data),
            'v1_time': v1_time,
            'v2_time': v2_time,
            'speedup': speedup,
        })

    return results


if __name__ == "__main__":
    # 运行性能测试
    result = run_performance_test()

    # 检查是否达到 10x 目标
    print(f"\n{'='*60}")
    if result['speedup'] >= 10:
        print(f"✓ 性能目标达成: {result['speedup']:.1f}x >= 10x")
    elif result['speedup'] >= 5:
        print(f"⚠ 性能提升显著: {result['speedup']:.1f}x，建议优化")
    else:
        print(f"✗ 性能提升不足: {result['speedup']:.1f}x < 10x")

    # 运行扩展性测试
    scalability_results = run_scalability_test()

    print(f"\n{'='*60}")
    print(f"测试完成")
    print(f"{'='*60}")
