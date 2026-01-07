"""
价格趋势因子 - alpha_010
版本: v2.0
更新日期: 2025-12-30

核心逻辑: 短周期（4日）股价涨跌一致性特征

计算公式:
    1. 计算每日涨跌幅: Δclose = close_t - close_{t-1}
    2. 统计4日Δclose的ts_min/ts_max
    3. 三元规则取值:
       - 如果 ts_min > 0: 说明4日连续上涨，取 Δclose（正值）
       - 如果 ts_max < 0: 说明4日连续下跌，取 Δclose（负值）
       - 否则: 取 -Δclose（反转信号）
    4. 全市场rank（从小到大）得到alpha_010

数据来源:
    - daily_kline表: ts_code, trade_date, close
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import logging

from core.config.params import get_factor_param
from core.utils.db_connection import db
from core.utils.data_loader import data_loader

logger = logging.getLogger(__name__)


class PriTrend4Dv2Factor:
    """alpha_010因子计算类"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化因子计算参数

        Args:
            params: 因子参数字典
                {
                    'window': 4,              # 窗口期（4日）
                    'min_data_days': 5        # 最小数据天数（4+1）
                }
        """
        self.params = params or get_factor_param('alpha_010', 'standard')

    def calculate(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算alpha_010因子

        Args:
            price_df: 价格数据，包含ts_code, trade_date, close

        Returns:
            DataFrame包含ts_code, alpha_010, delta_close, ts_min, ts_max, rule_value
        """
        if len(price_df) == 0:
            return pd.DataFrame()

        window = self.params.get('window', 4)
        min_data_days = self.params.get('min_data_days', 5)

        results = []
        nan_reasons = {}

        for ts_code, group in price_df.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            # 检查数据
            if len(group) < min_data_days:
                nan_reasons[ts_code] = f"数据不足({len(group)}天<{min_data_days}天)"
                continue

            # 计算每日涨跌幅 Δclose
            group['delta_close'] = group['close'].diff()

            # 获取最后一条数据（目标日）
            target_row = group.iloc[-1]

            # 检查是否有有效涨跌幅
            if pd.isna(target_row['delta_close']):
                nan_reasons[ts_code] = "目标日Δclose为NaN"
                continue

            # 获取最近4日的Δclose（包含目标日）
            window_data = group.tail(window + 1).copy()  # 需要4个Δclose值
            if len(window_data) < window + 1:
                nan_reasons[ts_code] = f"窗口数据不足"
                continue

            # 计算4日Δclose的ts_min和ts_max
            delta_values = window_data['delta_close'].dropna().values
            if len(delta_values) < window:
                nan_reasons[ts_code] = "Δclose数据不足4个"
                continue

            ts_min = delta_values.min()
            ts_max = delta_values.max()
            target_delta = target_row['delta_close']

            # 三元规则取值
            if ts_min > 0:
                # 4日连续上涨
                rule_value = target_delta
                rule_type = "连续上涨"
            elif ts_max < 0:
                # 4日连续下跌
                rule_value = target_delta
                rule_type = "连续下跌"
            else:
                # 震荡或反转
                rule_value = -target_delta
                rule_type = "震荡反转"

            results.append({
                'ts_code': ts_code,
                'delta_close': target_delta,
                'ts_min': ts_min,
                'ts_max': ts_max,
                'rule_value': rule_value,
                'rule_type': rule_type,
            })

        df_result = pd.DataFrame(results)

        if len(df_result) == 0:
            return pd.DataFrame()

        # 全市场rank（从小到大）
        df_result['alpha_010'] = df_result['rule_value'].rank(method='min')

        logger.info(f"alpha_010计算完成: {len(df_result)}只股票")

        return df_result[['ts_code', 'alpha_010', 'delta_close', 'ts_min', 'ts_max', 'rule_value', 'rule_type']]

    def calculate_by_period(
        self,
        start_date: str,
        end_date: str,
        target_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        按时间段计算alpha_010因子

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
        print(f"计算alpha_010因子: {target_date}")
        print(f"{'='*80}")

        # 获取可交易股票
        stocks = data_loader.get_tradable_stocks(target_date)
        if not stocks:
            logger.error("无有效股票")
            return pd.DataFrame()

        # 获取价格数据（需要足够长的历史）
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

        if 'alpha_010' in factor_df.columns:
            valid_data = factor_df['alpha_010'].dropna()
            stats['alpha_010_mean'] = valid_data.mean()
            stats['alpha_010_std'] = valid_data.std()
            stats['alpha_010_min'] = valid_data.min()
            stats['alpha_010_max'] = valid_data.max()
            stats['alpha_010_median'] = valid_data.median()

        return stats


# 工厂函数
def create_factor(version: str = 'standard') -> PriTrend4Dv2Factor:
    """
    创建指定版本的alpha_010因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        PriTrend4Dv2Factor实例
    """
    try:
        params = get_factor_param('alpha_010', version)
        logger.info(f"创建alpha_010因子 - 版本: {version}, 参数: {params}")
        return PriTrend4Dv2Factor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        # 回退到标准版
        params = get_factor_param('alpha_010', 'standard')
        return PriTrend4Dv2Factor(params)


__all__ = [
    'PriTrend4Dv2Factor',
    'create_factor',
]