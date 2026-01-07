#!/usr/bin/env python3
"""
Robust optimization script with proper error handling and progress tracking
"""

import sys
sys.path.insert(0, '/home/zcy/alpha006_20251223')

import argparse
from datetime import datetime
import os
import traceback
import pandas as pd

from backtest.engine.backtest_hold_days_optimize import HoldDaysOptimizer


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='alpha_peg因子持仓天数优化回测')

    parser.add_argument('--start', type=str, default='20240101',
                       help='回测开始日期 (YYYYMMDD)')

    parser.add_argument('--end', type=str, default='20250901',
                       help='回测结束日期 (YYYYMMDD)')

    parser.add_argument('--days', type=str, default='10,60',
                       help='持仓天数范围，格式: 起始,结束 (默认: 10,60)')

    parser.add_argument('--step', type=int, default=1,
                       help='持仓天数步长 (默认: 1)')

    parser.add_argument('--top-n', type=int, default=3,
                       help='每行业选股数量 (默认: 3)')

    parser.add_argument('--outlier-sigma', type=float, default=3.0,
                       help='异常值阈值 (默认: 3.0)')

    parser.add_argument('--initial-capital', type=float, default=1000000.0,
                       help='初始资金 (默认: 1,000,000)')

    parser.add_argument('--log-dir', type=str, default='/home/zcy/alpha006_20251223/results/backtest',
                       help='日志输出目录')

    return parser.parse_args()


def setup_logging(log_dir, start_date, end_date):
    """设置日志文件"""
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'{log_dir}/optimization_{start_date}_{end_date}_{timestamp}.log'

    # Create a custom print function that writes to both console and file
    def log_print(*args, **kwargs):
        print(*args, **kwargs)
        with open(log_file, 'a', encoding='utf-8') as f:
            print(*args, **kwargs, file=f)

    return log_print, log_file


def main():
    """主函数"""
    args = parse_arguments()

    # Setup logging
    log_print, log_file = setup_logging(args.log_dir, args.start, args.end)

    log_print("="*100)
    log_print("ALPHA_PEG因子持仓天数优化回测 (ROBUST VERSION)")
    log_print("="*100)
    log_print(f"回测区间: {args.start} ~ {args.end}")
    log_print(f"持仓天数范围: {args.days}")
    log_print(f"步长: {args.step}")
    log_print(f"每行业选股: {args.top_n}")
    log_print(f"异常值阈值: {args.outlier_sigma}")
    log_print(f"初始资金: {args.initial_capital:,.0f}")
    log_print(f"日志文件: {log_file}")
    log_print("="*100)

    # 解析持仓天数范围
    days_range = args.days.split(',')
    start_day = int(days_range[0])
    end_day = int(days_range[1])
    hold_days_range = list(range(start_day, end_day + 1, args.step))

    log_print(f"\n测试持仓天数: {hold_days_range}")
    log_print(f"共 {len(hold_days_range)} 个测试")

    # 创建优化器
    optimizer = HoldDaysOptimizer(args.start, args.end)

    # 运行优化
    start_time = datetime.now()

    try:
        # 准备数据（这是最耗时的部分）
        log_print("\n【阶段1】数据准备")
        from backtest.engine.vbt_data_preparation import VBTDataPreparation

        preparer = VBTDataPreparation(args.start, args.end)
        data = preparer.prepare_all(
            outlier_sigma=args.outlier_sigma,
            normalization=None,
            top_n=args.top_n
        )

        log_print(f"✓ 数据准备完成: {len(data['signal_matrix'])}个交易日, {len(data['signal_matrix'].columns)}只股票")

        # 初始化引擎
        log_print("\n【阶段2】初始化回测引擎")
        from backtest.engine.vbt_backtest_engine import VBTBacktestEngine

        engine = VBTBacktestEngine(
            price_df=data['price_df'],
            signal_matrix=data['signal_matrix']
        )
        log_print("✓ 引擎初始化完成")

        # 运行多天数回测（逐个运行以便跟踪进度）
        log_print("\n【阶段3】运行多持仓天数回测")
        results = []

        for i, hold_days in enumerate(hold_days_range, 1):
            log_print(f"\n--- 测试 {i}/{len(hold_days_range)}: {hold_days}天 ---")

            try:
                result = engine.run_backtest(hold_days, args.initial_capital)

                if result and 'summary' in result:
                    results.append(result['summary'])
                    log_print(f"✓ 成功: 最终价值 {result['summary']['final_value']:.0f}, "
                             f"年化收益 {result['summary']['annual_return']:.2%}")
                else:
                    log_print(f"⚠️ 跳过: 无有效结果")

            except Exception as e:
                log_print(f"❌ 失败: {e}")
                traceback.print_exc()
                continue

        # 转换为DataFrame
        results_df = pd.DataFrame(results)
        log_print(f"\n✓ 完成所有测试，共收集 {len(results_df)} 个有效结果")

        if len(results_df) == 0:
            log_print("❌ 无有效结果，退出")
            return None

        # 对比分析
        log_print("\n【阶段4】对比分析")
        from backtest.engine.vbt_backtest_engine import compare_hold_days_results

        comparison = compare_hold_days_results(results_df)

        if not comparison:
            log_print("❌ 对比分析失败")
            return None

        # 保存结果
        log_print("\n【阶段5】保存结果")

        # 保存详细结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        detailed_file = f'{args.log_dir}/hold_days_detailed_{args.start}_{args.end}_{timestamp}.csv'
        results_df.to_csv(detailed_file, index=False, encoding='utf-8-sig')
        log_print(f"✓ 详细结果: {detailed_file}")

        # 保存对比表
        comparison_table = comparison['comparison_table']
        comparison_file = f'{args.log_dir}/hold_days_comparison_{args.start}_{args.end}_{timestamp}.csv'
        comparison_table.to_csv(comparison_file, index=False, encoding='utf-8-sig')
        log_print(f"✓ 对比表: {comparison_file}")

        # 生成报告
        report_file = f'{args.log_dir}/hold_days_optimize_report_{args.start}_{args.end}_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("ALPHA_PEG因子持仓天数优化分析报告\n")
            f.write("="*80 + "\n\n")
            f.write(f"回测区间: {args.start} ~ {args.end}\n")
            f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            best = comparison['best_by_sharpe']
            f.write("最优持仓天数分析:\n")
            f.write(f"  最优天数: {int(best['holding_days'])}天\n")
            f.write(f"  夏普比率: {best['sharpe_ratio']:.3f}\n")
            f.write(f"  累计收益: {best['total_return']:.2%}\n")
            f.write(f"  年化收益: {best['annual_return']:.2%}\n")
            f.write(f"  最大回撤: {best['max_drawdown']:.2%}\n")
            f.write(f"  换手率: {best['turnover']:.3f}\n")
            f.write(f"  交易次数: {best['total_trades']}\n\n")

            f.write("综合评分排名:\n")
            top_5 = results_df.nlargest(5, 'composite_score')
            for idx, row in top_5.iterrows():
                f.write(f"  {int(row['holding_days'])}天: 评分={row['composite_score']:.3f}, "
                       f"夏普={row['sharpe_ratio']:.3f}, 收益={row['total_return']:.2%}\n")

        log_print(f"✓ 分析报告: {report_file}")

        # 输出最优结果摘要
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        log_print("\n" + "="*100)
        log_print(f"✅ 优化完成！总耗时: {elapsed:.1f}秒")
        log_print("="*100)

        best = comparison['best_by_sharpe']
        log_print(f"\n【最优持仓天数】")
        log_print(f"  天数: {int(best['holding_days'])}天")
        log_print(f"  夏普比率: {best['sharpe_ratio']:.3f}")
        log_print(f"  累计收益: {best['total_return']:.2%}")
        log_print(f"  年化收益: {best['annual_return']:.2%}")
        log_print(f"  最大回撤: {best['max_drawdown']:.2%}")
        log_print(f"  换手率: {best['turnover']:.3f}")
        log_print(f"  交易次数: {best['total_trades']}")

        log_print(f"\n【结果文件】")
        log_print(f"  详细结果: {detailed_file}")
        log_print(f"  对比表: {comparison_file}")
        log_print(f"  分析报告: {report_file}")
        log_print(f"  日志文件: {log_file}")

        return {
            'results_df': results_df,
            'comparison': comparison,
            'log_file': log_file
        }

    except Exception as e:
        log_print(f"\n❌ 执行失败: {e}")
        traceback.print_exc()
        return None


if __name__ == '__main__':
    main()