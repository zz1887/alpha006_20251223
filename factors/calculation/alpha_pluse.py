"""
文件input(依赖外部什么): pandas, numpy, factors.core.base_factor, core.config.params, core.utils.data_loader
文件output(提供什么): alpha_pluse因子标准计算类，继承BaseFactor基类
文件pos(系统局部地位): 因子计算层 - 20日量能扩张因子实现

详细说明:
1. 因子逻辑: 20日内满足「交易量=14日均值的1.4-3.5倍」的交易日数量∈[2,4]则=1，否则=0
2. 计算公式:
   - alpha_pluse = 1 if count_20d ∈ [2,4] else 0
   - count_20d = sum(vol_t ∈ [1.4×mean_14d, 3.5×mean_14d] for t in T-19 to T)
3. 数据来源: stock_database.daily_kline表
4. 异常值处理: 删除NaN值，检查成交量>0

使用示例:
    from factors.calculation.alpha_pluse import AlphaPluseFactor
    factor = AlphaPluseFactor()
    result = factor.calculate(data)

返回值:
    DataFrame包含ts_code, trade_date, factor列
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import logging

from factors.core.base_factor import BaseFactor
from core.config.params import get_factor_param
from core.utils.data_loader import data_loader

logger = logging.getLogger(__name__)


class AlphaPluseFactor(BaseFactor):
    """alpha_pluse因子标准计算类"""

    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'window_20d': 20,          # 回溯窗口
            'lookback_14d': 14,        # 均值周期
            'lower_mult': 1.4,         # 下限倍数
            'upper_mult': 3.5,         # 上限倍数
            'min_count': 2,            # 最小满足数量
            'max_count': 4,            # 最大满足数量
            'min_data_days': 34,       # 最小数据天数
            'outlier_sigma': 3.0,      # 异常值阈值
        }

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        验证输入数据

        Args:
            data: 输入数据，应包含ts_code, trade_date, vol列

        Returns:
            bool: 数据是否有效
        """
        if data is None or len(data) == 0:
            logger.warning("输入数据为空")
            return False

        required_cols = ['ts_code', 'trade_date', 'vol']
        missing_cols = [col for col in required_cols if col not in data.columns]

        if missing_cols:
            logger.warning(f"缺少必要列: {missing_cols}")
            return False

        # 检查数据质量
        if data['vol'].isna().all():
            logger.warning("vol列全为NaN")
            return False

        return True

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算alpha_pluse因子

        Args:
            data: 包含ts_code, trade_date, vol的DataFrame

        Returns:
            DataFrame包含ts_code, trade_date, factor列
        """
        if not self.validate_data(data):
            return pd.DataFrame()

        window_20d = self.params.get('window_20d', 20)
        lookback_14d = self.params.get('lookback_14d', 14)
        lower_mult = self.params.get('lower_mult', 1.4)
        upper_mult = self.params.get('upper_mult', 3.5)
        min_count = self.params.get('min_count', 2)
        max_count = self.params.get('max_count', 4)
        min_data_days = self.params.get('min_data_days', 34)

        results = []

        for ts_code, group in data.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            # 数据不足检查
            if len(group) < min_data_days:
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
                if not pd.isna(last_row['count_20d']):
                    results.append({
                        'ts_code': ts_code,
                        'trade_date': last_row['trade_date'],
                        'factor': int(last_row['alpha_pluse']),
                        'count_20d': last_row['count_20d'],
                    })

        if not results:
            return pd.DataFrame()

        df_result = pd.DataFrame(results)

        # 异常值处理（虽然alpha_pluse是0/1，但保留框架）
        outlier_sigma = self.params.get('outlier_sigma', 3.0)
        if outlier_sigma > 0:
            df_result = self._winsorize(df_result, 'count_20d', outlier_sigma)

        # 保留必要列
        result = df_result[['ts_code', 'trade_date', 'factor']].copy()

        signal_count = result['factor'].sum()
        logger.info(f"alpha_pluse计算完成: {len(result)}只股票, 信号数: {signal_count}, 信号比例: {signal_count/len(result):.2%}")

        return result

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
        result = self.calculate(price_df)

        return result

    def _winsorize(self, df: pd.DataFrame, column: str, sigma: float) -> pd.DataFrame:
        """缩尾处理"""
        if sigma <= 0:
            return df

        values = df[column].dropna()
        if len(values) == 0:
            return df

        mean = values.mean()
        std = values.std()

        if std == 0:
            return df

        lower_bound = mean - sigma * std
        upper_bound = mean + sigma * std

        df[column] = np.clip(df[column], lower_bound, upper_bound)

        return df


# 工厂函数
def create_factor(version: str = 'standard') -> AlphaPluseFactor:
    """
    创建指定版本的alpha_pluse因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        AlphaPluseFactor实例
    """
    try:
        params = get_factor_param('alpha_pluse', version)
        logger.info(f"创建alpha_pluse因子 - 版本: {version}, 参数: {params}")
        return AlphaPluseFactor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        params = get_factor_param('alpha_pluse', 'standard')
        return AlphaPluseFactor(params)


__all__ = [
    'AlphaPluseFactor',
    'create_factor',
]
