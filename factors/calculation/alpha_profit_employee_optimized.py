"""
文件input(依赖外部什么): pandas, numpy, BaseFactor, FactorRegistry
文件output(提供什么): AlphaProfitEmployeeOptimizedFactor类，提供优化的价值因子计算能力
文件pos(系统局部地位): 因子计算层，提供优化的截面价值因子实现

数学公式:
    factor_raw = -(operate_profit + c_paid_to_for_empl) / (total_mv * 10000)  # 取反
    factor = CSRank(factor_raw, by=ann_date)  # 按公告日期截面排名

优化说明:
    原始因子方向错误，高因子值对应低收益
    优化方案：因子取反，使高因子值对应高收益

使用示例:
    from factors.calculation.alpha_profit_employee_optimized import AlphaProfitEmployeeOptimizedFactor
    factor = AlphaProfitEmployeeOptimizedFactor()
    result = factor.calculate(data)

返回值:
    pd.DataFrame: [ts_code, trade_date, factor]
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from factors.core.base_factor import BaseFactor
from factors.core.factor_registry import FactorRegistry


class AlphaProfitEmployeeOptimizedFactor(BaseFactor):
    """
    Alpha Profit Employee优化因子 - 截面价值因子（取反版本）

    因子说明:
    - 计算营业利润+职工现金相对于市值的价值比率
    - **因子取反**：使用负值，使高因子值对应高收益
    - 按公告日期进行横截面排名（CSRank）
    - 反映公司经营创造价值的能力

    数学公式:
        factor_raw = -(营业利润 + 支付给职工现金) / 总市值
        factor = CSRank(factor_raw, by=公告日期)

    优化逻辑:
        原始因子: (利润+职工现金)/市值
        问题: 高值对应低收益（可能是财务数据滞后导致）
        优化: 取反后使用，高值对应高收益

    参数说明:
    - outlier_sigma: 异常值阈值（标准差倍数）
    - normalization: 标准化方法（默认None，内部使用rank）
    - industry_neutral: 是否行业中性化
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)

    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'outlier_sigma': 3.0,
            'normalization': None,  # 默认使用截面排名
            'industry_neutral': False,
        }

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        数据验证

        必需字段:
        - ts_code: 股票代码
        - ann_date: 公告日期
        - operate_profit: 营业利润
        - c_paid_to_for_empl: 支付给职工现金
        - total_mv: 总市值
        """
        required_columns = ['ts_code', 'ann_date', 'operate_profit', 'c_paid_to_for_empl', 'total_mv']

        # 检查必需列
        for col in required_columns:
            if col not in data.columns:
                self.logger.error(f"缺少必需列: {col}")
                return False

        # 检查数据量
        if len(data) < 10:
            self.logger.error("数据量不足")
            return False

        # 检查空值（警告，不阻断）
        if data[required_columns].isnull().any().any():
            self.logger.warning("存在空值，将被剔除")

        return True

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算优化的营业利润+职工现金价值因子（取反版本）

        计算流程:
        1. 数据验证
        2. 数据预处理（排序、空值处理）
        3. 核心计算：-(分子/分母)  # 关键优化：取反
        4. 截面排名：按ann_date分组rank(pct=True)
        5. 异常值处理
        6. 返回结果（trade_date=ann_date）

        Args:
            data: 输入数据
                必需列: ts_code, ann_date, operate_profit, c_paid_to_for_empl, total_mv

        Returns:
            pd.DataFrame: 因子数据 [ts_code, trade_date, factor]
        """
        if not self.validate_data(data):
            raise ValueError("数据验证失败")

        # 1. 数据预处理
        df = data.copy()
        df = df.sort_values(['ts_code', 'ann_date'])

        # 2. 核心计算（取反版本）
        df['factor_raw'] = self._calculate_core_logic(df)

        # 3. 截面排名（CSRank）
        df['factor'] = self._cross_sectional_rank(df)

        # 4. 异常值处理
        df = self._handle_outliers(df)

        # 5. 标准化（可选）
        df = self._normalize_factor(df)

        # 6. 行业中性化（可选）
        if self.params.get('industry_neutral', False):
            df = self._industry_neutralize(df)

        # 7. 返回结果
        result = df[['ts_code', 'ann_date', 'factor']].copy()
        result = result.rename(columns={'ann_date': 'trade_date'})
        result = result.dropna()

        self.logger.info(f"优化因子计算完成，记录数: {len(result)}")
        return result

    def _calculate_core_logic(self, data: pd.DataFrame) -> pd.Series:
        """
        核心计算逻辑：-(营业利润 + 支付给职工现金) / 总市值

        关键优化：取反操作
        """
        # 获取数据
        profit = data['operate_profit'].copy()
        employee_cash = data['c_paid_to_for_empl'].copy()
        total_mv = data['total_mv'].copy()

        # 数据清洗
        profit = profit.where(profit.notna(), np.nan)
        employee_cash = employee_cash.where(employee_cash.notna(), np.nan)

        # 总市值处理（单位转换：万元 -> 元）
        total_mv = total_mv.where(total_mv > 0, np.nan)  # 必须为正
        total_mv = total_mv * 10000  # 转换为元

        # 计算分子
        numerator = profit + employee_cash

        # 计算比率（关键：取反）
        ratio = -(numerator / total_mv)

        return ratio

    def _cross_sectional_rank(self, df: pd.DataFrame) -> pd.Series:
        """
        截面排名（CSRank）

        按公告日期分组，计算每个组内的排名（分位数）
        结果范围: [0, 1]，值越大表示越好
        """
        if 'factor_raw' not in df.columns:
            self.logger.error("缺少factor_raw列，无法进行截面排名")
            return pd.Series([np.nan] * len(df), index=df.index)

        # 按ann_date分组进行排名
        factor = df.groupby('ann_date')['factor_raw'].rank(pct=True, method='first')

        self.logger.info(f"截面排名完成，因子范围: [{factor.min():.4f}, {factor.max():.4f}]")
        return factor

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """异常值处理 - 缩尾处理"""
        sigma = self.params.get('outlier_sigma', 3.0)

        if 'factor' in df.columns:
            # 按公告日期分组计算统计量
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

            df['factor'] = df.groupby('ann_date')['factor'].transform(clip_group)

        return df

    def _normalize_factor(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化（可选）"""
        method = self.params.get('normalization')

        if method is None or 'factor' not in df.columns:
            return df

        if method == 'zscore':
            # Z-score标准化
            df['factor'] = df.groupby('ann_date')['factor'].transform(
                lambda x: (x - x.mean()) / x.std() if x.std() != 0 else 0
            )
        elif method == 'rank':
            # 秩标准化（已经是截面排名，可选再次排名）
            df['factor'] = df.groupby('ann_date')['factor'].rank(pct=True)

        return df

    def _industry_neutralize(self, df: pd.DataFrame) -> pd.DataFrame:
        """行业中性化"""
        if 'industry' not in df.columns:
            self.logger.warning("缺少行业数据，无法进行行业中性化")
            return df

        # 计算行业均值
        industry_mean = df.groupby(['ann_date', 'industry'])['factor'].transform('mean')

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
FactorRegistry.register('alpha_profit_employee_optimized', AlphaProfitEmployeeOptimizedFactor, 'valuation')
FactorRegistry.register('profit_employee_optimized', AlphaProfitEmployeeOptimizedFactor, 'valuation')  # 别名
