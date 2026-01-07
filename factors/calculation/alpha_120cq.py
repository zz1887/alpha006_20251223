"""
文件input(依赖外部什么): pandas, numpy, factors.core.base_factor, core.config.params, core.utils.data_loader
文件output(提供什么): alpha_120cq因子标准计算类，继承BaseFactor基类
文件pos(系统局部地位): 因子计算层 - 120日价格位置因子实现

详细说明:
1. 因子逻辑: 当日收盘价在120日有效交易日序列中的分位数
2. 计算公式: alpha_120cq = (rank - 1) / (N - 1)
   - rank = 当日close在120日序列中的排名（1=最小，N=最大）
   - N = 有效交易日数量（≤120）
3. 数据来源: stock_database.daily_kline表
4. 异常值处理: 删除NaN值，检查收盘价>0

使用示例:
    from factors.calculation.alpha_120cq import Alpha120CqFactor
    factor = Alpha120CqFactor()
    result = factor.calculate(data, target_date)

返回值:
    DataFrame包含ts_code, trade_date, factor列
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from factors.core.base_factor import BaseFactor
from core.config.params import get_factor_param
from core.utils.data_loader import data_loader

logger = logging.getLogger(__name__)


class Alpha120CqFactor(BaseFactor):
    """alpha_120cq因子标准计算类"""

    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'window': 120,             # 窗口期
            'min_days': 30,            # 最小有效天数
            'min_data_days': 120,      # 最小数据天数
            'outlier_sigma': 3.0,      # 异常值阈值
            'normalization': None,     # 标准化方法
        }

    def validate_data(self, data: pd.DataFrame, target_date: str) -> bool:
        """
        验证输入数据

        Args:
            data: 输入数据
            target_date: 目标日期

        Returns:
            bool: 数据是否有效
        """
        if data is None or len(data) == 0:
            logger.warning("输入数据为空")
            return False

        required_cols = ['ts_code', 'trade_date', 'close']
        missing_cols = [col for col in required_cols if col not in data.columns]

        if missing_cols:
            logger.warning(f"缺少必要列: {missing_cols}")
            return False

        return True

    def calculate(self, data: pd.DataFrame, target_date: str) -> pd.DataFrame:
        """
        计算alpha_120cq因子

        Args:
            data: 包含ts_code, trade_date, close的DataFrame
            target_date: 目标日期 (YYYYMMDD)

        Returns:
            DataFrame包含ts_code, trade_date, factor列
        """
        if not self.validate_data(data, target_date):
            return pd.DataFrame()

        window = self.params.get('window', 120)
        min_days = self.params.get('min_days', 30)
        min_data_days = self.params.get('min_data_days', 120)

        target_date_dt = pd.to_datetime(target_date, format='%Y%m%d')

        # 确保trade_date是datetime类型
        data = data.copy()
        data['trade_date'] = pd.to_datetime(data['trade_date'], format='%Y%m%d')

        results = []

        for ts_code, group in data.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            # 获取目标日数据
            target_row = group[group['trade_date'] == target_date_dt]

            if len(target_row) == 0:
                continue

            target_close = target_row.iloc[0]['close']

            if pd.isna(target_close) or target_close <= 0:
                continue

            # 获取窗口数据
            window_data = group[group['trade_date'] <= target_date_dt]

            if len(window_data) < min_data_days:
                continue

            # 取最近的N个交易日
            window_120 = window_data.tail(window)
            N = len(window_120)

            if N < min_days:
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
                'trade_date': target_date_dt,
                'factor': alpha_120cq,
            })

        if not results:
            return pd.DataFrame()

        df_result = pd.DataFrame(results)

        # 异常值处理
        outlier_sigma = self.params.get('outlier_sigma', 3.0)
        if outlier_sigma > 0:
            df_result = self._winsorize(df_result, 'factor', outlier_sigma)

        # 可选标准化
        normalization = self.params.get('normalization', None)
        if normalization:
            df_result = self._normalize(df_result, normalization)

        logger.info(f"alpha_120cq因子计算完成: {len(df_result)}只股票")

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

        # 计算开始日期（需要额外缓冲）
        target_dt = datetime.strptime(target_date, '%Y%m%d')
        start_dt = target_dt - timedelta(days=150)  # 150天缓冲
        start_date_calc = start_dt.strftime('%Y%m%d')

        # 获取价格数据
        price_df = data_loader.get_price_data(stocks, start_date_calc, target_date)

        if len(price_df) == 0:
            logger.error("价格数据为空")
            return pd.DataFrame()

        # 计算因子
        result = self.calculate(price_df, target_date)

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

    def _normalize(self, df: pd.DataFrame, method: str) -> pd.DataFrame:
        """标准化处理"""
        if method == 'zscore':
            mean = df['factor'].mean()
            std = df['factor'].std()
            if std > 0:
                df['factor'] = (df['factor'] - mean) / std
        elif method == 'rank':
            df['factor'] = df['factor'].rank(method='min')

        return df


# 工厂函数
def create_factor(version: str = 'standard') -> Alpha120CqFactor:
    """
    创建指定版本的alpha_120cq因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        Alpha120CqFactor实例
    """
    try:
        params = get_factor_param('alpha_120cq', version)
        logger.info(f"创建alpha_120cq因子 - 版本: {version}, 参数: {params}")
        return Alpha120CqFactor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        params = get_factor_param('alpha_120cq', 'standard')
        return Alpha120CqFactor(params)


__all__ = [
    'Alpha120CqFactor',
    'create_factor',
]
