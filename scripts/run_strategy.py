#!/usr/bin/env python3
"""
文件input(依赖外部什么): config.strategies.*, scripts.run_six_factor_backtest
文件output(提供什么): 统一策略调用接口, 自动配置加载
文件pos(系统局部地位): 策略执行层的统一入口, 连接配置和执行器

策略统一调用脚本 - Strategy Runner

功能:
- 统一的策略调用接口
- 支持多策略切换
- 自动加载策略配置
- 结果自动保存和管理

使用方法:
    python scripts/run_strategy.py --strategy six_factor_monthly --start 20240601 --end 20251130
    python scripts/run_strategy.py -s six_factor_monthly -s 20240601 -e 20251130
    python scripts/run_strategy.py --strategy six_factor_monthly --start 20240601 --end 20251130 --version standard
"""

import sys
import os
import argparse
import importlib
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, '/home/zcy/alpha006_20251223')

# 策略映射表
STRATEGY_MAP = {
    'six_factor_monthly': {
        'module': 'config.strategies.six_factor_monthly',
        'class': None,  # 使用函数式调用
        'runner': 'scripts.run_six_factor_backtest',
        'description': '六因子月末智能调仓策略',
    },
    'six_factor': {
        'module': 'config.strategies.six_factor_monthly',
        'class': None,
        'runner': 'scripts.run_six_factor_backtest',
        'description': '六因子策略(别名)',
    },
    'strategy3': {
        'module': 'config.backtest_config',
        'class': None,
        'runner': 'scripts.run_strategy3',
        'description': '多因子综合得分策略',
    },
}

def load_strategy_config(strategy_name: str) -> Optional[Dict[str, Any]]:
    """
    加载策略配置

    Args:
        strategy_name: 策略名称

    Returns:
        策略配置字典
    """
    if strategy_name not in STRATEGY_MAP:
        print(f"❌ 未知策略: {strategy_name}")
        print(f"可用策略: {list(STRATEGY_MAP.keys())}")
        return None

    strategy_info = STRATEGY_MAP[strategy_name]

    try:
        # 动态导入策略配置模块
        module = importlib.import_module(strategy_info['module'])

        # 尝试获取配置
        if hasattr(module, 'get_strategy_config'):
            return module.get_strategy_config()
        elif hasattr(module, 'get_strategy_params'):
            return {'params': module.get_strategy_params()}
        else:
            # 直接返回模块中的配置
            return {name: getattr(module, name) for name in dir(module) if name.isupper()}

    except Exception as e:
        print(f"❌ 加载策略配置失败: {e}")
        return None

def run_strategy(strategy_name: str, start_date: str, end_date: str, version: str = 'standard', **kwargs) -> bool:
    """
    运行策略

    Args:
        strategy_name: 策略名称
        start_date: 开始日期
        end_date: 结束日期
        version: 策略版本
        **kwargs: 其他参数

    Returns:
        是否成功
    """
    if strategy_name not in STRATEGY_MAP:
        print(f"❌ 未知策略: {strategy_name}")
        return False

    strategy_info = STRATEGY_MAP[strategy_name]
    runner_module = strategy_info['runner']

    print("\n" + "="*80)
    print(f"策略执行: {strategy_info['description']}")
    print("="*80)
    print(f"策略名称: {strategy_name}")
    print(f"时间区间: {start_date} - {end_date}")
    print(f"策略版本: {version}")
    print("="*80 + "\n")

    try:
        # 根据策略类型选择执行器
        if runner_module == 'scripts.run_six_factor_backtest':
            # 六因子策略
            from scripts.run_six_factor_backtest import SixFactorBacktest

            backtest = SixFactorBacktest(start_date, end_date, version)
            results = backtest.run_backtest()

            if len(results['dates']) == 0:
                print("❌ 回测失败: 无有效数据")
                return False

            # 生成输出目录
            output_dir = f"/home/zcy/alpha006_20251223/results/backtest/six_factor_{start_date}_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(output_dir, exist_ok=True)

            # 保存结果
            backtest.save_results(results, output_dir)
            backtest.generate_visualizations(results, output_dir)

            print("\n" + "="*80)
            print("✅ 回测完成!")
            print(f"结果保存至: {output_dir}")
            print("="*80)

            return True

        elif runner_module == 'scripts.run_strategy3':
            # 策略3
            from scripts.run_strategy3 import run_strategy3_backtest

            result = run_strategy3_backtest(start_date, end_date)

            if result:
                print("\n" + "="*80)
                print("✅ 回测完成!")
                print("="*80)
                return True
            else:
                print("\n❌ 回测失败")
                return False

        else:
            print(f"❌ 未知的执行器: {runner_module}")
            return False

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def list_strategies():
    """列出所有可用策略"""
    print("\n" + "="*80)
    print("可用策略列表")
    print("="*80)

    for name, info in STRATEGY_MAP.items():
        print(f"\n策略名称: {name}")
        print(f"  描述: {info['description']}")
        print(f"  模块: {info['module']}")
        print(f"  执行器: {info['runner']}")

    print("\n" + "="*80)

def show_strategy_info(strategy_name: str):
    """显示策略详细信息"""
    if strategy_name not in STRATEGY_MAP:
        print(f"❌ 未知策略: {strategy_name}")
        return

    config = load_strategy_config(strategy_name)
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
    success = run_strategy(
        strategy_name=args.strategy,
        start_date=args.start,
        end_date=args.end,
        version=args.version
    )

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
