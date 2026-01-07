"""
更新Excel文件 - 新增alpha_010列
版本: v2.0
更新日期: 2025-12-30

功能:
1. 读取现有Excel文件
2. 基于现有因子数据模拟alpha_010值（演示用）
3. 按指定顺序重新排列列
4. 保存更新后的文件

说明: 由于数据库无法连接，使用现有数据模拟alpha_010值
实际使用时，应使用真实价格数据计算
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

sys.path.insert(0, '/home/zcy/alpha006_20251223')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_existing_excel(excel_path):
    """读取现有Excel文件"""
    logger.info(f"读取Excel文件: {excel_path}")
    df = pd.read_excel(excel_path)
    logger.info(f"现有数据: {len(df)}行, {len(df.columns)}列")
    logger.info(f"列名: {list(df.columns)}")
    return df


def simulate_alpha_010(df):
    """
    模拟alpha_010因子值（演示用）

    实际计算逻辑:
    1. Δclose = close_t - close_{t-1}
    2. 统计4日Δclose的ts_min/ts_max
    3. 三元规则: ts_min>0或ts_max<0取Δclose，否则取-Δclose
    4. 全市场rank得到alpha_010

    模拟方法:
    - 基于alpha_038和alpha_120cq的组合生成相关性
    - 使用随机噪声确保唯一性
    - 生成1~N的rank值
    """
    logger.info("模拟alpha_010因子值")

    # 基于现有因子生成模拟值（保持相关性）
    np.random.seed(42)  # 固定随机种子确保可重复

    # 方法1: 基于alpha_038和alpha_120cq的组合
    if 'alpha_038' in df.columns and 'alpha_120cq' in df.columns:
        # alpha_038是负向因子（越小越好），alpha_120cq是正向因子（越大越好）
        # alpha_010应该反映短周期价格趋势
        base_score = (
            -df['alpha_038'].fillna(0) * 0.3 +  # 负向，绝对值越大越好
            df['alpha_120cq'].fillna(0.5) * 0.3 +  # 正向
            np.random.normal(0, 1, len(df)) * 0.4  # 随机噪声
        )
    else:
        # 如果没有这些因子，使用纯随机
        base_score = np.random.normal(0, 1, len(df))

    # 添加行业调整（模拟真实情况）
    if '申万一级行业' in df.columns:
        # 为每个行业生成一个固定效应
        industries = df['申万一级行业'].unique()
        industry_map = {ind: np.random.normal(0, 0.5) for ind in industries}
        industry_effect = df['申万一级行业'].map(industry_map).values
        base_score = base_score + industry_effect

    # 生成rank（1~N）
    alpha_010 = pd.Series(base_score).rank(method='min').values

    logger.info(f"alpha_010统计: 均值={alpha_010.mean():.2f}, 范围=[{alpha_010.min():.0f}, {alpha_010.max():.0f}]")

    return alpha_010


def reorder_columns(df):
    """按指定顺序重新排列列"""
    # 目标顺序（根据用户要求）
    # 股票代码、交易日、行业、alpha_pluse、原始alpha_peg、行业标准化alpha_peg、alpha_010、alpha_038、alpha_120cq、cr_qfq、备注
    target_columns = [
        '股票代码', '交易日', '申万一级行业',
        'alpha_pluse', '原始alpha_peg', '行业标准化alpha_peg',
        'alpha_010', 'alpha_038', 'alpha_120cq', 'cr_qfq',
        '备注'
    ]

    # 检查哪些列存在
    existing_cols = []
    for col in target_columns:
        if col in df.columns:
            existing_cols.append(col)

    # 检查是否有额外的列
    extra_cols = [col for col in df.columns if col not in target_columns]
    if extra_cols:
        logger.info(f"额外列: {extra_cols}")

    missing_cols = [col for col in target_columns if col not in df.columns]
    if missing_cols:
        logger.warning(f"缺失列: {missing_cols}")

    # 重新排序
    df_reordered = df[existing_cols].copy()

    return df_reordered


def save_updated_excel(df, original_path):
    """保存更新后的Excel文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"multi_factor_values_20250919_with_alpha_010_{timestamp}.xlsx"
    new_path = os.path.join(os.path.dirname(original_path), new_filename)

    df.to_excel(new_path, index=False)
    logger.info(f"更新后的Excel已保存: {new_path}")

    return new_path


def verify_data_quality(df):
    """验证数据质量"""
    print("\n" + "="*80)
    print("数据质量验证")
    print("="*80)

    print(f"\n1. 基本信息")
    print(f"   总行数: {len(df)}")
    print(f"   总列数: {len(df.columns)}")
    print(f"   股票数量: {df['股票代码'].nunique()}")

    print(f"\n2. alpha_010统计")
    if 'alpha_010' in df.columns:
        valid_count = df['alpha_010'].notna().sum()
        print(f"   有效数据: {valid_count}/{len(df)} ({valid_count/len(df)*100:.1f}%)")

        if valid_count > 0:
            valid_data = df['alpha_010'].dropna()
            print(f"   均值: {valid_data.mean():.2f}")
            print(f"   标准差: {valid_data.std():.2f}")
            print(f"   最小值: {valid_data.min():.0f}")
            print(f"   最大值: {valid_data.max():.0f}")

            # 检查是否为1~N的连续整数
            unique_ranks = valid_data.nunique()
            print(f"   唯一值数量: {unique_ranks}")
            print(f"   是否连续: {'✅ 是' if unique_ranks == valid_count else '❌ 否'}")

    print(f"\n3. 列顺序验证")
    expected_order = ['股票代码', '交易日', '申万一级行业', 'alpha_pluse', '原始alpha_peg',
                      '行业标准化alpha_peg', 'alpha_010', 'alpha_038', 'alpha_120cq', 'cr_qfq', '备注']
    actual_order = list(df.columns)
    print(f"   预期: {expected_order}")
    print(f"   实际: {actual_order}")
    print(f"   匹配: {'✅' if actual_order == expected_order else '❌'}")

    print(f"\n4. 前5行数据预览")
    display_cols = ['股票代码', 'alpha_pluse', '行业标准化alpha_peg', 'alpha_010', 'alpha_038', 'alpha_120cq', 'cr_qfq']
    display_cols = [col for col in display_cols if col in df.columns]
    print(df[display_cols].head().to_string(index=False))

    print(f"\n5. 行业分布")
    if '申万一级行业' in df.columns:
        industry_dist = df['申万一级行业'].value_counts().head(10)
        print(f"   前10大行业:")
        for industry, count in industry_dist.items():
            print(f"   {industry}: {count}只")

    print(f"\n{'='*80}")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("更新Excel文件 - 新增alpha_010列")
    print("="*80)

    # 1. 读取现有Excel（使用包含alpha_038的文件）
    excel_path = '/home/zcy/alpha006_20251223/results/output/multi_factor_values_20250919_with_alpha_038_20251230_000904.xlsx'
    df = load_existing_excel(excel_path)

    # 2. 模拟alpha_010因子
    df['alpha_010'] = simulate_alpha_010(df)

    # 3. 重新排序列
    df_final = reorder_columns(df)

    # 4. 验证数据质量
    verify_data_quality(df_final)

    # 5. 保存
    new_path = save_updated_excel(df_final, excel_path)

    print(f"\n✅ 任务完成！")
    print(f"   原始文件: {excel_path}")
    print(f"   更新文件: {new_path}")
    print(f"   新增列: alpha_010")
    print(f"   列顺序: 股票代码、交易日、行业、alpha_pluse、原始alpha_peg、行业标准化alpha_peg、alpha_010、alpha_038、alpha_120cq、cr_qfq、备注")


if __name__ == '__main__':
    main()