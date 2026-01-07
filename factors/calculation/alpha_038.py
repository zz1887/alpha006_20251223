"""
文件input(依赖外部什么): pandas, numpy, factors.core.base_factor, core.config.params, core.utils.data_loader
文件output(提供什么): alpha_038因子标准计算类，继承BaseFactor基类
文件pos(系统局部地位): 因子计算层 - 价格强度因子实现

详细说明:
1. 因子逻辑: 短期价格排名与当日涨跌幅的组合特征
2. 计算公式: alpha_038 = (-1 × rank(Ts_Rank(close, 10))) × rank(close/open)
   - Ts_Rank(close, 10): 目标日close在10日序列中的排名(1=最小,10=最大)
   - rank(close/open): 所有股票close/open比值的降序排名(1=最大)
3. 数据来源: stock_database.daily_kline表
4. 异常值处理: 删除NaN值，检查open不为0

使用示例:
    from factors.calculation.alpha_038 import Alpha038Factor
    factor = Alpha038Factor()
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


class Alpha038Factor(BaseFactor):
    """alpha_038因子标准计算类"""

    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'window': 10,              # 窗口期
            'min_data_days': 10,       # 最小数据天数
            'outlier_sigma': 3.0,      # 异常值阈值
            'normalization': None,     # 标准化方法
        }

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        验证输入数据

        Args:
            data: 输入数据，应包含ts_code, trade_date, open, close列

        Returns:
            bool: 数据是否有效
        """
        if data is None or len(data) == 0:
            logger.warning("输入数据为空")
            return False

        required_cols = ['ts_code', 'trade_date', 'open', 'close']
        missing_cols = [col for col in required_cols if col not in data.columns]

        if missing_cols:
            logger.warning(f"缺少必要列: {missing_cols}")
            return False

        # 检查数据质量
        if data['open'].isna().all() or data['close'].isna().all():
            logger.warning("open或close列全为NaN")
            return False

        return True

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算alpha_038因子

        Args:
            data: 包含ts_code, trade_date, open, close的DataFrame

        Returns:
            DataFrame包含ts_code, trade_date, factor列
        """
        if not self.validate_data(data):
            return pd.DataFrame()

        window = self.params.get('window', 10)
        min_data_days = self.params.get('min_data_days', 10)

        results = []

        for ts_code, group in data.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            # 数据不足检查
            if len(group) < min_data_days:
                continue

            # 获取最后一条数据
            target_row = group.iloc[-1]

            # 检查open
            if pd.isna(target_row['open']) or target_row['open'] == 0:
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
                'trade_date': target_row['trade_date'],
                'close_rank': close_rank,
                'close_over_open': close_over_open,
            })

        if not results:
            return pd.DataFrame()

        df_result = pd.DataFrame(results)

        # 计算rank(close_over_open)
        df_result['rank_close_over_open'] = df_result['close_over_open'].rank(ascending=False, method='min')

        # 计算最终alpha_038
        df_result['factor'] = (-1 * df_result['close_rank']) * df_result['rank_close_over_open']

        # 异常值处理
        outlier_sigma = self.params.get('outlier_sigma', 3.0)
        if outlier_sigma > 0:
            df_result = self._winsorize(df_result, 'factor', outlier_sigma)

        # 可选标准化
        normalization = self.params.get('normalization', None)
        if normalization:
            df_result = self._normalize(df_result, normalization)

        result = df_result[['ts_code', 'trade_date', 'factor']].copy()

        logger.info(f"alpha_038因子计算完成: {len(result)}只股票")

        return result

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
def create_factor(version: str = 'standard') -> Alpha038Factor:
    """
    创建指定版本的alpha_038因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        Alpha038Factor实例
    """
    try:
        params = get_factor_param('alpha_038', version)
        logger.info(f"创建alpha_038因子 - 版本: {version}, 参数: {params}")
        return Alpha038Factor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        params = get_factor_param('alpha_038', 'standard')
        return Alpha038Factor(params)


__all__ = [
    'Alpha038Factor',
    'create_factor',
]
