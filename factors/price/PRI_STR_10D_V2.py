"""
价格强度因子 - alpha_038
版本: v2.0
更新日期: 2025-12-30

核心逻辑: 短期价格排名与当日涨跌幅的组合特征

计算公式:
    alpha_038 = (-1 × rank(Ts_Rank(close, 10))) × rank(close/open)

其中:
    - Ts_Rank(close, 10): 目标日close在10日序列中的排名(1=最小,10=最大)
    - rank(close/open): 所有股票close/open比值的降序排名(1=最大)

数据来源:
    - daily_kline表: ts_code, trade_date, open, close
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import logging

from core.config.params import get_factor_param
from core.utils.db_connection import db
from core.utils.data_loader import data_loader

logger = logging.getLogger(__name__)


class PriStr10Dv2Factor:
    """alpha_038因子计算类"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化因子计算参数

        Args:
            params: 因子参数字典
                {
                    'window': 10,              # 窗口期
                    'min_data_days': 10        # 最小数据天数
                }
        """
        self.params = params or get_factor_param('alpha_038', 'standard')

    def calculate(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算alpha_038因子

        Args:
            price_df: 价格数据，包含ts_code, trade_date, open, close

        Returns:
            DataFrame包含ts_code, alpha_038
        """
        if len(price_df) == 0:
            return pd.DataFrame()

        window = self.params.get('window', 10)
        min_data_days = self.params.get('min_data_days', 10)

        results = []
        nan_reasons = {}

        for ts_code, group in price_df.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            # 检查数据
            if len(group) < min_data_days:
                nan_reasons[ts_code] = f"数据不足({len(group)}天<{min_data_days}天)"
                continue

            # 获取最后一条数据
            target_row = group.iloc[-1]

            # 检查open
            if pd.isna(target_row['open']) or target_row['open'] == 0:
                nan_reasons[ts_code] = "open为NaN或0"
                continue

            # 获取窗口数据
            window_data = group.tail(window).copy()

            # 1. Ts_Rank(close, 10)
            close_values = window_data['close'].values
            target_close = target_row['close']
            close_rank = (close_values <= target_close).sum()

            # 2. close/open
            close_over_open = target_close / target_row['open']

            results.append({
                'ts_code': ts_code,
                'close_rank': close_rank,
                'close_over_open': close_over_open,
            })

        df_result = pd.DataFrame(results)

        if len(df_result) == 0:
            return pd.DataFrame()

        # 计算rank(close_over_open)
        df_result['rank_close_over_open'] = df_result['close_over_open'].rank(ascending=False, method='min')

        # 计算最终alpha_038
        df_result['alpha_038'] = (-1 * df_result['close_rank']) * df_result['rank_close_over_open']

        logger.info(f"alpha_038计算完成: {len(df_result)}只股票")

        return df_result[['ts_code', 'alpha_038']]

    def calculate_by_period(
        self,
        start_date: str,
        end_date: str,
        target_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        按时间段计算alpha_038因子

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            target_date: 目标日期 (YYYYMMDD)

        Returns:
            因子DataFrame
        """
        if target_date is None:
            target_date = end_date

        print(f"\n{'='*80}")
        print(f"计算alpha_038因子: {target_date}")
        print(f"{'='*80}")

        # 获取可交易股票
        stocks = data_loader.get_tradable_stocks(target_date)
        if not stocks:
            logger.error("无有效股票")
            return pd.DataFrame()

        # 获取价格数据
        price_df = data_loader.get_price_data(stocks, start_date, target_date)

        if len(price_df) == 0:
            logger.error("价格数据为空")
            return pd.DataFrame()

        # 计算因子
        df_result = self.calculate(price_df)

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

        if 'alpha_038' in factor_df.columns:
            valid_data = factor_df['alpha_038'].dropna()
            stats['alpha_038_mean'] = valid_data.mean()
            stats['alpha_038_std'] = valid_data.std()
            stats['alpha_038_min'] = valid_data.min()
            stats['alpha_038_max'] = valid_data.max()

        return stats


# 工厂函数
def create_factor(version: str = 'standard') -> PriStr10Dv2Factor:
    """
    创建指定版本的alpha_038因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        PriStr10Dv2Factor实例
    """
    try:
        params = get_factor_param('alpha_038', version)
        logger.info(f"创建alpha_038因子 - 版本: {version}, 参数: {params}")
        return PriStr10Dv2Factor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        # 回退到标准版
        params = get_factor_param('alpha_038', 'standard')
        return PriStr10Dv2Factor(params)


__all__ = [
    'PriStr10Dv2Factor',
    'create_factor',
]