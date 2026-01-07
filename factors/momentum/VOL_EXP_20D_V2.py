"""
量能因子 - alpha_pluse
版本: v2.0
更新日期: 2025-12-30

核心逻辑: 20日内满足「交易量=14日均值的1.4-3.5倍」的交易日数量∈[2,4]则=1，否则=0

计算公式:
    alpha_pluse = 1 if count_20d ∈ [2,4] else 0
    count_20d = sum(vol_t ∈ [1.4×mean_14d, 3.5×mean_14d] for t in T-19 to T)

数据来源:
    - daily_kline表: ts_code, trade_date, vol
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import logging

from core.config.params import get_factor_param
from core.utils.db_connection import db
from core.utils.data_loader import data_loader

logger = logging.getLogger(__name__)


class VolExp20Dv2Factor:
    """alpha_pluse因子计算类"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化因子计算参数

        Args:
            params: 因子参数字典
                {
                    'window_20d': 20,          # 回溯窗口
                    'lookback_14d': 14,        # 均值周期
                    'lower_mult': 1.4,         # 下限倍数
                    'upper_mult': 3.5,         # 上限倍数
                    'min_count': 2,            # 最小满足数量
                    'max_count': 4,            # 最大满足数量
                    'min_data_days': 34        # 最小数据天数
                }
        """
        self.params = params or get_factor_param('alpha_pluse', 'standard')

    def calculate(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算alpha_pluse因子

        Args:
            price_df: 价格数据，包含ts_code, trade_date, vol

        Returns:
            DataFrame包含ts_code, alpha_pluse, count_20d
        """
        if len(price_df) == 0:
            return pd.DataFrame()

        window_20d = self.params.get('window_20d', 20)
        lookback_14d = self.params.get('lookback_14d', 14)
        lower_mult = self.params.get('lower_mult', 1.4)
        upper_mult = self.params.get('upper_mult', 3.5)
        min_count = self.params.get('min_count', 2)
        max_count = self.params.get('max_count', 4)
        min_data_days = self.params.get('min_data_days', 34)

        results = []
        nan_reasons = {}

        for ts_code, group in price_df.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            # 数据不足检查
            if len(group) < min_data_days:
                nan_reasons[ts_code] = f"数据不足({len(group)}天<{min_data_days}天)"
                continue

            # 计算14日均值
            group['vol_14_mean'] = group['vol'].rolling(
                window=lookback_14d, min_periods=lookback_14d
            ).mean()

            # 标记条件
            group['condition'] = (
                (group['vol'] >= group['vol_14_mean'] * lower_mult) &
                (group['vol'] <= group['vol_14_mean'] * upper_mult) &
                group['vol_14_mean'].notna()
            )

            # 20日滚动计数
            def count_conditions(idx):
                if idx < window_20d - 1:
                    return np.nan
                window_data = group.iloc[idx - window_20d + 1:idx + 1]
                return window_data['condition'].sum()

            group['count_20d'] = [count_conditions(i) for i in range(len(group))]

            # 计算alpha_pluse
            group['alpha_pluse'] = (
                (group['count_20d'] >= min_count) &
                (group['count_20d'] <= max_count)
            ).astype(int)

            # 获取最后一天结果
            if len(group) > 0:
                last_row = group.iloc[-1]
                results.append({
                    'ts_code': ts_code,
                    'alpha_pluse': int(last_row['alpha_pluse']),
                    'count_20d': last_row['count_20d'],
                })

        df_result = pd.DataFrame(results)

        if len(df_result) > 0:
            signal_count = df_result['alpha_pluse'].sum()
            logger.info(f"alpha_pluse计算完成: {len(df_result)}只股票, 信号数: {signal_count}, 信号比例: {signal_count/len(df_result):.2%}")

        return df_result

    def calculate_by_period(
        self,
        start_date: str,
        end_date: str,
        target_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        按时间段计算alpha_pluse因子

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
        print(f"计算alpha_pluse因子: {target_date}")
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
            'signal_count': factor_df['alpha_pluse'].sum(),
            'signal_ratio': factor_df['alpha_pluse'].mean(),
        }

        if 'count_20d' in factor_df.columns:
            valid_data = factor_df['count_20d'].dropna()
            stats['count_mean'] = valid_data.mean()
            stats['count_std'] = valid_data.std()
            stats['count_min'] = valid_data.min()
            stats['count_max'] = valid_data.max()

        return stats


# 工厂函数
def create_factor(version: str = 'standard') -> VolExp20Dv2Factor:
    """
    创建指定版本的alpha_pluse因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        VolExp20Dv2Factor实例
    """
    try:
        params = get_factor_param('alpha_pluse', version)
        logger.info(f"创建alpha_pluse因子 - 版本: {version}, 参数: {params}")
        return VolExp20Dv2Factor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        # 回退到标准版
        params = get_factor_param('alpha_pluse', 'standard')
        return VolExp20Dv2Factor(params)


__all__ = [
    'VolExp20Dv2Factor',
    'create_factor',
]