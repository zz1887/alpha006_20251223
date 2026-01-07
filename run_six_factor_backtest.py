#!/usr/bin/env python3
"""
六因子策略回测 - 2025年1月1日到6月30日

调用方式:
    python run_six_factor_backtest.py

每月最后一个交易日调仓
"""

import sys
sys.path.insert(0, '/home/zcy/alpha006_20251223')

from scripts.backtest.six_factor import SixFactorBacktestOptimized, run_optimized_backtest
import pandas as pd
import numpy as np
from datetime import datetime
import os

def run_backtest_2025_h1():
    """运行2025年上半年回测"""

    # 用户指定的日期范围
    start_date = '20250101'
    end_date = '20250630'  # 修正为有效日期

    print("="*80)
    print("六因子策略回测 - 2025年上半年")
    print("="*80)
    print(f"回测周期: {start_date} ~ {end_date}")
    print("调仓规则: 每月最后一个交易日调仓")
    print("策略版本: 优化版 (optimized_v2)")
    print()

    # 检查日期有效性
    try:
        from datetime import datetime
        datetime.strptime(start_date, '%Y%m%d')
        datetime.strptime(end_date, '%Y%m%d')
        print("✅ 日期格式有效")
    except:
        print("❌ 日期格式无效")
        return False

    # 运行回测
    try:
        backtest = SixFactorBacktestOptimized(start_date, end_date, 'optimized_v2')
        results = backtest.run_backtest()

        if len(results) > 0:
            # 计算性能指标
            metrics = backtest.calculate_performance_metrics(results)

            # 保存结果
            output_dir = f"/home/zcy/alpha006_20251223/results/backtest/six_factor_{start_date}_{end_date}_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(output_dir, exist_ok=True)

            # 保存详细数据
            if results['dates']:
                # Pad IC values
                ic_values = results['ic_values'] if results['ic_values'] else []
                if len(ic_values) < len(results['dates']):
                    ic_values = ic_values + [np.nan] * (len(results['dates']) - len(ic_values))

                # Calculate average turnover per period
                turnover_rates = results['turnover_rates'] if results['turnover_rates'] else []
                avg_turnover = []
                if turnover_rates:
                    num_periods = len(results['dates'])
                    for i in range(num_periods):
                        start_idx = i * 5
                        end_idx = start_idx + 5
                        if end_idx <= len(turnover_rates):
                            period_turnover = turnover_rates[start_idx:end_idx]
                            avg_turnover.append(sum(period_turnover) / len(period_turnover))
                        else:
                            avg_turnover.append(0)
                else:
                    avg_turnover = [0] * len(results['dates'])

                detail_data = {
                    'Date': results['dates'],
                    'Benchmark': results['benchmark_returns'],
                    'IC_Value': ic_values,
                    'Turnover': avg_turnover,
                }
                for g in range(1, 6):
                    detail_data[f'Group_{g}'] = results['group_returns'][g]

                if results['group_returns'][1] and results['group_returns'][5]:
                    detail_data['Long_Short'] = [g1 - g5 for g1, g5 in zip(results['group_returns'][1], results['group_returns'][5])]
                else:
                    detail_data['Long_Short'] = [0] * len(results['dates'])

                df_detail = pd.DataFrame(detail_data)
                df_detail.to_excel(f"{output_dir}/backtest_data.xlsx", index=False)

                if len(metrics) > 0:
                    metrics.to_excel(f"{output_dir}/performance_metrics.xlsx", index=False)

            print(f"\n✅ 回测完成!")
            print(f"结果已保存至: {output_dir}")
            print(f"\n关键结果:")
            print(f"- 回测周期: {len(results['dates'])}期")
            print(f"- 基准表现: {results['benchmark_returns']}")
            print(f"- 组1表现: {results['group_returns'][1]}")
            print(f"- 组5表现: {results['group_returns'][5]}")

            if 'Long_Short' in detail_data:
                ls_returns = detail_data['Long_Short']
                if len(ls_returns) > 0:
                    avg_ls = np.mean([r for r in ls_returns if not pd.isna(r)])
                    print(f"- 多空平均: {avg_ls:.4f}")

            return True
        else:
            print("❌ 回测失败")
            return False

    except Exception as e:
        print(f"❌ 回测异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_backtest_2025_h1()
    sys.exit(0 if success else 1)