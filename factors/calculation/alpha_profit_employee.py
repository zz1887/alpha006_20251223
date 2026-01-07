"""
文件input(依赖外部什么): pandas, numpy, BaseFactor, FactorRegistry, core.utils.db_connection
文件output(提供什么): AlphaProfitEmployeeFactor类，提供营业利润+职工现金价值因子计算能力
文件pos(系统局部地位): 因子计算层，提供截面价值因子标准化实现

数学公式:
    factor_raw = (operate_profit + c_paid_to_for_empl) / (total_mv * 10000)
    factor = CSRank(factor_raw, by=ann_date)  # 按公告日期截面排名

使用示例:
    from factors.calculation.alpha_profit_employee import AlphaProfitEmployeeFactor
    factor = AlphaProfitEmployeeFactor()
    result = factor.calculate(data)

    # 通过注册器获取
    from factors import FactorRegistry
    factor = FactorRegistry.get_factor('alpha_profit_employee', version='standard')
    result = factor.calculate(data)

参数说明:
    outlier_sigma: 异常值阈值（默认3.0）
    normalization: 标准化方法（默认None，使用rank进行截面排名）
    industry_neutral: 是否行业中性化（默认False）

返回值:
    pd.DataFrame: [ts_code, trade_date, factor]
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from factors.core.base_factor import BaseFactor
from factors.core.factor_registry import FactorRegistry


class AlphaProfitEmployeeFactor(BaseFactor):
    """
    Alpha Profit Employee因子 - 截面价值因子

    因子说明:
    - 计算营业利润+职工现金相对于市值的价值比率
    - 按公告日期进行横截面排名（CSRank）
    - 反映公司经营创造价值的能力

    数学公式:
        factor_raw = (营业利润 + 支付给职工现金) / 总市值
        factor = CSRank(factor_raw, by=公告日期)

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

        Args:
            data: 输入数据

        Returns:
            bool: 数据是否有效
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

    def calculate(self, data: pd.DataFrame, trade_dates: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        计算营业利润+职工现金价值因子（支持动态截面）

        计算流程:
        1. 数据验证
        2. 数据预处理（排序、空值处理）
        3. 核心计算：分子/分母
        4. 动态截面排名：对于每个trade_date T，使用ann_date ≤ T的股票进行CSRank
        5. 异常值处理
        6. 返回结果

        核心原则:
        - 绝对不使用未来未披露的数据
        - 每个时间点T的截面只包含已披露数据的股票
        - 确保排序的公平性和回测的真实性

        Args:
            data: 输入数据
                必需列: ts_code, ann_date, operate_profit, c_paid_to_for_empl, total_mv
            trade_dates: 交易日期序列（用于定义时间点T）
                        如果为None，则使用ann_date作为trade_date（静态截面）

        Returns:
            pd.DataFrame: 因子数据 [ts_code, trade_date, factor]
        """
        if not self.validate_data(data):
            raise ValueError("数据验证失败")

        # 1. 数据预处理
        df = data.copy()
        df = df.sort_values(['ts_code', 'ann_date'])

        # 确保日期格式正确
        df['ann_date'] = pd.to_datetime(df['ann_date'], format='%Y%m%d')

        # 2. 核心计算
        df['factor_raw'] = self._calculate_core_logic(df)

        # 3. 动态截面排名
        if trade_dates is None:
            # 静态截面：使用ann_date作为trade_date
            df['factor'] = self._cross_sectional_rank(df)
            result = df[['ts_code', 'ann_date', 'factor']].copy()
            result = result.rename(columns={'ann_date': 'trade_date'})
        else:
            # 动态截面：对于每个trade_date，使用已披露数据进行排名
            trade_dates = pd.to_datetime(trade_dates, format='%Y%m%d')
            result = self._dynamic_cross_sectional_rank(df, trade_dates)

        # 4. 异常值处理
        result = self._handle_outliers(result)

        # 5. 标准化（可选）
        result = self._normalize_factor(result)

        # 6. 行业中性化（可选）
        if self.params.get('industry_neutral', False):
            result = self._industry_neutralize(result)

        # 7. 清理和返回
        result = result.dropna()
        result['trade_date'] = result['trade_date'].dt.strftime('%Y%m%d')

        self.logger.info(f"营业利润+职工现金因子计算完成，记录数: {len(result)}")
        return result

    def _convert_cumulative_to_period(self, data: pd.DataFrame, column: str) -> pd.Series:
        """
        将累计财务数据转换为单期数据

        财务数据累计规则:
        - Q1: 直接使用（累计=单期）
        - Q2（半年报）: 半年报 - Q1 = Q2单期
        - Q3: 三季报 - 半年报 = Q3单期
        - Q4（年报）: 年报 - 三季报 = Q4单期

        Args:
            data: 包含ts_code, ann_date, 和指定列的数据
            column: 需要转换的列名

        Returns:
            转换后的单期数据
        """
        df = data[['ts_code', 'ann_date', column]].copy()
        df['ann_date'] = pd.to_datetime(df['ann_date'], format='%Y%m%d')

        # 提取季度信息
        df['month'] = df['ann_date'].dt.month
        df['quarter'] = df['month'].map(lambda x: (x - 1) // 3 + 1)

        # 按股票分组，按日期排序
        result = pd.Series(index=data.index, dtype=float)

        for ts_code, group in df.groupby('ts_code'):
            group = group.sort_values('ann_date')

            prev_value = None
            prev_quarter = None

            for idx, row in group.iterrows():
                current_value = row[column]
                current_quarter = row['quarter']

                if pd.isna(current_value):
                    result[idx] = np.nan
                    continue

                # Q1数据不需要转换
                if current_quarter == 1:
                    result[idx] = current_value
                    prev_value = current_value
                    prev_quarter = 1

                # Q2/Q3/Q4需要减去上一期累计
                elif prev_value is not None and prev_quarter is not None:
                    # 确保是连续的季度
                    if current_quarter == prev_quarter + 1 or (current_quarter == 2 and prev_quarter == 1) or (current_quarter == 4 and prev_quarter == 3):
                        period_value = current_value - prev_value
                        result[idx] = period_value if period_value >= 0 else np.nan
                        prev_value = current_value
                        prev_quarter = current_quarter
                    else:
                        # 季度不连续，无法计算
                        result[idx] = np.nan
                else:
                    # 没有上一期数据，无法计算
                    result[idx] = np.nan

        self.logger.info(f"累计数据转换完成: {column}")
        return result

    def _calculate_core_logic(self, data: pd.DataFrame) -> pd.Series:
        """
        核心计算逻辑：(营业利润 + 支付给职工现金) / 总市值

        增强功能:
        1. 自动处理财务数据的累计性质（Q2/Q3/Q4需要减去上一期）
        2. 确保使用的是单期数据而非累计数据

        处理规则:
        - 营业利润缺失: 跳过
        - 职工现金缺失: 跳过
        - 总市值缺失或为零: 跳过
        - 总市值单位转换：万元 -> 元
        """
        # 1. 转换累计数据为单期数据
        self.logger.info("开始转换累计财务数据为单期数据...")

        # 转换营业利润
        period_profit = self._convert_cumulative_to_period(data, 'operate_profit')

        # 转换职工现金
        period_employee_cash = self._convert_cumulative_to_period(data, 'c_paid_to_for_empl')

        # 2. 获取总市值（不需要转换，使用最新值）
        total_mv = data['total_mv'].copy()

        # 3. 数据清洗
        period_profit = period_profit.where(period_profit.notna(), np.nan)
        period_employee_cash = period_employee_cash.where(period_employee_cash.notna(), np.nan)

        # 4. 总市值处理（单位转换：万元 -> 元）
        total_mv = total_mv.where(total_mv > 0, np.nan)  # 必须为正
        total_mv = total_mv * 10000  # 转换为元

        # 5. 计算分子（单期营业利润 + 单期职工现金）
        numerator = period_profit + period_employee_cash

        # 6. 计算比率
        ratio = numerator / total_mv

        # 统计有效数据
        valid_count = ratio.notna().sum()
        total_count = len(ratio)
        self.logger.info(f"核心计算完成，有效数据: {valid_count}/{total_count} ({valid_count/total_count*100:.1f}%)")

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

    def _dynamic_cross_sectional_rank(self, df: pd.DataFrame, trade_dates: pd.Series) -> pd.DataFrame:
        """
        动态截面排名 - 对于每个trade_date T，使用ann_date ≤ T的股票进行CSRank

        核心原则:
        - 绝对不使用未来未披露的数据
        - 每个时间点T的截面只包含已披露数据的股票
        - 确保排序的公平性和回测的真实性

        算法:
        1. 遍历每个trade_date
        2. 筛选ann_date ≤ trade_date的股票（已披露数据）
        3. 对筛选后的数据进行CSRank
        4. 返回结果

        Args:
            df: 包含factor_raw和ann_date的数据框
            trade_dates: 交易日期序列

        Returns:
            pd.DataFrame: [ts_code, trade_date, factor]
        """
        if 'factor_raw' not in df.columns:
            self.logger.error("缺少factor_raw列，无法进行动态截面排名")
            return pd.DataFrame(columns=['ts_code', 'trade_date', 'factor'])

        results = []

        for trade_date in trade_dates:
            # 筛选：ann_date ≤ trade_date（只使用已披露数据）
            eligible_data = df[df['ann_date'] <= trade_date].copy()

            if len(eligible_data) == 0:
                self.logger.warning(f"交易日期 {trade_date.strftime('%Y%m%d')} 无可用数据")
                continue

            # 对筛选后的数据进行CSRank
            # 使用rank(pct=True, method='first')确保每个股票都有唯一的排名
            eligible_data['factor'] = eligible_data['factor_raw'].rank(pct=True, method='first')
            eligible_data['trade_date'] = trade_date

            results.append(eligible_data[['ts_code', 'trade_date', 'factor']])

            self.logger.debug(f"交易日期 {trade_date.strftime('%Y%m%d')}: "
                            f"{len(eligible_data)}只股票, "
                            f"因子范围[{eligible_data['factor'].min():.4f}, {eligible_data['factor'].max():.4f}]")

        if len(results) == 0:
            self.logger.error("所有交易日期均无有效数据")
            return pd.DataFrame(columns=['ts_code', 'trade_date', 'factor'])

        # 合并所有结果
        result = pd.concat(results, ignore_index=True)

        self.logger.info(f"动态截面排名完成，总记录数: {len(result)}, "
                        f"交易日期数: {result['trade_date'].nunique()}, "
                        f"因子范围: [{result['factor'].min():.4f}, {result['factor'].max():.4f}]")

        return result

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """异常值处理 - 缩尾处理"""
        sigma = self.params.get('outlier_sigma', 3.0)

        if 'factor' in df.columns:
            # 根据数据格式选择分组字段（动态截面使用trade_date，静态截面使用ann_date）
            group_col = 'trade_date' if 'trade_date' in df.columns else 'ann_date'

            # 按分组计算统计量
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

            df['factor'] = df.groupby(group_col)['factor'].transform(clip_group)

        return df

    def _normalize_factor(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化（可选）"""
        method = self.params.get('normalization')

        if method is None or 'factor' not in df.columns:
            return df

        # 根据数据格式选择分组字段
        group_col = 'trade_date' if 'trade_date' in df.columns else 'ann_date'

        if method == 'zscore':
            # Z-score标准化
            df['factor'] = df.groupby(group_col)['factor'].transform(
                lambda x: (x - x.mean()) / x.std() if x.std() != 0 else 0
            )
        elif method == 'rank':
            # 秩标准化（已经是截面排名，可选再次排名）
            df['factor'] = df.groupby(group_col)['factor'].rank(pct=True)

        return df

    def _industry_neutralize(self, df: pd.DataFrame) -> pd.DataFrame:
        """行业中性化"""
        if 'industry' not in df.columns:
            self.logger.warning("缺少行业数据，无法进行行业中性化")
            return df

        # 根据数据格式选择分组字段
        group_col = 'trade_date' if 'trade_date' in df.columns else 'ann_date'

        # 计算行业均值
        industry_mean = df.groupby([group_col, 'industry'])['factor'].transform('mean')

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
FactorRegistry.register('alpha_profit_employee', AlphaProfitEmployeeFactor, 'valuation')
FactorRegistry.register('profit_employee', AlphaProfitEmployeeFactor, 'valuation')  # 别名