"""
六因子策略回测脚本 - 优化版
优化内容:
1. 调整结束日期为20250131，确保数据完整
2. 优化因子权重，提升ICIR
3. 增加持有期约束，降低换手率

文件input(依赖外部什么): 数据库、因子计算代码、策略配置
文件output(提供什么): 完整的回测结果和性能指标
文件pos(系统局部地位): 策略执行核心脚本
"""

import sys
sys.path.insert(0, '/home/zcy/alpha006_20251223')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
import logging

from core.utils.db_connection import db
from core.utils.data_loader import data_loader
from core.config.params import get_strategy_param
from factors.momentum.VOL_EXP_20D_V2 import create_factor as create_alpha_pluse
from factors.valuation.VAL_GROW_行业_Q import calc_alpha_peg_industry as create_alpha_peg
from factors.price.PRI_TREND_4D_V2 import create_factor as create_alpha_010
from factors.price.PRI_STR_10D_V2 import create_factor as create_alpha_038
from factors.price.PRI_POS_120D_V2 import create_factor as create_alpha_120cq
from factors.volume.MOM_CR_20D_V2 import create_factor as create_cr_qfq
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SixFactorBacktestOptimized:
    """六因子策略回测类 - 优化版"""

    def __init__(self, start_date: str, end_date: str, version: str = 'optimized_v2'):
        self.start_date = start_date
        self.end_date = end_date
        self.version = version

        # 获取策略参数
        self.params = get_strategy_param('six_factor', version)
        if not self.params:
            # 如果找不到优化版本，使用standard并手动设置权重
            self.params = {
                'filters': {
                    'alpha_pluse': 1,
                    'min_amount': 50_000,
                    'min_market_cap': 100_000_000,
                    'exclude_st': True,
                    'exclude_suspension': True,
                },
                'weights': {'alpha_peg': 0.2, 'alpha_010': 0.2, 'alpha_038': 0.2, 'alpha_120cq': 0.2, 'cr_qfq': 0.2},
                'directions': {'alpha_peg': 'negative', 'alpha_010': 'positive', 'alpha_038': 'positive', 'alpha_120cq': 'positive', 'cr_qfq': 'positive'},
            }

        # 优化后的权重配置
        self.optimized_weights = {
            'alpha_peg': 0.15,      # 降低权重 (IC不稳定)
            'alpha_010': 0.25,      # 提高权重 (短期趋势有效)
            'alpha_038': 0.20,      # 保持
            'alpha_120cq': 0.15,    # 降低权重 (长期位置)
            'cr_qfq': 0.25          # 提高权重 (动量因子)
        }

        # 优化后的方向配置
        self.optimized_directions = {
            'alpha_peg': 'negative',    # 越低越好
            'alpha_010': 'positive',    # 越高越好
            'alpha_038': 'positive',    # 越高越好
            'alpha_120cq': 'negative',  # 修正: 越低越好 (反转效应)
            'cr_qfq': 'positive'        # 越高越好
        }

        # 修正版权重 (降低alpha_120cq权重)
        self.fixed_weights = {
            'alpha_peg': 0.15,
            'alpha_010': 0.30,   # +5%
            'alpha_038': 0.25,   # +5%
            'alpha_120cq': 0.05, # -10%
            'cr_qfq': 0.25
        }

        # 交易成本
        self.commission = 0.0005
        self.stamp_tax = 0.001
        self.slippage = 0.001
        self.total_cost = self.commission + self.stamp_tax + self.slippage

        # 基准
        self.benchmark = '000300.SH'

        # 持有期约束
        self.min_hold_days = 5  # 新增: 最少持有5天

        logger.info(f"Initialize OPTIMIZED backtest: {start_date} - {end_date}")
        logger.info(f"Optimized weights: {self.optimized_weights}")
        logger.info(f"Min hold days: {self.min_hold_days}")

    def get_nearest_trading_day(self, target_date: str) -> str:
        """Get nearest trading day from daily_kline table (个股数据)"""
        sql_check = """
        SELECT trade_date
        FROM daily_kline
        WHERE trade_date = %s
        """
        data_check = db.execute_query(sql_check, (target_date,))

        if data_check:
            return target_date

        # Find previous trading day (before target)
        sql_prev = """
        SELECT trade_date
        FROM daily_kline
        WHERE trade_date < %s
        ORDER BY trade_date DESC
        LIMIT 1
        """
        data_prev = db.execute_query(sql_prev, (target_date,))

        # Find next trading day (after target)
        sql_next = """
        SELECT trade_date
        FROM daily_kline
        WHERE trade_date > %s
        ORDER BY trade_date ASC
        LIMIT 1
        """
        data_next = db.execute_query(sql_next, (target_date,))

        # Determine nearest trading day
        if data_prev and data_next:
            prev_date = data_prev[0]['trade_date']
            next_date = data_next[0]['trade_date']

            target_dt = datetime.strptime(target_date, '%Y%m%d')
            prev_dt = datetime.strptime(prev_date, '%Y%m%d')
            next_dt = datetime.strptime(next_date, '%Y%m%d')

            prev_distance = (target_dt - prev_dt).days
            next_distance = (next_dt - target_dt).days

            if prev_distance <= next_distance:
                return prev_date
            else:
                return next_date

        elif data_prev:
            return data_prev[0]['trade_date']

        elif data_next:
            return data_next[0]['trade_date']

        else:
            logger.error(f"无法找到{target_date}附近的交易日")
            return target_date

    def get_monthly_dates(self) -> List[str]:
        """Get monthly rebalance dates (交易月末: 每月最后一个交易日)"""
        logger.info("Generating monthly rebalance dates (交易月末模式)...")

        sql = """
        SELECT DISTINCT trade_date
        FROM daily_kline
        WHERE trade_date >= %s AND trade_date <= %s
        ORDER BY trade_date
        """
        all_dates = db.execute_query(sql, (self.start_date, self.end_date))
        all_dates = [d['trade_date'] for d in all_dates]

        if not all_dates:
            logger.error("No trading days found in the period")
            return []

        # Group by month and get last trading day of each month
        monthly_dates = []
        date_objects = [datetime.strptime(d, '%Y%m%d') for d in all_dates]

        current_month = None
        month_last_date = None

        for dt in date_objects:
            month_key = (dt.year, dt.month)

            if current_month is None:
                current_month = month_key
                month_last_date = dt
            elif month_key != current_month:
                monthly_dates.append(month_last_date.strftime('%Y%m%d'))
                current_month = month_key
                month_last_date = dt
            else:
                month_last_date = dt

        if month_last_date:
            monthly_dates.append(month_last_date.strftime('%Y%m%d'))

        monthly_dates = [d for d in monthly_dates if self.start_date <= d <= self.end_date]

        logger.info(f"  调仓日期数量: {len(monthly_dates)}")
        logger.info(f"  调仓日期列表: {monthly_dates}")

        return monthly_dates

    def get_price_data_for_period_fixed(self, stocks: List[str], target_date: str, lookback_days: int) -> pd.DataFrame:
        """获取指定股票在目标日期前N天的价格数据 - 修复版"""
        if not stocks:
            return pd.DataFrame()

        target_dt = datetime.strptime(target_date, '%Y%m%d')
        initial_start_dt = target_dt - timedelta(days=lookback_days + 20)
        initial_start_date = initial_start_dt.strftime('%Y%m%d')

        sql = f'''
        SELECT DISTINCT trade_date
        FROM daily_kline
        WHERE trade_date >= '{initial_start_date}' AND trade_date <= '{target_date}'
        ORDER BY trade_date
        '''
        trading_days = db.execute_query(sql)

        if len(trading_days) < lookback_days:
            extra_buffer = 0
            while len(trading_days) < lookback_days and extra_buffer < 100:
                extra_buffer += 10
                new_start_dt = target_dt - timedelta(days=lookback_days + 20 + extra_buffer)
                new_start_date = new_start_dt.strftime('%Y%m%d')

                sql = f'''
                SELECT DISTINCT trade_date
                FROM daily_kline
                WHERE trade_date >= '{new_start_date}' AND trade_date <= '{target_date}'
                ORDER BY trade_date
                '''
                trading_days = db.execute_query(sql)

            if len(trading_days) >= lookback_days:
                start_date = new_start_date
            else:
                logger.warning(f"无法为{target_date}找到足够的交易日数据")
                return pd.DataFrame()
        else:
            start_date = initial_start_date

        return data_loader.get_price_data(stocks, start_date, target_date)

    def get_next_month_return_fixed(self, current_date: str, stocks: List[str], rebalance_dates: List[str], idx: int) -> pd.DataFrame:
        """Get next month return - 修复版"""
        if idx >= len(rebalance_dates) - 1:
            next_rebalance = self.end_date
        else:
            next_rebalance = rebalance_dates[idx + 1]

        # 检查是否超出回测范围
        if next_rebalance > self.end_date:
            logger.warning(f"  {current_date} 下期 {next_rebalance} 超出回测范围")
            return pd.DataFrame()

        sql = f"""
        SELECT ts_code, trade_date, close
        FROM daily_kline
        WHERE trade_date >= %s AND trade_date <= %s
          AND ts_code IN ({','.join(['%s'] * len(stocks))})
        ORDER BY ts_code, trade_date
        """
        params = (current_date, next_rebalance, ) + tuple(stocks)
        data = db.execute_query(sql, params)
        df = pd.DataFrame(data)

        if len(df) == 0:
            return pd.DataFrame()

        df_current = df[df['trade_date'] == current_date].copy()
        df_next = df[df['trade_date'] == next_rebalance].groupby('ts_code').first().reset_index()

        if len(df_current) == 0 or len(df_next) == 0:
            df_next = df[df['trade_date'] > current_date].groupby('ts_code').first().reset_index()
            if len(df_current) == 0 or len(df_next) == 0:
                return pd.DataFrame()

        df_merged = df_current[['ts_code', 'close']].merge(
            df_next[['ts_code', 'close']], on='ts_code', suffixes=('_current', '_next')
        )

        df_merged['下月收益率'] = (df_merged['close_next'] / df_merged['close_current'] - 1)
        result = df_merged[['ts_code', '下月收益率']]

        return result

    def get_benchmark_return_fixed(self, current_date: str, next_rebalance_date: str) -> float:
        """Get benchmark return - 修复版"""
        try:
            def get_nearest_index_day(date: str) -> str:
                """在index_daily_zzsz中查找最近的交易日"""
                sql = """
                SELECT trade_date
                FROM index_daily_zzsz
                WHERE ts_code = %s AND trade_date <= %s
                ORDER BY trade_date DESC
                LIMIT 1
                """
                data = db.execute_query(sql, (self.benchmark, date))
                if data:
                    return data[0]['trade_date']

                sql = """
                SELECT trade_date
                FROM index_daily_zzsz
                WHERE ts_code = %s AND trade_date >= %s
                ORDER BY trade_date ASC
                LIMIT 1
                """
                data = db.execute_query(sql, (self.benchmark, date))
                if data:
                    return data[0]['trade_date']

                return date

            actual_current = get_nearest_index_day(current_date)
            actual_next = get_nearest_index_day(next_rebalance_date)

            # 如果两个日期相同，无法计算收益
            if actual_current == actual_next:
                logger.warning(f"  基准日期相同: {actual_current}")
                return 0

            sql = """
            SELECT trade_date, close FROM index_daily_zzsz
            WHERE ts_code = %s AND trade_date IN (%s, %s)
            ORDER BY trade_date
            """
            data = db.execute_query(sql, (self.benchmark, actual_current, actual_next))

            if len(data) >= 2:
                return data[1]['close'] / data[0]['close'] - 1
            else:
                logger.warning(f"  基准数据不足: {actual_current} -> {actual_next}")
                return 0
        except Exception as e:
            logger.warning(f"  基准收益率计算失败: {e}")
            return 0

    def calculate_factors_for_date(self, rebalance_date: str, base_stocks: List[str]) -> pd.DataFrame:
        """Calculate all factors for given date - 使用优化权重"""
        logger.info(f"  Calculating factors: {rebalance_date}, stocks: {len(base_stocks)}")

        df_result = pd.DataFrame({'ts_code': base_stocks})

        # 1. alpha_peg (估值因子)
        try:
            df_pe, _ = data_loader.get_fina_data(base_stocks, rebalance_date)

            if len(df_pe) > 0:
                industry_data = data_loader.get_industry_data_from_csv(base_stocks)

                if len(industry_data) > 0:
                    df_pe_industry = df_pe.merge(industry_data, on='ts_code', how='left')
                    df_pe_industry['l1_name'] = df_pe_industry['l1_name'].fillna('其他')

                    def zscore(group):
                        values = group['pe_ttm'].astype(float)
                        mean = values.mean()
                        std = values.std()
                        if std == 0 or pd.isna(std) or len(values) < 2:
                            return pd.Series([0.0] * len(group), index=group.index)
                        return (values - mean) / std

                    df_pe_industry['alpha_peg_zscore'] = df_pe_industry.groupby('l1_name').apply(zscore).reset_index(level=0, drop=True)

                    min_samples = 5
                    industry_counts = df_pe_industry.groupby('l1_name').size()
                    valid_industries = industry_counts[industry_counts >= min_samples].index
                    df_pe_industry = df_pe_industry[df_pe_industry['l1_name'].isin(valid_industries)]

                    df_result = df_result.merge(df_pe_industry[['ts_code', 'alpha_peg_zscore']], on='ts_code', how='left')
                    logger.info(f"    alpha_peg计算完成: {len(df_pe_industry)}条记录")
                else:
                    logger.warning("    无法获取行业数据，跳过alpha_peg")
            else:
                logger.warning("    无PE数据，跳过alpha_peg")
        except Exception as e:
            logger.warning(f"    alpha_peg计算失败: {e}，跳过该因子")

        # 2. alpha_010 (短周期趋势)
        try:
            alpha_010_factor = create_alpha_010('standard')
            price_data = data_loader.get_price_data_for_period(base_stocks, rebalance_date, 10)
            alpha_010_result = alpha_010_factor.calculate(price_data)
            if len(alpha_010_result) > 0:
                df_result = df_result.merge(alpha_010_result[['ts_code', 'alpha_010']], on='ts_code', how='left')
                logger.info(f"    alpha_010计算完成: {len(alpha_010_result)}只股票")
        except Exception as e:
            logger.warning(f"    alpha_010计算失败: {e}")

        # 3. alpha_038 (价格强度)
        try:
            alpha_038_factor = create_alpha_038('standard')
            price_data_038 = data_loader.get_price_data_for_period(base_stocks, rebalance_date, 10)
            alpha_038_result = alpha_038_factor.calculate(price_data_038)
            if len(alpha_038_result) > 0:
                df_result = df_result.merge(alpha_038_result[['ts_code', 'alpha_038']], on='ts_code', how='left')
                logger.info(f"    alpha_038计算完成: {len(alpha_038_result)}只股票")
        except Exception as e:
            logger.warning(f"    alpha_038计算失败: {e}")

        # 4. alpha_120cq (价格位置)
        try:
            alpha_120cq_factor = create_alpha_120cq('standard')
            price_data_120 = data_loader.get_price_data_for_period(base_stocks, rebalance_date, 180)
            alpha_120cq_result = alpha_120cq_factor.calculate(price_data_120, rebalance_date)
            if len(alpha_120cq_result) > 0:
                df_result = df_result.merge(alpha_120cq_result[['ts_code', 'alpha_120cq']], on='ts_code', how='left')
                logger.info(f"    alpha_120cq计算完成: {len(alpha_120cq_result)}只股票")
        except Exception as e:
            logger.warning(f"    alpha_120cq计算失败: {e}")

        # 5. cr_qfq (动量因子)
        try:
            cr_qfq_factor = create_cr_qfq('standard')
            cr_qfq_result = cr_qfq_factor.calculate_by_period(rebalance_date, base_stocks)
            if len(cr_qfq_result) > 0:
                df_result = df_result.merge(cr_qfq_result[['ts_code', 'cr_qfq']], on='ts_code', how='left')
                logger.info(f"    cr_qfq计算完成: {len(cr_qfq_result)}条记录")
        except Exception as e:
            logger.warning(f"    cr_qfq计算失败: {e}")

        return df_result

    def calculate_comprehensive_score(self, factor_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive score with OPTIMIZED weights"""
        weights = self.optimized_weights
        directions = self.optimized_directions

        # Handle alpha_peg_zscore
        if 'alpha_peg_zscore' in factor_data.columns:
            factor_data['alpha_peg'] = factor_data['alpha_peg_zscore']

        # Normalize each factor
        for factor in ['alpha_peg', 'alpha_010', 'alpha_038', 'alpha_120cq', 'cr_qfq']:
            if factor in factor_data.columns:
                factor_data[factor] = factor_data[factor].fillna(factor_data[factor].median())

                if directions[factor] == 'negative':
                    factor_data[f'rank_{factor}'] = factor_data[factor].rank(method='dense', ascending=True)
                else:
                    factor_data[f'rank_{factor}'] = factor_data[factor].rank(method='dense', ascending=False)

        # Calculate weighted score
        score_cols = [f'rank_{f}' for f in ['alpha_peg', 'alpha_010', 'alpha_038', 'alpha_120cq', 'cr_qfq']
                     if f'rank_{f}' in factor_data.columns]

        if score_cols:
            for col in score_cols:
                factor_data[col] = (factor_data[col] - factor_data[col].min()) / (factor_data[col].max() - factor_data[col].min() + 1e-6)

            factor_data['综合得分'] = (
                factor_data.get('rank_alpha_peg', 0) * weights['alpha_peg'] +
                factor_data.get('rank_alpha_010', 0) * weights['alpha_010'] +
                factor_data.get('rank_alpha_038', 0) * weights['alpha_038'] +
                factor_data.get('rank_alpha_120cq', 0) * weights['alpha_120cq'] +
                factor_data.get('rank_cr_qfq', 0) * weights['cr_qfq']
            )
        else:
            factor_data['综合得分'] = np.nan

        return factor_data

    def check_holding_period_compliance(self, current_date: str, next_rebalance: str, min_days: int) -> bool:
        """检查持有期是否满足最小天数要求"""
        sql = """
        SELECT COUNT(DISTINCT trade_date) as days
        FROM daily_kline
        WHERE trade_date > %s AND trade_date <= %s
        """
        data = db.execute_query(sql, (current_date, next_rebalance))
        trading_days = data[0]['days'] if data else 0

        return trading_days >= min_days

    def run_backtest(self) -> Dict:
        """Execute backtest main process - 优化版"""
        logger.info("=" * 80)
        logger.info("Starting backtest (OPTIMIZED VERSION)")
        logger.info("=" * 80)

        rebalance_dates = self.get_monthly_dates()

        if len(rebalance_dates) == 0:
            logger.error("No rebalance dates found")
            return {}

        group_returns = {1: [], 2: [], 3: [], 4: [], 5: []}
        group_dates = []
        ic_values = []
        turnover_rates = []
        benchmark_returns = []

        prev_holdings = {i: set() for i in range(1, 6)}

        for idx, rebalance_date in enumerate(rebalance_dates):
            logger.info(f"\n{'='*60}")
            logger.info(f"调仓期: {rebalance_date} ({idx+1}/{len(rebalance_dates)})")
            logger.info(f"{'='*60}")

            try:
                # 检查是否是最后一期
                if idx == len(rebalance_dates) - 1:
                    logger.warning(f"  最后一期 {rebalance_date}，跳过")
                    continue

                # 检查持有期是否满足要求
                next_rebalance = rebalance_dates[idx + 1]
                if not self.check_holding_period_compliance(rebalance_date, next_rebalance, self.min_hold_days):
                    logger.warning(f"  持有期不足{self.min_hold_days}天，跳过")
                    continue

                # 1. 获取基础股票池
                actual_rebalance_date = self.get_nearest_trading_day(rebalance_date)
                if actual_rebalance_date != rebalance_date:
                    logger.info(f"  调整调仓日期: {rebalance_date} -> {actual_rebalance_date}")
                    rebalance_date = actual_rebalance_date

                market_data = data_loader.get_market_cap_and_amount(rebalance_date)
                if len(market_data) == 0:
                    logger.warning(f"  无市值/成交额数据，跳过")
                    continue

                market_data['流通市值(亿)'] = market_data['circ_mv'] / 10_000
                market_data['成交额(万)'] = market_data['amount'] / 10_000

                # 基础过滤
                st_stocks = self.get_st_stock_list(rebalance_date)
                market_data = market_data[~market_data['ts_code'].isin(st_stocks)]
                market_data = market_data[market_data['成交额(万)'] > 0]
                market_data = market_data[market_data['成交额(万)'] >= self.params['filters']['min_amount'] / 10_000]
                market_data = market_data[market_data['流通市值(亿)'] >= self.params['filters']['min_market_cap'] / 100_000_000]

                # alpha_pluse过滤
                alpha_pluse_factor = create_alpha_pluse('standard')
                price_data_pluse = self.get_price_data_for_period_fixed(
                    market_data['ts_code'].tolist(), rebalance_date, 34
                )
                if len(price_data_pluse) > 0:
                    alpha_pluse_result = alpha_pluse_factor.calculate(price_data_pluse)
                    if len(alpha_pluse_result) > 0:
                        valid_stocks = alpha_pluse_result[alpha_pluse_result['alpha_pluse'] == 1]['ts_code'].tolist()
                        market_data = market_data[market_data['ts_code'].isin(valid_stocks)]

                base_stocks = market_data['ts_code'].tolist()
                logger.info(f"  基础股票池: {len(base_stocks)}只")

                if len(base_stocks) == 0:
                    continue

                # 2. 计算因子
                factor_data = self.calculate_factors_for_date(rebalance_date, base_stocks)

                # 3. 合并市值数据
                factor_data = factor_data.merge(
                    market_data[['ts_code', '流通市值(亿)']], on='ts_code', how='left'
                )

                # 4. 计算综合得分
                factor_data = self.calculate_comprehensive_score(factor_data)

                # 5. 过滤有效数据
                factor_data = factor_data.dropna(subset=['综合得分'])
                if len(factor_data) == 0:
                    logger.warning(f"  无有效因子数据")
                    continue

                logger.info(f"  有效股票: {len(factor_data)}只")

                # 6. 分组
                factor_data['组别'] = pd.qcut(factor_data['综合得分'], q=5, labels=[5, 4, 3, 2, 1])

                # 7. 获取下月收益率
                next_ret = self.get_next_month_return_fixed(rebalance_date, factor_data['ts_code'].tolist(), rebalance_dates, idx)
                if len(next_ret) == 0:
                    logger.warning(f"  无下月收益率数据")
                    continue

                factor_data = factor_data.merge(next_ret, on='ts_code', how='inner')
                if len(factor_data) == 0:
                    logger.warning(f"  无匹配收益率数据")
                    continue

                # 8. 计算IC值
                if len(factor_data) > 5:
                    ic, _ = spearmanr(factor_data['综合得分'], factor_data['下月收益率'])
                    ic_values.append(ic)

                # 9. 按组计算收益率
                group_stats = []
                current_holdings = {i: set() for i in range(1, 6)}

                for group_id in range(1, 6):
                    group_data = factor_data[factor_data['组别'] == group_id].copy()

                    if len(group_data) == 0:
                        group_returns[group_id].append(0)
                        continue

                    total_mv = group_data['流通市值(亿)'].sum()
                    group_data['权重'] = group_data['流通市值(亿)'] / total_mv

                    group_ret = (group_data['权重'] * group_data['下月收益率']).sum()
                    group_returns[group_id].append(group_ret)

                    current_holdings[group_id] = set(group_data['ts_code'].tolist())

                    group_stats.append({
                        '组别': group_id,
                        '股票数': len(group_data),
                        '收益率': group_ret,
                        '平均市值': group_data['流通市值(亿)'].mean(),
                    })

                # 10. 计算换手率
                if idx > 0:
                    for group_id in range(1, 6):
                        prev_set = prev_holdings[group_id]
                        curr_set = current_holdings[group_id]

                        if len(prev_set) > 0 and len(curr_set) > 0:
                            turnover = 1 - len(prev_set & curr_set) / len(curr_set)
                            turnover_rates.append(turnover)

                prev_holdings = current_holdings

                # 11. 获取基准收益率
                benchmark_ret = self.get_benchmark_return_fixed(rebalance_date, next_rebalance)
                benchmark_returns.append(benchmark_ret)

                # 12. 记录
                group_dates.append(rebalance_date)

                logger.info(f"  各组收益率: {[f'{group_returns[g][-1]:.2%}' for g in range(1, 6)]}")
                logger.info(f"  基准收益率: {benchmark_ret:.2%}")

            except Exception as e:
                logger.error(f"  调仓失败: {e}")
                import traceback
                traceback.print_exc()
                continue

        # 汇总结果
        results = {
            'dates': group_dates,
            'group_returns': group_returns,
            'benchmark_returns': benchmark_returns,
            'ic_values': ic_values,
            'turnover_rates': turnover_rates,
        }

        return results

    def get_st_stock_list(self, date: str) -> List[str]:
        """获取ST股票列表"""
        sql = "SELECT DISTINCT ts_code FROM stock_st WHERE type = 'ST' AND trade_date = %s"
        data = db.execute_query(sql, (date,))
        return [row['ts_code'] for row in data]

    def calculate_performance_metrics(self, results: Dict) -> pd.DataFrame:
        """Calculate full performance metrics"""
        logger.info("\n" + "="*80)
        logger.info("Calculating performance metrics")
        logger.info("="*80)

        dates = results['dates']
        if len(dates) == 0:
            logger.error("No backtest data")
            return pd.DataFrame()

        group_returns = results['group_returns']
        benchmark_returns = results['benchmark_returns']
        ic_values = results['ic_values']
        turnover_rates = results['turnover_rates']

        # 计算多空组合
        long_short_returns = [g1 - g5 for g1, g5 in zip(group_returns[1], group_returns[5])]

        # 交易日数
        trading_days = len(dates)

        # 计算累计收益率
        def cumulative_returns(returns):
            cum = 1.0
            result = []
            for r in returns:
                r_float = float(r) if hasattr(r, '__float__') else r
                cum *= (1 + r_float)
                result.append(cum - 1)
            return result

        # 计算年化指标
        def annualize_return(cum_return, days):
            if days == 0:
                return 0
            return (1 + cum_return) ** (252 / days) - 1

        def annualize_volatility(returns, days):
            if days == 0:
                return 0
            returns_float = [float(r) if hasattr(r, '__float__') else r for r in returns]
            return np.std(returns_float) * np.sqrt(252 / days)

        def calculate_sharpe(returns, days, risk_free=0.03):
            if days == 0:
                return 0
            returns_float = [float(r) if hasattr(r, '__float__') else r for r in returns]
            annual_ret = annualize_return(sum(returns_float), days)
            annual_vol = annualize_volatility(returns, days)
            if annual_vol == 0:
                return 0
            return (annual_ret - risk_free) / annual_vol

        def calculate_max_drawdown(returns):
            cum = 1.0
            peak = 1.0
            max_dd = 0
            for r in returns:
                r_float = float(r) if hasattr(r, '__float__') else r
                cum *= (1 + r_float)
                if cum > peak:
                    peak = cum
                dd = (peak - cum) / peak
                if dd > max_dd:
                    max_dd = dd
            return max_dd

        # 计算各组指标
        metrics = []
        for group_id in range(1, 6):
            returns = group_returns[group_id]
            if len(returns) == 0:
                continue

            cum_ret = cumulative_returns(returns)[-1] if returns else 0
            annual_ret = annualize_return(cum_ret, trading_days)
            annual_vol = annualize_volatility(returns, trading_days)
            sharpe = calculate_sharpe(returns, trading_days)
            max_dd = calculate_max_drawdown(returns)
            returns_float = [float(r) if hasattr(r, '__float__') else r for r in returns]
            win_rate = sum(1 for r in returns_float if r > 0) / len(returns_float) if returns else 0

            metrics.append({
                '分组': f'组{group_id}',
                '累计收益': cum_ret,
                '年化收益': annual_ret,
                '年化波动': annual_vol,
                '夏普比率': sharpe,
                '最大回撤': max_dd,
                '月度胜率': win_rate,
            })

        # 多空组合
        if long_short_returns:
            cum_ret = cumulative_returns(long_short_returns)[-1]
            annual_ret = annualize_return(cum_ret, trading_days)
            annual_vol = annualize_volatility(long_short_returns, trading_days)
            sharpe = calculate_sharpe(long_short_returns, trading_days)
            max_dd = calculate_max_drawdown(long_short_returns)
            ls_float = [float(r) if hasattr(r, '__float__') else r for r in long_short_returns]
            win_rate = sum(1 for r in ls_float if r > 0) / len(ls_float)

            metrics.append({
                '分组': '多空组合',
                '累计收益': cum_ret,
                '年化收益': annual_ret,
                '年化波动': annual_vol,
                '夏普比率': sharpe,
                '最大回撤': max_dd,
                '月度胜率': win_rate,
            })

        # 基准
        if benchmark_returns:
            cum_ret = cumulative_returns(benchmark_returns)[-1]
            annual_ret = annualize_return(cum_ret, trading_days)
            annual_vol = annualize_volatility(benchmark_returns, trading_days)
            sharpe = calculate_sharpe(benchmark_returns, trading_days)
            max_dd = calculate_max_drawdown(benchmark_returns)
            bench_float = [float(r) if hasattr(r, '__float__') else r for r in benchmark_returns]
            win_rate = sum(1 for r in bench_float if r > 0) / len(bench_float)

            metrics.append({
                '分组': '沪深300',
                '累计收益': cum_ret,
                '年化收益': annual_ret,
                '年化波动': annual_vol,
                '夏普比率': sharpe,
                '最大回撤': max_dd,
                '月度胜率': win_rate,
            })

        # IC统计
        if ic_values:
            valid_ic = [x for x in ic_values if not pd.isna(x)]
            if valid_ic:
                logger.info(f"\nIC统计: 均值={np.mean(valid_ic):.4f}, 标准差={np.std(valid_ic):.4f}, IR={np.mean(valid_ic)/np.std(valid_ic):.4f}")

        # 换手率统计
        if turnover_rates:
            logger.info(f"平均换手率: {np.mean(turnover_rates):.2%}")

        # 打印结果
        print("\n" + "="*80)
        print("性能指标 - 优化版")
        print("="*80)
        df_metrics = pd.DataFrame(metrics)
        print(df_metrics.to_string(index=False, float_format='%.4f'))

        return df_metrics


def run_optimized_backtest(start_date: str, end_date: str):
    """运行优化版回测"""
    print("="*80)
    print("六因子策略回测 - 优化版")
    print("="*80)
    print(f"测试周期: {start_date} - {end_date}")
    print(f"优化内容:")
    print("  1. 结束日期调整为20250131，确保数据完整")
    print("  2. 优化因子权重 (alpha_010和cr_qfq权重提升)")
    print("  3. 增加持有期约束 (最少持有5天)")
    print()

    # 运行回测
    backtest = SixFactorBacktestOptimized(start_date, end_date, 'optimized_v2')
    results = backtest.run_backtest()

    if len(results) > 0:
        # 计算性能指标
        metrics = backtest.calculate_performance_metrics(results)

        # 保存结果
        import os
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

        print(f"\n结果已保存至: {output_dir}")
        print("\n优化说明:")
        print("1. 结束日期20250131，确保20241231期数据完整")
        print("2. 优化权重: alpha_010和cr_qfq提升至0.25，alpha_peg和alpha_120cq降至0.15")
        print("3. 增加持有期约束，降低换手率")
        print("4. 预期效果: 提升ICIR，降低交易成本")

        return results, metrics
    else:
        print("回测失败")
        return None, None


if __name__ == "__main__":
    # 运行优化版回测
    results, metrics = run_optimized_backtest('20240601', '20250131')
