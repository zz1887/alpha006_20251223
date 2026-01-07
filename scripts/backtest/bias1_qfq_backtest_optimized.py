"""
文件input(依赖外部什么): core.utils, pandas, numpy, argparse, logging
文件output(提供什么): bias1_qfq优化因子（-bias1_qfq）的完整T+20回测结果
文件pos(系统局部地位): 回测执行层，提供因子策略回测功能

基于BIAS乖离率逻辑优化的因子回测：
    1. 使用优化因子：-bias1_qfq（负值反转）
    2. 使用正确价格源：stock_database.daily_kline
    3. T+20持有策略
    4. 包含交易成本（0.154%）

使用示例:
    python3 bias1_qfq_backtest_optimized.py --start_date 20250101 --end_date 20251231

返回值:
    回测结果CSV文件（每日数据、绩效指标、分组收益、交易记录）
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import argparse
import logging
from typing import Dict, List, Tuple

# 配置路径
sys.path.insert(0, '/home/zcy/alpha因子库')

from core.utils.db_connection import DBConnection
from core.config import DATABASE_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Bias1QfqOptimizedBacktest:
    """
    Bias1 Qfq 优化因子回测器

    优化逻辑：
    - 原始因子：bias1_qfq（正偏离=超买）
    - 优化因子：-bias1_qfq（负偏离=超卖=买入信号）
    - 价格数据：stock_database.daily_kline（修正数据源）
    - 持有周期：T+20天
    """

    def __init__(self, start_date: str, end_date: str, hold_days: int = 20, output_dir: str = None):
        self.start_date = start_date
        self.end_date = end_date
        self.hold_days = hold_days
        self.output_dir = output_dir or f"/home/zcy/alpha因子库/results/bias1_qfq/optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

        # 初始化数据库连接
        self.db = DBConnection(DATABASE_CONFIG)

        # 交易成本
        self.buy_cost = 0.00154  # 买入成本0.154%
        self.sell_cost = 0.00154  # 卖出成本0.154%

        logger.info(f"优化回测器初始化完成")
        logger.info(f"时间范围: {start_date} 至 {end_date}")
        logger.info(f"持有天数: {hold_days}")
        logger.info(f"输出目录: {self.output_dir}")

    def load_original_factor(self) -> pd.DataFrame:
        """从数据库加载原始bias1_qfq因子"""
        logger.info("正在从数据库加载原始bias1_qfq因子...")

        query = f"""
        SELECT ts_code, trade_date, bias1_qfq
        FROM stock_database.stk_factor_pro
        WHERE trade_date BETWEEN '{self.start_date}' AND '{self.end_date}'
          AND bias1_qfq IS NOT NULL
        ORDER BY ts_code, trade_date
        """

        result = self.db.execute_query(query)
        factor_df = pd.DataFrame(result)

        if len(factor_df) == 0:
            raise ValueError("未获取到bias1_qfq因子数据，请检查数据库和日期范围")

        # 转换数据类型
        factor_df['bias1_qfq'] = factor_df['bias1_qfq'].astype(float)
        factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'])

        logger.info(f"加载原始因子数据: {len(factor_df):,} 条记录")
        return factor_df

    def create_optimized_factor(self, original_df: pd.DataFrame) -> pd.DataFrame:
        """创建优化因子：使用 -bias1_qfq"""
        logger.info("正在创建优化因子（-bias1_qfq）...")

        optimized_df = original_df.copy()
        optimized_df['factor_value'] = -original_df['bias1_qfq']  # 关键优化：负值反转

        # 统计信息
        stats = optimized_df['factor_value'].describe()
        logger.info(f"优化因子统计:")
        logger.info(f"  均值: {stats['mean']:.4f}")
        logger.info(f"  标准差: {stats['std']:.4f}")
        logger.info(f"  最小值: {stats['min']:.4f}")
        logger.info(f"  最大值: {stats['max']:.4f}")

        return optimized_df[['ts_code', 'trade_date', 'factor_value']]

    def load_price_data(self) -> pd.DataFrame:
        """加载价格数据（使用daily_kline）"""
        logger.info("正在从daily_kline加载价格数据...")

        query = f"""
        SELECT ts_code, trade_date, close
        FROM stock_database.daily_kline
        WHERE trade_date BETWEEN '{self.start_date}' AND '{self.end_date}'
        ORDER BY ts_code, trade_date
        """

        result = self.db.execute_query(query)
        price_df = pd.DataFrame(result)

        if len(price_df) == 0:
            raise ValueError("未获取到价格数据，请检查数据库和日期范围")

        # 转换数据类型
        price_df['close'] = price_df['close'].astype(float)
        price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])

        logger.info(f"加载价格数据: {len(price_df):,} 条记录")
        return price_df

    def calculate_forward_returns(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """计算未来收益（T+hold_days收益）"""
        logger.info(f"正在计算T+{self.hold_days}未来收益...")

        price_df = price_df.sort_values(['ts_code', 'trade_date']).copy()

        # 计算未来N日收盘价
        price_df['future_close'] = price_df.groupby('ts_code')['close'].shift(-self.hold_days)
        price_df['forward_return'] = (price_df['future_close'] - price_df['close']) / price_df['close']

        # 只保留有效记录
        returns_df = price_df[['ts_code', 'trade_date', 'forward_return']].dropna()

        logger.info(f"计算未来收益: {len(returns_df):,} 条有效记录")
        return returns_df

    def group_backtest(self, factor_df: pd.DataFrame, returns_df: pd.DataFrame) -> Dict[str, any]:
        """分组回测分析"""
        logger.info("正在进行分组回测...")

        # 合并数据
        merged = pd.merge(factor_df, returns_df, on=['ts_code', 'trade_date'], how='inner')

        if len(merged) == 0:
            raise ValueError("因子数据和收益数据无交集")

        # 按日期分组，计算分位数（5组）
        merged['group'] = merged.groupby('trade_date')['factor_value'].transform(
            lambda x: pd.qcut(x, 5, labels=False, duplicates='drop')
        )

        # 计算各组平均收益
        group_returns = merged.groupby(['trade_date', 'group'])['forward_return'].mean().reset_index()
        group_stats = group_returns.groupby('group')['forward_return'].agg(['mean', 'std', 'count']).reset_index()

        # 计算单调性
        group_means = group_stats['mean'].values
        monotonic = all(group_means[i] <= group_means[i+1] for i in range(len(group_means)-1))

        # 计算分组差异
        high_minus_low = group_means[-1] - group_means[0]

        result = {
            'group_stats': group_stats,
            'monotonic': monotonic,
            'high_minus_low': high_minus_low,
            'group_means': group_means.tolist(),
            'merged_data': merged,
        }

        logger.info(f"分组分析:")
        logger.info(f"  分组差异(高-低): {high_minus_low:.4f}")
        logger.info(f"  单调性: {'✓' if monotonic else '✗'}")
        for i, row in group_stats.iterrows():
            logger.info(f"  组{int(row['group'])}: 均值={row['mean']:.4f}, 标准差={row['std']:.4f}")

        return result

    def run_strategy(self, factor_df: pd.DataFrame, price_df: pd.DataFrame) -> Dict[str, any]:
        """运行策略回测"""
        logger.info("开始运行策略回测...")

        # 按日期排序
        factor_df = factor_df.sort_values(['ts_code', 'trade_date']).copy()
        price_df = price_df.sort_values(['ts_code', 'trade_date']).copy()

        # 创建价格索引（用于快速查找）
        price_index = price_df.set_index(['ts_code', 'trade_date'])['close'].to_dict()

        # 按日期分组处理
        daily_results = []
        trade_records = []

        # 获取所有交易日
        trade_dates = sorted(factor_df['trade_date'].unique())

        for trade_date in trade_dates:
            # 当日因子数据
            daily_factor = factor_df[factor_df['trade_date'] == trade_date].copy()

            if len(daily_factor) == 0:
                continue

            # 按因子值排序，选择前20%（多头）
            n_select = max(1, int(len(daily_factor) * 0.2))
            selected = daily_factor.nlargest(n_select, 'factor_value').copy()

            # 获取当日价格
            selected['buy_price'] = selected.apply(
                lambda row: price_index.get((row['ts_code'], trade_date), np.nan),
                axis=1
            )

            # 过滤无效价格
            selected = selected.dropna(subset=['buy_price'])

            if len(selected) == 0:
                continue

            # 计算卖出日期和价格
            sell_date = trade_date + pd.Timedelta(days=self.hold_days)
            selected['sell_date'] = sell_date

            # 获取卖出价格
            selected['sell_price'] = selected.apply(
                lambda row: price_index.get((row['ts_code'], sell_date), np.nan),
                axis=1
            )

            # 过滤无效卖出
            valid_trades = selected.dropna(subset=['sell_price']).copy()

            if len(valid_trades) == 0:
                continue

            # 计算单笔收益（扣除交易成本）
            valid_trades['gross_return'] = (valid_trades['sell_price'] - valid_trades['buy_price']) / valid_trades['buy_price']
            valid_trades['net_return'] = valid_trades['gross_return'] - self.buy_cost - self.sell_cost

            # 记录交易
            for _, trade in valid_trades.iterrows():
                trade_records.append({
                    'buy_date': trade_date,
                    'sell_date': trade['sell_date'],
                    'ts_code': trade['ts_code'],
                    'buy_price': trade['buy_price'],
                    'sell_price': trade['sell_price'],
                    'gross_return': trade['gross_return'],
                    'net_return': trade['net_return'],
                })

            # 计算当日策略收益（等权重）
            if len(valid_trades) > 0:
                daily_return = valid_trades['net_return'].mean()
                daily_results.append({
                    'trade_date': trade_date,
                    'return': daily_return,
                    'holdings': len(valid_trades),
                })

        # 转换为DataFrame
        performance_df = pd.DataFrame(daily_results)
        trades_df = pd.DataFrame(trade_records)

        logger.info(f"回测完成，共{len(performance_df)}个交易日，{len(trades_df)}笔交易")
        return {
            'performance': performance_df,
            'trades': trades_df,
        }

    def calculate_metrics(self, performance_df: pd.DataFrame) -> Dict[str, float]:
        """计算绩效指标"""
        logger.info("正在计算绩效指标...")

        if len(performance_df) == 0:
            return {}

        # 基础指标
        total_return = (1 + performance_df['return']).prod() - 1
        n_days = len(performance_df)
        annual_return = (1 + total_return) ** (243 / n_days) - 1  # 假设243个交易日

        # 波动率和夏普比率
        volatility = performance_df['return'].std() * np.sqrt(243)  # 年化波动率
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0

        # 最大回撤
        cumulative = (1 + performance_df['return']).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # Calmar比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown < 0 else 0

        # 信息比率（相对于0基准）
        excess_return = performance_df['return'].mean() * 243
        excess_std = performance_df['return'].std() * np.sqrt(243)
        info_ratio = excess_return / excess_std if excess_std > 0 else 0

        # 胜率
        win_rate = (performance_df['return'] > 0).mean()

        # 换手率估算（每日持仓变化）
        turnover = 1.0  # 每日再平衡，换手率100%

        metrics = {
            '累计收益率': total_return,
            '年化收益率': annual_return,
            '年化波动率': volatility,
            '夏普比率': sharpe_ratio,
            '最大回撤': max_drawdown,
            'Calmar比率': calmar_ratio,
            '信息比率': info_ratio,
            '胜率': win_rate,
            '换手率': turnover,
        }

        logger.info("绩效指标:")
        for k, v in metrics.items():
            logger.info(f"  {k}: {v:.4f}")

        return metrics

    def save_results(self, performance_df: pd.DataFrame, metrics: Dict, group_result: Dict, trades_df: pd.DataFrame):
        """保存回测结果"""
        logger.info("正在保存回测结果...")

        # 1. 回测表现数据（添加资产价值曲线）
        # 计算每日资产价值
        initial_capital = 1000000.0
        portfolio_value = initial_capital
        portfolio_values = []

        for _, row in performance_df.iterrows():
            daily_return = row['return']
            portfolio_value *= (1 + daily_return)
            portfolio_values.append(portfolio_value)

        # 添加资产价值列到原始DataFrame（in-place修改）
        performance_df['portfolio_value'] = portfolio_values

        perf_path = os.path.join(self.output_dir, f"bias1_qfq_optimized_performance_{self.start_date}_{self.end_date}.csv")
        performance_df.to_csv(perf_path, index=False, float_format='%.6f')
        logger.info(f"回测表现已保存: {perf_path}")

        # 2. 绩效指标
        metrics_df = pd.DataFrame([metrics])
        metrics_path = os.path.join(self.output_dir, f"bias1_qfq_optimized_metrics_{self.start_date}_{self.end_date}.csv")
        metrics_df.to_csv(metrics_path, index=False, float_format='%.6f')
        logger.info(f"绩效指标已保存: {metrics_path}")

        # 3. 分组收益
        group_df = group_result['group_stats']
        group_path = os.path.join(self.output_dir, f"bias1_qfq_optimized_groups_{self.start_date}_{self.end_date}.csv")
        group_df.to_csv(group_path, index=False, float_format='%.6f')
        logger.info(f"分组收益已保存: {group_path}")

        # 4. 交易记录
        trades_path = os.path.join(self.output_dir, f"bias1_qfq_optimized_trades_{self.start_date}_{self.end_date}.csv")
        trades_df.to_csv(trades_path, index=False, float_format='%.6f')
        logger.info(f"交易记录已保存: {trades_path}")

    def generate_report(self, performance_df: pd.DataFrame, metrics: Dict, group_result: Dict):
        """生成回测报告"""
        logger.info("正在生成回测报告...")

        report_path = os.path.join(self.output_dir, "backtest_report.txt")

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("BIAS1_QFQ 优化因子回测报告\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"回测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"时间范围: {self.start_date} 至 {self.end_date}\n")
            f.write(f"持有天数: {self.hold_days}天\n")
            f.write(f"优化方案: 使用 -bias1_qfq 作为因子\n")
            f.write(f"价格数据: stock_database.daily_kline\n\n")

            f.write("-" * 80 + "\n")
            f.write("1. 绩效指标\n")
            f.write("-" * 80 + "\n")
            for k, v in metrics.items():
                f.write(f"{k}: {v:.4f}\n")
            f.write("\n")

            # 添加资产价值曲线信息
            if 'portfolio_value' in performance_df.columns:
                f.write("-" * 80 + "\n")
                f.write("2. 资产价值曲线\n")
                f.write("-" * 80 + "\n")
                initial_value = performance_df['portfolio_value'].iloc[0]
                final_value = performance_df['portfolio_value'].iloc[-1]
                f.write(f"初始资产: {initial_value:,.2f}\n")
                f.write(f"最终资产: {final_value:,.2f}\n")
                f.write(f"资产增长: {final_value/initial_value - 1:.4f} ({((final_value/initial_value - 1)*100):.2f}%)\n\n")

                # 显示关键时间点的资产价值
                f.write("关键时间点资产价值:\n")
                key_dates = [performance_df['trade_date'].iloc[0]]
                # 添加季度末时间点
                for date in performance_df['trade_date']:
                    if date.day == 1:  # 每月第一天
                        if date not in key_dates:
                            key_dates.append(date)
                key_dates.append(performance_df['trade_date'].iloc[-1])

                for date in key_dates:
                    if date in performance_df['trade_date'].values:
                        value = performance_df[performance_df['trade_date'] == date]['portfolio_value'].iloc[0]
                        f.write(f"  {date.strftime('%Y-%m-%d')}: {value:,.2f}\n")
                f.write("\n")

            f.write("-" * 80 + "\n")
            f.write("3. 分组收益分析\n")
            f.write("-" * 80 + "\n")
            f.write(f"分组差异(高组-低组): {group_result['high_minus_low']:.4f}\n")
            f.write(f"单调性: {'✓ 通过' if group_result['monotonic'] else '✗ 未通过'}\n\n")

            f.write("各组平均收益:\n")
            for i, row in group_result['group_stats'].iterrows():
                f.write(f"  组{int(row['group'])}: {row['mean']:.4f} (样本数: {int(row['count'])})\n")
            f.write("\n")

            f.write("-" * 80 + "\n")
            f.write("4. 结论\n")
            f.write("-" * 80 + "\n")

            # 综合判断
            total_return = metrics['累计收益率']
            sharpe = metrics['夏普比率']
            max_dd = metrics['最大回撤']
            group_diff = group_result['high_minus_low']

            if total_return > 0 and sharpe > 1.0 and max_dd > -0.2 and group_diff > 0.01:
                verdict = "✅ 因子有效，建议使用"
            elif total_return > 0 and sharpe > 0.5:
                verdict = "⚠️  因子一般，需要优化"
            else:
                verdict = "❌ 因子无效，不建议使用"

            f.write(f"回测结论: {verdict}\n\n")

            f.write("优化说明:\n")
            f.write("  1. 因子方向修正：使用 -bias1_qfq 获得正向预测能力\n")
            f.write("  2. BIAS乖离率逻辑：负偏离=超卖=买入信号\n")
            f.write("  3. 价格数据修正：使用 daily_kline 替代 stk_factor_pro\n")
            f.write("  4. T+20持有策略：每日再平衡，等权重配置\n\n")

            f.write("=" * 80 + "\n")
            f.write("报告结束\n")
            f.write("=" * 80 + "\n")

        logger.info(f"回测报告已保存: {report_path}")
        return report_path

    def run(self):
        """运行完整回测流程"""
        try:
            logger.info("=" * 80)
            logger.info("开始优化因子回测流程")
            logger.info("=" * 80)

            # 1. 加载原始因子
            original_df = self.load_original_factor()

            # 2. 创建优化因子
            optimized_df = self.create_optimized_factor(original_df)

            # 3. 加载价格数据（修正）
            price_df = self.load_price_data()

            # 4. 计算未来收益
            returns_df = self.calculate_forward_returns(price_df)

            # 5. 分组回测分析
            group_result = self.group_backtest(optimized_df, returns_df)

            # 6. 运行策略回测
            strategy_result = self.run_strategy(optimized_df, price_df)

            # 7. 计算绩效指标
            metrics = self.calculate_metrics(strategy_result['performance'])

            # 8. 保存结果（包含资产价值曲线）
            self.save_results(
                strategy_result['performance'],
                metrics,
                group_result,
                strategy_result['trades']
            )

            # 9. 生成报告
            report_path = self.generate_report(strategy_result['performance'], metrics, group_result)

            logger.info("=" * 80)
            logger.info("优化回测流程完成！")
            logger.info(f"报告: {report_path}")
            logger.info(f"输出目录: {self.output_dir}")
            logger.info("=" * 80)

            return {
                'success': True,
                'report_path': report_path,
                'output_dir': self.output_dir,
                'metrics': metrics,
                'group_result': group_result,
            }

        except Exception as e:
            logger.error(f"回测过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Bias1 Qfq 优化因子回测')
    parser.add_argument('--start_date', type=str, default='20250101', help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end_date', type=str, default='20251231', help='结束日期 (YYYYMMDD)')
    parser.add_argument('--hold_days', type=int, default=20, help='持有天数')
    parser.add_argument('--output_dir', type=str, default=None, help='输出目录')

    args = parser.parse_args()

    backtest = Bias1QfqOptimizedBacktest(
        start_date=args.start_date,
        end_date=args.end_date,
        hold_days=args.hold_days,
        output_dir=args.output_dir
    )

    result = backtest.run()

    if result['success']:
        print(f"\n✅ 回测成功！")
        print(f"报告: {result['report_path']}")
        print(f"输出目录: {result['output_dir']}")

        metrics = result['metrics']
        print(f"\n核心指标:")
        print(f"  累计收益率: {metrics['累计收益率']:.2%}")
        print(f"  年化收益率: {metrics['年化收益率']:.2%}")
        print(f"  夏普比率: {metrics['夏普比率']:.2f}")
        print(f"  最大回撤: {metrics['最大回撤']:.2%}")

        group_result = result['group_result']
        print(f"  分组差异: {group_result['high_minus_low']:.4f}")
        print(f"  单调性: {'✓' if group_result['monotonic'] else '✗'}")
    else:
        print(f"\n❌ 回测失败: {result['error']}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())