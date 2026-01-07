"""
持仓天数优化回测主模块 - backtest/engine/backtest_hold_days_optimize.py

功能:
- 整合vectorbt多天数回测
- 最优天数筛选
- 结果可视化
- 稳定性验证
- 行业拆解分析

使用方法:
    python backtest/engine/backtest_hold_days_optimize.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

from backtest.engine.vbt_data_preparation import VBTDataPreparation
from backtest.engine.vbt_backtest_engine import VBTBacktestEngine, compare_hold_days_results
from core.constants.config import PATH_CONFIG


class HoldDaysOptimizer:
    """持仓天数优化器"""

    def __init__(self, start_date: str, end_date: str):
        """
        初始化优化器

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        """
        self.start_date = start_date
        self.end_date = end_date
        self.data = None
        self.engine = None
        self.results = None
        self.comparison = None

    def run_full_optimization(self,
                              hold_days_range: List[int],
                              outlier_sigma: float = 3.0,
                              normalization: Optional[str] = None,
                              top_n: int = 3,
                              initial_capital: float = 1000000.0) -> Dict[str, Any]:
        """
        运行完整的持仓天数优化流程

        Args:
            hold_days_range: 持有天数范围列表
            outlier_sigma: 异常值阈值
            normalization: 标准化方法
            top_n: 每行业选股数量
            initial_capital: 初始资金

        Returns:
            优化结果字典
        """
        print(f"\n{'='*100}")
        print("ALPHA_PEG因子持仓天数优化分析")
        print(f"回测区间: {self.start_date} ~ {self.end_date}")
        print(f"测试持仓天数: {min(hold_days_range)}-{max(hold_days_range)}天 (共{len(hold_days_range)}个)")
        print(f"{'='*100}")

        # 1. 准备数据
        print("\n【阶段1】数据准备")
        preparer = VBTDataPreparation(self.start_date, self.end_date)
        self.data = preparer.prepare_all(
            outlier_sigma=outlier_sigma,
            normalization=normalization,
            top_n=top_n
        )

        # 2. 初始化回测引擎
        print("\n【阶段2】初始化回测引擎")
        self.engine = VBTBacktestEngine(
            price_df=self.data['price_df'],
            signal_matrix=self.data['signal_matrix']
        )

        # 3. 运行多天数回测
        print("\n【阶段3】运行多持仓天数回测")
        results_df = self.engine.run_multiple_hold_days(
            hold_days_range=hold_days_range,
            initial_capital=initial_capital
        )

        # 4. 对比分析
        print("\n【阶段4】对比分析与最优天数筛选")
        self.comparison = compare_hold_days_results(results_df)
        self.results = results_df

        # 5. 生成可视化
        print("\n【阶段5】生成可视化图表")
        self.generate_visualizations()

        # 6. 行业维度分析
        print("\n【阶段6】行业维度拆解分析")
        industry_analysis = None
        if self.comparison and len(self.comparison) > 0:
            try:
                industry_analysis = self.analyze_by_industry()
            except Exception as e:
                print(f"⚠️ 行业分析失败: {e}")

        # 7. 稳定性验证
        print("\n【阶段7】稳定性验证")
        stability_results = None
        if self.comparison and len(self.comparison) > 0:
            try:
                stability_results = self.validate_stability()
            except Exception as e:
                print(f"⚠️ 稳定性验证失败: {e}")

        # 8. 保存结果
        print("\n【阶段8】保存结果")
        if len(results_df) > 0:
            try:
                self.save_results()
            except Exception as e:
                print(f"⚠️ 保存结果失败: {e}")

        return {
            'results_df': results_df,
            'comparison': self.comparison,
            'industry_analysis': industry_analysis,
            'stability_results': stability_results,
            'data': self.data
        }

    def generate_visualizations(self):
        """生成可视化图表"""
        if self.results is None or self.comparison is None:
            print("⚠️ 跳过可视化: 无结果数据")
            return

        output_dir = PATH_CONFIG['results_visual']
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 检查数据是否足够
        if len(self.results) < 2:
            print("⚠️ 跳过可视化: 数据点不足")
            return

        # 1. 持仓天数 vs 夏普比率
        plt.figure(figsize=(12, 6))
        plt.subplot(2, 2, 1)
        plt.plot(self.results['holding_days'], self.results['sharpe_ratio'],
                marker='o', linewidth=2, markersize=6)
        if 'best_by_sharpe' in self.comparison:
            plt.axvline(self.comparison['best_by_sharpe']['holding_days'],
                       color='red', linestyle='--', alpha=0.7, label='最优')
        plt.xlabel('持仓天数')
        plt.ylabel('夏普比率')
        plt.title('持仓天数 vs 夏普比率')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # 2. 持仓天数 vs 累计收益
        plt.subplot(2, 2, 2)
        plt.plot(self.results['holding_days'], self.results['total_return'] * 100,
                marker='s', linewidth=2, markersize=6, color='green')
        plt.axvline(self.comparison['best_by_return']['holding_days'],
                   color='red', linestyle='--', alpha=0.7, label='最优')
        plt.xlabel('持仓天数')
        plt.ylabel('累计收益 (%)')
        plt.title('持仓天数 vs 累计收益')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # 3. 持仓天数 vs 最大回撤
        plt.subplot(2, 2, 3)
        plt.plot(self.results['holding_days'], self.results['max_drawdown'] * 100,
                marker='^', linewidth=2, markersize=6, color='orange')
        plt.axvline(self.comparison['best_by_drawdown']['holding_days'],
                   color='red', linestyle='--', alpha=0.7, label='最优')
        plt.xlabel('持仓天数')
        plt.ylabel('最大回撤 (%)')
        plt.title('持仓天数 vs 最大回撤')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # 4. 持仓天数 vs 换手率
        plt.subplot(2, 2, 4)
        plt.plot(self.results['holding_days'], self.results['turnover'],
                marker='v', linewidth=2, markersize=6, color='purple')
        plt.axvline(self.comparison['best_by_turnover']['holding_days'],
                   color='red', linestyle='--', alpha=0.7, label='最优')
        plt.xlabel('持仓天数')
        plt.ylabel('换手率')
        plt.title('持仓天数 vs 换手率')
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{output_dir}/hold_days_metrics_{timestamp}.png', dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ 指标趋势图: {output_dir}/hold_days_metrics_{timestamp}.png")

        # 5. 最优天数 vs 1天持仓收益曲线对比
        best_days = int(self.comparison['best_by_sharpe']['holding_days'])

        # 运行1天持仓作为基准
        engine_1day = VBTBacktestEngine(self.data['price_df'], self.data['signal_matrix'])
        result_1day = engine_1day.run_backtest(1, 1000000.0)

        # 运行最优天数
        result_best = self.engine.run_backtest(best_days, 1000000.0)

        plt.figure(figsize=(12, 6))
        nav_1day = result_1day['daily_nav']
        nav_best = result_best['daily_nav']

        plt.plot(nav_1day.index, nav_1day.values / 1000000.0,
                label=f'T+1 (基准)', linewidth=2, alpha=0.8)
        plt.plot(nav_best.index, nav_best.values / 1000000.0,
                label=f'T+{best_days} (最优)', linewidth=2, color='red')

        plt.xlabel('日期')
        plt.ylabel('净值 (归一化)')
        plt.title(f'收益曲线对比: T+1 vs T+{best_days}')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        plt.savefig(f'{output_dir}/nav_comparison_{timestamp}.png', dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ 收益曲线对比图: {output_dir}/nav_comparison_{timestamp}.png")

        # 6. 综合评分热力图
        if 'composite_score' in self.results.columns:
            plt.figure(figsize=(10, 6))
            scores = self.results[['holding_days', 'sharpe_ratio', 'total_return',
                                  'max_drawdown', 'turnover', 'composite_score']].copy()
            scores['max_drawdown'] = -scores['max_drawdown']  # 转为正数便于比较

            # 归一化
            for col in ['sharpe_ratio', 'total_return', 'max_drawdown', 'turnover']:
                scores[f'{col}_norm'] = (scores[col] - scores[col].min()) / (scores[col].max() - scores[col].min())

            # 绘制热力图
            heatmap_data = scores.set_index('holding_days')[[
                'sharpe_ratio_norm', 'total_return_norm', 'max_drawdown_norm', 'turnover_norm'
            ]]

            sns.heatmap(heatmap_data.T, annot=True, cmap='RdYlGn', center=0.5,
                       cbar_kws={'label': '归一化得分'})
            plt.title('持仓天数多维度评分热力图')
            plt.xlabel('持仓天数')
            plt.ylabel('指标')
            plt.tight_layout()

            plt.savefig(f'{output_dir}/heatmap_{timestamp}.png', dpi=300, bbox_inches='tight')
            plt.close()

            print(f"✓ 综合评分热力图: {output_dir}/heatmap_{timestamp}.png")

    def analyze_by_industry(self) -> pd.DataFrame:
        """
        行业维度拆解分析

        Returns:
            行业分析DataFrame
        """
        if self.data is None or self.comparison is None:
            raise ValueError("请先运行优化流程")

        best_days = int(self.comparison['best_by_sharpe']['holding_days'])
        selected_df = self.data['selected_df']

        # 筛选最优天数下的交易记录
        # 由于是T+N持有，我们需要计算每个股票的实际持有期
        selected_df['trade_date'] = pd.to_datetime(selected_df['trade_date'], format='%Y%m%d')

        # 按股票和日期分组，计算持有期间的收益
        price_df = self.data['price_df']
        price_df['trade_date'] = pd.to_datetime(price_df['trade_date'], format='%Y%m%d')

        industry_returns = []

        for industry, group in selected_df.groupby('l1_name'):
            # 获取该行业的所有选股记录
            stocks = group['ts_code'].unique()

            # 计算该行业的平均收益贡献
            total_return = 0
            trade_count = 0

            for stock in stocks:
                stock_signals = group[group['ts_code'] == stock].sort_values('trade_date')

                for _, signal in stock_signals.iterrows():
                    buy_date = signal['trade_date']
                    sell_date = buy_date + pd.Timedelta(days=best_days)

                    # 获取买入和卖出价格
                    buy_price_row = price_df[(price_df['ts_code'] == stock) &
                                           (price_df['trade_date'] == buy_date)]
                    sell_price_row = price_df[(price_df['ts_code'] == stock) &
                                            (price_df['trade_date'] <= sell_date) &
                                            (price_df['trade_date'] > buy_date)].head(1)

                    if len(buy_price_row) > 0 and len(sell_price_row) > 0:
                        buy_price = buy_price_row['close'].iloc[0]
                        sell_price = sell_price_row['close'].iloc[0]
                        stock_return = (sell_price - buy_price) / buy_price
                        total_return += stock_return
                        trade_count += 1

            if trade_count > 0:
                avg_return = total_return / trade_count
                industry_returns.append({
                    '行业': industry,
                    '交易次数': trade_count,
                    '平均收益': avg_return,
                    '收益贡献': avg_return * trade_count
                })

        industry_df = pd.DataFrame(industry_returns)
        industry_df = industry_df.sort_values('平均收益', ascending=False)

        print(f"\n行业收益贡献 (T+{best_days}):")
        print(industry_df.to_string(index=False, float_format='%.4f'))

        return industry_df

    def validate_stability(self, sub_periods: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        稳定性验证 - 细分区间验证

        Args:
            sub_periods: 子时间段列表，如 ['20250101_20250131', '20250201_20250228', ...]

        Returns:
            稳定性验证结果
        """
        if self.comparison is None:
            raise ValueError("请先运行优化流程")

        best_days = int(self.comparison['best_by_sharpe']['holding_days'])

        # 默认使用2025年前三个月
        if sub_periods is None:
            sub_periods = [
                ('20250101', '20250131'),
                ('20250201', '20250228'),
                ('20250301', '20250331')
            ]

        print(f"\n验证最优天数 T+{best_days} 在细分区间的稳定性:")

        stability_results = []

        for start, end in sub_periods:
            print(f"\n  测试区间: {start} ~ {end}")

            try:
                # 准备该区间数据
                preparer = VBTDataPreparation(start, end)
                sub_data = preparer.prepare_all(
                    outlier_sigma=3.0,
                    normalization=None,
                    top_n=3
                )

                # 运行回测
                sub_engine = VBTBacktestEngine(
                    price_df=sub_data['price_df'],
                    signal_matrix=sub_data['signal_matrix']
                )

                # 测试最优天数
                result_best = sub_engine.run_backtest(best_days, 1000000.0)

                # 测试1天作为基准
                result_1day = sub_engine.run_backtest(1, 1000000.0)

                stability_results.append({
                    '区间': f"{start}~{end}",
                    '最优天数': best_days,
                    '最优收益': result_best['summary']['total_return'],
                    '最优夏普': result_best['summary']['sharpe_ratio'],
                    '最优回撤': result_best['summary']['max_drawdown'],
                    '基准收益': result_1day['summary']['total_return'],
                    '基准夏普': result_1day['summary']['sharpe_ratio'],
                    '超额收益': result_best['summary']['total_return'] - result_1day['summary']['total_return']
                })

                print(f"    ✓ T+{best_days}: 收益={result_best['summary']['total_return']:.2%}, "
                      f"夏普={result_best['summary']['sharpe_ratio']:.3f}, "
                      f"回撤={result_best['summary']['max_drawdown']:.2%}")
                print(f"    ✓ T+1: 收益={result_1day['summary']['total_return']:.2%}, "
                      f"夏普={result_1day['summary']['sharpe_ratio']:.3f}")

            except Exception as e:
                print(f"    ❌ 区间 {start}~{end} 验证失败: {e}")
                continue

        stability_df = pd.DataFrame(stability_results)

        if len(stability_df) > 0:
            avg_excess = stability_df['超额收益'].mean()
            avg_sharpe = stability_df['最优夏普'].mean()

            print(f"\n  稳定性总结:")
            print(f"    平均超额收益: {avg_excess:.2%}")
            print(f"    平均夏普比率: {avg_sharpe:.3f}")
            print(f"    验证通过: {'✅' if avg_excess > 0 else '❌'}")

        return {
            'stability_df': stability_df,
            'best_days': best_days,
            'is_stable': len(stability_df) > 0 and stability_df['超额收益'].mean() > 0
        }

    def save_results(self):
        """保存所有结果到文件"""
        if self.results is None or self.comparison is None:
            return

        output_dir = PATH_CONFIG['results_backtest']
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. 保存量化对比表
        comparison_table = self.comparison['comparison_table']
        comparison_file = f'{output_dir}/hold_days_comparison_{self.start_date}_{self.end_date}_{timestamp}.csv'
        comparison_table.to_csv(comparison_file, index=False, encoding='utf-8-sig')
        print(f"✓ 量化对比表: {comparison_file}")

        # 2. 保存详细结果
        detailed_file = f'{output_dir}/hold_days_detailed_{self.start_date}_{self.end_date}_{timestamp}.csv'
        self.results.to_csv(detailed_file, index=False, encoding='utf-8-sig')
        print(f"✓ 详细结果表: {detailed_file}")

        # 3. 生成汇总报告
        report_file = f'{output_dir}/hold_days_optimize_report_{self.start_date}_{self.end_date}_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("ALPHA_PEG因子持仓天数优化分析报告\n")
            f.write("="*80 + "\n\n")
            f.write(f"回测区间: {self.start_date} ~ {self.end_date}\n")
            f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            best = self.comparison['best_by_sharpe']
            f.write("最优持仓天数分析:\n")
            f.write(f"  最优天数: {int(best['holding_days'])}天\n")
            f.write(f"  夏普比率: {best['sharpe_ratio']:.3f}\n")
            f.write(f"  累计收益: {best['total_return']:.2%}\n")
            f.write(f"  年化收益: {best['annual_return']:.2%}\n")
            f.write(f"  最大回撤: {best['max_drawdown']:.2%}\n")
            f.write(f"  换手率: {best['turnover']:.3f}\n")
            f.write(f"  交易次数: {best['total_trades']}\n\n")

            f.write("综合评分排名:\n")
            top_5 = self.results.nlargest(5, 'composite_score')
            for idx, row in top_5.iterrows():
                f.write(f"  {int(row['holding_days'])}天: 评分={row['composite_score']:.3f}, "
                       f"夏普={row['sharpe_ratio']:.3f}, 收益={row['total_return']:.2%}\n")

            f.write("\n特殊天数标注:\n")
            for idx, row in self.comparison['comparison_table'].iterrows():
                if row['备注'] != '-':
                    f.write(f"  {int(row['holding_days'])}天: {row['备注']}\n")

        print(f"✓ 分析报告: {report_file}")


def main():
    """主函数 - 执行完整优化流程"""
    # 测试区间
    start_date = '20240801'
    end_date = '20250931'  # 注意：9月31日不存在，实际会自动调整为9月30日

    # 持仓天数测试范围 (10-45天)
    hold_days_range = list(range(10, 46))

    # 创建优化器
    optimizer = HoldDaysOptimizer(start_date, end_date)

    # 运行完整优化
    results = optimizer.run_full_optimization(
        hold_days_range=hold_days_range,
        outlier_sigma=3.0,
        normalization=None,
        top_n=3,
        initial_capital=1000000.0
    )

    print("\n" + "="*100)
    print("优化完成！")
    print("="*100)

    return results


if __name__ == '__main__':
    main()
