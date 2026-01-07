"""
六大因子选股策略
版本: v1.0
更新日期: 2025-12-30

基于六大因子的综合选股策略:
- alpha_pluse: 量能因子
- alpha_peg: 估值因子（行业标准化）
- alpha_010: 短周期价格趋势
- alpha_038: 价格强度
- alpha_120cq: 价格位置
- cr_qfq: 动量因子
"""

import pandas as pd
import numpy as np
import sys
import os
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, '/home/zcy/alpha006_20251223')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入必要的模块
from core.utils.data_loader import data_loader
from core.utils.db_connection import db
from core.config.params import get_strategy_param, get_factor_param
from factors.price.PRI_TREND_4D_V2 import create_factor as create_alpha_010
from factors.price.PRI_STR_10D_V2 import create_factor as create_alpha_038
from factors.price.PRI_POS_120D_V2 import create_factor as create_alpha_120cq
from factors.momentum.VOL_EXP_20D_V2 import create_factor as create_alpha_pluse
from factors.valuation.alpha_peg import ValGrowQFactor
from factors.volume.MOM_CR_20D_V2 import create_factor as create_cr_qfq

from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')


class SixFactorStrategy:
    """六大因子选股策略类"""

    def __init__(self, target_date: str, version: str = 'standard'):
        """
        初始化策略

        Args:
            target_date: 目标日期 (YYYYMMDD)
            version: 策略版本 (standard/conservative/aggressive)
        """
        self.target_date = target_date
        self.version = version
        self.params = get_strategy_param('six_factor', version)
        self.filter_stats = {}
        self.factor_data = {}

        logger.info(f"初始化策略: {self.params['name']}")
        logger.info(f"目标日期: {target_date}, 版本: {version}")

    def get_market_data(self) -> pd.DataFrame:
        """获取流通市值和成交额数据"""
        logger.info("步骤1: 获取流通市值和成交额数据...")

        df = data_loader.get_market_cap_and_amount(self.target_date)

        if len(df) == 0:
            raise ValueError(f"未获取到流通市值/成交额数据: {self.target_date}")

        # 单位转换
        # circ_mv单位是万元，转换为亿: 万元 / 10000 = 亿
        df['流通市值(亿)'] = df['circ_mv'] / 10_000
        # amount单位是元，转换为万: 元 / 10000 = 万
        df['成交额(万)'] = df['amount'] / 10_000

        logger.info(f"获取流通市值/成交额数据: {len(df)} 只股票")
        self.filter_stats['初始股票数'] = len(df)

        return df

    def get_st_stock_list(self) -> List[str]:
        """获取ST股票列表"""
        sql = f"SELECT ts_code FROM stock_st WHERE type = 'ST'"
        data = db.execute_query(sql, ())
        return [row['ts_code'] for row in data]

    def apply_base_filters(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """应用基础过滤"""
        logger.info("步骤2: 应用基础过滤...")

        initial_count = len(df)
        filter_log = {}

        # 1. 剔除ST股票
        if self.params['filters']['exclude_st']:
            st_stocks = self.get_st_stock_list()
            df = df[~df['ts_code'].isin(st_stocks)]
            filter_log['剔除ST'] = initial_count - len(df)
            initial_count = len(df)

        # 2. 剔除停牌（成交额为0或NaN）
        if self.params['filters']['exclude_suspension']:
            df = df[df['成交额(万)'] > 0]
            filter_log['剔除停牌'] = initial_count - len(df)
            initial_count = len(df)

        # 3. 剔除低流动性
        min_amount = self.params['filters']['min_amount'] / 10_000  # 转换为万
        df = df[df['成交额(万)'] >= min_amount]
        filter_log['剔除低流动性'] = initial_count - len(df)
        initial_count = len(df)

        # 4. 剔除小市值（使用流通市值）
        min_market_cap = self.params['filters']['min_market_cap'] / 100_000_000  # 转换为亿
        df = df[df['流通市值(亿)'] >= min_market_cap]
        filter_log['剔除小市值'] = initial_count - len(df)
        initial_count = len(df)

        # 5. alpha_pluse = 1 (只对过滤后的股票计算)
        if len(df) > 0:
            alpha_pluse_factor = create_alpha_pluse('standard')
            # 获取过滤后股票的价格数据（需要34天数据）
            stocks = df['ts_code'].tolist()
            price_data = data_loader.get_price_data_for_period(stocks, self.target_date, 34)

            if len(price_data) > 0:
                alpha_pluse_result = alpha_pluse_factor.calculate(price_data)

                if len(alpha_pluse_result) > 0:
                    valid_stocks = alpha_pluse_result[alpha_pluse_result['alpha_pluse'] == 1]['ts_code'].tolist()
                    df = df[df['ts_code'].isin(valid_stocks)]
                    filter_log['alpha_pluse=1'] = initial_count - len(df)
                    initial_count = len(df)
                else:
                    filter_log['alpha_pluse=1'] = initial_count
                    df = df.iloc[0:0]  # Empty dataframe
            else:
                filter_log['alpha_pluse=1'] = initial_count
                df = df.iloc[0:0]  # Empty dataframe
        else:
            filter_log['alpha_pluse=1'] = 0

        self.filter_stats.update(filter_log)
        self.filter_stats['基础过滤后'] = len(df)

        logger.info(f"基础过滤后剩余: {len(df)} 只股票")
        for key, value in filter_log.items():
            if value > 0:
                logger.info(f"  - {key}: {value}只")

        return df, filter_log

    def calculate_all_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有因子"""
        logger.info("步骤3: 计算各因子...")

        stocks = df['ts_code'].tolist()

        # 添加行业数据
        logger.info("  获取行业数据...")
        industry_data = data_loader.get_industry_data_from_csv(stocks)
        if len(industry_data) > 0:
            df = df.merge(industry_data[['ts_code', 'l1_name']], on='ts_code', how='left')
            df.rename(columns={'l1_name': '申万一级行业'}, inplace=True)
            logger.info(f"  行业数据已添加: {len(industry_data)}条")
        else:
            logger.warning("  无法获取行业数据")

        # 1. alpha_peg (估值因子 = PE_TTM，进行行业标准化)
        logger.info("  计算alpha_peg...")
        try:
            # 获取PE数据
            df_pe, _ = data_loader.get_fina_data(stocks, self.target_date)

            if len(df_pe) > 0:
                # 获取行业数据
                industry_data = data_loader.get_industry_data_from_csv(stocks)

                if len(industry_data) > 0:
                    # 合并行业
                    df_pe_industry = df_pe.merge(industry_data, on='ts_code', how='left')
                    df_pe_industry['l1_name'] = df_pe_industry['l1_name'].fillna('其他')

                    # 计算行业Z-Score
                    def zscore(group):
                        values = group['pe_ttm'].astype(float)
                        mean = values.mean()
                        std = values.std()
                        if std == 0 or pd.isna(std) or len(values) < 2:
                            return pd.Series([0.0] * len(group), index=group.index)
                        return (values - mean) / std

                    df_pe_industry['alpha_peg_zscore'] = df_pe_industry.groupby('l1_name').apply(zscore).reset_index(level=0, drop=True)

                    # 过滤样本不足的行业
                    min_samples = 5
                    industry_counts = df_pe_industry.groupby('l1_name').size()
                    valid_industries = industry_counts[industry_counts >= min_samples].index
                    df_pe_industry = df_pe_industry[df_pe_industry['l1_name'].isin(valid_industries)]

                    # 合并到主数据
                    df = df.merge(df_pe_industry[['ts_code', 'alpha_peg_zscore']], on='ts_code', how='left')
                    self.factor_data['alpha_peg'] = df_pe_industry

                    logger.info(f"  alpha_peg计算完成: {len(df_pe_industry)}条记录")
                else:
                    logger.warning("无法获取行业数据，跳过alpha_peg")
            else:
                logger.warning("无PE数据，跳过alpha_peg")
        except Exception as e:
            logger.warning(f"alpha_peg计算失败: {e}，跳过该因子")

        # 2. alpha_010 (短周期趋势)
        logger.info("  计算alpha_010...")
        alpha_010_factor = create_alpha_010(self.version)
        price_data = data_loader.get_price_data_for_period(stocks, self.target_date, 10)
        alpha_010_result = alpha_010_factor.calculate(price_data)

        if len(alpha_010_result) > 0:
            df = df.merge(alpha_010_result[['ts_code', 'alpha_010']], on='ts_code', how='left')
            self.factor_data['alpha_010'] = alpha_010_result

        # 3. alpha_038 (价格强度)
        logger.info("  计算alpha_038...")
        alpha_038_factor = create_alpha_038(self.version)
        # 需要至少10天数据，所以从target_date往前推10天
        price_data_038 = data_loader.get_price_data_for_period(stocks, self.target_date, 10)
        alpha_038_result = alpha_038_factor.calculate(price_data_038)

        if len(alpha_038_result) > 0:
            df = df.merge(alpha_038_result[['ts_code', 'alpha_038']], on='ts_code', how='left')
            self.factor_data['alpha_038'] = alpha_038_result

        # 4. alpha_120cq (价格位置)
        logger.info("  计算alpha_120cq...")
        alpha_120cq_factor = create_alpha_120cq(self.version)
        price_data_120 = data_loader.get_price_data_for_period(stocks, self.target_date, 180)
        alpha_120cq_result = alpha_120cq_factor.calculate(price_data_120, self.target_date)

        if len(alpha_120cq_result) > 0:
            df = df.merge(alpha_120cq_result[['ts_code', 'alpha_120cq']], on='ts_code', how='left')
            self.factor_data['alpha_120cq'] = alpha_120cq_result

        # 5. cr_qfq (动量因子)
        logger.info("  获取cr_qfq...")
        cr_qfq_factor = create_cr_qfq(self.version)
        cr_qfq_result = cr_qfq_factor.calculate_by_period(
            self.target_date, stocks
        )

        if len(cr_qfq_result) > 0:
            df = df.merge(cr_qfq_result[['ts_code', 'cr_qfq']], on='ts_code', how='left')
            self.factor_data['cr_qfq'] = cr_qfq_result

        # 6. alpha_pluse (量能因子) - 作为独立因子参与打分
        logger.info("  计算alpha_pluse...")
        alpha_pluse_factor = create_alpha_pluse('standard')
        # 获取价格数据（需要34天数据）
        price_data_pluse = data_loader.get_price_data_for_period(stocks, self.target_date, 34)

        if len(price_data_pluse) > 0:
            alpha_pluse_result = alpha_pluse_factor.calculate(price_data_pluse)

            if len(alpha_pluse_result) > 0:
                # alpha_pluse是0/1二元变量，转换为数值参与计算
                df = df.merge(alpha_pluse_result[['ts_code', 'alpha_pluse']], on='ts_code', how='left')
                self.factor_data['alpha_pluse'] = alpha_pluse_result

                # 将alpha_pluse转换为数值（0或1）
                df['alpha_pluse'] = pd.to_numeric(df['alpha_pluse'], errors='coerce').fillna(0)

        # 记录因子数据统计
        logger.info("因子数据统计:")
        for factor in ['alpha_peg_zscore', 'alpha_010', 'alpha_038', 'alpha_120cq', 'cr_qfq', 'alpha_pluse']:
            if factor in df.columns:
                valid = df[factor].dropna()
                if len(valid) > 0:
                    logger.info(f"  {factor}: {len(valid)}/{len(df)} 有效, 均值={valid.mean():.2f}")

        return df

    def apply_factor_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """应用因子筛选"""
        logger.info("步骤4: 应用因子筛选...")

        initial_count = len(df)
        filter_log = {}

        # 如果股票数量太少，使用更宽松的筛选
        min_threshold = 5 if initial_count >= 20 else 2  # 动态调整最小保留数

        # 1. alpha_peg 前30%（值越小越好）
        if 'alpha_peg_zscore' in df.columns and len(df) > min_threshold:
            threshold = self.params['factor_thresholds']['alpha_peg']
            valid_stocks = df.dropna(subset=['alpha_peg_zscore'])
            if len(valid_stocks) > min_threshold:
                cutoff = valid_stocks['alpha_peg_zscore'].quantile(threshold)
                df = df[df['alpha_peg_zscore'] <= cutoff]
                filter_log['alpha_peg前30%'] = initial_count - len(df)
                initial_count = len(df)

        # 2. alpha_010 前30%（值越大越好）
        if 'alpha_010' in df.columns and len(df) > min_threshold:
            threshold = self.params['factor_thresholds']['alpha_010']
            valid_stocks = df.dropna(subset=['alpha_010'])
            if len(valid_stocks) > min_threshold:
                cutoff = valid_stocks['alpha_010'].quantile(1 - threshold)
                df = df[df['alpha_010'] >= cutoff]
                filter_log['alpha_010前30%'] = initial_count - len(df)
                initial_count = len(df)

        # 3. alpha_038 前30%（值越小越好，负值）
        if 'alpha_038' in df.columns and len(df) > min_threshold:
            threshold = self.params['factor_thresholds']['alpha_038']
            valid_stocks = df.dropna(subset=['alpha_038'])
            if len(valid_stocks) > min_threshold:
                cutoff = valid_stocks['alpha_038'].quantile(threshold)
                df = df[df['alpha_038'] <= cutoff]
                filter_log['alpha_038前30%'] = initial_count - len(df)
                initial_count = len(df)

        # 4. alpha_120cq 在 [0.2, 0.8] 区间
        if 'alpha_120cq' in df.columns and len(df) > min_threshold:
            low = self.params['factor_thresholds']['alpha_120cq_low']
            high = self.params['factor_thresholds']['alpha_120cq_high']
            filtered = df[(df['alpha_120cq'] >= low) & (df['alpha_120cq'] <= high)]
            if len(filtered) >= min_threshold:
                df = filtered
                filter_log['alpha_120cq[0.2,0.8]'] = initial_count - len(df)
                initial_count = len(df)

        # 5. cr_qfq 前40%（值越大越好）
        if 'cr_qfq' in df.columns and len(df) > min_threshold:
            threshold = self.params['factor_thresholds']['cr_qfq']
            valid_stocks = df.dropna(subset=['cr_qfq'])
            if len(valid_stocks) > min_threshold:
                cutoff = valid_stocks['cr_qfq'].quantile(1 - threshold)
                df = df[df['cr_qfq'] >= cutoff]
                filter_log['cr_qfq前40%'] = initial_count - len(df)
                initial_count = len(df)

        # 6. alpha_pluse = 1（量能因子，已在基础过滤中筛选，这里作为验证）
        if 'alpha_pluse' in df.columns and len(df) > min_threshold:
            valid_stocks = df.dropna(subset=['alpha_pluse'])
            before_filter = len(df)
            df = df[valid_stocks['alpha_pluse'] == 1]
            filter_log['alpha_pluse=1'] = before_filter - len(df)
            initial_count = len(df)

        self.filter_stats.update(filter_log)
        self.filter_stats['因子筛选后'] = len(df)

        logger.info(f"因子筛选后剩余: {len(df)} 只股票")
        for key, value in filter_log.items():
            if value > 0:
                logger.info(f"  - {key}: {value}只")

        return df

    def neutralize_factor(self, df: pd.DataFrame, factor_col: str, market_cap_col: str = '流通市值(亿)', industry_col: str = '申万一级行业') -> pd.DataFrame:
        """
        因子中性化：剔除市值和行业暴露

        公式：因子残差 = 原始因子 - β1 * 市值 - β2 * 行业哑变量

        Args:
            df: 包含因子、市值、行业的DataFrame
            factor_col: 因子列名
            market_cap_col: 市值列名
            industry_col: 行业列名

        Returns:
            中性化后的DataFrame，添加 factor_col_neutral 列
        """
        if factor_col not in df.columns:
            logger.warning(f"因子列 {factor_col} 不存在，跳过中性化")
            return df

        if market_cap_col not in df.columns:
            logger.warning(f"市值列 {market_cap_col} 不存在，跳过中性化")
            return df

        if industry_col not in df.columns:
            logger.warning(f"行业列 {industry_col} 不存在，跳过中性化")
            return df

        # 准备数据
        df_neutral = df[[factor_col, market_cap_col, industry_col, 'ts_code']].copy()
        df_neutral = df_neutral.dropna(subset=[factor_col])

        if len(df_neutral) < 10:
            logger.warning(f"数据量不足({len(df_neutral)}条)，跳过 {factor_col} 中性化")
            return df

        # 关键：转换数据类型为float，避免Decimal类型错误
        try:
            df_neutral[factor_col] = pd.to_numeric(df_neutral[factor_col], errors='coerce')
            df_neutral[market_cap_col] = pd.to_numeric(df_neutral[market_cap_col], errors='coerce')
        except Exception as e:
            logger.warning(f"  数据类型转换失败: {e}")
            return df

        # 再次删除NaN
        df_neutral = df_neutral.dropna(subset=[factor_col, market_cap_col])

        if len(df_neutral) < 10:
            logger.warning(f"类型转换后数据量不足({len(df_neutral)}条)，跳过 {factor_col} 中性化")
            return df

        # 1. 对数市值（更符合线性假设）
        df_neutral['log_mcap'] = np.log(df_neutral[market_cap_col] + 1e-8)

        # 2. 行业哑变量
        industry_dummies = pd.get_dummies(df_neutral[industry_col], prefix='industry')

        # 3. 构建特征矩阵
        X = pd.concat([
            df_neutral[['log_mcap']],  # 市值
            industry_dummies           # 行业哑变量
        ], axis=1)

        # 4. 目标变量
        y = df_neutral[factor_col].values  # 转为numpy数组

        # 5. 线性回归
        try:
            reg = LinearRegression(fit_intercept=True)
            reg.fit(X, y)

            # 6. 预测值
            y_pred = reg.predict(X)

            # 7. 计算残差（中性化后的因子）
            residual = y - y_pred

            # 8. 标准化残差（Z-Score）
            residual_mean = residual.mean()
            residual_std = residual.std()

            if residual_std > 0:
                residual_zscore = (residual - residual_mean) / residual_std
            else:
                residual_zscore = residual * 0  # 标准差为0，全部设为0

            # 9. 合并回原数据
            df_neutral[factor_col + '_neutral'] = residual_zscore

            # 10. 合并到原DataFrame
            df = df.merge(
                df_neutral[['ts_code', factor_col + '_neutral']],
                on='ts_code',
                how='left'
            )

            # 统计信息
            logger.info(f"  {factor_col} 中性化完成:")
            logger.info(f"    回归R²: {reg.score(X, y):.4f}")
            logger.info(f"    残差均值: {residual_mean:.6f}")
            logger.info(f"    残差标准差: {residual_std:.6f}")
            if factor_col + '_neutral' in df.columns:
                logger.info(f"    中性化后均值: {df[factor_col + '_neutral'].mean():.6f}")
                logger.info(f"    中性化后标准差: {df[factor_col + '_neutral'].std():.6f}")

        except Exception as e:
            logger.warning(f"  {factor_col} 中性化失败: {e}")
            df[factor_col + '_neutral'] = np.nan

        return df

    def standardize_factor(self, series: pd.Series) -> pd.Series:
        """
        因子标准化：Z-Score标准化（均值为0，标准差为1）

        Args:
            series: 原始因子序列

        Returns:
            标准化后的序列
        """
        if series.isna().all():
            return series

        valid = series.dropna()
        if len(valid) == 0:
            return series

        mean = valid.mean()
        std = valid.std()

        if std == 0 or pd.isna(std):
            logger.warning("标准差为0或NaN，无法标准化")
            return series * 0

        return (series - mean) / std

    def normalize_factor(self, series: pd.Series, direction: str) -> pd.Series:
        """标准化因子值到[0,1]区间"""
        if series.isna().all():
            return series

        valid = series.dropna()
        if len(valid) == 0:
            return series

        min_val = valid.min()
        max_val = valid.max()

        if max_val == min_val:
            return pd.Series([0.5] * len(series), index=series.index)

        if direction == 'positive':
            # 越大越好
            return (series - min_val) / (max_val - min_val)
        else:
            # 越小越好
            return 1 - (series - min_val) / (max_val - min_val)

    def calculate_comprehensive_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算加权综合得分"""
        logger.info("步骤5: 计算加权综合得分...")

        weights = self.params['weights']
        directions = self.params['directions']

        # 检查哪些因子可用
        available_factors = []
        factor_columns = {
            'alpha_peg': 'alpha_peg_zscore',
            'alpha_010': 'alpha_010',
            'alpha_038': 'alpha_038',
            'alpha_120cq': 'alpha_120cq',
            'cr_qfq': 'cr_qfq',
            'alpha_pluse': 'alpha_pluse'
        }

        for factor_name, col_name in factor_columns.items():
            if col_name in df.columns and not df[col_name].dropna().empty:
                available_factors.append(factor_name)

        logger.info(f"可用因子: {available_factors}")

        # 重新计算权重（按比例分配）
        total_weight = sum(weights[f] for f in available_factors)
        if total_weight > 0:
            # 归一化权重
            normalized_weights = {f: weights[f] / total_weight for f in available_factors}
            logger.info(f"重新分配权重: {normalized_weights}")
        else:
            normalized_weights = weights
            logger.warning("所有因子权重为0，使用原始权重")

        # 标准化各因子
        df['因子_估值'] = self.normalize_factor(df.get('alpha_peg_zscore', pd.Series(np.nan, index=df.index)),
                                               directions['alpha_peg'])
        df['因子_趋势'] = self.normalize_factor(df.get('alpha_010', pd.Series(np.nan, index=df.index)),
                                               directions['alpha_010'])
        df['因子_强度'] = self.normalize_factor(df.get('alpha_038', pd.Series(np.nan, index=df.index)),
                                               directions['alpha_038'])
        df['因子_位置'] = self.normalize_factor(df.get('alpha_120cq', pd.Series(np.nan, index=df.index)),
                                               directions['alpha_120cq'])
        df['因子_动量'] = self.normalize_factor(df.get('cr_qfq', pd.Series(np.nan, index=df.index)),
                                               directions['cr_qfq'])
        df['因子_量能'] = self.normalize_factor(df.get('alpha_pluse', pd.Series(np.nan, index=df.index)),
                                               directions['alpha_pluse'])

        # 计算综合得分（只使用可用因子）
        df['综合得分'] = 0.0

        if 'alpha_peg' in available_factors:
            df['综合得分'] += df['因子_估值'] * normalized_weights['alpha_peg']
        if 'alpha_010' in available_factors:
            df['综合得分'] += df['因子_趋势'] * normalized_weights['alpha_010']
        if 'alpha_038' in available_factors:
            df['综合得分'] += df['因子_强度'] * normalized_weights['alpha_038']
        if 'alpha_120cq' in available_factors:
            df['综合得分'] += df['因子_位置'] * normalized_weights['alpha_120cq']
        if 'cr_qfq' in available_factors:
            df['综合得分'] += df['因子_动量'] * normalized_weights['cr_qfq']
        if 'alpha_pluse' in available_factors:
            df['综合得分'] += df['因子_量能'] * normalized_weights['alpha_pluse']

        # 按综合得分排序
        df = df.sort_values('综合得分', ascending=False).reset_index(drop=True)

        if len(df) > 0:
            logger.info(f"综合得分范围: {df['综合得分'].min():.4f} ~ {df['综合得分'].max():.4f}")
        else:
            logger.warning("无有效数据计算综合得分")

        return df

    def export_to_excel(self, df: pd.DataFrame):
        """导出到Excel"""
        logger.info("步骤6: 导出Excel...")

        # 标准化列名（将数据库列名转换为中文列名）
        column_mapping = {
            'ts_code': '股票代码',
            'circ_mv': '流通市值(亿)',
            'amount': '成交额(万)',
        }

        # 重命名列
        df_export = df.copy()
        for db_col, cn_col in column_mapping.items():
            if db_col in df_export.columns and cn_col not in df_export.columns:
                df_export.rename(columns={db_col: cn_col}, inplace=True)

        # 选择并排序列（包含原始因子和中性化后因子）
        output_columns = [
            '股票代码', '申万一级行业', '流通市值(亿)', '成交额(万)',
            # 原始因子
            'alpha_peg_zscore', 'alpha_010', 'alpha_038', 'alpha_120cq', 'cr_qfq', 'alpha_pluse',
            # 中性化后因子
            'alpha_peg_neutral', 'alpha_010_neutral', 'alpha_038_neutral', 'alpha_120cq_neutral', 'cr_qfq_neutral', 'alpha_pluse_neutral',
            # 综合得分和标准化因子
            '综合得分',
            '因子_估值', '因子_趋势', '因子_强度', '因子_位置', '因子_动量', '因子_量能'
        ]

        # 只保留存在的列
        existing_cols = [col for col in output_columns if col in df_export.columns]
        df_output = df_export[existing_cols].copy()

        # 导出完整结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = '/home/zcy/alpha006_20251223/results/output'
        os.makedirs(output_dir, exist_ok=True)

        # 完整结果
        full_path = f"{output_dir}/six_factor_scores_{self.target_date}_{timestamp}.xlsx"
        df_output.to_excel(full_path, index=False)
        logger.info(f"完整结果已保存: {full_path}")

        # 前100名
        top_n = self.params['top_n']
        top_path = f"{output_dir}/six_factor_top{top_n}_{self.target_date}_{timestamp}.xlsx"
        df_output.head(top_n).to_excel(top_path, index=False)
        logger.info(f"前{top_n}名已保存: {top_path}")

        # 保存筛选日志
        log_path = f"{output_dir}/six_factor_log_{self.target_date}_{timestamp}.txt"
        self._save_filter_log(log_path)
        logger.info(f"筛选日志已保存: {log_path}")

        return full_path, top_path, log_path

    def _save_filter_log(self, log_path: str):
        """保存筛选日志"""
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("六大因子选股策略 - 筛选日志\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"执行日期: {self.target_date}\n")
            f.write(f"策略版本: {self.version}\n")
            f.write(f"策略名称: {self.params['name']}\n")
            f.write(f"计算时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("=" * 80 + "\n")
            f.write("策略配置:\n")
            f.write("=" * 80 + "\n\n")

            f.write("基础过滤:\n")
            for key, value in self.params['filters'].items():
                f.write(f"  - {key}: {value}\n")

            f.write("\n因子筛选阈值:\n")
            for key, value in self.params['factor_thresholds'].items():
                f.write(f"  - {key}: {value}\n")

            f.write("\n权重分配:\n")
            for key, value in self.params['weights'].items():
                f.write(f"  - {key}: {value}\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("筛选过程记录:\n")
            f.write("=" * 80 + "\n\n")

            for key, value in self.filter_stats.items():
                f.write(f"{key}: {value}\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("最终结果:\n")
            f.write("=" * 80 + "\n")

    def print_summary(self, df: pd.DataFrame):
        """打印执行总结"""
        print("\n" + "=" * 80)
        print("执行总结")
        print("=" * 80)

        print(f"\n📊 数据统计:")
        print(f"  目标日期: {self.target_date}")
        print(f"  策略版本: {self.version}")
        print(f"  最终选股: {len(df)}只")

        if len(df) > 0 and '综合得分' in df.columns:
            print(f"\n📈 综合得分统计:")
            print(f"  均值: {df['综合得分'].mean():.4f}")
            print(f"  标准差: {df['综合得分'].std():.4f}")
            print(f"  最小值: {df['综合得分'].min():.4f}")
            print(f"  最大值: {df['综合得分'].max():.4f}")
            print(f"  中位数: {df['综合得分'].median():.4f}")

            # 前10名
            if len(df) >= 10:
                print(f"\n📝 前10名优质个股:")
                for i in range(min(10, len(df))):
                    row = df.iloc[i]
                    stock = row.get('股票代码', 'N/A')
                    industry = row.get('申万一级行业', 'N/A')
                    score = row.get('综合得分', 0)
                    print(f"  {i+1:2d}. {stock:<12} {industry:<8} 得分={score:.4f}")

            # 行业分布
            if '申万一级行业' in df.columns:
                industry_counts = df['申万一级行业'].value_counts().head(10)
                if len(industry_counts) > 0:
                    print(f"\n📊 行业分布(前10):")
                    for industry, count in industry_counts.items():
                        print(f"  {industry:<8}: {count}只")

        print("\n" + "=" * 80)
        print("✅ 任务完成！")
        print("=" * 80)

    def run(self):
        """执行完整策略流程"""
        try:
            # 1. 获取市值和成交额
            df = self.get_market_data()

            # 2. 基础过滤
            df, _ = self.apply_base_filters(df)

            if len(df) == 0:
                logger.error("基础过滤后无有效股票")
                return

            # 3. 计算因子
            df = self.calculate_all_factors(df)

            # 4. 因子中性化（剔除市值和行业暴露）
            logger.info("步骤4: 因子中性化...")
            df = self._neutralize_all_factors(df)

            # 5. 因子筛选（使用中性化后的因子）
            df = self.apply_factor_filters(df)

            if len(df) == 0:
                logger.error("因子筛选后无有效股票")
                return

            # 6. 计算综合得分（使用中性化后的因子）
            df = self.calculate_comprehensive_score(df)

            # 7. 导出结果
            full_path, top_path, log_path = self.export_to_excel(df)

            # 8. 打印总结
            self.print_summary(df)

            return df

        except Exception as e:
            logger.error(f"策略执行失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _neutralize_all_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        对所有因子进行中性化处理

        处理流程：
        1. 对每个因子进行市值+行业中性化（alpha_pluse除外）
        2. 将中性化后的因子替换原因子（或添加新列）
        3. 标准化为Z-Score
        4. alpha_pluse保持原始值（二值因子不适合中性化）
        """
        logger.info("  开始因子中性化处理...")

        # 因子映射：原始列名 -> 中性化后列名
        # 注意：alpha_pluse 不进行中性化，因为它是二值因子(0/1)
        factor_map = {
            'alpha_peg_zscore': 'alpha_peg_neutral',
            'alpha_010': 'alpha_010_neutral',
            'alpha_038': 'alpha_038_neutral',
            'alpha_120cq': 'alpha_120cq_neutral',
            'cr_qfq': 'cr_qfq_neutral'
        }

        # 确保有行业和市值数据
        if '申万一级行业' not in df.columns:
            logger.warning("  缺少行业数据，无法进行行业中性化")
            return df

        if '流通市值(亿)' not in df.columns:
            logger.warning("  缺少市值数据，无法进行市值中性化")
            return df

        # 预处理：确保所有因子列都是数值类型
        for original_col in factor_map.keys():
            if original_col in df.columns:
                try:
                    df[original_col] = pd.to_numeric(df[original_col], errors='coerce')
                except:
                    logger.warning(f"  无法转换 {original_col} 为数值类型")
                    df[original_col] = np.nan

        # 对每个因子进行中性化（跳过alpha_pluse）
        for original_col, neutral_col in factor_map.items():
            if original_col in df.columns and not df[original_col].isna().all():
                logger.info(f"  中性化因子: {original_col}")
                df = self.neutralize_factor(df, original_col, '流通市值(亿)', '申万一级行业')

                # 如果中性化成功，使用中性化后的因子
                if neutral_col in df.columns and not df[neutral_col].isna().all():
                    # 标准化为Z-Score（中性化时已标准化，这里确保一致性）
                    df[neutral_col] = self.standardize_factor(df[neutral_col])

                    # 用中性化因子替换原因子（用于后续筛选和打分）
                    df[original_col] = df[neutral_col]

                    logger.info(f"  {original_col} 已替换为中性化版本")
                else:
                    logger.warning(f"  {original_col} 中性化失败，保留原始值")
            else:
                logger.warning(f"  {original_col} 无有效数据，跳过中性化")

        # alpha_pluse 不中性化，但添加 neutral 列（与原始值相同）用于导出
        if 'alpha_pluse' in df.columns:
            df['alpha_pluse_neutral'] = df['alpha_pluse']
            logger.info("  alpha_pluse 保持原始值（二值因子不中性化）")

        logger.info("  因子中性化完成")
        return df


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='六大因子选股策略')
    parser.add_argument('--date', type=str, required=True, help='目标日期 (YYYYMMDD)')
    parser.add_argument('--version', type=str, default='standard',
                       choices=['standard', 'conservative', 'aggressive'],
                       help='策略版本')
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("六大因子选股策略")
    print("=" * 80)
    print(f"日期: {args.date}")
    print(f"版本: {args.version}")
    print("=" * 80 + "\n")

    strategy = SixFactorStrategy(args.date, args.version)
    strategy.run()


if __name__ == '__main__':
    main()
