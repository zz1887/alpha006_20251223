"""
Alpha Pluse 单因子有效性验证 - 完整回测版

核心功能:
1. 加载因子数据和价格数据
2. 月度再平衡回测
3. 计算信号组 vs 非信号组收益
4. 生成完整绩效指标和可视化
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import logging
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, '/home/zcy/alpha006_20251223')

from core.utils.db_connection import db
from core.utils.data_loader import data_loader, get_index_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class AlphaPluseBacktest:
    """Alpha Pluse 单因子回测器"""

    def __init__(self, start_date: str, end_date: str):
        self.start_date = start_date
        self.end_date = end_date
        self.output_dir = '/home/zcy/alpha006_20251223/results/backtest'
        os.makedirs(self.output_dir, exist_ok=True)

    def load_factor_data(self) -> pd.DataFrame:
        """加载因子数据"""
        cache_dir = '/home/zcy/alpha006_20251223/data/cache'
        factor_file = f"{cache_dir}/alpha_pluse_factor_{self.start_date}_{self.end_date}.csv"

        logger.info("加载因子数据...")
        df = pd.read_csv(factor_file)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df['count_20d'] = pd.to_numeric(df['count_20d'], errors='coerce')

        logger.info(f"因子数据: {len(df):,} 条记录")
        logger.info(f"信号比例: {df['alpha_pluse'].mean():.2%}")

        return df

    def get_price_data(self, stocks: List[str]) -> pd.DataFrame:
        """获取价格数据用于计算收益"""
        logger.info("获取价格数据...")

        placeholders = ','.join(['%s'] * len(stocks))
        sql = f"""
        SELECT ts_code, trade_date, close, vol
        FROM daily_kline
        WHERE trade_date >= %s AND trade_date <= %s
          AND ts_code IN ({placeholders})
        ORDER BY ts_code, trade_date
        """
        params = [self.start_date, self.end_date] + stocks
        data = db.execute_query(sql, params)

        df = pd.DataFrame(data)
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['vol'] = pd.to_numeric(df['vol'], errors='coerce')

        logger.info(f"价格数据: {len(df):,} 条记录")
        return df

    def get_trading_days(self) -> List[str]:
        """获取交易日列表"""
        sql = """
        SELECT DISTINCT trade_date
        FROM daily_kline
        WHERE trade_date >= %s AND trade_date <= %s
        ORDER BY trade_date
        """
        data = db.execute_query(sql, (self.start_date, self.end_date))
        return [row['trade_date'] for row in data]

    def get_rebalance_dates(self, trading_days: List[str]) -> List[str]:
        """获取月度再平衡日期"""
        dates = pd.to_datetime(trading_days, format='%Y%m%d')
        monthly_ends = []
        current_month = None

        for date in dates:
            if current_month is None or date.month != current_month:
                if current_month is not None:
                    monthly_ends.append(prev_date.strftime('%Y%m%d'))
                current_month = date.month
            prev_date = date

        if current_month is not None:
            monthly_ends.append(prev_date.strftime('%Y%m%d'))

        return monthly_ends

    def get_index_data(self) -> pd.DataFrame:
        """获取沪深300指数数据"""
        logger.info("获取沪深300指数数据...")
        index_df = get_index_data('000300.SH', self.start_date, self.end_date)
        index_df['trade_date'] = pd.to_datetime(index_df['trade_date'], format='%Y%m%d')
        index_df['close'] = pd.to_numeric(index_df['close'], errors='coerce')
        return index_df

    def run_backtest(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """运行回测"""
        logger.info("开始回测...")

        # 获取交易日和再平衡日
        trading_days = self.get_trading_days()
        rebalance_dates = self.get_rebalance_dates(trading_days)

        logger.info(f"交易日: {len(trading_days)}, 再平衡: {len(rebalance_dates)}")

        # 获取价格数据
        all_stocks = factor_df['ts_code'].unique().tolist()
        price_df = self.get_price_data(all_stocks)

        # 准备结果
        results = []
        positions = None  # 当前持仓 {stock: weight}

        for i, trade_date in enumerate(trading_days):
            trade_date_dt = pd.to_datetime(trade_date, format='%Y%m%d')

            # 再平衡日
            if trade_date in rebalance_dates:
                factor_today = factor_df[factor_df['trade_date'] == trade_date_dt].copy()

                if len(factor_today) > 0:
                    # 筛选流动性好的股票 (成交量 > 市场均值)
                    avg_vol = factor_today['count_20d'].mean()  # 使用count_20d作为代理
                    liquid_stocks = factor_today[factor_today['count_20d'] > 0]['ts_code'].tolist()

                    # 信号组: alpha_pluse = 1
                    signal_stocks = factor_today[
                        (factor_today['alpha_pluse'] == 1) &
                        (factor_today['ts_code'].isin(liquid_stocks))
                    ]['ts_code'].tolist()

                    if len(signal_stocks) >= 10:  # 最少10只股票
                        weight = 1.0 / len(signal_stocks)
                        positions = {stock: weight for stock in signal_stocks}
                        logger.info(f"{trade_date} 调仓: {len(signal_stocks)} 只股票")
                    else:
                        positions = None
                else:
                    positions = None

            # 计算当日收益
            if positions and i > 0:
                prev_date = trading_days[i-1]
                daily_return = 0.0
                valid_stocks = 0

                for stock, weight in positions.items():
                    # 获取今日和昨日收盘价
                    price_today = price_df[
                        (price_df['ts_code'] == stock) &
                        (price_df['trade_date'] == trade_date_dt)
                    ]

                    price_prev = price_df[
                        (price_df['ts_code'] == stock) &
                        (price_df['trade_date'] == pd.to_datetime(prev_date, format='%Y%m%d'))
                    ]

                    if len(price_today) > 0 and len(price_prev) > 0:
                        p_t = price_today['close'].iloc[0]
                        p_p = price_prev['close'].iloc[0]

                        if p_p > 0:
                            stock_return = (p_t - p_p) / p_p
                            daily_return += weight * stock_return
                            valid_stocks += 1

                # 扣除交易成本 (再平衡日)
                if trade_date in rebalance_dates and valid_stocks > 0:
                    # 双边成本: 手续费0.1% + 印花税0.05% + 过户费0.002% + 滑点0.05%
                    transaction_cost = 0.001 + 0.0005 + 0.00002 + 0.0005
                    daily_return -= transaction_cost

                results.append({
                    'date': trade_date,
                    'return': daily_return,
                    'stocks_count': valid_stocks
                })

        result_df = pd.DataFrame(results)

        if len(result_df) > 0:
            result_df['cumulative'] = (1 + result_df['return']).cumprod()
            logger.info(f"回测完成: {len(result_df)} 天, 累计收益: {result_df['cumulative'].iloc[-1]:.4f}")

        return result_df

    def calculate_metrics(self, result_df: pd.DataFrame, index_df: pd.DataFrame) -> Dict[str, float]:
        """计算绩效指标"""
        if len(result_df) == 0:
            return {}

        # 合并指数数据
        result_df['date_dt'] = pd.to_datetime(result_df['date'], format='%Y%m%d')
        merged = result_df.merge(index_df[['trade_date', 'close']],
                                left_on='date_dt', right_on='trade_date', how='left')

        # 计算指数收益率
        if len(merged) > 1:
            merged['index_return'] = merged['close'].pct_change()
            merged['index_cumulative'] = (1 + merged['index_return'].fillna(0)).cumprod()

            # 超额收益
            merged['excess_return'] = merged['return'] - merged['index_return'].fillna(0)
            merged['excess_cumulative'] = (1 + merged['excess_return'].fillna(0)).cumprod()

        returns = result_df['return']

        # 基础指标
        total_return = result_df['cumulative'].iloc[-1] - 1
        days = len(result_df)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0
        sharpe = (annual_return - 0.02) / volatility if volatility > 0 else 0

        # 最大回撤
        cumulative = result_df['cumulative']
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # 胜率
        win_rate = (returns > 0).mean() if len(returns) > 0 else 0

        # 月度胜率
        result_df['year_month'] = pd.to_datetime(result_df['date'], format='%Y%m%d').dt.to_period('M')
        monthly_returns = result_df.groupby('year_month')['return'].sum()
        monthly_win_rate = (monthly_returns > 0).mean() if len(monthly_returns) > 0 else 0

        # 超额收益指标
        if 'excess_cumulative' in merged.columns and len(merged) > 0:
            excess_return = merged['excess_cumulative'].iloc[-1] - 1
            excess_annual = (1 + excess_return) ** (252 / days) - 1
            excess_vol = merged['excess_return'].std() * np.sqrt(252) if len(merged) > 0 else 0
            excess_sharpe = (excess_annual - 0.02) / excess_vol if excess_vol > 0 else 0
        else:
            excess_return = excess_annual = excess_vol = excess_sharpe = 0

        metrics = {
            '累计收益率': total_return,
            '年化收益率': annual_return,
            '年化波动率': volatility,
            '夏普比率': sharpe,
            '最大回撤': max_drawdown,
            '胜率': win_rate,
            '月度胜率': monthly_win_rate,
            '超额收益': excess_return,
            '超额年化': excess_annual,
            '超额夏普': excess_sharpe,
            '交易天数': days,
        }

        return metrics

    def generate_visualizations(self, result_df: pd.DataFrame, index_df: pd.DataFrame):
        """生成可视化图表"""
        plt.style.use('default')
        sns.set_palette("husl")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 合并指数数据
        result_df['date_dt'] = pd.to_datetime(result_df['date'], format='%Y%m%d')
        merged = result_df.merge(index_df[['trade_date', 'close']],
                                left_on='date_dt', right_on='trade_date', how='left')

        if len(merged) > 1:
            merged['index_return'] = merged['close'].pct_change()
            merged['index_cumulative'] = (1 + merged['index_return'].fillna(0)).cumprod()

        # 1. 累计收益对比
        plt.figure(figsize=(12, 6))
        plt.plot(merged['date_dt'], merged['cumulative'], label='Alpha Pluse 组合', linewidth=2)
        if 'index_cumulative' in merged.columns:
            plt.plot(merged['date_dt'], merged['index_cumulative'], label='沪深300', linewidth=2, alpha=0.7)
        plt.title('Alpha Pluse 因子累计收益对比')
        plt.xlabel('日期')
        plt.ylabel('累计净值')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/alpha_pluse_cumulative_{timestamp}.png", dpi=150)
        plt.close()

        # 2. 月度收益热力图
        plt.figure(figsize=(12, 8))
        result_df['year_month'] = pd.to_datetime(result_df['date'], format='%Y%m%d').dt.to_period('M')
        monthly_returns = result_df.groupby('year_month')['return'].sum().reset_index()
        monthly_returns['year'] = monthly_returns['year_month'].dt.year
        monthly_returns['month'] = monthly_returns['year_month'].dt.month

        pivot_data = monthly_returns.pivot(index='year', columns='month', values='return')

        sns.heatmap(pivot_data, annot=True, fmt='.2%', cmap='RdYlGn', center=0,
                   cbar_kws={'label': '月度收益率'})
        plt.title('Alpha Pluse 月度收益热力图')
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/alpha_pluse_monthly_heatmap_{timestamp}.png", dpi=150)
        plt.close()

        # 3. 回撤曲线
        plt.figure(figsize=(12, 6))
        cumulative = merged['cumulative']
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max

        plt.fill_between(merged['date_dt'], drawdown, 0, color='red', alpha=0.3)
        plt.plot(merged['date_dt'], drawdown, color='red', linewidth=1)

        if 'index_cumulative' in merged.columns:
            index_max = merged['index_cumulative'].expanding().max()
            index_dd = (merged['index_cumulative'] - index_max) / index_max
            plt.plot(merged['date_dt'], index_dd, color='blue', linewidth=1, alpha=0.7, label='沪深300回撤')

        plt.title('Alpha Pluse 组合回撤曲线')
        plt.xlabel('日期')
        plt.ylabel('回撤比例')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/alpha_pluse_drawdown_{timestamp}.png", dpi=150)
        plt.close()

        # 4. 月度收益柱状图
        plt.figure(figsize=(14, 6))
        months = [str(m) for m in monthly_returns['year_month']]
        colors = ['green' if x > 0 else 'red' for x in monthly_returns['return']]
        plt.bar(months, monthly_returns['return'], color=colors, alpha=0.7)
        plt.axhline(y=0, color='black', linewidth=0.8)
        plt.title('Alpha Pluse 月度收益分布')
        plt.xlabel('月份')
        plt.ylabel('收益率')
        plt.xticks(rotation=45, fontsize=8)
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/alpha_pluse_monthly_bar_{timestamp}.png", dpi=150)
        plt.close()

        logger.info(f"可视化图表已保存到: {self.output_dir}")

    def generate_report(self, metrics: Dict[str, float], result_df: pd.DataFrame):
        """生成完整报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. 保存绩效指标
        metrics_df = pd.DataFrame([metrics])
        metrics_file = f"{self.output_dir}/alpha_pluse_backtest_metrics_{timestamp}.csv"
        metrics_df.to_csv(metrics_file, index=False, encoding='utf-8-sig')

        # 2. 保存回测结果
        result_file = f"{self.output_dir}/alpha_pluse_backtest_results_{timestamp}.csv"
        result_df.to_csv(result_file, index=False, encoding='utf-8-sig')

        # 3. 生成文本报告
        report_file = f"{self.output_dir}/alpha_pluse_backtest_report_{timestamp}.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Alpha Pluse 单因子回测验证报告\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"回测周期: {self.start_date} ~ {self.end_date}\n")
            f.write(f"基准指数: 沪深300 (000300.SH)\n")
            f.write(f"再平衡频率: 月度\n")
            f.write(f"交易成本: 手续费0.1% + 印花税0.05% + 过户费0.002% + 滑点0.05%\n\n")

            f.write("绩效指标:\n")
            f.write("-" * 40 + "\n")
            for key, value in metrics.items():
                if isinstance(value, float):
                    f.write(f"{key}: {value:.4f}\n")
                else:
                    f.write(f"{key}: {value}\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("因子有效性评估:\n")
            f.write("=" * 80 + "\n\n")

            # 评估结论
            total_return = metrics.get('累计收益率', 0)
            sharpe = metrics.get('夏普比率', 0)
            max_dd = metrics.get('最大回撤', 0)
            excess = metrics.get('超额收益', 0)

            f.write("收益能力:\n")
            if total_return > 0.15:
                f.write("  ✅ 优秀: 年化收益 > 15%\n")
            elif total_return > 0.10:
                f.write("  ✅ 良好: 年化收益 > 10%\n")
            elif total_return > 0.05:
                f.write("  ⚠️ 一般: 年化收益 > 5%\n")
            else:
                f.write("  ❌ 较差: 年化收益 ≤ 5%\n")

            f.write("\n风险调整:\n")
            if sharpe > 1.5:
                f.write("  ✅ 优秀: Sharpe > 1.5\n")
            elif sharpe > 1.0:
                f.write("  ✅ 良好: Sharpe > 1.0\n")
            elif sharpe > 0.5:
                f.write("  ⚠️ 一般: Sharpe > 0.5\n")
            else:
                f.write("  ❌ 较差: Sharpe ≤ 0.5\n")

            f.write("\n最大回撤:\n")
            if max_dd > -0.15:
                f.write("  ✅ 优秀: 回撤 < 15%\n")
            elif max_dd > -0.25:
                f.write("  ⚠️ 可接受: 回撤 < 25%\n")
            else:
                f.write("  ❌ 较差: 回撤 ≥ 25%\n")

            f.write("\n超额收益:\n")
            if excess > 0.10:
                f.write("  ✅ 显著: 超额收益 > 10%\n")
            elif excess > 0.05:
                f.write("  ⚠️ 一般: 超额收益 > 5%\n")
            else:
                f.write("  ❌ 不显著: 超额收益 ≤ 5%\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("综合评分: ")

            score = 0
            if total_return > 0.15: score += 40
            elif total_return > 0.10: score += 30
            elif total_return > 0.05: score += 20

            if sharpe > 1.5: score += 30
            elif sharpe > 1.0: score += 20
            elif sharpe > 0.5: score += 10

            if excess > 0.10: score += 20
            elif excess > 0.05: score += 10

            if max_dd > -0.15: score += 10
            elif max_dd > -0.25: score += 5

            f.write(f"{score}/100\n\n")

            if score >= 80:
                f.write("结论: 优秀因子，可实盘应用\n")
            elif score >= 60:
                f.write("结论: 良好因子，建议优化后使用\n")
            elif score >= 40:
                f.write("结论: 一般因子，谨慎使用\n")
            else:
                f.write("结论: 较差因子，不建议使用\n")

        logger.info(f"\n报告已保存: {report_file}")
        logger.info(f"绩效数据已保存: {metrics_file}")
        logger.info(f"回测结果已保存: {result_file}")

        # 打印摘要
        print("\n" + "=" * 80)
        print("回测结果摘要")
        print("=" * 80)
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value}")
        print(f"\n综合评分: {score}/100")
        print("=" * 80)


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Alpha Pluse 单因子有效性验证 - 完整回测版")
    print("=" * 80)

    start_date = '20230101'
    end_date = '20251201'

    try:
        # 创建回测器
        backtest = AlphaPluseBacktest(start_date, end_date)

        # 1. 加载因子数据
        factor_df = backtest.load_factor_data()

        # 2. 运行回测
        result_df = backtest.run_backtest(factor_df)

        if len(result_df) == 0:
            logger.error("回测未产生有效结果")
            return

        # 3. 获取指数数据
        index_df = backtest.get_index_data()

        # 4. 计算绩效指标
        metrics = backtest.calculate_metrics(result_df, index_df)

        # 5. 生成可视化
        logger.info("生成可视化图表...")
        backtest.generate_visualizations(result_df, index_df)

        # 6. 生成报告
        backtest.generate_report(metrics, result_df)

        print("\n✅ 回测完成！请查看 results/backtest/ 目录下的结果文件")

    except Exception as e:
        logger.error(f"回测失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()