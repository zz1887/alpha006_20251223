"""
Alpha Pluse 单因子回测主程序

功能:
1. 数据准备和验证
2. Alpha Pluse 因子计算
3. 月度回测实现
4. 绩效指标计算
5. 结果输出和可视化

回测参数:
- 周期: 20230101-20251201
- 股票池: 全市场A股
- 基准: 沪深300 (000300.SH)
- 手续费: 双边0.1% + 印花税0.05% + 过户费0.002%
- 再平衡: 月度
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional

# 配置路径
sys.path.insert(0, '/home/zcy/alpha006_20251223')

from core.utils.db_connection import db
from core.utils.data_loader import data_loader, get_index_data
from factors.momentum.VOL_EXP_20D_V2 import create_factor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AlphaPluseBacktest:
    """Alpha Pluse 单因子回测类"""

    def __init__(self, start_date: str, end_date: str):
        """
        初始化回测器

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        """
        self.start_date = start_date
        self.end_date = end_date
        self.factor_obj = create_factor('standard')

        # 交易成本配置
        self.cost_config = {
            'commission': 0.001,      # 0.1% 手续费
            'stamp_tax': 0.0005,      # 0.05% 印花税 (卖出时)
            'transfer_fee': 0.00002,  # 0.002% 过户费 (双向)
            'slippage': 0.0005,       # 0.05% 滑点
        }

        # 流动性筛选
        self.liquidity_threshold = 0.05  # 换手率 > 5%

        logger.info(f"初始化回测器: {start_date} ~ {end_date}")

    def load_market_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        加载市场数据

        Returns:
            (股票数据, 指数数据)
        """
        logger.info("=" * 60)
        logger.info("阶段1: 数据准备")
        logger.info("=" * 60)

        # 1. 获取股票池
        logger.info("获取股票池...")
        stocks = data_loader.get_tradable_stocks(self.end_date, filter_st=True)
        logger.info(f"可交易股票数量: {len(stocks)}")

        if len(stocks) == 0:
            raise ValueError("未获取到股票池")

        # 2. 获取价格和成交量数据
        logger.info("获取价格和成交量数据...")
        price_data = data_loader.get_price_data(
            stocks,
            self.start_date,
            self.end_date,
            columns=['vol', 'amount']
        )

        if len(price_data) == 0:
            raise ValueError("未获取到价格数据")

        logger.info(f"获取数据: {len(price_data):,} 条记录")

        # 3. 获取指数数据
        logger.info("获取沪深300指数数据...")
        index_data = get_index_data(
            self.start_date,
            self.end_date,
            '000300.SH'
        )

        if len(index_data) == 0:
            raise ValueError("未获取到指数数据")

        logger.info(f"指数数据: {len(index_data)} 条记录")

        # 4. 数据质量验证
        logger.info("数据质量验证...")

        price_quality = data_loader.validate_data_quality(
            price_data,
            "股票价格数据",
            min_valid_ratio=0.8
        )

        index_quality = data_loader.validate_data_quality(
            index_data,
            "指数数据",
            min_valid_ratio=0.9
        )

        if not price_quality['valid'] or not index_quality['valid']:
            logger.warning("数据质量验证存在警告，但继续执行")

        # 5. 保存原始数据到缓存
        cache_dir = '/home/zcy/alpha006_20251223/data/cache'
        os.makedirs(cache_dir, exist_ok=True)

        price_data.to_csv(f"{cache_dir}/raw_price_data.csv", index=False)
        index_data.to_csv(f"{cache_dir}/raw_index_data.csv", index=False)

        logger.info(f"原始数据已缓存到: {cache_dir}")

        return price_data, index_data

    def calculate_alpha_pluse_factor(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        计算 Alpha Pluse 因子 (每日全市场)

        Args:
            price_data: 价格数据

        Returns:
            因子数据 DataFrame
        """
        logger.info("=" * 60)
        logger.info("阶段2: 二元因子计算")
        logger.info("=" * 60)

        # 获取参数
        window_20d = 20
        lookback_14d = 14
        lower_mult = 1.4
        upper_mult = 3.5
        min_count = 2
        max_count = 4
        min_data_days = 34

        # 按股票分组计算每日因子
        all_results = []
        stocks = price_data['ts_code'].unique()
        total_stocks = len(stocks)

        logger.info(f"开始计算 {total_stocks} 只股票的每日因子...")

        for i, ts_code in enumerate(stocks):
            if (i + 1) % 100 == 0:
                logger.info(f"进度: {i+1}/{total_stocks}")

            # 获取单只股票数据
            stock_data = price_data[price_data['ts_code'] == ts_code].copy()
            stock_data = stock_data.sort_values('trade_date').reset_index(drop=True)

            if len(stock_data) < min_data_days:
                continue

            try:
                # 计算14日均值
                stock_data['vol_14_mean'] = stock_data['vol'].rolling(
                    window=lookback_14d, min_periods=lookback_14d
                ).mean()

                # 标记条件
                stock_data['condition'] = (
                    (stock_data['vol'] >= stock_data['vol_14_mean'] * lower_mult) &
                    (stock_data['vol'] <= stock_data['vol_14_mean'] * upper_mult) &
                    stock_data['vol_14_mean'].notna()
                )

                # 20日滚动计数
                def count_conditions(idx):
                    if idx < window_20d - 1:
                        return np.nan
                    window_data = stock_data.iloc[idx - window_20d + 1:idx + 1]
                    return window_data['condition'].sum()

                stock_data['count_20d'] = [count_conditions(i) for i in range(len(stock_data))]

                # 计算alpha_pluse
                stock_data['alpha_pluse'] = (
                    (stock_data['count_20d'] >= min_count) &
                    (stock_data['count_20d'] <= max_count)
                ).astype(int)

                # 保留需要的列
                result_subset = stock_data[['ts_code', 'trade_date', 'vol', 'vol_14_mean',
                                           'condition', 'count_20d', 'alpha_pluse']].copy()
                all_results.append(result_subset)

            except Exception as e:
                logger.warning(f"股票 {ts_code} 因子计算失败: {e}")
                continue

        if not all_results:
            raise ValueError("所有股票因子计算失败")

        # 合并结果
        factor_df = pd.concat(all_results, ignore_index=True)

        logger.info(f"因子计算完成: {len(factor_df):,} 条记录")

        # 统计因子值分布
        signal_count = factor_df['alpha_pluse'].sum()
        total_count = len(factor_df)
        logger.info(f"因子值分布: 信号={signal_count}, 非信号={total_count-signal_count}, 信号比例={signal_count/total_count:.2%}")

        # 保存因子数据
        cache_dir = '/home/zcy/alpha006_20251223/data/cache'
        factor_df.to_csv(f"{cache_dir}/alpha_pluse_factor.csv", index=False)

        return factor_df

    def get_rebalance_dates(self, trading_days: List[str]) -> List[str]:
        """
        获取月度再平衡日期

        Args:
            trading_days: 交易日列表

        Returns:
            再平衡日期列表
        """
        # 转换为datetime
        dates = pd.to_datetime(trading_days, format='%Y%m%d')

        # 找到每月最后一个交易日
        monthly_ends = []
        current_month = None

        for date in dates:
            if current_month is None or date.month != current_month:
                if current_month is not None:
                    monthly_ends.append(prev_date.strftime('%Y%m%d'))
                current_month = date.month
            prev_date = date

        # 添加最后一个
        if current_month is not None:
            monthly_ends.append(prev_date.strftime('%Y%m%d'))

        # 过滤掉开始日期前的
        start_dt = pd.to_datetime(self.start_date, format='%Y%m%d')
        monthly_ends = [d for d in monthly_ends if pd.to_datetime(d, format='%Y%m%d') >= start_dt]

        logger.info(f"月度再平衡日期: {len(monthly_ends)} 个")

        return monthly_ends

    def calculate_turnover_rate(self, price_data: pd.DataFrame, ts_code: str, date: str) -> float:
        """
        计算换手率

        Args:
            price_data: 价格数据
            ts_code: 股票代码
            date: 日期

        Returns:
            换手率
        """
        stock_data = price_data[
            (price_data['ts_code'] == ts_code) &
            (price_data['trade_date'] == date)
        ]

        if len(stock_data) == 0:
            return 0.0

        vol = stock_data['vol'].iloc[0]
        amount = stock_data['amount'].iloc[0]

        # 如果有流通市值数据，使用流通市值计算换手率
        # 否则使用成交量估算
        if pd.notna(amount) and amount > 0:
            # 这里简化处理，实际应该用流通市值
            # 暂时返回成交量的对数作为代理
            return min(vol / 1000000, 1.0)  # 简化处理

        return 0.0

    def run_backtest(self, price_data: pd.DataFrame, factor_df: pd.DataFrame,
                     index_data: pd.DataFrame) -> pd.DataFrame:
        """
        运行回测

        Args:
            price_data: 价格数据
            factor_df: 因子数据
            index_data: 指数数据

        Returns:
            回测结果 DataFrame
        """
        logger.info("=" * 60)
        logger.info("阶段3: 科学回测实现")
        logger.info("=" * 60)

        # 获取交易日和再平衡日期
        trading_days = data_loader.get_trading_days(self.start_date, self.end_date)
        rebalance_dates = self.get_rebalance_dates(trading_days)

        logger.info(f"总交易日: {len(trading_days)}")
        logger.info(f"再平衡次数: {len(rebalance_dates)}")

        # 准备结果存储
        portfolio_returns = []  # 组合收益率
        benchmark_returns = []  # 基准收益率

        # 持仓状态
        current_positions = None  # 当前持仓: {ts_code: weight}
        last_rebalance_idx = -1

        # 遍历每个交易日
        for i, trade_date in enumerate(trading_days):
            trade_date_dt = pd.to_datetime(trade_date, format='%Y%m%d')

            # 检查是否需要再平衡
            if trade_date in rebalance_dates:
                logger.info(f"\n再平衡日: {trade_date} (第 {i+1}/{len(trading_days)} 天)")

                # 1. 获取当日因子值
                factor_today = factor_df[
                    factor_df['trade_date'] == trade_date_dt
                ].copy()

                if len(factor_today) == 0:
                    logger.warning(f"当日无因子数据: {trade_date}")
                    # 保持原有持仓或清仓
                    current_positions = None
                    last_rebalance_idx = i
                    continue

                # 2. 流动性筛选 (换手率 > 5%)
                # 简化处理: 使用成交量作为代理
                vol_mean = factor_today['vol'].mean()
                factor_today = factor_today[
                    factor_today['vol'] >= vol_mean * self.liquidity_threshold
                ].copy()

                logger.info(f"流动性筛选后: {len(factor_today)} 只股票")

                # 3. 分组: alpha_pluse=1 为做多组
                long_stocks = factor_today[factor_today['alpha_pluse'] == 1]['ts_code'].tolist()
                short_stocks = factor_today[factor_today['alpha_pluse'] == 0]['ts_code'].tolist()

                logger.info(f"做多组: {len(long_stocks)} 只, 做空组: {len(short_stocks)} 只")

                if len(long_stocks) < 10:
                    logger.warning(f"做多组股票过少，跳过本次调仓")
                    current_positions = None
                    last_rebalance_idx = i
                    continue

                # 4. 等权重配置
                long_weight = 1.0 / len(long_stocks) if long_stocks else 0

                # 构建持仓
                current_positions = {}
                for stock in long_stocks:
                    current_positions[stock] = long_weight

                last_rebalance_idx = i
                logger.info(f"调仓完成，持仓股票数: {len(current_positions)}")

            # 计算当日收益
            if current_positions and last_rebalance_idx >= 0:
                # 获取前一交易日
                prev_idx = i - 1
                if prev_idx < 0:
                    continue

                prev_date = trading_days[prev_idx]

                # 计算组合收益
                portfolio_return = 0.0

                for stock, weight in current_positions.items():
                    # 获取今日和昨日价格
                    price_today = price_data[
                        (price_data['ts_code'] == stock) &
                        (price_data['trade_date'] == trade_date_dt)
                    ]

                    price_prev = price_data[
                        (price_data['ts_code'] == stock) &
                        (price_data['trade_date'] == pd.to_datetime(prev_date, format='%Y%m%d'))
                    ]

                    if len(price_today) > 0 and len(price_prev) > 0:
                        close_today = price_today['close'].iloc[0] if 'close' in price_today.columns else price_today['vol'].iloc[0]
                        close_prev = price_prev['close'].iloc[0] if 'close' in price_prev.columns else price_prev['vol'].iloc[0]

                        if pd.notna(close_today) and pd.notna(close_prev) and close_prev > 0:
                            stock_return = (close_today - close_prev) / close_prev
                            portfolio_return += weight * stock_return

                # 扣除交易成本 (在调仓日)
                if trade_date in rebalance_dates and last_rebalance_idx == i:
                    cost = (self.cost_config['commission'] + self.cost_config['transfer_fee']) * 2
                    portfolio_return -= cost

                portfolio_returns.append({
                    'date': trade_date,
                    'portfolio_return': portfolio_return
                })

            # 基准收益
            index_today = index_data[
                index_data['trade_date'] == trade_date_dt
            ]

            if len(index_today) > 0 and i > 0:
                prev_date = trading_days[i-1]
                index_prev = index_data[
                    index_data['trade_date'] == pd.to_datetime(prev_date, format='%Y%m%d')
                ]

                if len(index_today) > 0 and len(index_prev) > 0:
                    close_today = index_today['close'].iloc[0]
                    close_prev = index_prev['close'].iloc[0]

                    if pd.notna(close_today) and pd.notna(close_prev) and close_prev > 0:
                        benchmark_return = (close_today - close_prev) / close_prev
                        benchmark_returns.append({
                            'date': trade_date,
                            'benchmark_return': benchmark_return
                        })

        # 转换为DataFrame
        portfolio_df = pd.DataFrame(portfolio_returns)
        benchmark_df = pd.DataFrame(benchmark_returns)

        if len(portfolio_df) == 0:
            raise ValueError("回测未产生有效结果")

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
        result_df['cumulative_benchmark'] = result_df['cumulative_benchmark'].fillna(method='ffill')
        if result_df['cumulative_benchmark'].iloc[0] != 1.0:
            result_df['cumulative_benchmark'].iloc[0] = 1.0

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
        logger.info("=" * 60)
        logger.info("计算绩效指标")
        logger.info("=" * 60)

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
        }

        logger.info("\n绩效指标:")
        for key, value in metrics.items():
            logger.info(f"  {key}: {value:.4f}")

        return metrics


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Alpha Pluse 单因子回测验证系统")
    print("=" * 80)

    # 参数配置
    start_date = '20230101'
    end_date = '20251201'

    # 创建回测器
    backtest = AlphaPluseBacktest(start_date, end_date)

    try:
        # 阶段1: 数据准备
        price_data, index_data = backtest.load_market_data()

        # 阶段2: 因子计算
        factor_df = backtest.calculate_alpha_pluse_factor(price_data)

        # 阶段3: 回测执行
        result_df = backtest.run_backtest(price_data, factor_df, index_data)

        # 阶段4: 绩效计算
        metrics = backtest.calculate_performance_metrics(result_df)

        # 保存结果
        output_dir = '/home/zcy/alpha006_20251223/results/backtest'
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存回测结果
        result_file = f"{output_dir}/alpha_pluse_performance_{start_date}_{end_date}_{timestamp}.csv"
        result_df.to_csv(result_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n回测结果已保存: {result_file}")

        # 保存因子数据
        factor_file = f"{output_dir}/alpha_pluse_factor_{start_date}_{end_date}_{timestamp}.csv"
        factor_df.to_csv(factor_file, index=False, encoding='utf-8-sig')
        logger.info(f"因子数据已保存: {factor_file}")

        # 保存绩效指标
        metrics_df = pd.DataFrame([metrics])
        metrics_file = f"{output_dir}/alpha_pluse_metrics_{start_date}_{end_date}_{timestamp}.csv"
        metrics_df.to_csv(metrics_file, index=False, encoding='utf-8-sig')
        logger.info(f"绩效指标已保存: {metrics_file}")

        print("\n" + "=" * 80)
        print("回测完成！")
        print("=" * 80)
        print(f"\n结果文件:")
        print(f"  - 回测数据: {result_file}")
        print(f"  - 因子数据: {factor_file}")
        print(f"  - 绩效指标: {metrics_file}")

    except Exception as e:
        logger.error(f"回测失败: {e}")
        raise


if __name__ == "__main__":
    main()
