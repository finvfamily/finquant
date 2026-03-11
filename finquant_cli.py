#!/usr/bin/env python
"""
finquant 命令行工具

Usage:
    finquant backtest --code SH600519 --strategy ma_cross
    finquant compare --codes SH600519,SH000001 --strategies ma_cross,rsi
    finquant optimize --strategy rsi --params period:5-30
"""

import sys
import argparse
from typing import List
import pandas as pd


def cmd_backtest(args):
    """回测命令"""
    from finquant.api import backtest

    print(f"回测: {args.code}")
    print(f"策略: {args.strategy}")
    print(f"参数: {args.params}")
    print(f"资金: {args.capital}")
    print(f"时间: {args.start} ~ {args.end}")
    print("-" * 50)

    # 解析策略参数
    params = {}
    if args.params:
        for p in args.params:
            if '=' in p:
                k, v = p.split('=')
                try:
                    params[k] = int(v)
                except:
                    try:
                        params[k] = float(v)
                    except:
                        params[k] = v

    # 运行回测
    result = backtest(
        data=args.code,
        strategy=args.strategy,
        initial_capital=args.capital,
        start=args.start,
        end=args.end,
        **params
    )

    # 输出结果
    print("\n========== 回测结果 ==========")
    print(f"初始资金: {result.initial_capital:,.2f}")
    print(f"最终资金: {result.final_capital:,.2f}")
    print(f"总收益: {result.total_return:.2%}")
    print(f"年化收益: {result.annual_return:.2%}")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"最大回撤: {result.max_drawdown:.2%}")
    print(f"胜率: {result.win_rate:.2%}")
    print(f"交易次数: {result.total_trades}")

    # 保存结果
    if args.output:
        result.to_dataframe().to_csv(args.output, index=False)
        print(f"\n结果已保存到: {args.output}")


def cmd_compare(args):
    """策略对比命令"""
    from finquant.api import compare

    codes = args.codes.split(',')
    strategies = args.strategies.split(',')

    print(f"对比策略: {strategies}")
    print(f"股票: {codes}")
    print("-" * 50)

    # 如果是多个股票，合并数据
    from finquant.data_v2 import get_kline
    data_list = []
    for code in codes:
        df = get_kline(code, start=args.start, end=args.end)
        if not df.empty:
            data_list.append(df)

    if not data_list:
        print("没有获取到数据")
        return

    data = pd.concat(data_list, ignore_index=True)

    # 对比
    results = compare(
        strategies=strategies,
        data=data,
        initial_capital=args.capital,
    )

    print("\n========== 策略对比结果 ==========")
    print(results.to_string(index=False))

    if args.output:
        results.to_csv(args.output, index=False)
        print(f"\n结果已保存到: {args.output}")


def cmd_optimize(args):
    """参数优化命令"""
    from finquant.api import optimize

    print(f"优化策略: {args.strategy}")
    print(f"参数范围: {args.params}")
    print(f"优化目标: {args.objective}")
    print("-" * 50)

    # 解析参数范围
    param_dict = {}
    for p in args.params:
        if ':' in p:
            k, v = p.split(':')
            if ',' in v:
                # 网格搜索
                values = [int(x) for x in v.split(',')]
                param_dict[k] = values
            elif '-' in v:
                # 贝叶斯优化范围
                lo, hi = v.split('-')
                param_dict[k] = (float(lo), float(hi))

    # 优化
    result = optimize(
        data=args.code,
        strategy=args.strategy,
        params=param_dict,
        objective=args.objective,
        method=args.method,
        start=args.start,
        end=args.end,
    )

    print("\n========== 优化结果 ==========")
    print(f"最优参数: {result['best_params']}")
    print(f"最优分数: {result['best_score']:.4f}")

    if 'all_results' in result:
        print("\n所有结果:")
        print(result['all_results'].head(10).to_string(index=False))

    if args.output:
        if 'all_results' in result:
            result['all_results'].to_csv(args.output, index=False)
        print(f"\n结果已保存到: {args.output}")


def cmd_data(args):
    """数据命令"""
    from finquant.data_v2 import get_kline

    codes = args.code.split(',')

    print(f"获取数据: {codes}")
    print(f"时间: {args.start} ~ {args.end}")
    print(f"周期: {args.period}")
    print("-" * 50)

    data = get_kline(codes, start=args.start, end=args.end, period=args.period)

    print(f"\n获取到 {len(data)} 条数据")

    if args.output:
        data.to_csv(args.output, index=False)
        print(f"数据已保存到: {args.output}")
    elif args.preview:
        print(data.head(20).to_string())


def main():
    parser = argparse.ArgumentParser(
        description="finquant - 量化回测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # backtest 命令
    backtest_parser = subparsers.add_parser('backtest', help='运行回测')
    backtest_parser.add_argument('--code', '-c', required=True, help='股票代码')
    backtest_parser.add_argument('--strategy', '-s', default='ma_cross', help='策略名称')
    backtest_parser.add_argument('--params', '-p', nargs='+', help='策略参数，如 short=5')
    backtest_parser.add_argument('--capital', type=float, default=100000, help='初始资金')
    backtest_parser.add_argument('--start', default='2020-01-01', help='开始日期')
    backtest_parser.add_argument('--end', help='结束日期')
    backtest_parser.add_argument('--output', '-o', help='输出文件')

    # compare 命令
    compare_parser = subparsers.add_parser('compare', help='策略对比')
    compare_parser.add_argument('--codes', required=True, help='股票代码，逗号分隔')
    compare_parser.add_argument('--strategies', required=True, help='策略名称，逗号分隔')
    compare_parser.add_argument('--capital', type=float, default=100000, help='初始资金')
    compare_parser.add_argument('--start', default='2020-01-01', help='开始日期')
    compare_parser.add_argument('--end', help='结束日期')
    compare_parser.add_argument('--output', '-o', help='输出文件')

    # optimize 命令
    optimize_parser = subparsers.add_parser('optimize', help='参数优化')
    optimize_parser.add_argument('--code', '-c', required=True, help='股票代码')
    optimize_parser.add_argument('--strategy', '-s', required=True, help='策略名称')
    optimize_parser.add_argument('--params', '-p', nargs='+', required=True, help='参数范围，如 short:5,10,15')
    optimize_parser.add_argument('--objective', default='sharpe', choices=['sharpe', 'return', 'drawdown'], help='优化目标')
    optimize_parser.add_argument('--method', default='grid', choices=['grid', 'bayesian'], help='优化方法')
    optimize_parser.add_argument('--start', default='2020-01-01', help='开始日期')
    optimize_parser.add_argument('--end', help='结束日期')
    optimize_parser.add_argument('--output', '-o', help='输出文件')

    # data 命令
    data_parser = subparsers.add_parser('data', help='获取数据')
    data_parser.add_argument('--code', '-c', required=True, help='股票代码')
    data_parser.add_argument('--start', default='2020-01-01', help='开始日期')
    data_parser.add_argument('--end', help='结束日期')
    data_parser.add_argument('--period', default='daily', help='周期')
    data_parser.add_argument('--output', '-o', help='输出文件')
    data_parser.add_argument('--preview', '-p', action='store_true', help='预览数据')

    args = parser.parse_args()

    if args.command == 'backtest':
        cmd_backtest(args)
    elif args.command == 'compare':
        cmd_compare(args)
    elif args.command == 'optimize':
        cmd_optimize(args)
    elif args.command == 'data':
        cmd_data(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
