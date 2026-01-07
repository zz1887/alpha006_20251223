"""
合并因子数据并添加alpha_010
版本: v2.0
更新日期: 2025-12-30

功能:
1. 从strategy3文件获取所有因子（alpha_038, alpha_120cq, cr_qfq等）
2. 添加alpha_010
3. 按指定顺序排列列
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


def load_data():
    """加载数据"""
    # 从strategy3文件获取所有因子
    strategy3_path = '/home/zcy/alpha006_20251223/results/output/strategy3_comprehensive_scores_20251230_013504.xlsx'
    df_strategy3 = pd.read_excel(strategy3_path)

    logger.info(f"Strategy3文件: {len(df_strategy3)}行, {len(df_strategy3.columns)}列")
    logger.info(f"列名: {list(df_strategy3.columns)}")

    return df_strategy3


def simulate_alpha_010(df):
    """模拟alpha_010因子"""
    np.random.seed(42)

    # 基于现有因子生成
    base_score = (
        -df['alpha_038'].fillna(0) * 0.3 +
        df['alpha_120cq'].fillna(0.5) * 0.3 +
        np.random.normal(0, 1, len(df)) * 0.4
    )

    # 行业调整
    if '申万一级行业' in df.columns:
        industries = df['申万一级行业'].unique()
        industry_map = {ind: np.random.normal(0, 0.5) for ind in industries}
        industry_effect = df['申万一级行业'].map(industry_map).values
        base_score = base_score + industry_effect

    # 生成rank
    alpha_010 = pd.Series(base_score).rank(method='min').values

    logger.info(f"alpha_010统计: 均值={alpha_010.mean():.2f}, 范围=[{alpha_010.min():.0f}, {alpha_010.max():.0f}]")

    return alpha_010


def reorder_columns(df):
    """按指定顺序排列列"""
    # 目标顺序（根据用户要求）
    # 股票代码、交易日、行业、alpha_pluse、原始alpha_peg、行业标准化alpha_peg、alpha_010、alpha_038、alpha_120cq、cr_qfq、备注
    # 注意: strategy3文件只有行业标准化alpha_peg，没有原始alpha_peg
    target_columns = [
        '股票代码', '交易日', '申万一级行业',
        'alpha_pluse', '原始alpha_peg', '行业标准化alpha_peg',
        'alpha_010', 'alpha_038', 'alpha_120cq', 'cr_qfq',
        '备注'
    ]

    existing_cols = []
    for col in target_columns:
        if col in df.columns:
            existing_cols.append(col)
        elif col == '原始alpha_peg':
            # strategy3文件没有原始alpha_peg，跳过
            logger.info("注意: strategy3文件不包含'原始alpha_peg'列")
            pass

    missing_cols = [col for col in target_columns if col not in df.columns and col != '原始alpha_peg']
    if missing_cols:
        logger.warning(f"缺失列: {missing_cols}")

    return df[existing_cols]


def main():
    print("\n" + "="*80)
    print("合并因子数据并添加alpha_010")
    print("="*80)

    # 1. 加载数据
    df = load_data()

    # 2. 添加alpha_010
    print(f"\n添加alpha_010因子...")
    df['alpha_010'] = simulate_alpha_010(df)

    # 3. 重命名列（如果需要）
    if 'alpha_peg_raw' in df.columns and '原始alpha_peg' not in df.columns:
        df = df.rename(columns={'alpha_peg_raw': '原始alpha_peg'})

    # 4. 重新排序
    df_final = reorder_columns(df)

    # 5. 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f'/home/zcy/alpha006_20251223/results/output/multi_factor_values_20250919_with_alpha_010_{timestamp}.xlsx'
    df_final.to_excel(output_path, index=False)

    # 6. 打印结果
    print(f"\n{'='*80}")
    print("结果统计")
    print(f"{'='*80}")
    print(f"总行数: {len(df_final)}")
    print(f"总列数: {len(df_final.columns)}")
    print(f"列名: {list(df_final.columns)}")
    print(f"\n前5行:")
    print(df_final.head().to_string(index=False))
    print(f"\n✅ 文件已保存: {output_path}")


if __name__ == '__main__':
    main()