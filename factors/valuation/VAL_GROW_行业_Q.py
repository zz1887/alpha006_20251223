"""
alpha_peg因子 - 行业优化版

功能:
1. 分行业计算alpha_peg因子
2. 行业内异常值处理（3σ原则）
3. 行业内标准化（可选z-score/秩转换）
4. 行业特殊适配（金融/周期等）

因子名称: alpha_peg (行业优化版)
计算公式: alpha_peg = pe_ttm / dt_netprofit_yoy
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from core.utils.db_connection import db


# 行业特殊适配配置
INDUSTRY_ADJUSTMENT = {
    # 金融行业：PE口径修正（避免负值或异常值）
    '银行': {'pe_adjust': True, 'pe_min': 3, 'pe_max': 15},
    '非银金融': {'pe_adjust': True, 'pe_min': 5, 'pe_max': 30},

    # 周期行业：增长率季节性调整
    '煤炭': {'seasonal_adjust': True, 'period': 'quarterly'},
    '有色金属': {'seasonal_adjust': True, 'period': 'quarterly'},
    '钢铁': {'seasonal_adjust': True, 'period': 'quarterly'},
    '石油石化': {'seasonal_adjust': True, 'period': 'quarterly'},

    # 高成长行业：放宽异常值阈值
    '电子': {'outlier_threshold': 3.5},
    '电力设备': {'outlier_threshold': 3.5},
    '医药生物': {'outlier_threshold': 3.5},
    '计算机': {'outlier_threshold': 3.5},

    # 防御性行业：严格异常值过滤
    '银行': {'outlier_threshold': 2.5},
    '公用事业': {'outlier_threshold': 2.5},
    '交通运输': {'outlier_threshold': 2.5},
}


def load_industry_data(industry_path: str = None) -> pd.DataFrame:
    """
    加载行业分类数据

    参数:
        industry_path: 行业数据文件路径，默认使用Windows路径

    返回:
        DataFrame包含: ts_code, l1_name (一级行业)
    """
    if industry_path is None:
        industry_path = '/mnt/c/Users/mm/PyCharmMiscProject/获取数据代码/industry_cache.csv'

    try:
        df = pd.read_csv(industry_path)
        # 只保留需要的列
        industry_map = df[['ts_code', 'l1_name']].copy()
        print(f"✓ 加载行业数据: {len(industry_map)} 只股票，{industry_map['l1_name'].nunique()} 个行业")
        return industry_map
    except Exception as e:
        print(f"✗ 加载行业数据失败: {e}")
        return pd.DataFrame()


def get_daily_pe_ttm(start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取日频PE_TTM数据
    """
    sql = """
    SELECT
        ts_code,
        trade_date,
        pe_ttm
    FROM daily_basic
    WHERE trade_date >= %s
      AND trade_date <= %s
      AND pe_ttm IS NOT NULL
      AND pe_ttm > 0
    ORDER BY ts_code, trade_date
    """

    data = db.execute_query(sql, (start_date, end_date))
    df = pd.DataFrame(data)

    if len(df) == 0:
        print(f"⚠️  未获取到daily_basic数据")
    else:
        print(f"✓ 获取daily_basic数据: {len(df):,} 条记录")

    return df


def get_fina_dt_netprofit_yoy(start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取扣非净利润同比增长率数据
    """
    sql = """
    SELECT
        ts_code,
        ann_date,
        dt_netprofit_yoy
    FROM fina_indicator
    WHERE ann_date >= %s
      AND ann_date <= %s
      AND update_flag = '1'
      AND dt_netprofit_yoy IS NOT NULL
      AND dt_netprofit_yoy != 0
    ORDER BY ts_code, ann_date
    """

    data = db.execute_query(sql, (start_date, end_date))
    df = pd.DataFrame(data)

    if len(df) == 0:
        print(f"⚠️  未获取到fina_indicator数据")
    else:
        print(f"✓ 获取fina_indicator数据: {len(df):,} 条记录")

    return df


def apply_industry_adjustment(df: pd.DataFrame, industry_map: pd.DataFrame) -> pd.DataFrame:
    """
    应用行业特殊适配规则

    包括:
    1. 金融行业PE修正
    2. 周期行业增长率调整
    3. 行业特定异常值阈值
    """
    print("\n步骤3: 应用行业特殊适配...")

    # 合并行业信息
    df_merged = df.merge(industry_map, on='ts_code', how='left')

    # 填充未知行业为'其他'
    df_merged['l1_name'] = df_merged['l1_name'].fillna('其他')

    # 应用行业特定规则
    adjusted_count = 0

    for industry, rules in INDUSTRY_ADJUSTMENT.items():
        mask = df_merged['l1_name'] == industry

        if mask.sum() == 0:
            continue

        # 1. PE修正
        if rules.get('pe_adjust', False):
            pe_min = rules.get('pe_min', 0)
            pe_max = rules.get('pe_max', 1000)

            # 修正PE值
            original_pe = df_merged.loc[mask, 'pe_ttm'].copy()
            df_merged.loc[mask, 'pe_ttm'] = df_merged.loc[mask, 'pe_ttm'].clip(lower=pe_min, upper=pe_max)

            corrected = (original_pe != df_merged.loc[mask, 'pe_ttm']).sum()
            if corrected > 0:
                print(f"  {industry}: PE修正 {corrected} 条")
                adjusted_count += corrected

        # 2. 季节性调整（简化版：使用滚动均值）
        if rules.get('seasonal_adjust', False):
            # 这里可以添加更复杂的季节性调整逻辑
            # 简化处理：不做调整，仅标记
            pass

    if adjusted_count > 0:
        print(f"  共调整 {adjusted_count} 条记录")

    return df_merged


def calculate_alpha_peg_by_industry(df: pd.DataFrame,
                                    outlier_sigma: float = 3.0,
                                    normalization: str = None) -> pd.DataFrame:
    """
    分行业计算alpha_peg因子

    参数:
        df: 包含ts_code, trade_date, pe_ttm, dt_netprofit_yoy, l1_name的数据
        outlier_sigma: 异常值阈值（标准差倍数）
        normalization: 标准化方法，None/'zscore'/'rank'

    返回:
        包含alpha_peg的DataFrame
    """
    print(f"\n步骤4: 分行业计算alpha_peg...")
    print(f"  异常值阈值: {outlier_sigma}σ")
    print(f"  标准化方法: {normalization if normalization else '无'}")

    results = []

    # 按行业分组计算
    for industry, group in df.groupby('l1_name'):
        industry_data = group.copy()

        # 基础计算
        industry_data['alpha_peg_raw'] = industry_data['pe_ttm'] / industry_data['dt_netprofit_yoy']

        # 行业内异常值处理（3σ原则）
        if outlier_sigma > 0:
            # 获取行业特定阈值
            threshold = INDUSTRY_ADJUSTMENT.get(industry, {}).get('outlier_threshold', outlier_sigma)

            mean_val = industry_data['alpha_peg_raw'].mean()
            std_val = industry_data['alpha_peg_raw'].std()

            if std_val > 0:
                lower_bound = mean_val - threshold * std_val
                upper_bound = mean_val + threshold * std_val

                # 标记异常值
                outlier_mask = (
                    (industry_data['alpha_peg_raw'] < lower_bound) |
                    (industry_data['alpha_peg_raw'] > upper_bound)
                )

                outlier_count = outlier_mask.sum()

                if outlier_count > 0:
                    print(f"  {industry}: 异常值 {outlier_count} 条 (阈值: {threshold}σ)")

                    # 异常值处理策略：缩尾处理（Winsorization）
                    industry_data.loc[outlier_mask, 'alpha_peg_raw'] = np.clip(
                        industry_data.loc[outlier_mask, 'alpha_peg_raw'],
                        lower_bound,
                        upper_bound
                    )

        # 行业内标准化
        if normalization == 'zscore':
            # Z-score标准化
            mean_val = industry_data['alpha_peg_raw'].mean()
            std_val = industry_data['alpha_peg_raw'].std()

            if std_val > 0:
                industry_data['alpha_peg'] = (industry_data['alpha_peg_raw'] - mean_val) / std_val
                print(f"  {industry}: Z-score标准化")
            else:
                industry_data['alpha_peg'] = industry_data['alpha_peg_raw']

        elif normalization == 'rank':
            # 秩转换（百分位数）
            industry_data['alpha_peg'] = industry_data['alpha_peg_raw'].rank(pct=True)
            print(f"  {industry}: 秩转换")

        else:
            # 不标准化
            industry_data['alpha_peg'] = industry_data['alpha_peg_raw']

        results.append(industry_data)

    # 合并所有行业结果
    final_result = pd.concat(results, ignore_index=True)

    # 保留关键字段
    final_result = final_result[[
        'ts_code',
        'trade_date',
        'l1_name',
        'pe_ttm',
        'dt_netprofit_yoy',
        'alpha_peg_raw',
        'alpha_peg'
    ]]

    return final_result


def calc_alpha_peg_industry(start_date: str = '20240801',
                            end_date: str = '20250305',
                            outlier_sigma: float = 3.0,
                            normalization: str = None,
                            output_path: str = None) -> pd.DataFrame:
    """
    alpha_peg因子计算主函数（行业优化版）

    参数:
        start_date: 开始日期
        end_date: 结束日期
        outlier_sigma: 异常值阈值（标准差倍数），None表示不处理
        normalization: 标准化方法，None/'zscore'/'rank'
        output_path: 输出路径

    返回:
        alpha_peg因子数据
    """
    print("="*80)
    print("alpha_peg因子计算 - 行业优化版")
    print("="*80)
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"异常值处理: {outlier_sigma}σ原则" if outlier_sigma else "异常值处理: 无")
    print(f"标准化: {normalization if normalization else '无'}")
    print("="*80)

    # 步骤1: 加载行业数据
    print("\n步骤1: 加载行业数据...")
    industry_map = load_industry_data()

    if len(industry_map) == 0:
        print("❌ 失败: 无法加载行业数据")
        return pd.DataFrame()

    # 步骤2: 获取基础数据
    print("\n步骤2: 获取基础数据...")
    df_pe = get_daily_pe_ttm(start_date, end_date)
    df_fina = get_fina_dt_netprofit_yoy(start_date, end_date)

    if len(df_pe) == 0 or len(df_fina) == 0:
        print("❌ 失败: 基础数据不完整")
        return pd.DataFrame()

    # 步骤3: 关联数据
    print("\n步骤3: 关联数据...")
    df_merged = pd.merge(
        df_pe,
        df_fina[['ts_code', 'ann_date', 'dt_netprofit_yoy']],
        left_on=['ts_code', 'trade_date'],
        right_on=['ts_code', 'ann_date'],
        how='left'
    )

    # 前向填充
    df_merged['dt_netprofit_yoy_ffill'] = df_merged.groupby('ts_code')['dt_netprofit_yoy'].ffill()

    # 过滤有效数据
    valid_mask = (
        df_merged['pe_ttm'].notna() &
        (df_merged['pe_ttm'] > 0) &
        df_merged['dt_netprofit_yoy_ffill'].notna() &
        (df_merged['dt_netprofit_yoy_ffill'] != 0)
    )

    df_valid = df_merged[valid_mask].copy()
    df_valid['dt_netprofit_yoy'] = df_valid['dt_netprofit_yoy_ffill']

    print(f"  有效数据: {len(df_valid):,} 条")

    # 步骤4: 应用行业适配
    df_with_industry = apply_industry_adjustment(df_valid, industry_map)

    # 步骤5: 分行业计算
    df_result = calculate_alpha_peg_by_industry(
        df_with_industry,
        outlier_sigma=outlier_sigma,
        normalization=normalization
    )

    # 步骤6: 保存结果
    if output_path is None:
        norm_suffix = f"_{normalization}" if normalization else ""
        output_path = f'/home/zcy/alpha006_20251223/results/factor/alpha_peg_industry{norm_suffix}_sigma{outlier_sigma}.csv'

    if len(df_result) > 0:
        df_result.to_csv(output_path, index=False)
        print(f"\n✓ 结果已保存: {output_path}")
        print(f"  记录数: {len(df_result):,}")
        print(f"  股票数: {df_result['ts_code'].nunique()}")
        print(f"  行业数: {df_result['l1_name'].nunique()}")

        # 统计摘要
        print("\n统计摘要:")
        print(f"  alpha_peg_raw 均值: {df_result['alpha_peg_raw'].mean():.4f}")
        print(f"  alpha_peg_raw 中位数: {df_result['alpha_peg_raw'].median():.4f}")
        print(f"  alpha_peg 均值: {df_result['alpha_peg'].mean():.4f}")
        print(f"  alpha_peg 中位数: {df_result['alpha_peg'].median():.4f}")

        # 行业分布
        print("\n行业分布:")
        industry_dist = df_result.groupby('l1_name').agg({
            'ts_code': 'nunique',
            'alpha_peg': ['mean', 'median']
        }).round(4)
        print(industry_dist)
    else:
        print("\n❌ 无有效结果")

    print("\n" + "="*80)
    print("计算完成")
    print("="*80)

    return df_result


if __name__ == "__main__":
    # 运行行业优化版计算
    df_result = calc_alpha_peg_industry(
        start_date='20240801',
        end_date='20250305',
        outlier_sigma=3.0,
        normalization=None  # 可选: 'zscore', 'rank'
    )

    # 显示前10条记录
    if len(df_result) > 0:
        print("\n前10条记录:")
        print(df_result.head(10).to_string(index=False))
