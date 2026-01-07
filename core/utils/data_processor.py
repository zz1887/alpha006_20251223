"""
数据处理工具 - 增强版
版本: v2.0
更新日期: 2025-12-30

功能:
- 因子计算核心逻辑
- 数据标准化和归一化
- 异常值处理
- 行业标准化
- 数据合并和转换
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
import logging

# 导入配置
try:
    from core.config.params import FACTOR_PARAMS, get_factor_param
    from core.config.settings import INDUSTRY_CONFIG
except ImportError:
    # 回退配置
    FACTOR_PARAMS = {}
    INDUSTRY_CONFIG = {}

logger = logging.getLogger(__name__)

# 默认异常值阈值
DEFAULT_OUTLIER_SIGMA = 3.0


def merge_pe_fina_data(df_pe: pd.DataFrame, df_fina: pd.DataFrame) -> pd.DataFrame:
    """
    关联PE数据和财务数据

    Args:
        df_pe: PE数据 (ts_code, trade_date, pe_ttm)
        df_fina: 财务数据 (ts_code, ann_date, dt_netprofit_yoy)

    Returns:
        关联后的DataFrame
    """
    df_merged = pd.merge(
        df_pe,
        df_fina[['ts_code', 'ann_date', 'dt_netprofit_yoy']],
        left_on=['ts_code', 'trade_date'],
        right_on=['ts_code', 'ann_date'],
        how='left'
    )

    # 转换为float类型
    if len(df_merged) > 0:
        df_merged['pe_ttm'] = df_merged['pe_ttm'].astype(float)
        if 'dt_netprofit_yoy' in df_merged.columns:
            df_merged['dt_netprofit_yoy'] = df_merged['dt_netprofit_yoy'].astype(float)

    return df_merged


def forward_fill_fina_data(df: pd.DataFrame, group_col: str = 'ts_code', fill_col: str = 'dt_netprofit_yoy') -> pd.DataFrame:
    """
    前向填充财务数据

    Args:
        df: 包含财务数据的DataFrame
        group_col: 分组列名
        fill_col: 需要填充的列名

    Returns:
        填充后的DataFrame
    """
    df[f'{fill_col}_ffill'] = df.groupby(group_col)[fill_col].ffill()
    return df


def filter_valid_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    过滤有效数据

    Args:
        df: 包含pe_ttm和dt_netprofit_yoy的DataFrame

    Returns:
        有效数据DataFrame
    """
    valid_mask = (
        df['pe_ttm'].notna() &
        (df['pe_ttm'] > 0) &
        df['dt_netprofit_yoy_ffill'].notna() &
        (df['dt_netprofit_yoy_ffill'] != 0)
    )

    df_valid = df[valid_mask].copy()
    df_valid['dt_netprofit_yoy'] = df_valid['dt_netprofit_yoy_ffill'].astype(float)

    print(f"  有效数据: {len(df_valid):,} 条")
    return df_valid


def merge_industry_data(df: pd.DataFrame, df_industry: pd.DataFrame) -> pd.DataFrame:
    """
    合并行业分类数据

    Args:
        df: 主数据
        df_industry: 行业数据 (ts_code, l1_name)

    Returns:
        合并后的DataFrame
    """
    df_with_industry = df.merge(df_industry, on='ts_code', how='left')
    df_with_industry['l1_name'] = df_with_industry['l1_name'].fillna('其他')
    return df_with_industry


def clip_outliers_by_industry(df: pd.DataFrame,
                              outlier_sigma: float = DEFAULT_OUTLIER_SIGMA,
                              industry_specific: bool = True) -> pd.DataFrame:
    """
    分行业异常值处理 (3σ原则)

    Args:
        df: 包含alpha_peg_raw和l1_name的DataFrame
        outlier_sigma: 异常值阈值
        industry_specific: 是否使用行业特定阈值

    Returns:
        异常值处理后的DataFrame
    """
    results = []

    for industry, group in df.groupby('l1_name'):
        industry_data = group.copy()

        # 获取行业特定阈值
        threshold = outlier_sigma
        if industry_specific and industry in INDUSTRY_THRESHOLD:
            threshold = INDUSTRY_THRESHOLD[industry]

        # 计算均值和标准差
        mean_val = industry_data['alpha_peg_raw'].mean()
        std_val = industry_data['alpha_peg_raw'].std()

        if std_val > 0:
            lower_bound = mean_val - threshold * std_val
            upper_bound = mean_val + threshold * std_val
            industry_data['alpha_peg_raw'] = industry_data['alpha_peg_raw'].clip(lower_bound, upper_bound)

        results.append(industry_data)

    return pd.concat(results, ignore_index=True)


def normalize_factor(df: pd.DataFrame,
                     method: Optional[str] = None,
                     factor_col: str = 'alpha_peg_raw') -> pd.DataFrame:
    """
    因子标准化

    Args:
        df: 包含因子的DataFrame
        method: 标准化方法 ('zscore', 'rank', None)
        factor_col: 因子列名

    Returns:
        标准化后的DataFrame
    """
    if method is None:
        df['alpha_peg'] = df[factor_col]
    elif method == 'zscore':
        mean_val = df[factor_col].mean()
        std_val = df[factor_col].std()
        df['alpha_peg'] = (df[factor_col] - mean_val) / std_val if std_val > 0 else df[factor_col]
    elif method == 'rank':
        df['alpha_peg'] = df[factor_col].rank(ascending=True, method='min') / len(df)
    else:
        raise ValueError(f"不支持的标准化方法: {method}")

    return df


def calculate_rank(df: pd.DataFrame,
                   group_cols: List[str],
                   factor_col: str = 'alpha_peg',
                   ascending: bool = True,
                   method: str = 'first') -> pd.DataFrame:
    """
    分组排名

    Args:
        df: 包含因子的DataFrame
        group_cols: 分组列名 (如['trade_date', 'l1_name'])
        factor_col: 因子列名
        ascending: 排序方向 (True: 值越小越好)
        method: 排名方法

    Returns:
        包含排名的DataFrame
    """
    df['industry_rank'] = df.groupby(group_cols)[factor_col].rank(ascending=ascending, method=method)
    return df


def calculate_alpha_peg_factor(df_pe: pd.DataFrame,
                               df_fina: pd.DataFrame,
                               df_industry: pd.DataFrame,
                               outlier_sigma: float = DEFAULT_OUTLIER_SIGMA,
                               normalization: Optional[str] = None,
                               industry_specific: bool = True) -> pd.DataFrame:
    """
    完整的alpha_peg因子计算流程

    Args:
        df_pe: PE数据
        df_fina: 财务数据
        df_industry: 行业数据
        outlier_sigma: 异常值阈值
        normalization: 标准化方法
        industry_specific: 是否使用行业特定阈值

    Returns:
        包含alpha_peg因子的DataFrame
    """
    print("\n" + "="*80)
    print("alpha_peg因子计算流程")
    print("="*80)

    # 1. 关联数据
    print("\n步骤1: 关联PE和财务数据...")
    df_merged = merge_pe_fina_data(df_pe, df_fina)

    # 2. 前向填充
    print("步骤2: 前向填充财务数据...")
    df_merged = forward_fill_fina_data(df_merged)

    # 3. 过滤有效数据
    print("步骤3: 过滤有效数据...")
    df_valid = filter_valid_data(df_merged)

    if len(df_valid) == 0:
        print("❌ 无有效数据")
        return pd.DataFrame()

    # 4. 合并行业
    print("步骤4: 合并行业分类...")
    df_with_industry = merge_industry_data(df_valid, df_industry)

    # 5. 计算原始因子
    print("步骤5: 计算原始alpha_peg...")
    df_with_industry['alpha_peg_raw'] = df_with_industry['pe_ttm'] / df_with_industry['dt_netprofit_yoy']

    # 6. 异常值处理
    print("步骤6: 异常值处理...")
    df_processed = clip_outliers_by_industry(df_with_industry, outlier_sigma, industry_specific)

    # 7. 标准化
    print("步骤7: 标准化...")
    df_normalized = normalize_factor(df_processed, normalization)

    # 8. 分行业排名
    print("步骤8: 分行业排名...")
    df_final = calculate_rank(df_normalized, ['trade_date', 'l1_name'], 'alpha_peg')

    # 9. 保留关键字段
    result_cols = ['ts_code', 'trade_date', 'l1_name', 'pe_ttm',
                   'dt_netprofit_yoy', 'alpha_peg', 'industry_rank']
    df_result = df_final[result_cols]

    print(f"\n✅ 因子计算完成")
    print(f"  记录数: {len(df_result):,}")
    print(f"  股票数: {df_result['ts_code'].nunique()}")
    print(f"  行业数: {df_result['l1_name'].nunique()}")

    return df_result


def calculate_alpha_pluse_factor(df_price: pd.DataFrame,
                                 window_20d: int = 20,
                                 lookback_14d: int = 14,
                                 lower_mult: float = 1.4,
                                 upper_mult: float = 3.5,
                                 min_count: int = 2,
                                 max_count: int = 4) -> pd.DataFrame:
    """
    完整的alpha_pluse因子计算流程

    Args:
        df_price: 价格数据 (ts_code, trade_date, vol)
        window_20d: 回溯窗口
        lookback_14d: 成交量均值计算周期
        lower_mult: 下限倍数
        upper_mult: 上限倍数
        min_count: 最小满足数量
        max_count: 最大满足数量

    Returns:
        包含alpha_pluse因子的DataFrame
    """
    print("\n" + "="*80)
    print("alpha_pluse因子计算流程")
    print("="*80)

    print(f"\n参数配置:")
    print(f"  回溯窗口: {window_20d} 日")
    print(f"  成交量均值周期: {lookback_14d} 日")
    print(f"  倍数范围: [{lower_mult}, {upper_mult}]")
    print(f"  满足数量范围: [{min_count}, {max_count}]")

    results = []
    stock_count = 0

    # 按股票分组计算
    for ts_code, group in df_price.groupby('ts_code'):
        group = group.sort_values('trade_date').copy()

        if len(group) < window_20d + lookback_14d:
            continue

        # 计算14日成交量均值
        group['vol_14_mean'] = group['vol'].rolling(
            window=lookback_14d, min_periods=lookback_14d
        ).mean()

        # 标记每个交易日是否满足条件
        group['condition'] = (
            (group['vol'] >= group['vol_14_mean'] * lower_mult) &
            (group['vol'] <= group['vol_14_mean'] * upper_mult) &
            group['vol_14_mean'].notna()
        )

        # 计算20日滚动满足数量
        def count_conditions(idx):
            """统计当前日往前20日内满足条件的数量"""
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

        # 保留结果
        result_group = group[[
            'ts_code', 'trade_date', 'alpha_pluse', 'count_20d'
        ]].copy().dropna()

        if len(result_group) > 0:
            results.append(result_group)

        stock_count += 1

    if not results:
        print("❌ 未计算出任何结果")
        return pd.DataFrame()

    # 合并结果
    final_result = pd.concat(results, ignore_index=True)

    # 统计
    total_signals = final_result['alpha_pluse'].sum()
    total_data = len(final_result)

    print(f"\n✅ 因子计算完成")
    print(f"  处理股票数: {stock_count}")
    print(f"  总数据条数: {total_data:,}")
    print(f"  有效信号数: {total_signals:,}")
    print(f"  信号比例: {total_signals/total_data:.4f}")

    return final_result
