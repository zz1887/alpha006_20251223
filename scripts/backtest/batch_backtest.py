#!/usr/bin/env python3
"""
批量回测执行脚本 - run_batch_backtest.py

功能:
- 执行多持仓天数的批量回测
- 测试范围: 5-45天（关键节点）
- 保存完整回测结果
- 生成执行日志

使用方法:
    python run_batch_backtest.py

目标区间: 20240101 - 20250831
测试天数: 5, 10, 15, 20, 25, 30, 35, 40, 45天
"""

import sys
sys.path.insert(0, '/home/zcy/alpha006_20251223')

import os
import pandas as pd
from datetime import datetime
from backtest.engine.backtest_hold_days_optimize import HoldDaysOptimizer
from core.constants.config import PATH_CONFIG

def print_header(title):
    """打印标题"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")

def run_batch_backtest():
    """执行批量回测"""
    print_header("ALPHA_PEG因子批量回测任务")

    # 配置参数
    start_date = '20240101'
    end_date = '20250831'

    # 测试范围：关键节点测试（更高效）
    hold_days_range = [5, 10, 15, 20, 25, 30, 35, 40, 45]

    # 因子参数
    outlier_sigma = 3.0
    normalization = None
    top_n = 3
    initial_capital = 1000000.0

    print(f"回测区间: {start_date} ~ {end_date}")
    print(f"测试持仓天数: {hold_days_range}")
    print(f"测试数量: {len(hold_days_range)}个")
    print(f"因子参数: outlier_sigma={outlier_sigma}, top_n={top_n}")
    print(f"初始资金: {initial_capital:,.0f}")

    # 创建优化器
    optimizer = HoldDaysOptimizer(start_date, end_date)

    # 执行优化
    start_time = datetime.now()
    print(f"\n开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        results = optimizer.run_full_optimization(
            hold_days_range=hold_days_range,
            outlier_sigma=outlier_sigma,
            normalization=normalization,
            top_n=top_n,
            initial_capital=initial_capital
        )

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        print_header("执行完成")
        print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")

        # 输出最优结果
        if results and 'comparison' in results:
            comparison = results['comparison']

            print("\n【最优持仓天数分析】")

            if 'best_by_sharpe' in comparison:
                best = comparison['best_by_sharpe']
                print(f"\n  夏普比率最优:")
                print(f"    持仓天数: {int(best['holding_days'])}天")
                print(f"    夏普比率: {best['sharpe_ratio']:.3f}")
                print(f"    累计收益: {best['total_return']:.2%}")
                print(f"    年化收益: {best['annual_return']:.2%}")
                print(f"    最大回撤: {best['max_drawdown']:.2%}")
                print(f"    换手率: {best['turnover']:.3f}")

            if 'best_by_composite' in comparison:
                best_comp = comparison['best_by_composite']
                print(f"\n  综合评分最优:")
                print(f"    持仓天数: {int(best_comp['holding_days'])}天")
                print(f"    综合评分: {best_comp['composite_score']:.3f}")
                print(f"    夏普比率: {best_comp['sharpe_ratio']:.3f}")

            # 显示完整对比表
            if 'comparison_table' in comparison:
                print(f"\n  完整对比表:")
                print(comparison['comparison_table'].to_string(index=False))

        return results

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def save_execution_log(results, start_date, end_date, hold_days_range):
    """保存执行日志"""
    if results is None:
        return

    log_dir = PATH_CONFIG['results_backtest']
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'batch_backtest_log_{start_date}_{end_date}_{timestamp}.txt')

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("ALPHA_PEG因子批量回测执行日志\n")
        f.write("="*80 + "\n\n")
        f.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"回测区间: {start_date} ~ {end_date}\n")
        f.write(f"测试天数: {hold_days_range}\n")
        f.write(f"测试数量: {len(hold_days_range)}个\n\n")

        if results and 'comparison' in results:
            comparison = results['comparison']

            if 'best_by_sharpe' in comparison:
                best = comparison['best_by_sharpe']
                f.write("最优持仓天数 (夏普优先):\n")
                f.write(f"  天数: {int(best['holding_days'])}天\n")
                f.write(f"  夏普比率: {best['sharpe_ratio']:.3f}\n")
                f.write(f"  累计收益: {best['total_return']:.2%}\n")
                f.write(f"  年化收益: {best['annual_return']:.2%}\n")
                f.write(f"  最大回撤: {best['max_drawdown']:.2%}\n")
                f.write(f"  换手率: {best['turnover']:.3f}\n\n")

            if 'comparison_table' in comparison:
                f.write("完整对比表:\n")
                f.write(comparison['comparison_table'].to_string(index=False))

    print(f"\n执行日志已保存: {log_file}")

def main():
    """主函数"""
    try:
        # 执行批量回测
        results = run_batch_backtest()

        # 保存日志
        if results:
            save_execution_log(
                results,
                '20240101',
                '20250831',
                [5, 10, 15, 20, 25, 30, 35, 40, 45]
            )

            print("\n" + "="*80)
            print("✅ 批量回测任务完成！")
            print("="*80)
            print("\n下一步：运行阶段4（结果筛选）")
            print("命令: python analyze_results.py")

        return results

    except Exception as e:
        print(f"\n❌ 批量回测任务失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    main()