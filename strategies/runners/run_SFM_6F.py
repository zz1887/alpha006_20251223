#!/usr/bin/env python3
"""
六因子策略运行脚本 - run_six_factor.py

功能:
- 专门运行六因子策略
- 支持多版本切换
- 自动配置加载
- 结果可视化

使用方法:
    python strategies/runners/run_six_factor.py --start 20240601 --end 20251130
    python strategies/runners/run_six_factor.py --start 20240601 --end 20251130 --version standard
"""

import sys
import os
import argparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/zcy/alpha006_20251223')

from strategies.executors.SFM_6F_executor import execute


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='六因子策略运行脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # 标准回测
  python run_six_factor.py --start 20240601 --end 20251130

  # 指定版本
  python run_six_factor.py --start 20240601 --end 20251130 --version standard

  # 简化参数
  python run_six_factor.py -s 20240601 -e 20251130
        '''
    )

    parser.add_argument('--start', '-s', type=str, required=True, help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', '-e', type=str, required=True, help='结束日期 (YYYYMMDD)')
    parser.add_argument('--version', '-v', type=str, default='standard', help='策略版本')

    args = parser.parse_args()

    print("\n" + "="*80)
    print("六因子策略 - 智能调仓回测系统")
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