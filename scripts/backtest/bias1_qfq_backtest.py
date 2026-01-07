"""
文件input(依赖外部什么): core.utils, core.config, pandas, numpy
文件output(提供什么): bias1_qfq因子回测脚本
文件pos(系统局部地位): 回测执行层，提供bias1_qfq单因子回测功能
文件功能:
    1. 从stock_database.stk_factor_pro提取bias1_qfq因子
    2. 执行T+20回测
    3. 计算绩效指标
    4. 生成回测报告

使用示例:
    python bias1_qfq_backtest.py --start_date 20240101 --end_date 20241231 --hold_days 20

参数说明:
    start_date: 回测开始日期
    end_date: 回测结束日期
    hold_days: 持有天数（默认20）
    n_groups: 分组数量（默认5，使用前20%股票）

返回值:
    回测结果CSV文件
    绩效指标报告
    因子数据文件

回测逻辑:
    1. 每日根据bias1_qfq因子值排序
    2. 选择因子值最大的前20%股票（多头组）
    3. T日等权重买入，持有N天后卖出
    4. 计算累计收益、年化收益、夏普比率、最大回撤等指标
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
import argparse
import logging
from typing import Dict, List, Tuple

# 配置路径
sys.path.insert(0, '/home/zcy/alpha因子库')

from core.utils.db_connection import DBConnection
from core.utils.data_loader import DataLoader, get_index_data
from core.config import DATABASE_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Bias1QfqBacktest:
    """Bias1 Qfq 单因子回测类"""

    def __init__(self, start_date: str, end_date: str, hold_days: int = 20, n_groups: int = 5):
        """
        初始化回测器

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            hold_days: 持有天数
            n_groups: 分组数量（用于计算分组收益）
        """
        self.start_date = start_date
        self.end_date = end_date
        self.hold_days = hold_days
        self.n_groups = n_groups

        # 交易成本配置
        self.cost_config = {
            'commission': 0.001,      # 0.1% 手续费
            'stamp_tax': 0.0005,      # 0.05% 印花税 (卖出时)
            'transfer_fee': 0.00002,  # 0.002% 过户费 (双向)
            'slippage': 0.0005,       # 0.05% 滑点
        }
        self.total_cost = 0.001 + 0.0005 + 0.00002 * 2  # 0.00154

        # 流动性筛选
        self.liquidity_threshold = 0.05  # 换手率 > 5%

        # 数据库连接
        self.db = DBConnection(DATABASE_CONFIG)
        self.data_loader = DataLoader()

        logger.info(f"初始化回测器: {start_date} ~ {end_date}, 持有{hold_days}天, {n_groups}分组")

    def extract_bias1_qfq_factor(self) -> pd.DataFrame:
        """
        从stock_database.stk_factor_pro提取bias1_qfq因子

        Returns:
            因子数据 DataFrame: ts_code, trade_date, bias1_qfq
        """
        logger.info("=" * 60)
        logger.info("阶段1: 提取bias1_qfq因子数据")
        logger.info("=" * 60)

        query = f"""
        SELECT
            ts_code,
            trade_date,
            bias1_qfq
        FROM stock_database.stk_factor_pro
        WHERE bias1_qfq IS NOT NULL
            AND trade_date >= '{self.start_date}'
            AND trade_date <= '{self.end_date}'
        ORDER BY trade_date, ts_code
        """

        logger.info("执行数据库查询...")
        result = self.db.execute_query(query)
        factor_df = pd.DataFrame(result)

        if len(factor_df) == 0:
            raise ValueError("未获取到bias1_qfq因子数据，请检查日期范围和数据表")

        # 转换日期格式
        factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'], format='%Y%m%d')

        logger.info(f"获取因子数据: {len(factor_df):,} 条记录")
        logger.info(f"日期范围: {factor_df['trade_date'].min()} ~ {factor_df['trade_date'].max()}")
        logger.info(f"股票数量: {factor_df['ts_code'].nunique()}")

        # 统计因子值分布
        logger.info(f"\n因子值统计:")
        logger.info(f"  均值: {factor_df['bias1_qfq'].mean():.4f}")
        logger.info(f"  标准差: {factor_df['bias1_qfq'].std():.4f}")
        logger.info(f"  最小值: {factor_df['bias1_qfq'].min():.4f}")
        logger.info(f"  最大值: {factor_df['bias1_qfq'].max():.4f}")

        return factor_df

    def load_market_data(self, stocks: List[str]) -> pd.DataFrame:
        """
        加载市场数据（价格、成交量）

        Args:
            stocks: 股票列表

        Returns:
            价格数据 DataFrame
        """
        logger.info("\n加载市场数据...")

        # 获取价格和成交量数据
        price_data = self.data_loader.get_price_data(
            stocks,
            self.start_date,
            self.end_date,
            columns=['open', 'close', 'vol']
        )

        if len(price_data) == 0:
            raise ValueError("未获取到价格数据")

        logger.info(f"价格数据: {len(price_data):,} 条记录")

        return price_data

    def load_index_data(self) -> pd.DataFrame:
        """
        加载基准指数数据（沪深300）

        Returns:
            指数数据 DataFrame
        """
        logger.info("\n加载沪深300指数数据...")

        index_data = get_index_data(
            self.start_date,
            self.end_date,
            '000300.SH'
        )

        if len(index_data) == 0:
            raise ValueError("未获取到指数数据")

        logger.info(f"指数数据: {len(index_data)} 条记录")

        return index_data

    def get_rebalance_dates(self, trading_days: List[str]) -> List[str]:
        """
        获取再平衡日期（每日再平衡）

        Args:
            trading_days: 交易日列表

        Returns:
            再平衡日期列表
        """
        # 每日都进行再平衡
        return trading_days

    def run_backtest(self, factor_df: pd.DataFrame, price_df: pd.DataFrame,
                     index_df: pd.DataFrame) -> pd.DataFrame:
        """
        运行回测

        Args:
            factor_df: 因子数据
            price_df: 价格数据
            index_df: 指数数据

        Returns:
            回测结果 DataFrame
        """
        logger.info("\n" + "=" * 60)
        logger.info("阶段2: 执行回测")
        logger.info("=" * 60)

        # 获取交易日列表
        trading_days = sorted(factor_df['trade_date'].unique().astype(str))
        logger.info(f"总交易日: {len(trading_days)}")

        # 准备价格索引
        price_df['trade_date_str'] = price_df['trade_date'].astype(str)
        # 确保列存在
        required_cols = ['open', 'close', 'vol']
        available_cols = [col for col in required_cols if col in price_df.columns]
        price_index = price_df.set_index(['ts_code', 'trade_date_str'])[available_cols].to_dict('index')

        # 准备指数索引
        index_df['trade_date_str'] = index_df['trade_date'].astype(str)
        index_index = index_df.set_index('trade_date_str')['close'].to_dict()

        # 回测结果存储
        portfolio_records = []
        benchmark_records = []
        trade_records = []

        # 持仓管理
        positions = {}  # {ts_code: {'shares': shares, 'buy_date': date, 'buy_price': price}}

        # 初始资金
        initial_capital = 1000000
        available_cash = initial_capital

        # 遍历每个交易日
        for i, trade_date in enumerate(trading_days):
            # 1. 卖出到期持仓
            sell_value = 0
            stocks_to_sell = []

            for ts_code, pos in list(positions.items()):
                buy_date = pos['buy_date']
                buy_date_idx = trading_days.index(buy_date)
                current_date_idx = i

                # 检查是否持有足够天数
                if current_date_idx - buy_date_idx >= self.hold_days:
                    price_key_str = (ts_code, str(trade_date))
                    if price_key_str in price_index:
                        close_price = price_index[price_key_str]['close']
                        gross_value = pos['shares'] * close_price
                        net_value = gross_value * (1 - self.total_cost)

                        sell_value += net_value
                        available_cash += net_value  # 现金增加
                        stocks_to_sell.append(ts_code)

                        trade_records.append({
                            'trade_date': trade_date,
                            'ts_code': ts_code,
                            'action': 'SELL',
                            'price': close_price,
                            'shares': pos['shares'],
                            'gross_value': gross_value,
                            'net_value': net_value,
                            'return': (net_value / (pos['shares'] * pos['buy_price']) - 1) if pos['buy_price'] > 0 else 0
                        })

            # 移除已卖出的持仓
            for ts_code in stocks_to_sell:
                del positions[ts_code]

            # 2. 买入新信号（在再平衡日）
            # 获取当日因子数据
            factor_today = factor_df[factor_df['trade_date'].astype(str) == trade_date].copy()

            if len(factor_today) > 0:
                # 流动性筛选（使用成交量作为代理）
                vol_mean = factor_today['bias1_qfq'].mean() if len(factor_today) > 0 else 0
                # 这里简化处理，实际应该用成交量数据

                # 按bias1_qfq因子值排序，选择前20%（多头组）
                factor_today = factor_today.sort_values('bias1_qfq', ascending=False)
                n_select = max(1, int(len(factor_today) * 0.2))  # 前20%
                selected_stocks = factor_today.head(n_select)['ts_code'].tolist()

                # 等权重配置
                if len(selected_stocks) > 0:
                    # 使用可用现金进行买入，而不是仅使用卖出所得
                    cash_per_stock = available_cash / len(selected_stocks) if available_cash > 0 else 0

                    for ts_code in selected_stocks:
                        price_key = (ts_code, str(trade_date))
                        if price_key in price_index:
                            open_price = price_index[price_key]['open']

                            if open_price > 0 and cash_per_stock > 0:
                                shares = int(cash_per_stock / open_price)
                                if shares > 0:
                                    positions[ts_code] = {
                                        'shares': shares,
                                        'buy_date': trade_date,
                                        'buy_price': open_price
                                    }

                                    # 扣除买入成本
                                    cost = shares * open_price * (1 - self.total_cost)
                                    available_cash -= cost

                                    trade_records.append({
                                        'trade_date': trade_date,
                                        'ts_code': ts_code,
                                        'action': 'BUY',
                                        'price': open_price,
                                        'shares': shares,
                                        'gross_value': shares * open_price,
                                        'net_value': cost,
                                        'return': 0
                                    })

            # 3. 计算当日总价值（持仓价值 + 现金）
            holdings_value = 0
            for ts_code, pos in positions.items():
                price_key = (ts_code, str(trade_date))
                if price_key in price_index:
                    close_price = price_index[price_key]['close']
                    holdings_value += pos['shares'] * close_price

            daily_value = holdings_value + available_cash

            # 4. 计算当日收益
            if i > 0:
                prev_value = portfolio_records[-1]['portfolio_value']
                daily_return = (daily_value - prev_value) / prev_value if prev_value > 0 else 0
            else:
                daily_return = 0

            portfolio_records.append({
                'date': trade_date,
                'portfolio_value': daily_value,
                'portfolio_return': daily_return,
                'position_count': len(positions)
            })

            # 5. 基准收益
            if trade_date in index_index and i > 0:
                prev_date = trading_days[i-1]
                if prev_date in index_index:
                    today_close = index_index[trade_date]
                    prev_close = index_index[prev_date]
                    if prev_close > 0:
                        benchmark_return = (today_close - prev_close) / prev_close
                        benchmark_records.append({
                            'date': trade_date,
                            'benchmark_return': benchmark_return
                        })

            # 日志输出
            if (i + 1) % 20 == 0 or i == len(trading_days) - 1:
                logger.info(f"进度: {i+1}/{len(trading_days)} | 日期: {trade_date} | 持仓: {len(positions)} | 资产: {daily_value:,.0f}")

        # 转换为DataFrame
        portfolio_df = pd.DataFrame(portfolio_records)
        benchmark_df = pd.DataFrame(benchmark_records)

        # 计算累计收益
        portfolio_df['cumulative_return'] = (1 + portfolio_df['portfolio_return']).cumprod()
        benchmark_df['cumulative_return'] = (1 + benchmark_df['benchmark_return']).cumprod()

        # 合并结果
        result_df = portfolio_df.merge(
            benchmark_df,
            on='date',
            how='left',
            suffixes=('_portfolio', '_benchmark')
        )

        # 填充基准收益
        result_df['benchmark_return'] = result_df['benchmark_return'].fillna(0)
        result_df['cumulative_benchmark'] = result_df['cumulative_return_benchmark'].ffill()
        if len(result_df) > 0 and result_df['cumulative_benchmark'].iloc[0] != 1.0:
            result_df.loc[result_df.index[0], 'cumulative_benchmark'] = 1.0

        # 重命名投资组合累计收益列，方便后续使用
        result_df['cumulative_return'] = result_df['cumulative_return_portfolio']

        # 保存交易记录
        self.trade_records = pd.DataFrame(trade_records) if trade_records else pd.DataFrame()

        logger.info(f"\n回测完成，交易日数: {len(result_df)}")

        return result_df

    def calculate_performance_metrics(self, result_df: pd.DataFrame) -> Dict[str, float]:
        """
        计算绩效指标

        Args:
            result_df: 回测结果

        Returns:
            绩效指标字典
        """
        logger.info("\n" + "=" * 60)
        logger.info("阶段3: 计算绩效指标")
        logger.info("=" * 60)

        if len(result_df) == 0:
            raise ValueError("回测结果为空")

        # 基础收益率
        total_return = result_df['cumulative_return'].iloc[-1] - 1
        benchmark_return = result_df['cumulative_benchmark'].iloc[-1] - 1
        excess_return = total_return - benchmark_return

        # 年化收益率
        days = len(result_df)
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
        annual_benchmark = (1 + benchmark_return) ** (252 / days) - 1 if days > 0 else 0

        # 波动率
        returns = result_df['portfolio_return'].dropna()
        volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0

        # 夏普比率 (假设无风险利率为2%)
        risk_free_rate = 0.02
        sharpe = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0

        # 最大回撤
        cumulative = result_df['cumulative_return']
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # 胜率
        win_rate = (returns > 0).mean() if len(returns) > 0 else 0

        # 信息比率
        excess_returns = result_df['portfolio_return'] - result_df['benchmark_return']
        tracking_error = excess_returns.std() * np.sqrt(252) if len(excess_returns) > 0 else 0
        info_ratio = (annual_return - annual_benchmark) / tracking_error if tracking_error > 0 else 0

        # Calmar比率
        calmar = annual_return / abs(max_drawdown) if max_drawdown < 0 else 0

        # 换手率（估算）
        turnover = self.calculate_turnover_estimate()

        metrics = {
            '累计收益率': total_return,
            '年化收益率': annual_return,
            '基准年化收益': annual_benchmark,
            '超额收益': excess_return,
            '年化波动率': volatility,
            '夏普比率': sharpe,
            '最大回撤': max_drawdown,
            'Calmar比率': calmar,
            '信息比率': info_ratio,
            '胜率': win_rate,
            '换手率(估算)': turnover,
        }

        logger.info("\n绩效指标:")
        for key, value in metrics.items():
            logger.info(f"  {key}: {value:.4f}")

        return metrics

    def calculate_turnover_estimate(self) -> float:
        """
        估算换手率

        Returns:
            换手率
        """
        if not hasattr(self, 'trade_records') or len(self.trade_records) == 0:
            return 0.0

        # 计算总买入金额
        buy_trades = self.trade_records[self.trade_records['action'] == 'BUY']
        if len(buy_trades) == 0:
            return 0.0

        total_buy = buy_trades['net_value'].sum()

        # 计算平均持仓价值（估算）
        avg_position = total_buy / max(len(buy_trades), 1)

        # 换手率 = 买入金额 / 平均持仓
        turnover = total_buy / (avg_position * len(buy_trades)) if avg_position > 0 else 0

        return turnover

    def calculate_group_returns(self, factor_df: pd.DataFrame, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算分组收益（用于验证因子有效性）

        Args:
            factor_df: 因子数据
            price_df: 价格数据

        Returns:
            分组收益 DataFrame
        """
        logger.info("\n计算分组收益...")

        # 准备价格索引
        price_df['trade_date_str'] = price_df['trade_date'].astype(str)
        price_index = price_df.set_index(['ts_code', 'trade_date_str'])['close'].to_dict()

        # 获取交易日
        trading_days = sorted(factor_df['trade_date'].unique().astype(str))

        group_records = []

        for trade_date in trading_days:
            # 获取当日因子数据
            factor_today = factor_df[factor_df['trade_date'].astype(str) == trade_date].copy()

            if len(factor_today) < 10:  # 股票数太少
                continue

            # 分组
            factor_today['group'] = pd.qcut(factor_today['bias1_qfq'], self.n_groups, labels=False, duplicates='drop')

            # 计算下一期收益（T+1到T+20）
            current_idx = trading_days.index(trade_date)
            next_idx = min(current_idx + self.hold_days, len(trading_days) - 1)
            next_date = trading_days[next_idx]

            for group in range(self.n_groups):
                group_stocks = factor_today[factor_today['group'] == group]['ts_code'].tolist()

                if len(group_stocks) == 0:
                    continue

                # 计算组内平均收益
                group_returns = []
                for ts_code in group_stocks:
                    price_key_current = (ts_code, trade_date)
                    price_key_next = (ts_code, next_date)

                    if price_key_current in price_index and price_key_next in price_index:
                        price_current = price_index[price_key_current]
                        price_next = price_index[price_key_next]

                        if price_current > 0:
                            ret = (price_next - price_current) / price_current
                            group_returns.append(ret)

                if group_returns:
                    avg_return = np.mean(group_returns)
                    group_records.append({
                        'date': trade_date,
                        'group': group,
                        'return': avg_return
                    })

        if not group_records:
            return pd.DataFrame()

        group_df = pd.DataFrame(group_records)

        # 计算各组平均收益
        group_summary = group_df.groupby('group')['return'].agg(['mean', 'std', 'count']).reset_index()

        logger.info("\n分组收益统计:")
        for _, row in group_summary.iterrows():
            logger.info(f"  组{int(row['group'])}: 均值={row['mean']:.4f}, 标准差={row['std']:.4f}, 样本={int(row['count'])}")

        return group_df

    def run(self) -> Dict:
        """
        运行完整回测流程

        Returns:
            回测结果字典
        """
        try:
            # 1. 提取因子数据
            factor_df = self.extract_bias1_qfq_factor()

            # 2. 获取股票列表并加载价格数据
            stocks = factor_df['ts_code'].unique().tolist()
            price_df = self.load_market_data(stocks)

            # 3. 加载指数数据
            index_df = self.load_index_data()

            # 4. 运行回测
            result_df = self.run_backtest(factor_df, price_df, index_df)

            # 5. 计算绩效指标
            metrics = self.calculate_performance_metrics(result_df)

            # 6. 计算分组收益（可选）
            try:
                group_df = self.calculate_group_returns(factor_df, price_df)
            except Exception as e:
                logger.warning(f"分组收益计算失败: {e}")
                group_df = pd.DataFrame()

            return {
                'result_df': result_df,
                'metrics': metrics,
                'factor_df': factor_df,
                'group_df': group_df,
                'trade_records': self.trade_records if hasattr(self, 'trade_records') else pd.DataFrame()
            }

        except Exception as e:
            logger.error(f"回测失败: {e}")
            raise


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Bias1 Qfq 单因子回测系统")
    print("=" * 80)

    # 参数解析
    parser = argparse.ArgumentParser(description='Bias1 Qfq 因子回测')
    parser.add_argument('--start_date', type=str, default='20240101', help='回测开始日期')
    parser.add_argument('--end_date', type=str, default='20241231', help='回测结束日期')
    parser.add_argument('--hold_days', type=int, default=20, help='持有天数')
    parser.add_argument('--n_groups', type=int, default=5, help='分组数量')
    parser.add_argument('--output_dir', type=str, default='/home/zcy/alpha因子库/results/bias1_qfq', help='输出目录')

    args = parser.parse_args()

    # 创建回测器
    backtest = Bias1QfqBacktest(
        start_date=args.start_date,
        end_date=args.end_date,
        hold_days=args.hold_days,
        n_groups=args.n_groups
    )

    # 运行回测
    results = backtest.run()

    # 保存结果
    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 保存回测结果
    result_file = f"{args.output_dir}/bias1_qfq_performance_{args.start_date}_{args.end_date}_{timestamp}.csv"
    results['result_df'].to_csv(result_file, index=False, encoding='utf-8-sig')
    logger.info(f"\n回测结果已保存: {result_file}")

    # 保存绩效指标
    metrics_df = pd.DataFrame([results['metrics']])
    metrics_file = f"{args.output_dir}/bias1_qfq_metrics_{args.start_date}_{args.end_date}_{timestamp}.csv"
    metrics_df.to_csv(metrics_file, index=False, encoding='utf-8-sig')
    logger.info(f"绩效指标已保存: {metrics_file}")

    # 保存因子数据
    factor_file = f"{args.output_dir}/bias1_qfq_factor_{args.start_date}_{args.end_date}_{timestamp}.csv"
    results['factor_df'].to_csv(factor_file, index=False, encoding='utf-8-sig')
    logger.info(f"因子数据已保存: {factor_file}")

    # 保存分组收益（如果有）
    if len(results['group_df']) > 0:
        group_file = f"{args.output_dir}/bias1_qfq_groups_{args.start_date}_{args.end_date}_{timestamp}.csv"
        results['group_df'].to_csv(group_file, index=False, encoding='utf-8-sig')
        logger.info(f"分组收益已保存: {group_file}")

    # 保存交易记录（如果有）
    if len(results['trade_records']) > 0:
        trade_file = f"{args.output_dir}/bias1_qfq_trades_{args.start_date}_{args.end_date}_{timestamp}.csv"
        results['trade_records'].to_csv(trade_file, index=False, encoding='utf-8-sig')
        logger.info(f"交易记录已保存: {trade_file}")

    # 打印总结
    print("\n" + "=" * 80)
    print("回测完成！")
    print("=" * 80)
    print(f"\n参数:")
    print(f"  时间范围: {args.start_date} ~ {args.end_date}")
    print(f"  持有天数: {args.hold_days}")
    print(f"  分组数量: {args.n_groups}")
    print(f"\n绩效指标:")
    for key, value in results['metrics'].items():
        print(f"  {key}: {value:.4f}")
    print(f"\n结果文件:")
    print(f"  - 回测数据: {result_file}")
    print(f"  - 绩效指标: {metrics_file}")
    print(f"  - 因子数据: {factor_file}")
    if len(results['group_df']) > 0:
        print(f"  - 分组收益: {group_file}")
    if len(results['trade_records']) > 0:
        print(f"  - 交易记录: {trade_file}")


if __name__ == "__main__":
    main()
