#!/usr/bin/env python3
"""
回测执行脚本 - scripts/run_backtest.py

功能:
- 执行T+20策略回测
- 支持多策略预设
- 生成回测报告

使用方法:
    python scripts/run_backtest.py --period 2025Q1 --strategy t20_standard
"""

import sys
import os
sys.path.insert(0, '/home/zcy/alpha006_20251223')

import argparse
from datetime import datetime

from backtest.rules.industry_rank_rule import IndustryRankRule, create_strategy
from core.constants.config import BACKTEST_PERIODS, PATH_CONFIG


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='执行T+20策略回测')

    parser.add_argument('--period', type=str, default='2025Q1',
                       choices=['2024Q1', '2025Q1', '2025Q2', 'custom'],
                       help='回测时间区间')

    parser.add_argument('--start', type=str, default=None,
                       help='自定义开始日期 (YYYYMMDD)')

    parser.add_argument('--end', type=str, default=None,
                       help='自定义结束日期 (YYYYMMDD)')

    parser.add_argument('--strategy', type=str, default='t20_standard',
                       choices=['t20_standard', 't10_short', 't5_quick', 't30_long', 'conservative', 'aggressive'],
                       help='策略预设')

    parser.add_argument('--initial-capital', type=float, default=1000000.0,
                       help='初始资金')

    parser.add_argument('--industry-path', type=str, default=None,
                       help='行业数据路径')

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()

    print("="*80)
    print("alpha_peg策略回测脚本")
    print("="*80)

    # 1. 确定时间区间
    if args.period == 'custom':
        if not args.start or not args.end:
            print("❌ 自定义模式需要指定 --start 和 --end")
            return
        start_date = args.start
        end_date = args.end
        period_name = f"{start_date}_{end_date}"
        period_info = f"自定义区间: {start_date} ~ {end_date}"
    else:
        period_config = BACKTEST_PERIODS[args.period]
        start_date = period_config['start']
        end_date = period_config['end']
        period_name = args.period
        period_info = f"{period_config['name']} ({start_date} ~ {end_date})"

    print(f"\n时间区间: {period_info}")
    print(f"策略: {args.strategy}")
    print(f"初始资金: {args.initial_capital:,.0f}")

    # 2. 创建策略
    strategy = create_strategy(args.strategy)

    # 3. 运行回测
    print("\n开始回测...")
    start_time = datetime.now()

    results = strategy.run_backtest(
        start_date=start_date,
        end_date=end_date,
        industry_path=args.industry_path,
        initial_capital=args.initial_capital
    )

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    if not results:
        print("❌ 回测失败")
        return

    print(f"\n✅ 回测完成，耗时: {elapsed:.2f}秒")

    # 4. 输出总结
    summary = results['summary']
    print("\n" + "="*80)
    print("回测结果总结")
    print("="*80)
    print(f"最终价值: {summary['final_value']:,.0f}")
    print(f"总收益: {summary['total_return']:.4f} ({summary['total_return']*100:.2f}%)")
    print(f"年化收益: {summary['annual_return']:.4f} ({summary['annual_return']*100:.2f}%)")
    print(f"最大回撤: {summary['max_drawdown']:.4f} ({summary['max_drawdown']*100:.2f}%)")
    print(f"夏普比率: {summary['sharpe_ratio']:.4f}")
    print(f"胜率: {summary['win_rate']:.2%}")
    print(f"盈亏比: {summary['profit_loss_ratio']:.2f}")
    print(f"交易次数: {summary['total_trades']}")

    if 'excess_summary' in results:
        print("\n超额收益:")
        print(f"  超额收益: {results['excess_summary']['excess_return']:.2%}")
        print(f"  超额胜率: {results['excess_summary']['excess_win_rate']:.2%}")

    print("\n" + "="*80)
    print("脚本执行完成")
    print("="*80)
    print("\n结果文件已保存至:")
    print(f"  {PATH_CONFIG['results_backtest']}/")
    print("\n请查看对应时间戳的文件获取详细结果。")


if __name__ == '__main__':
    main()
