"""
计算alpha_010因子并更新Excel文件
版本: v2.0
更新日期: 2025-12-30
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, '/home/zcy/alpha006_20251223')

from core.utils.db_connection import db
from core.utils.data_loader import data_loader
from factors.price.PRI_TREND_4D_V2 import PriTrend4Dv2Factor
from core.config.params import get_factor_param

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


def get_target_date_from_excel(df):
    """从Excel中提取目标日期"""
    if '交易日' in df.columns:
        target_date = df['交易日'].iloc[0]
        if isinstance(target_date, (int, str)):
            return str(target_date)
        elif isinstance(target_date, pd.Timestamp):
            return target_date.strftime('%Y%m%d')
    # 默认使用20250919
    return '20250919'


def calculate_alpha_010_for_stocks(stocks, target_date):
    """
    为指定股票列表计算alpha_010因子

    计算逻辑:
    1. 获取最近5天的价格数据（4天计算 + 1天目标）
    2. 计算每日涨跌幅 Δclose
    3. 统计4日Δclose的ts_min/ts_max
    4. 三元规则取值
    5. 全市场rank
    """
    logger.info(f"开始计算alpha_010因子，目标日期: {target_date}")

    # 计算开始日期（需要5天数据）
    target_dt = pd.to_datetime(target_date, format='%Y%m%d')
    start_dt = target_dt - timedelta(days=10)  # 缓冲10天
    start_date = start_dt.strftime('%Y%m%d')

    # 获取价格数据
    price_df = data_loader.get_price_data(stocks, start_date, target_date)
    logger.info(f"获取价格数据: {len(price_df)}条")

    if len(price_df) == 0:
        logger.error("无法获取价格数据")
        return pd.DataFrame()

    # 创建因子计算器
    params = get_factor_param('alpha_010', 'standard')
    factor = PriTrend4Dv2Factor(params)

    # 计算因子
    result = factor.calculate(price_df)

    if len(result) > 0:
        logger.info(f"计算完成: {len(result)}只股票")
        logger.info(f"alpha_010统计: 均值={result['alpha_010'].mean():.2f}, 范围=[{result['alpha_010'].min():.0f}, {result['alpha_010'].max():.0f}]")

    return result


def merge_alpha_010_to_excel(df_existing, df_alpha010):
    """将alpha_010合并到现有Excel数据"""
    logger.info("开始合并alpha_010到Excel")

    # 重命名列以匹配
    df_alpha010_merged = df_alpha010[['ts_code', 'alpha_010']].copy()
    df_alpha010_merged.columns = ['股票代码', 'alpha_010']

    # 合并数据
    df_merged = df_existing.merge(df_alpha010_merged, on='股票代码', how='left')

    # 检查合并结果
    merge_rate = df_merged['alpha_010'].notna().sum() / len(df_merged) * 100
    logger.info(f"合并完成: {len(df_merged)}行, alpha_010有效率: {merge_rate:.1f}%")

    return df_merged


def reorder_columns(df):
    """按指定顺序重新排列列"""
    target_columns = [
        '股票代码', '交易日', '申万一级行业',
        'alpha_pluse', '原始alpha_peg', '行业标准化alpha_peg',
        'alpha_010', 'alpha_038', 'alpha_120cq', 'cr_qfq',
        '备注'
    ]

    # 检查哪些列存在
    existing_cols = [col for col in target_columns if col in df.columns]
    missing_cols = [col for col in target_columns if col not in df.columns]

    if missing_cols:
        logger.warning(f"缺失列: {missing_cols}")

    # 重新排序
    df_reordered = df[existing_cols].copy()

    return df_reordered


def save_updated_excel(df, original_path):
    """保存更新后的Excel文件"""
    # 生成新文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    new_filename = f"multi_factor_values_20250919_with_alpha_010_{timestamp}.xlsx"
    new_path = os.path.join(os.path.dirname(original_path), new_filename)

    # 保存
    df.to_excel(new_path, index=False)
    logger.info(f"更新后的Excel已保存: {new_path}")

    return new_path


def main():
    """主函数"""
    print("\n" + "="*80)
    print("计算alpha_010因子并更新Excel")
    print("="*80)

    # 1. 读取现有Excel
    excel_path = '/home/zcy/alpha006_20251223/results/output/multi_factor_values_20250919.xlsx'
    df_existing = load_existing_excel(excel_path)

    # 2. 获取目标日期
    target_date = get_target_date_from_excel(df_existing)
    logger.info(f"目标日期: {target_date}")

    # 3. 获取Excel中的股票列表
    stocks = df_existing['股票代码'].tolist()
    logger.info(f"需要计算的股票数量: {len(stocks)}")

    # 4. 计算alpha_010因子
    df_alpha010 = calculate_alpha_010_for_stocks(stocks, target_date)

    if len(df_alpha010) == 0:
        logger.error("alpha_010计算失败")
        return

    # 5. 合并到Excel
    df_merged = merge_alpha_010_to_excel(df_existing, df_alpha010)

    # 6. 重新排序列
    df_final = reorder_columns(df_merged)

    # 7. 保存
    new_path = save_updated_excel(df_final, excel_path)

    # 8. 打印统计信息
    print("\n" + "="*80)
    print("计算结果统计")
    print("="*80)
    print(f"总股票数: {len(df_final)}")
    print(f"alpha_010有效数: {df_final['alpha_010'].notna().sum()}")
    print(f"缺失数: {df_final['alpha_010'].isna().sum()}")

    if df_final['alpha_010'].notna().sum() > 0:
        valid_data = df_final['alpha_010'].dropna()
        print(f"\nalpha_010统计:")
        print(f"  均值: {valid_data.mean():.2f}")
        print(f"  标准差: {valid_data.std():.2f}")
        print(f"  最小值: {valid_data.min():.0f}")
        print(f"  最大值: {valid_data.max():.0f}")
        print(f"  中位数: {valid_data.median():.2f}")

        # 显示前10名
        print(f"\nalpha_010前10名:")
        top10 = df_final[df_final['alpha_010'].notna()].nlargest(10, 'alpha_010')[['股票代码', '申万一级行业', 'alpha_010', 'alpha_038', 'alpha_120cq']]
        print(top10.to_string(index=False))

    print(f"\n✅ 任务完成！文件已保存至: {new_path}")


if __name__ == '__main__':
    main()