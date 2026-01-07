#!/usr/bin/env python3
"""
持仓天数优化执行脚本 - scripts/run_hold_days_optimize.py

功能:
- 执行vectorbt多持仓天数回测
- 筛选最优持仓天数
- 生成对比报告和可视化

使用方法:
    python scripts/run_hold_days_optimize.py --start 20240801 --end 20250930 --days 10,45
"""

import sys
import os
sys.path.insert(0, '/home/zcy/alpha006_20251223')

import argparse
from datetime import datetime

from backtest.engine.backtest_hold_days_optimize import HoldDaysOptimizer


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='alpha_peg因子持仓天数优化回测')

    parser.add_argument('--start', type=str, default='20240801',
                       help='回测开始日期 (YYYYMMDD)')

    parser.add_argument('--end', type=str, default='20250930',
                       help='回测结束日期 (YYYYMMDD)')

    parser.add_argument('--days', type=str, default='10,45',
                       help='持仓天数范围，格式: 起始,结束 (默认: 10,45)')

    parser.add_argument('--step', type=int, default=1,
                       help='持仓天数步长 (默认: 1)')

    parser.add_argument('--top-n', type=int, default=3,
                       help='每行业选股数量 (默认: 3)')

    parser.add_argument('--outlier-sigma', type=float, default=3.0,
                       help='异常值阈值 (默认: 3.0)')

    parser.add_argument('--initial-capital', type=float, default=1000000.0,
                       help='初始资金 (默认: 1,000,000)')

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()

    print("="*100)
    print("ALPHA_PEG因子持仓天数优化回测")
    print("="*100)
    print(f"回测区间: {args.start} ~ {args.end}")
    print(f"持仓天数范围: {args.days}")
    print(f"步长: {args.step}")
    print(f"每行业选股: {args.top_n}")
    print(f"异常值阈值: {args.outlier_sigma}")
    print(f"初始资金: {args.initial_capital:,.0f}")
    print("="*100)

    # 解析持仓天数范围
    days_range = args.days.split(',')
    start_day = int(days_range[0])
    end_day = int(days_range[1])
    hold_days_range = list(range(start_day, end_day + 1, args.step))

    print(f"\n测试持仓天数: {hold_days_range}")
    print(f"共 {len(hold_days_range)} 个测试")

    # 创建优化器
    optimizer = HoldDaysOptimizer(args.start, args.end)

    # 运行优化
    start_time = datetime.now()

    try:
        results = optimizer.run_full_optimization(
            hold_days_range=hold_days_range,
            outlier_sigma=args.outlier_sigma,
            normalization=None,
            top_n=args.top_n,
            initial_capital=args.initial_capital
        )

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        print("\n" + "="*100)
        print(f"✅ 优化完成！总耗时: {elapsed:.1f}秒")
        print("="*100)

        # 输出最优结果摘要
        if results and 'comparison' in results:
            best = results['comparison']['best_by_sharpe']
            print(f"\n【最优持仓天数】")
            print(f"  天数: {int(best['holding_days'])}天")
            print(f"  夏普比率: {best['sharpe_ratio']:.3f}")
            print(f"  累计收益: {best['total_return']:.2%}")
            print(f"  年化收益: {best['annual_return']:.2%}")
            print(f"  最大回撤: {best['max_drawdown']:.2%}")
            print(f"  换手率: {best['turnover']:.3f}")
            print(f"  交易次数: {best['total_trades']}")

            print(f"\n【结果文件】")
            print(f"  请查看 results/backtest/ 目录下的文件")
            print(f"  请查看 results/visual/ 目录下的图表")

        return results

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    main()
