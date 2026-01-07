#!/usr/bin/env python3
"""
策略统一调用脚本 - run_strategy.py

功能:
- 统一的策略调用接口
- 支持多策略切换
- 自动加载策略配置
- 结果自动保存和管理

使用方法:
    python strategies/runners/run_strategy.py --strategy six_factor_monthly --start 20240601 --end 20251130
    python strategies/runners/run_strategy.py -s strategy3 -s 20240601 -e 20251130
    python strategies/runners/run_strategy.py --list
    python strategies/runners/run_strategy.py --info six_factor_monthly
"""

import sys
import os
import argparse
import importlib
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, '/home/zcy/alpha006_20251223')

# 导入基础模块
from strategies.base.strategy_runner import StrategyRunner

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='策略统一调用脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # 运行六因子策略
  python run_strategy.py --strategy six_factor_monthly --start 20240601 --end 20251130

  # 列出所有策略
  python run_strategy.py --list

  # 查看策略详情
  python run_strategy.py --info six_factor_monthly

  # 指定版本
  python run_strategy.py --strategy six_factor_monthly --start 20240601 --end 20251130 --version standard

  # 运行策略3
  python run_strategy.py --strategy strategy3 --start 20240601 --end 20251130 --version standard
        '''
    )

    # 基本参数
    parser.add_argument('-s', '--strategy', type=str, help='策略名称')
    parser.add_argument('--start', type=str, help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', type=str, help='结束日期 (YYYYMMDD)')
    parser.add_argument('--version', type=str, default='standard', help='策略版本')

    # 功能选项
    parser.add_argument('--list', action='store_true', help='列出所有可用策略')
    parser.add_argument('--info', type=str, help='查看策略详情')

    # 简化参数
    parser.add_argument('-S', '--start-date', dest='start', help='开始日期 (简写)')
    parser.add_argument('-E', '--end-date', dest='end', help='结束日期 (简写)')

    args = parser.parse_args()

    # 功能模式
    if args.list:
        list_strategies()
        return

    if args.info:
        show_strategy_info(args.info)
        return

    # 运行模式
    if not args.strategy:
        print("❌ 请指定策略名称")
        print("使用 --list 查看可用策略")
        print("使用 --info <策略名> 查看策略详情")
        return

    if not args.start or not args.end:
        print("❌ 请指定开始和结束日期")
        print("示例: --start 20240601 --end 20251130")
        return

    # 执行策略
    success = StrategyRunner.run_strategy(
        strategy_name=args.strategy,
        start_date=args.start,
        end_date=args.end,
        version=args.version
    )

    sys.exit(0 if success else 1)


def list_strategies():
    """列出所有可用策略"""
    strategies = StrategyRunner.list_strategies()

    print("\n" + "="*80)
    print("可用策略列表")
    print("="*80)

    for name, description in strategies.items():
        print(f"\n策略名称: {name}")
        print(f"  描述: {description}")

    print("\n" + "="*80)
    print("\n使用方法:")
    print("  python run_strategy.py --strategy <策略名> --start <开始日期> --end <结束日期>")
    print("  python run_strategy.py --info <策略名>  # 查看详情")
    print("="*80)


def show_strategy_info(strategy_name: str):
    """显示策略详细信息"""
    strategy_info = StrategyRunner.get_strategy_info(strategy_name)
    if not strategy_info:
        print(f"❌ 未知策略: {strategy_name}")
        return

    config = StrategyRunner.load_config(strategy_name)
    if not config:
        print(f"❌ 无法加载策略配置: {strategy_name}")
        return

    print("\n" + "="*80)
    print(f"策略详情: {strategy_name}")
    print("="*80)

    # 显示策略信息
    if 'info' in config:
        print("\n策略信息:")
        for key, value in config['info'].items():
            print(f"  {key}: {value}")

    # 显示因子配置
    if 'factors' in config and 'factors' in config['factors']:
        print("\n因子配置:")
        for factor_name, factor_info in config['factors']['factors'].items():
            print(f"  {factor_name}:")
            print(f"    名称: {factor_info['name']}")
            print(f"    权重: {factor_info['weight']}")
            print(f"    方向: {factor_info['direction']}")

    # 显示调仓配置
    if 'rebalance' in config:
        print("\n调仓配置:")
        print(f"  频率: {config['rebalance']['frequency']}")
        if 'monthly_logic' in config['rebalance']:
            print(f"  逻辑: {config['rebalance']['monthly_logic']['description']}")

    # 显示交易成本
    if 'trading_cost' in config:
        print("\n交易成本:")
        for key, value in config['trading_cost'].items():
            print(f"  {key}: {value}")

    print("\n" + "="*80)
    print("\n调用方式:")
    print(f"  python run_strategy.py --strategy {strategy_name} --start 20240601 --end 20251130")
    print("="*80)


if __name__ == '__main__':
    main()