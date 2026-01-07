#!/usr/bin/env python3
"""
策略3运行脚本 - run_strategy3.py

功能:
- 运行策略3多因子综合得分策略
- 支持多版本配置
- 输出Excel和统计报告

使用方法:
    python strategies/runners/run_strategy3.py --start 20240601 --end 20251130
    python strategies/runners/run_strategy3.py --start 20240601 --end 20251130 --version standard
"""

import sys
import os
import argparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/zcy/alpha006_20251223')

from strategies.executors.MFM_5F_executor import execute


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='策略3运行脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # 标准回测
  python run_strategy3.py --start 20240601 --end 20251130

  # 保守版本
  python run_strategy3.py --start 20240601 --end 20251130 --version conservative

  # 激进版本
  python run_strategy3.py --start 20240601 --end 20251130 --version aggressive
        '''
    )

    parser.add_argument('--start', '-s', type=str, required=True, help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', '-e', type=str, required=True, help='结束日期 (YYYYMMDD)')
    parser.add_argument('--version', '-v', type=str, default='standard', help='策略版本 (standard/conservative/aggressive)')

    args = parser.parse_args()

    # 版本验证
    valid_versions = ['standard', 'conservative', 'aggressive']
    if args.version not in valid_versions:
        print(f"❌ 无效版本: {args.version}")
        print(f"可选版本: {valid_versions}")
        sys.exit(1)

    print("\n" + "="*80)
    print("策略3 - 多因子综合得分策略")
    print("="*80)
    print(f"时间区间: {args.start} ~ {args.end}")
    print(f"策略版本: {args.version}")
    print("="*80 + "\n")

    # 执行策略
    success = execute(args.start, args.end, args.version)

    if success:
        print("\n✅ 策略执行完成!")
    else:
        print("\n❌ 策略执行失败!")

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()