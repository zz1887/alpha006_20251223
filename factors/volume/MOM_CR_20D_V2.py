"""
动量因子 - cr_qfq
版本: v2.0
更新日期: 2025-12-30

核心逻辑: CR指标（N=20），基于前复权的HIGH/LOW/CLOSE计算

计算公式:
    CR = SUM(HIGH - REF(CLOSE, 1), N) / SUM(REF(CLOSE, 1) - LOW, N) × 100

其中:
    - N = 20
    - 数据为前复权
    - CR指标衡量多空力量对比

数据来源:
    - stk_factor_pro表: ts_code, trade_date, cr_qfq
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
import logging

from core.config.params import get_factor_param
from core.utils.db_connection import db
from core.utils.data_loader import data_loader

logger = logging.getLogger(__name__)


class MomCr20Dv2Factor:
    """cr_qfq因子计算类"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化因子计算参数

        Args:
            params: 因子参数字典
                {
                    'period': 20,              # 周期
                    'source_table': 'stk_factor_pro',  # 数据来源表
                    'normalization': 'max_scale'  # 标准化方法
                }
        """
        self.params = params or get_factor_param('cr_qfq', 'standard')

    def calculate(self, df_cr: pd.DataFrame) -> pd.DataFrame:
        """
        计算cr_qfq因子（实际是从数据库读取预计算值）

        Args:
            df_cr: CR数据，包含ts_code, trade_date, cr_qfq

        Returns:
            DataFrame包含ts_code, cr_qfq
        """
        if len(df_cr) == 0:
            return pd.DataFrame()

        # 保留必要列
        result = df_cr[['ts_code', 'cr_qfq']].copy()

        logger.info(f"cr_qfq数据加载完成: {len(result)}条记录")

        return result

    def calculate_by_period(
        self,
        target_date: str,
        stocks: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        按日期获取cr_qfq因子

        Args:
            target_date: 目标日期 (YYYYMMDD)
            stocks: 股票列表，None则获取所有可交易股票

        Returns:
            因子DataFrame
        """
        print(f"\n{'='*80}")
        print(f"获取cr_qfq因子: {target_date}")
        print(f"{'='*80}")

        if stocks is None:
            stocks = data_loader.get_tradable_stocks(target_date)

        if not stocks:
            logger.error("无有效股票")
            return pd.DataFrame()

        # 从数据库获取CR数据
        placeholders = ','.join(['%s'] * len(stocks))
        source_table = self.params.get('source_table', 'stk_factor_pro')

        sql = f"""
        SELECT ts_code, trade_date, cr_qfq
        FROM {source_table}
        WHERE trade_date = %s
          AND ts_code IN ({placeholders})
        """

        data = db.execute_query(sql, [target_date] + stocks)
        df = pd.DataFrame(data)

        if len(df) == 0:
            logger.warning("未获取到CR数据")
            return df

        logger.info(f"获取CR数据: {len(df)}条记录")

        return df

    def normalize(self, df_cr: pd.DataFrame, method: Optional[str] = None) -> pd.DataFrame:
        """
        标准化CR指标

        Args:
            df_cr: CR数据
            method: 标准化方法，None则使用参数配置

        Returns:
            标准化后的数据
        """
        if len(df_cr) == 0:
            return df_cr

        if method is None:
            method = self.params.get('normalization', 'max_scale')

        df_result = df_cr.copy()

        if method == 'max_scale':
            max_val = df_result['cr_qfq'].max()
            if max_val > 0:
                df_result['cr_qfq_norm'] = df_result['cr_qfq'] / max_val
            else:
                df_result['cr_qfq_norm'] = 0
            logger.info(f"CR指标最大值标准化: max={max_val:.4f}")
        elif method == 'zscore':
            mean = df_result['cr_qfq'].mean()
            std = df_result['cr_qfq'].std()
            if std > 0:
                df_result['cr_qfq_norm'] = (df_result['cr_qfq'] - mean) / std
            else:
                df_result['cr_qfq_norm'] = 0
            logger.info(f"CR指标Z-Score标准化: mean={mean:.4f}, std={std:.4f}")
        else:
            df_result['cr_qfq_norm'] = df_result['cr_qfq']

        return df_result

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
        }

        for col in ['cr_qfq', 'cr_qfq_norm']:
            if col in factor_df.columns:
                valid_data = factor_df[col].dropna()
                stats[f'{col}_mean'] = valid_data.mean()
                stats[f'{col}_std'] = valid_data.std()
                stats[f'{col}_min'] = valid_data.min()
                stats[f'{col}_max'] = valid_data.max()

        return stats


# 工厂函数
def create_factor(version: str = 'standard') -> MomCr20Dv2Factor:
    """
    创建指定版本的cr_qfq因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        MomCr20Dv2Factor实例
    """
    try:
        params = get_factor_param('cr_qfq', version)
        logger.info(f"创建cr_qfq因子 - 版本: {version}, 参数: {params}")
        return MomCr20Dv2Factor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        # 回退到标准版
        params = get_factor_param('cr_qfq', 'standard')
        return MomCr20Dv2Factor(params)


__all__ = [
    'MomCr20Dv2Factor',
    'create_factor',
]