"""
估值因子 - alpha_peg
版本: v2.0
更新日期: 2025-12-30

核心逻辑: PE_TTM / 单季净利润同比增长率

数据来源:
- PE数据: daily_basic表，字段pe_ttm
- 财务数据: fina_indicator表，字段dt_netprofit_yoy
- 行业分类: sw_industry表，字段l1_name

计算公式: alpha_peg_raw = pe_ttm / dt_netprofit_yoy
行业标准化: alpha_peg_zscore = (alpha_peg_raw - 行业均值) / 行业标准差
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
import logging

from core.config.params import get_factor_param
from core.utils.db_connection import db
from core.utils.data_loader import data_loader
from core.utils.data_processor import calculate_alpha_peg_factor

logger = logging.getLogger(__name__)


class ValGrowQFactor:
    """alpha_peg因子计算类"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化因子计算参数

        Args:
            params: 因子参数字典
                {
                    'outlier_sigma': 3.0,      # 异常值阈值
                    'normalization': None,     # 标准化方法
                    'industry_specific': True  # 行业特定阈值
                }
        """
        self.params = params or get_factor_param('alpha_peg', 'standard')

    def calculate(
        self,
        df_pe: pd.DataFrame,
        df_fina: pd.DataFrame,
        df_industry: pd.DataFrame
    ) -> pd.DataFrame:
        """
        计算alpha_peg因子

        Args:
            df_pe: PE数据 (ts_code, trade_date, pe_ttm)
            df_fina: 财务数据 (ts_code, ann_date, dt_netprofit_yoy)
            df_industry: 行业数据 (ts_code, l1_name)

        Returns:
            DataFrame包含:
                ts_code, trade_date, l1_name, pe_ttm, dt_netprofit_yoy,
                alpha_peg_raw, alpha_peg_zscore, industry_rank
        """
        return calculate_alpha_peg_factor(
            df_pe=df_pe,
            df_fina=df_fina,
            df_industry=df_industry,
            outlier_sigma=self.params.get('outlier_sigma', 3.0),
            normalization=self.params.get('normalization', None),
            industry_specific=self.params.get('industry_specific', True)
        )

    def calculate_by_period(
        self,
        start_date: str,
        end_date: str,
        target_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        按时间段计算alpha_peg因子

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            target_date: 目标日期，用于获取最新数据 (YYYYMMDD)

        Returns:
            因子DataFrame
        """
        if target_date is None:
            target_date = end_date

        print(f"\n{'='*80}")
        print(f"计算alpha_peg因子: {target_date}")
        print(f"{'='*80}")

        # 获取可交易股票
        stocks = data_loader.get_tradable_stocks(target_date)
        if not stocks:
            logger.error("无有效股票")
            return pd.DataFrame()

        # 1. 获取PE数据
        df_pe, df_fina = data_loader.get_fina_data(stocks, target_date)

        if len(df_pe) == 0 or len(df_fina) == 0:
            logger.error("PE或财务数据为空")
            return pd.DataFrame()

        # 2. 获取行业数据
        df_industry = data_loader.get_industry_data(stocks)

        # 3. 计算因子
        df_result = self.calculate(df_pe, df_fina, df_industry)

        # 4. 添加目标日期
        if len(df_result) > 0:
            df_result['trade_date'] = target_date

        return df_result

    def calculate_industry_zscore(
        self,
        df_peg: pd.DataFrame,
        df_industry: pd.DataFrame
    ) -> pd.DataFrame:
        """
        计算行业Z-Score标准化

        Args:
            df_peg: 原始alpha_peg数据
            df_industry: 行业数据

        Returns:
            包含行业标准化的DataFrame
        """
        if len(df_peg) == 0:
            return pd.DataFrame()

        # 合并行业
        if len(df_industry) > 0:
            df_industry_unique = df_industry.drop_duplicates(subset=['ts_code'], keep='first')
            df_merged = df_peg.merge(df_industry_unique, on='ts_code', how='left')
            df_merged['l1_name'] = df_merged['l1_name'].fillna('其他')
        else:
            df_merged = df_peg.copy()
            df_merged['l1_name'] = '其他'

        # 计算Z-Score
        def zscore(group):
            values = group['alpha_peg_raw'].astype(float)
            mean = values.mean()
            std = values.std()
            if std == 0 or pd.isna(std) or len(values) < 2:
                return pd.Series([0.0] * len(group), index=group.index)
            return (values - mean) / std

        df_merged['alpha_peg_zscore'] = df_merged.groupby('l1_name').apply(zscore).reset_index(level=0, drop=True)

        # 过滤样本不足的行业
        min_samples = self.params.get('industry_threshold', 5)
        industry_counts = df_merged.groupby('l1_name').size()
        valid_industries = industry_counts[industry_counts >= min_samples].index
        df_merged = df_merged[df_merged['l1_name'].isin(valid_industries)]

        logger.info(f"行业标准化完成: {len(df_merged)}条记录, {len(valid_industries)}个行业")

        return df_merged

    def select_top_n_by_industry(
        self,
        factor_df: pd.DataFrame,
        top_n: int = 3
    ) -> pd.DataFrame:
        """
        每行业选择alpha_peg排名前N的个股

        Args:
            factor_df: 因子DataFrame
            top_n: 每行业选股数量

        Returns:
            选股DataFrame
        """
        if len(factor_df) == 0:
            return pd.DataFrame()

        print(f"\n{'='*80}")
        print(f"每行业选择前{top_n}名个股")
        print(f"{'='*80}")

        selected = []

        # 使用行业标准化alpha_peg进行排序
        sort_col = 'alpha_peg_zscore' if 'alpha_peg_zscore' in factor_df.columns else 'alpha_peg_raw'

        for (trade_date, industry), group in factor_df.groupby(['trade_date', 'l1_name']):
            # 确保有足够的股票
            if len(group) >= top_n:
                # alpha_peg越小越好
                top_n_stocks = group.nsmallest(top_n, sort_col)[
                    ['ts_code', 'trade_date', 'l1_name', sort_col]
                ]
                selected.append(top_n_stocks)

        if not selected:
            logger.warning("未选出任何股票")
            return pd.DataFrame()

        df_selected = pd.concat(selected, ignore_index=True)

        logger.info(f"选中记录数: {len(df_selected):,}")

        return df_selected

    def get_factor_stats(self, factor_df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取因子统计信息

        Args:
            factor_df: 因子DataFrame

        Returns:
            统计信息字典
        """
        if len(factor_df) == 0:
            return {}

        stats = {
            'total_records': len(factor_df),
            'stock_count': factor_df['ts_code'].nunique(),
            'industry_count': factor_df['l1_name'].nunique(),
            'date_count': factor_df['trade_date'].nunique() if 'trade_date' in factor_df.columns else 1,
        }

        # 统计各列
        for col in ['alpha_peg_raw', 'alpha_peg_zscore']:
            if col in factor_df.columns:
                valid_data = factor_df[col].dropna()
                stats[f'{col}_mean'] = valid_data.mean()
                stats[f'{col}_std'] = valid_data.std()
                stats[f'{col}_min'] = valid_data.min()
                stats[f'{col}_max'] = valid_data.max()

        return stats


# 工厂函数
def create_factor(version: str = 'standard') -> ValGrowQFactor:
    """
    创建指定版本的alpha_peg因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        ValGrowQFactor实例
    """
    try:
        params = get_factor_param('alpha_peg', version)
        logger.info(f"创建alpha_peg因子 - 版本: {version}, 参数: {params}")
        return ValGrowQFactor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        # 回退到标准版
        params = get_factor_param('alpha_peg', 'standard')
        return ValGrowQFactor(params)


__all__ = [
    'ValGrowQFactor',
    'create_factor',
]