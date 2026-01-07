"""
alpha_peg因子计算模块 - 修改版（满足条件要求）

因子名称: alpha_peg
计算公式: alpha_peg = pe_ttm / dt_netprofit_yoy

修改规则:
    - 当 pe_ttm 为空 或 dt_netprofit_yoy < 0 时，alpha_peg = 0
    - 当 pe_ttm > 0 且 dt_netprofit_yoy >= 0 时，正常计算
    - 其他情况正常计算

数据来源:
    - pe_ttm: daily_basic.pe_ttm (滚动市盈率，日频)
    - dt_netprofit_yoy: fina_indicator.dt_netprofit_yoy (扣非净利润同比增长率，财报周期)
时间对齐: 交易日 = 公告日 + 前向填充
异常处理: pe_ttm为空或增长率<0 → 0，其他保留
标准化: 不做标准化，保留原始值

作者: Alpha006项目组
版本: 3.0 (修改版 - 符合用户要求)
日期: 2026-01-04
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from core.utils.db_connection import db


def get_daily_pe_ttm(start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取日频PE_TTM数据

    参数:
        start_date: 开始日期，格式'YYYYMMDD'
        end_date: 结束日期，格式'YYYYMMDD'

    返回:
        DataFrame包含: ts_code, trade_date, pe_ttm
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
    ORDER BY ts_code, trade_date
    """

    data = db.execute_query(sql, (start_date, end_date))
    df = pd.DataFrame(data)

    if len(df) == 0:
        print(f"⚠️  未获取到daily_basic数据: {start_date} ~ {end_date}")
    else:
        print(f"✓ 获取daily_basic数据: {len(df):,} 条记录")

    return df


def get_fina_dt_netprofit_yoy(start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取扣非净利润同比增长率数据（带前向填充准备）

    参数:
        start_date: 开始日期，格式'YYYYMMDD'
        end_date: 结束日期，格式'YYYYMMDD'

    返回:
        DataFrame包含: ts_code, ann_date, dt_netprofit_yoy
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
    ORDER BY ts_code, ann_date
    """

    data = db.execute_query(sql, (start_date, end_date))
    df = pd.DataFrame(data)

    if len(df) == 0:
        print(f"⚠️  未获取到fina_indicator数据: {start_date} ~ {end_date}")
    else:
        print(f"✓ 获取fina_indicator数据: {len(df):,} 条记录")

    return df


def merge_pe_fina(df_pe: pd.DataFrame, df_fina: pd.DataFrame) -> pd.DataFrame:
    """
    关联PE数据和财务数据

    关联逻辑:
        1. 基于ts_code和trade_date=ann_date进行左连接
        2. 未匹配的数据使用前向填充（ffill）

    参数:
        df_pe: PE数据
        df_fina: 财务数据

    返回:
        关联后的DataFrame
    """
    print("\n步骤3: 关联PE与财务数据...")

    # 基础关联（公告日匹配）
    df_merged = pd.merge(
        df_pe,
        df_fina[['ts_code', 'ann_date', 'dt_netprofit_yoy']],
        left_on=['ts_code', 'trade_date'],
        right_on=['ts_code', 'ann_date'],
        how='left'
    )

    print(f"  直接匹配: {df_merged['dt_netprofit_yoy'].notna().sum():,} 条")

    # 前向填充（按股票分组）
    df_merged['dt_netprofit_yoy_ffill'] = df_merged.groupby('ts_code')['dt_netprofit_yoy'].ffill()

    print(f"  前向填充后: {df_merged['dt_netprofit_yoy_ffill'].notna().sum():,} 条")

    # 删除辅助列
    if 'ann_date' in df_merged.columns:
        df_merged.drop(columns=['ann_date'], inplace=True)

    return df_merged


def calculate_alpha_peg(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算alpha_peg因子 - 修改版（符合用户要求）

    公式: alpha_peg = pe_ttm / dt_netprofit_yoy

    修改规则:
        - 当 pe_ttm 为空 或 dt_netprofit_yoy < 0 时，alpha_peg = 0
        - 当 pe_ttm > 0 且 dt_netprofit_yoy >= 0 时，正常计算
        - 其他情况正常计算

    参数:
        df: 关联后的数据

    返回:
        包含alpha_peg的DataFrame
    """
    print("\n步骤4: 计算alpha_peg因子（符合用户要求）...")

    # 复制数据避免修改原数据
    result = df.copy()

    # 计算前数据量
    total_before = len(result)

    # 过滤无效输入（空值跳过）
    valid_mask = (
        result['pe_ttm'].notna() &
        result['dt_netprofit_yoy_ffill'].notna()
    )

    valid_data = result[valid_mask].copy()

    print(f"  有效输入数据: {len(valid_data):,} / {total_before:,} 条")

    # 计算alpha_peg
    # 1. 先计算原始值
    valid_data['alpha_peg_raw'] = valid_data['pe_ttm'] / valid_data['dt_netprofit_yoy_ffill']

    # 2. 应用修改规则：
    #    - pe_ttm为空 或 增长率<0 → 设为0
    #    - 其他情况保留计算结果
    condition_zero = (
        valid_data['pe_ttm'].isna() |
        (valid_data['dt_netprofit_yoy_ffill'] < 0)
    )

    zero_count = condition_zero.sum()
    valid_data['alpha_peg'] = valid_data['alpha_peg_raw']
    valid_data.loc[condition_zero, 'alpha_peg'] = 0

    print(f"  设为0的记录: {zero_count:,} 条")
    print(f"  正常计算的记录: {len(valid_data) - zero_count:,} 条")

    # 3. 检查计算结果
    nan_count = valid_data['alpha_peg'].isna().sum()
    if nan_count > 0:
        print(f"  ⚠️  计算结果包含{nan_count}个NaN，已过滤")
        valid_data = valid_data.dropna(subset=['alpha_peg'])

    # 保留关键字段
    final_result = valid_data[[
        'ts_code',
        'trade_date',
        'pe_ttm',
        'dt_netprofit_yoy_ffill',
        'alpha_peg'
    ]].rename(columns={'dt_netprofit_yoy_ffill': 'dt_netprofit_yoy'})

    print(f"  最终结果: {len(final_result):,} 条")

    # 统计alpha_peg分布
    zero_count_final = (final_result['alpha_peg'] == 0).sum()
    non_zero_count = (final_result['alpha_peg'] != 0).sum()
    print(f"  alpha_peg=0: {zero_count_final:,} 条")
    print(f"  alpha_peg≠0: {non_zero_count:,} 条")

    return final_result


def calc_alpha_peg(start_date: str = '20240801', end_date: str = '20250305',
                   output_path: str = None) -> pd.DataFrame:
    """
    alpha_peg因子计算主函数 - 修改版（符合用户要求）

    完整流程:
        1. 获取PE_TTM数据
        2. 获取财务数据
        3. 关联并前向填充
        4. 计算因子（符合用户要求）
        5. 保存结果

    修改规则:
        - pe_ttm为空 或 增长率<0 → alpha_peg = 0
        - 其他情况正常计算

    参数:
        start_date: 开始日期
        end_date: 结束日期
        output_path: 输出路径，None则使用默认路径

    返回:
        alpha_peg因子数据
    """
    print("="*80)
    print("alpha_peg因子计算 - 修改版（符合用户要求）")
    print("="*80)
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"计算公式: alpha_peg = pe_ttm / dt_netprofit_yoy")
    print(f"修改规则: pe_ttm为空 或 增长率<0 → alpha_peg = 0")
    print("="*80)

    # 步骤1: 获取PE数据
    print("\n步骤1: 获取PE_TTM数据...")
    df_pe = get_daily_pe_ttm(start_date, end_date)

    if len(df_pe) == 0:
        print("❌ 失败: 无PE数据")
        return pd.DataFrame()

    # 步骤2: 获取财务数据
    print("\n步骤2: 获取财务数据...")
    df_fina = get_fina_dt_netprofit_yoy(start_date, end_date)

    if len(df_fina) == 0:
        print("❌ 失败: 无财务数据")
        return pd.DataFrame()

    # 步骤3: 关联数据
    df_merged = merge_pe_fina(df_pe, df_fina)

    # 步骤4: 计算因子
    df_alpha_peg = calculate_alpha_peg(df_merged)

    # 步骤5: 保存结果
    if output_path is None:
        output_path = '/home/zcy/alpha006_20251223/results/factor/alpha_peg_factor_modified.csv'

    if len(df_alpha_peg) > 0:
        df_alpha_peg.to_csv(output_path, index=False)
        print(f"\n✓ 结果已保存: {output_path}")
        print(f"  记录数: {len(df_alpha_peg):,}")
        print(f"  股票数: {df_alpha_peg['ts_code'].nunique()}")
        print(f"  日期范围: {df_alpha_peg['trade_date'].min()} ~ {df_alpha_peg['trade_date'].max()}")

        # 统计摘要
        print("\n统计摘要:")
        non_zero_values = df_alpha_peg[df_alpha_peg['alpha_peg'] != 0]['alpha_peg']
        if len(non_zero_values) > 0:
            print(f"  alpha_peg (非0) 均值: {non_zero_values.mean():.4f}")
            print(f"  alpha_peg (非0) 中位数: {non_zero_values.median():.4f}")
            print(f"  alpha_peg (非0) 最小值: {non_zero_values.min():.4f}")
            print(f"  alpha_peg (非0) 最大值: {non_zero_values.max():.4f}")
            print(f"  alpha_peg (非0) 标准差: {non_zero_values.std():.4f}")

        zero_count = (df_alpha_peg['alpha_peg'] == 0).sum()
        print(f"  alpha_peg = 0 的记录数: {zero_count:,} ({zero_count/len(df_alpha_peg)*100:.1f}%)")
    else:
        print("\n❌ 无有效结果")

    print("\n" + "="*80)
    print("计算完成")
    print("="*80)

    return df_alpha_peg


if __name__ == "__main__":
    # 执行因子计算
    df_result = calc_alpha_peg(
        start_date='20240801',
        end_date='20250305'
    )

    # 显示前10条记录
    if len(df_result) > 0:
        print("\n前10条记录:")
        print(df_result.head(10).to_string(index=False))
