#!/usr/bin/env python3
"""
因子生成脚本 - scripts/run_factor_generation.py

功能:
- 生成alpha_peg因子
- 支持多版本因子计算
- 保存因子数据到results/factor/

使用方法:
    python scripts/run_factor_generation.py --period 2025Q1 --version industry_optimized
"""

import sys
import os
sys.path.insert(0, '/home/zcy/alpha006_20251223')

import argparse
from datetime import datetime
import pandas as pd

from factors.valuation.factor_alpha_peg import create_factor, ValGrowQFactor
from core.utils.data_loader import load_industry_data
from core.constants.config import BACKTEST_PERIODS, PATH_CONFIG


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='生成alpha_peg因子')

    parser.add_argument('--period', type=str, default='2025Q1',
                       choices=['2024Q1', '2025Q1', '2025Q2', 'custom'],
                       help='回测时间区间')

    parser.add_argument('--start', type=str, default=None,
                       help='自定义开始日期 (YYYYMMDD)')

    parser.add_argument('--end', type=str, default=None,
                       help='自定义结束日期 (YYYYMMDD)')

    parser.add_argument('--version', type=str, default='industry_optimized',
                       choices=['basic', 'industry_optimized', 'zscore', 'rank', 'conservative', 'aggressive'],
                       help='因子版本')

    parser.add_argument('--save', action='store_true', default=True,
                       help='保存因子数据')

    parser.add_argument('--output', type=str, default=None,
                       help='自定义输出文件名')

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()

    print("="*80)
    print("alpha_peg因子生成脚本")
    print("="*80)

    # 1. 确定时间区间
    if args.period == 'custom':
        if not args.start or not args.end:
            print("❌ 自定义模式需要指定 --start 和 --end")
            return
        start_date = args.start
        end_date = args.end
        period_name = f"{start_date}_{end_date}"
    else:
        period_config = BACKTEST_PERIODS[args.period]
        start_date = period_config['start']
        end_date = period_config['end']
        period_name = args.period
        print(f"时间区间: {period_config['name']} ({start_date} ~ {end_date})")

    # 2. 创建因子计算器
    print(f"\n因子版本: {args.version}")
    factor = create_factor(args.version)

    # 3. 计算因子
    print("\n开始计算因子...")
    start_time = datetime.now()

    factor_df = factor.calculate_by_period(start_date, end_date)

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    if len(factor_df) == 0:
        print("❌ 因子计算失败")
        return

    print(f"\n✅ 因子计算完成，耗时: {elapsed:.2f}秒")

    # 4. 统计信息
    stats = factor.get_factor_stats(factor_df)
    print("\n因子统计:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # 5. 保存因子数据
    if args.save:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if args.output:
            filename = args.output
        else:
            filename = f"factor_alpha_peg_{args.version}_{period_name}_{timestamp}.csv"

        output_path = os.path.join(PATH_CONFIG['results_factor'], filename)

        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        factor_df.to_csv(output_path, index=False)
        print(f"\n✓ 因子数据已保存: {output_path}")

        # 保存统计信息
        stats_file = filename.replace('.csv', '_stats.txt')
        stats_path = os.path.join(PATH_CONFIG['results_factor'], stats_file)
        with open(stats_path, 'w', encoding='utf-8') as f:
            f.write(f"alpha_peg因子统计 - {args.version}\n")
            f.write(f"时间区间: {start_date} ~ {end_date}\n")
            f.write(f"计算时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("统计信息:\n")
            for key, value in stats.items():
                if isinstance(value, float):
                    f.write(f"  {key}: {value:.6f}\n")
                else:
                    f.write(f"  {key}: {value}\n")
        print(f"✓ 统计信息已保存: {stats_path}")

    print("\n" + "="*80)
    print("脚本执行完成")
    print("="*80)


if __name__ == '__main__':
    main()
