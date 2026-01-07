"""
文件input(依赖外部什么): pandas, numpy, factors.core.base_factor, core.config.params, core.utils.db_connection, core.utils.data_loader
文件output(提供什么): cr_qfq因子标准计算类，继承BaseFactor基类
文件pos(系统局部地位): 因子计算层 - 20日能量潮CR指标实现

详细说明:
1. 因子逻辑: CR指标（N=20），基于前复权的HIGH/LOW/CLOSE计算
2. 计算公式: CR = SUM(HIGH - REF(CLOSE, 1), N) / SUM(REF(CLOSE, 1) - LOW, N) × 100
   - N = 20
   - 数据为前复权
   - CR指标衡量多空力量对比
3. 数据来源: stock_database.stk_factor_pro表（预计算值）
4. 异常值处理: 删除NaN值，可选标准化

使用示例:
    from factors.calculation.cr_qfq import CrQfqFactor
    factor = CrQfqFactor()
    result = factor.calculate(data)

返回值:
    DataFrame包含ts_code, trade_date, factor列
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
import logging

from factors.core.base_factor import BaseFactor
from core.config.params import get_factor_param
from core.utils.db_connection import db
from core.utils.data_loader import data_loader

logger = logging.getLogger(__name__)


class CrQfqFactor(BaseFactor):
    """cr_qfq因子标准计算类"""

    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'period': 20,                      # 周期
            'source_table': 'stock_database.stk_factor_pro',  # 数据来源表
            'normalization': 'max_scale',      # 标准化方法
            'outlier_sigma': 3.0,              # 异常值阈值
        }

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        验证输入数据

        Args:
            data: 输入数据，应包含ts_code, trade_date, cr_qfq列

        Returns:
            bool: 数据是否有效
        """
        if data is None or len(data) == 0:
            logger.warning("输入数据为空")
            return False

        required_cols = ['ts_code', 'trade_date', 'cr_qfq']
        missing_cols = [col for col in required_cols if col not in data.columns]

        if missing_cols:
            logger.warning(f"缺少必要列: {missing_cols}")
            return False

        # 检查数据质量
        if data['cr_qfq'].isna().all():
            logger.warning("cr_qfq列全为NaN")
            return False

        return True

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算cr_qfq因子（实际是从数据库读取预计算值）

        Args:
            data: 包含ts_code, trade_date, cr_qfq的DataFrame

        Returns:
            DataFrame包含ts_code, trade_date, factor列
        """
        if not self.validate_data(data):
            return pd.DataFrame()

        # 复制数据避免修改原数据
        df = data.copy()

        # 删除NaN值
        df = df.dropna(subset=['cr_qfq'])

        if len(df) == 0:
            logger.warning("清理后无有效数据")
            return pd.DataFrame()

        # 重命名cr_qfq为factor
        df['factor'] = df['cr_qfq'].astype(float)

        # 异常值处理
        outlier_sigma = self.params.get('outlier_sigma', 3.0)
        if outlier_sigma > 0:
            df = self._winsorize(df, 'factor', outlier_sigma)

        # 可选标准化
        normalization = self.params.get('normalization', None)
        if normalization:
            df = self._normalize(df, normalization)

        # 保留必要列
        result = df[['ts_code', 'trade_date', 'factor']].copy()

        logger.info(f"cr_qfq因子计算完成: {len(result)}条记录")

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
        source_table = self.params.get('source_table', 'stock_database.stk_factor_pro')

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

        # 转换类型
        df['cr_qfq'] = df['cr_qfq'].astype(float)

        logger.info(f"获取CR数据: {len(df)}条记录")

        # 计算因子
        result = self.calculate(df)

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
        if method == 'max_scale':
            max_val = df['factor'].max()
            if max_val > 0:
                df['factor'] = df['factor'] / max_val
            else:
                df['factor'] = 0
        elif method == 'zscore':
            mean = df['factor'].mean()
            std = df['factor'].std()
            if std > 0:
                df['factor'] = (df['factor'] - mean) / std
            else:
                df['factor'] = 0
        elif method == 'rank':
            df['factor'] = df['factor'].rank(method='min')

        return df


# 工厂函数
def create_factor(version: str = 'standard') -> CrQfqFactor:
    """
    创建指定版本的cr_qfq因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        CrQfqFactor实例
    """
    try:
        params = get_factor_param('cr_qfq', version)
        logger.info(f"创建cr_qfq因子 - 版本: {version}, 参数: {params}")
        return CrQfqFactor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        params = get_factor_param('cr_qfq', 'standard')
        return CrQfqFactor(params)


__all__ = [
    'CrQfqFactor',
    'create_factor',
]
