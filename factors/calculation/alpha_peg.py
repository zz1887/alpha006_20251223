"""
文件input(依赖外部什么): pandas, numpy, BaseFactor, FactorRegistry
文件output(提供什么): AlphaPegFactor类，提供PEG因子计算能力
文件pos(系统局部地位): 因子计算层，提供估值因子标准化实现
文件功能: 计算PEG比率因子，支持异常值处理、标准化、行业中性化

数学公式: alpha_peg = pe_ttm / dt_netprofit_yoy

使用示例:
    from factors.calculation.alpha_peg import AlphaPegFactor
    factor = AlphaPegFactor()
    result = factor.calculate(data)

    # 通过注册器获取
    from factors import FactorRegistry
    factor = FactorRegistry.get_factor('alpha_peg', version='standard')
    result = factor.calculate(data)

参数说明:
    outlier_sigma: 异常值阈值（默认3.0）
    normalization: 标准化方法（None/zscore/rank）
    industry_neutral: 是否行业中性化（默认False）
    min_growth_rate: 最小增长率阈值（默认0.01）
    max_pe: PE上限（默认100.0）

返回值:
    pd.DataFrame: [ts_code, trade_date, factor]
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from factors.core.base_factor import BaseFactor
from factors.core.factor_registry import FactorRegistry


class AlphaPegFactor(BaseFactor):
    """
    Alpha PEG因子 - 估值成长因子

    因子说明:
    - 计算PEG比率，用于评估股票的估值合理性
    - PEG = PE / 盈利增长率
    - 低PEG可能表示股票被低估

    参数说明:
    - outlier_sigma: 异常值阈值（标准差倍数）
    - normalization: 标准化方法（None/zscore/rank）
    - industry_neutral: 是否行业中性化
    - min_growth_rate: 最小增长率阈值（避免除零）
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)

    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'outlier_sigma': 3.0,
            'normalization': None,
            'industry_neutral': False,
            'min_growth_rate': 0.01,  # 最小增长率，避免除零
            'max_pe': 100.0,  # PE上限，避免极端值
        }

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        数据验证

        必需字段:
        - ts_code: 股票代码
        - trade_date: 交易日期
        - pe_ttm: 市盈率（滚动）
        - dt_netprofit_yoy: 净利润增长率

        Args:
            data: 输入数据

        Returns:
            bool: 数据是否有效
        """
        required_columns = ['ts_code', 'trade_date', 'pe_ttm', 'dt_netprofit_yoy']

        # 检查必需列
        for col in required_columns:
            if col not in data.columns:
                self.logger.error(f"缺少必需列: {col}")
                return False

        # 检查数据量
        if len(data) < 10:
            self.logger.error("数据量不足")
            return False

        # 检查空值
        if data[required_columns].isnull().any().any():
            self.logger.warning("存在空值，将被剔除")

        return True

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算PEG因子值

        计算流程:
        1. 数据验证
        2. 数据预处理（排序、空值处理）
        3. 行业适配（根据行业调整参数）
        4. 核心计算：PEG = PE / 增长率
        5. 异常值处理
        6. 标准化（可选）
        7. 行业中性化（可选）

        Args:
            data: 输入数据
                必需列: ts_code, trade_date, pe_ttm, dt_netprofit_yoy
                可选列: industry (用于行业中性化)

        Returns:
            pd.DataFrame: 因子数据 [ts_code, trade_date, factor]
        """
        if not self.validate_data(data):
            raise ValueError("数据验证失败")

        # 1. 数据预处理
        df = data.copy()
        df = df.sort_values(['ts_code', 'trade_date'])

        # 2. 行业适配（如果启用）
        if self.params.get('industry_specific', False):
            df = self._industry_adaptation(df)

        # 3. 核心计算
        df['factor'] = self._calculate_core_logic(df)

        # 4. 异常值处理
        df = self._handle_outliers(df)

        # 5. 标准化（可选）
        df = self._normalize_factor(df)

        # 6. 行业中性化（可选）
        if self.params.get('industry_neutral', False):
            df = self._industry_neutralize(df)

        # 7. 返回结果
        result = df[['ts_code', 'trade_date', 'factor']].copy()
        result = result.dropna()

        self.logger.info(f"PEG因子计算完成，记录数: {len(result)}")
        return result

    def _calculate_core_logic(self, data: pd.DataFrame) -> pd.Series:
        """
        核心计算逻辑：PEG = PE / 增长率

        处理规则:
        - PE <= 0: 跳过
        - 增长率 <= min_growth_rate: 使用min_growth_rate
        - 增长率缺失: 跳过
        """
        min_growth = self.params.get('min_growth_rate', 0.01)
        max_pe = self.params.get('max_pe', 100.0)

        # 复制数据
        pe = data['pe_ttm'].copy()
        growth = data['dt_netprofit_yoy'].copy()

        # 数据清洗
        pe = pe.clip(upper=max_pe)  # PE上限
        pe = pe.where(pe > 0, np.nan)  # PE必须为正

        # 增长率处理
        growth = growth.where(growth >= min_growth, min_growth)  # 最小增长率
        growth = growth.where(growth > 0, np.nan)  # 增长率必须为正

        # 计算PEG
        peg = pe / growth

        return peg

    def _industry_adaptation(self, df: pd.DataFrame) -> pd.DataFrame:
        """行业适配 - 根据行业调整参数"""
        # 这里可以根据不同行业设置不同的PE阈值和增长率阈值
        # 例如：金融行业PE较低，科技行业增长率较高
        self.logger.info("应用行业适配规则")
        return df

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """异常值处理 - 缩尾处理"""
        sigma = self.params.get('outlier_sigma', 3.0)

        if 'factor' in df.columns:
            # 按日期分组计算统计量
            def clip_group(group):
                if len(group) < 2:
                    return group
                mean = group.mean()
                std = group.std()
                if std > 0:
                    lower = mean - sigma * std
                    upper = mean + sigma * std
                    return group.clip(lower=lower, upper=upper)
                return group

            df['factor'] = df.groupby('trade_date')['factor'].transform(clip_group)

        return df

    def _normalize_factor(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化"""
        method = self.params.get('normalization')

        if method is None or 'factor' not in df.columns:
            return df

        if method == 'zscore':
            # Z-score标准化
            df['factor'] = df.groupby('trade_date')['factor'].transform(
                lambda x: (x - x.mean()) / x.std() if x.std() != 0 else 0
            )
        elif method == 'rank':
            # 秩标准化
            df['factor'] = df.groupby('trade_date')['factor'].rank(pct=True)

        return df

    def _industry_neutralize(self, df: pd.DataFrame) -> pd.DataFrame:
        """行业中性化"""
        if 'industry' not in df.columns:
            self.logger.warning("缺少行业数据，无法进行行业中性化")
            return df

        # 计算行业均值
        industry_mean = df.groupby(['trade_date', 'industry'])['factor'].transform('mean')

        # 减去行业均值
        df['factor'] = df['factor'] - industry_mean

        self.logger.info("完成行业中性化")
        return df

    def get_factor_stats(self, factor_df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取因子统计信息

        统计内容:
        - 记录总数、有效记录数
        - 股票数量、日期数量
        - 均值、标准差、最小值、最大值、中位数
        - 缺失率
        """
        if len(factor_df) == 0:
            return {}

        valid_data = factor_df['factor'].dropna()

        return {
            'total_records': len(factor_df),
            'valid_records': len(valid_data),
            'missing_ratio': 1 - len(valid_data) / len(factor_df),
            'stock_count': factor_df['ts_code'].nunique(),
            'date_count': factor_df['trade_date'].nunique(),
            'mean': float(valid_data.mean()),
            'std': float(valid_data.std()),
            'min': float(valid_data.min()),
            'max': float(valid_data.max()),
            'median': float(valid_data.median()),
        }


# 注册因子
FactorRegistry.register('alpha_peg', AlphaPegFactor, 'valuation')
FactorRegistry.register('peg', AlphaPegFactor, 'valuation')  # 别名