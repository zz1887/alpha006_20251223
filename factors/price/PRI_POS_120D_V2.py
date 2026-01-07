"""
价格位置因子 - alpha_120cq
版本: v2.0
更新日期: 2025-12-30

核心逻辑: 当日收盘价在120日有效交易日序列中的分位数

计算公式:
    alpha_120cq = (rank - 1) / (N - 1)
    其中:
        rank = 当日close在120日序列中的排名（1=最小，N=最大）
        N = 有效交易日数量（≤120）

数据来源:
    - daily_kline表: ts_code, trade_date, close
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from core.config.params import get_factor_param
from core.utils.db_connection import db
from core.utils.data_loader import data_loader

logger = logging.getLogger(__name__)


class PriPos120Dv2Factor:
    """alpha_120cq因子计算类"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化因子计算参数

        Args:
            params: 因子参数字典
                {
                    'window': 120,             # 窗口期
                    'min_days': 30,            # 最小有效天数
                    'min_data_days': 120       # 最小数据天数
                }
        """
        self.params = params or get_factor_param('alpha_120cq', 'standard')

    def calculate(self, price_df: pd.DataFrame, target_date: str) -> pd.DataFrame:
        """
        计算alpha_120cq因子

        Args:
            price_df: 价格数据，包含ts_code, trade_date, close
            target_date: 目标日期 (YYYYMMDD)

        Returns:
            DataFrame包含ts_code, alpha_120cq
        """
        if len(price_df) == 0:
            return pd.DataFrame()

        window = self.params.get('window', 120)
        min_days = self.params.get('min_days', 30)
        min_data_days = self.params.get('min_data_days', 120)

        target_date_dt = pd.to_datetime(target_date, format='%Y%m%d')
        results = []
        nan_reasons = {}

        for ts_code, group in price_df.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            # 获取目标日数据
            target_row = group[group['trade_date'] == target_date_dt]

            if len(target_row) == 0:
                nan_reasons[ts_code] = "目标日期无数据"
                continue

            target_close = target_row.iloc[0]['close']

            if pd.isna(target_close) or target_close <= 0:
                nan_reasons[ts_code] = "当日收盘价异常"
                continue

            # 获取窗口数据
            window_data = group[group['trade_date'] <= target_date_dt]

            if len(window_data) < min_data_days:
                nan_reasons[ts_code] = f"数据不足({len(window_data)}天<{min_data_days}天)"
                continue

            # 取最近的N个交易日
            window_120 = window_data.tail(window)
            N = len(window_120)

            if N < min_days:
                nan_reasons[ts_code] = f"有效数据不足{min_days}个"
                continue

            # 计算排名
            close_values = window_120['close'].values
            rank = (close_values <= target_close).sum()

            # 计算分位数
            if N == 1:
                alpha_120cq = 0.5
            else:
                alpha_120cq = (rank - 1) / (N - 1)

            results.append({
                'ts_code': ts_code,
                'alpha_120cq': alpha_120cq,
            })

        df_result = pd.DataFrame(results)

        if len(df_result) > 0:
            logger.info(f"alpha_120cq计算完成: {len(df_result)}只股票")

        return df_result

    def calculate_by_period(
        self,
        start_date: str,
        end_date: str,
        target_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        按时间段计算alpha_120cq因子

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
        print(f"计算alpha_120cq因子: {target_date}")
        print(f"{'='*80}")

        # 获取可交易股票
        stocks = data_loader.get_tradable_stocks(target_date)
        if not stocks:
            logger.error("无有效股票")
            return pd.DataFrame()

        # 获取价格数据（需要足够长的历史）
        # 计算开始日期（需要额外缓冲）
        target_dt = datetime.strptime(target_date, '%Y%m%d')
        start_dt = target_dt - timedelta(days=150)  # 150天缓冲
        start_date_calc = start_dt.strftime('%Y%m%d')

        price_df = data_loader.get_price_data(stocks, start_date_calc, target_date)

        if len(price_df) == 0:
            logger.error("价格数据为空")
            return pd.DataFrame()

        # 计算因子
        df_result = self.calculate(price_df, target_date)

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

        if 'alpha_120cq' in factor_df.columns:
            valid_data = factor_df['alpha_120cq'].dropna()
            stats['alpha_120cq_mean'] = valid_data.mean()
            stats['alpha_120cq_std'] = valid_data.std()
            stats['alpha_120cq_min'] = valid_data.min()
            stats['alpha_120cq_max'] = valid_data.max()
            stats['alpha_120cq_median'] = valid_data.median()

        return stats


# 工厂函数
def create_factor(version: str = 'standard') -> PriPos120Dv2Factor:
    """
    创建指定版本的alpha_120cq因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        PriPos120Dv2Factor实例
    """
    try:
        params = get_factor_param('alpha_120cq', version)
        logger.info(f"创建alpha_120cq因子 - 版本: {version}, 参数: {params}")
        return PriPos120Dv2Factor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        # 回退到标准版
        params = get_factor_param('alpha_120cq', 'standard')
        return PriPos120Dv2Factor(params)


__all__ = [
    'PriPos120Dv2Factor',
    'create_factor',
]