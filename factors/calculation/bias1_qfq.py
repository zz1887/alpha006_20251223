"""
文件input(依赖外部什么): pandas, numpy, factors.core.base_factor, core.config.params, core.utils.data_loader
文件output(提供什么): bias1_qfq因子标准计算类，继承BaseFactor基类
文件pos(系统局部地位): 因子计算层 - BIAS乖离率因子实现

详细说明:
1. 因子逻辑: BIAS乖离率 = (股价 - 移动平均线) / 移动平均线 × 100%
2. 优化方案: 使用 -bias1_qfq 作为因子值（负值反转）
   - 原始逻辑: 股价偏离移动平均线太远时会向均线靠拢
   - 负偏离(超卖) = 买入信号
   - 正偏离(超买) = 卖出信号
3. 数据处理: 从stock_database.stk_factor_pro获取预计算的bias1_qfq值
4. 异常值处理: 删除NaN值，可选缩尾处理

使用示例:
    from factors.calculation.bias1_qfq import Bias1QfqFactor
    factor = Bias1QfqFactor()
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
from core.utils.db_connection import db
from core.utils.data_loader import data_loader

logger = logging.getLogger(__name__)


class Bias1QfqFactor(BaseFactor):
    """bias1_qfq因子标准计算类"""

    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'source_table': 'stock_database.stk_factor_pro',  # 数据源表
            'outlier_sigma': 3.0,                             # 异常值阈值（缩尾处理）
            'normalization': None,                            # 标准化方法：None/zscore/rank
            'industry_neutral': False,                        # 是否行业中性化
        }

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        验证输入数据

        Args:
            data: 输入数据，应包含ts_code, trade_date, bias1_qfq列

        Returns:
            bool: 数据是否有效
        """
        if data is None or len(data) == 0:
            logger.warning("输入数据为空")
            return False

        required_cols = ['ts_code', 'trade_date', 'bias1_qfq']
        missing_cols = [col for col in required_cols if col not in data.columns]

        if missing_cols:
            logger.warning(f"缺少必要列: {missing_cols}")
            return False

        # 检查数据质量
        if data['bias1_qfq'].isna().all():
            logger.warning("bias1_qfq列全为NaN")
            return False

        return True

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算bias1_qfq因子

        Args:
            data: 包含ts_code, trade_date, bias1_qfq的DataFrame

        Returns:
            DataFrame包含ts_code, trade_date, factor列
        """
        if not self.validate_data(data):
            return pd.DataFrame()

        # 复制数据避免修改原数据
        df = data.copy()

        # 1. 删除bias1_qfq为NaN的行
        df = df.dropna(subset=['bias1_qfq'])

        if len(df) == 0:
            logger.warning("清理后无有效数据")
            return pd.DataFrame()

        # 2. 异常值处理 - 缩尾处理
        outlier_sigma = self.params.get('outlier_sigma', 3.0)
        if outlier_sigma > 0:
            df = self._winsorize(df, 'bias1_qfq', outlier_sigma)

        # 3. 核心优化：使用 -bias1_qfq 作为因子值
        df['factor'] = -df['bias1_qfq']

        # 4. 可选标准化
        normalization = self.params.get('normalization', None)
        if normalization:
            df = self._normalize(df, normalization)

        # 5. 可选行业中性化
        if self.params.get('industry_neutral', False):
            df = self._industry_neutralize(df)

        # 6. 保留必要列
        result = df[['ts_code', 'trade_date', 'factor']].copy()

        logger.info(f"bias1_qfq因子计算完成: {len(result)}条记录")

        return result

    def calculate_by_period(
        self,
        start_date: str,
        end_date: str,
        target_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        按时间段计算bias1_qfq因子

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            target_date: 目标日期 (YYYYMMDD)，None则使用end_date

        Returns:
            因子DataFrame
        """
        if target_date is None:
            target_date = end_date

        print(f"\n{'='*80}")
        print(f"计算bias1_qfq因子: {target_date}")
        print(f"{'='*80}")

        # 获取可交易股票
        stocks = data_loader.get_tradable_stocks(target_date)
        if not stocks:
            logger.error("无有效股票")
            return pd.DataFrame()

        # 从数据库获取bias1_qfq数据
        source_table = self.params.get('source_table', 'stock_database.stk_factor_pro')
        placeholders = ','.join(['%s'] * len(stocks))

        query = f"""
        SELECT ts_code, trade_date, bias1_qfq
        FROM {source_table}
        WHERE trade_date BETWEEN %s AND %s
          AND ts_code IN ({placeholders})
          AND bias1_qfq IS NOT NULL
        ORDER BY ts_code, trade_date
        """

        data = db.execute_query(query, [start_date, end_date] + stocks)
        df = pd.DataFrame(data)

        if len(df) == 0:
            logger.error("未获取到bias1_qfq数据")
            return pd.DataFrame()

        # 转换数据类型
        df['bias1_qfq'] = df['bias1_qfq'].astype(float)
        df['trade_date'] = pd.to_datetime(df['trade_date'])

        # 计算因子
        result = self.calculate(df)

        return result

    def _winsorize(self, df: pd.DataFrame, column: str, sigma: float) -> pd.DataFrame:
        """缩尾处理：将超出均值±sigma倍标准差的值替换为边界值"""
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

        logger.info(f"缩尾处理: {column} ∈ [{lower_bound:.4f}, {upper_bound:.4f}]")

        return df

    def _normalize(self, df: pd.DataFrame, method: str) -> pd.DataFrame:
        """标准化处理"""
        if method == 'zscore':
            mean = df['factor'].mean()
            std = df['factor'].std()
            if std > 0:
                df['factor'] = (df['factor'] - mean) / std
                logger.info(f"Z-score标准化: mean={mean:.4f}, std={std:.4f}")
        elif method == 'rank':
            df['factor'] = df['factor'].rank(method='min')
            logger.info("Rank标准化完成")

        return df

    def _industry_neutralize(self, df: pd.DataFrame) -> pd.DataFrame:
        """行业中性化处理（需要行业数据）"""
        logger.warning("行业中性化需要行业分类数据，暂未实现")
        return df


# 工厂函数
def create_factor(version: str = 'standard') -> Bias1QfqFactor:
    """
    创建指定版本的bias1_qfq因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        Bias1QfqFactor实例
    """
    try:
        params = get_factor_param('bias1_qfq', version)
        logger.info(f"创建bias1_qfq因子 - 版本: {version}, 参数: {params}")
        return Bias1QfqFactor(params)
    except Exception as e:
        logger.error(f"创建因子失败: {e}")
        # 回退到标准版
        params = get_factor_param('bias1_qfq', 'standard')
        return Bias1QfqFactor(params)


__all__ = [
    'Bias1QfqFactor',
    'create_factor',
]
