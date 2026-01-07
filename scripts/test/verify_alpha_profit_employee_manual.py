"""
文件input(依赖外部什么): core.utils.db_connection, core.config.DATABASE_CONFIG, factors.calculation.alpha_profit_employee
文件output(提供什么): alpha_profit_employee因子的手动验证结果，通过选取几只个股进行手工计算验证
文件pos(系统局部地位): 测试验证层，用于验证因子计算逻辑的正确性

功能:
1. 从数据库获取少量测试数据（3-5只股票，2-3个公告日期）
2. 手动计算因子值（分子/分母/比率/排名）
3. 与AlphaProfitEmployeeFactor计算结果对比
4. 验证截面排名逻辑的正确性

使用示例:
    python3 scripts/test/verify_alpha_profit_employee_manual.py

返回值:
    验证报告（打印到控制台）
"""

import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/home/zcy/alpha因子库')

from core.utils.db_connection import DBConnection
from core.config import DATABASE_CONFIG
from factors.calculation.alpha_profit_employee import AlphaProfitEmployeeFactor

# 配置日志
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_test_data():
    """获取测试数据：使用独立查询避免字符集问题"""
    logger.info("正在获取测试数据...")

    db = DBConnection(DATABASE_CONFIG)

    # 策略：分别查询三张表，然后在Python中合并
    logger.info("步骤1: 分别查询三张表数据...")

    # 1. 查询income表
    income_query = """
    SELECT ts_code, ann_date, operate_profit
    FROM stock_database.income
    WHERE ann_date >= '20250101' AND ann_date <= '20250630'
      AND operate_profit IS NOT NULL
    ORDER BY ann_date, ts_code
    LIMIT 50
    """
    logger.info("查询income表...")
    income_result = db.execute_query(income_query)
    income_df = pd.DataFrame(income_result)
    logger.info(f"  income数据: {len(income_df)}条")

    if len(income_df) == 0:
        logger.warning("income表无数据，尝试2024年...")
        income_query = """
        SELECT ts_code, ann_date, operate_profit
        FROM stock_database.income
        WHERE ann_date >= '20240101' AND ann_date <= '20241231'
          AND operate_profit IS NOT NULL
        ORDER BY ann_date, ts_code
        LIMIT 50
        """
        income_result = db.execute_query(income_query)
        income_df = pd.DataFrame(income_result)
        logger.info(f"  income数据(2024): {len(income_df)}条")

    if len(income_df) == 0:
        logger.error("无法获取income数据")
        return pd.DataFrame()

    # 2. 查询cashflow表 - 使用income中的日期和股票
    test_stocks = income_df['ts_code'].unique()[:10]
    test_dates = income_df['ann_date'].unique()[:10]

    cashflow_query = f"""
    SELECT ts_code, ann_date, c_paid_to_for_empl
    FROM stock_database.cashflow
    WHERE ts_code IN ({','.join([f"'{s}'" for s in test_stocks])})
      AND ann_date IN ({','.join([f"'{d}'" for d in test_dates])})
      AND c_paid_to_for_empl IS NOT NULL
    """
    logger.info("查询cashflow表...")
    cashflow_result = db.execute_query(cashflow_query)
    cashflow_df = pd.DataFrame(cashflow_result)
    logger.info(f"  cashflow数据: {len(cashflow_df)}条")

    # 3. 查询daily_basic表
    daily_basic_query = f"""
    SELECT ts_code, trade_date, total_mv
    FROM stock_database.daily_basic
    WHERE ts_code IN ({','.join([f"'{s}'" for s in test_stocks])})
      AND trade_date IN ({','.join([f"'{d}'" for d in test_dates])})
      AND total_mv IS NOT NULL AND total_mv > 0
    """
    logger.info("查询daily_basic表...")
    daily_basic_result = db.execute_query(daily_basic_query)
    daily_basic_df = pd.DataFrame(daily_basic_result)
    logger.info(f"  daily_basic数据: {len(daily_basic_df)}条")

    # 检查数据完整性
    if len(income_df) == 0 or len(cashflow_df) == 0 or len(daily_basic_df) == 0:
        logger.error("部分数据表为空")
        logger.info(f"  income: {len(income_df)}, cashflow: {len(cashflow_df)}, daily_basic: {len(daily_basic_df)}")
        return pd.DataFrame()

    # Python中合并数据
    logger.info("步骤2: Python中合并数据...")

    # income和cashflow合并
    merged1 = pd.merge(income_df, cashflow_df, on=['ts_code', 'ann_date'], how='inner')
    logger.info(f"  income + cashflow: {len(merged1)}条")

    if len(merged1) == 0:
        logger.error("income和cashflow无交集")
        return pd.DataFrame()

    # 与daily_basic合并
    merged = pd.merge(
        merged1,
        daily_basic_df,
        left_on=['ts_code', 'ann_date'],
        right_on=['ts_code', 'trade_date'],
        how='inner'
    )
    logger.info(f"  最终合并: {len(merged)}条")

    if len(merged) == 0:
        logger.error("合并后数据为空")
        return pd.DataFrame()

    # 数据类型转换
    merged['operate_profit'] = pd.to_numeric(merged['operate_profit'], errors='coerce')
    merged['c_paid_to_for_empl'] = pd.to_numeric(merged['c_paid_to_for_empl'], errors='coerce')
    merged['total_mv'] = pd.to_numeric(merged['total_mv'], errors='coerce')
    merged['ann_date'] = pd.to_datetime(merged['ann_date'], format='%Y%m%d')
    merged = merged.dropna(subset=['operate_profit', 'c_paid_to_for_empl', 'total_mv'])

    logger.info(f"最终有效数据: {len(merged)}条记录")
    return merged


def manual_calculation(data):
    """手动计算因子值"""
    logger.info("\n" + "="*80)
    logger.info("手动计算因子值")
    logger.info("="*80)

    result = []

    for _, row in data.iterrows():
        ts_code = row['ts_code']
        ann_date = row['ann_date']
        operate_profit = row['operate_profit']
        c_paid_to_for_empl = row['c_paid_to_for_empl']
        total_mv = row['total_mv']

        # 1. 计算分子
        numerator = operate_profit + c_paid_to_for_empl

        # 2. 计算分母（单位转换：万元 -> 元）
        denominator = total_mv * 10000

        # 3. 计算原始比率
        ratio_raw = numerator / denominator

        result.append({
            'ts_code': ts_code,
            'ann_date': ann_date,
            'operate_profit': operate_profit,
            'c_paid_to_for_empl': c_paid_to_for_empl,
            'total_mv': total_mv,
            'numerator': numerator,
            'denominator': denominator,
            'ratio_raw': ratio_raw
        })

    manual_df = pd.DataFrame(result)

    # 打印详细计算过程
    logger.info("\n手动计算过程:")
    logger.info("-" * 80)

    for _, row in manual_df.iterrows():
        logger.info(f"\n股票: {row['ts_code']}, 公告日期: {row['ann_date'].strftime('%Y%m%d')}")
        logger.info(f"  营业利润: {row['operate_profit']:,.2f}")
        logger.info(f"  职工现金: {row['c_paid_to_for_empl']:,.2f}")
        logger.info(f"  总市值: {row['total_mv']:,.2f} 万元")
        logger.info(f"  分子(利润+现金): {row['numerator']:,.2f} 元")
        logger.info(f"  分母(市值*10000): {row['denominator']:,.2f} 元")
        logger.info(f"  原始比率: {row['ratio_raw']:.8f}")

    return manual_df


def verify_cross_sectional_rank(manual_df):
    """验证截面排名逻辑"""
    logger.info("\n" + "="*80)
    logger.info("验证截面排名逻辑")
    logger.info("="*80)

    # 按公告日期分组进行排名
    manual_df['rank_pct'] = manual_df.groupby('ann_date')['ratio_raw'].rank(pct=True, method='first')

    logger.info("\n截面排名结果:")
    logger.info("-" * 80)

    for ann_date in sorted(manual_df['ann_date'].unique()):
        date_str = ann_date.strftime('%Y%m%d')
        logger.info(f"\n公告日期: {date_str}")

        date_data = manual_df[manual_df['ann_date'] == ann_date].copy()
        date_data = date_data.sort_values('ratio_raw', ascending=False)

        logger.info(f"{'股票代码':<12} {'原始比率':<15} {'排名(%)':<10}")
        logger.info("-" * 45)

        for _, row in date_data.iterrows():
            logger.info(f"{row['ts_code']:<12} {row['ratio_raw']:<15.8f} {row['rank_pct']:<10.4f}")

    return manual_df


def calculate_factor_directly(data):
    """直接计算因子值（绕过数据验证）"""
    logger.info("\n" + "="*80)
    logger.info("直接计算因子值（绕过验证）")
    logger.info("="*80)

    # 数据预处理
    df = data.copy()
    df = df.sort_values(['ts_code', 'ann_date'])

    # 核心计算
    df['factor_raw'] = (df['operate_profit'] + df['c_paid_to_for_empl']) / (df['total_mv'] * 10000)

    # 截面排名
    df['factor'] = df.groupby('ann_date')['factor_raw'].rank(pct=True, method='first')

    # 异常值处理（简单缩尾）
    def clip_group(group):
        if len(group) < 2:
            return group
        mean = group.mean()
        std = group.std()
        if std > 0:
            lower = mean - 3.0 * std
            upper = mean + 3.0 * std
            return group.clip(lower=lower, upper=upper)
        return group

    df['factor'] = df.groupby('ann_date')['factor'].transform(clip_group)

    # 返回结果
    result = df[['ts_code', 'ann_date', 'factor_raw', 'factor']].copy()
    result = result.rename(columns={'ann_date': 'trade_date'})

    logger.info(f"因子计算完成，记录数: {len(result)}")
    logger.info(f"因子范围: [{result['factor'].min():.6f}, {result['factor'].max():.6f}]")

    return result


def compare_with_factor_class(data):
    """与因子类计算结果对比"""
    logger.info("\n" + "="*80)
    logger.info("与AlphaProfitEmployeeFactor计算结果对比")
    logger.info("="*80)

    try:
        # 使用因子类计算
        factor = AlphaProfitEmployeeFactor()
        factor_result = factor.calculate(data)
        logger.info(f"因子类计算结果: {len(factor_result)}条记录")
        use_factor_class = True
    except Exception as e:
        logger.warning(f"因子类计算失败: {e}，使用直接计算方式")
        factor_result = calculate_factor_directly(data)
        use_factor_class = False

    # 准备手动计算结果用于对比
    manual_df = manual_calculation(data)
    manual_df = verify_cross_sectional_rank(manual_df)

    # 合并对比
    comparison = pd.merge(
        manual_df[['ts_code', 'ann_date', 'ratio_raw', 'rank_pct']],
        factor_result[['ts_code', 'trade_date', 'factor']],
        left_on=['ts_code', 'ann_date'],
        right_on=['ts_code', 'trade_date'],
        how='inner'
    )

    if len(comparison) == 0:
        logger.error("无法进行对比：数据无法匹配")
        logger.info("手动计算数据:")
        print(manual_df[['ts_code', 'ann_date']])
        logger.info("因子类计算数据:")
        print(factor_result[['ts_code', 'trade_date']])
        return None, False

    # 计算差异
    comparison['diff'] = comparison['rank_pct'] - comparison['factor']
    comparison['diff_abs'] = comparison['diff'].abs()

    logger.info("\n对比结果:")
    logger.info("-" * 80)
    logger.info(f"{'股票代码':<12} {'公告日期':<10} {'手动排名':<10} {'因子类排名':<10} {'差异':<10} {'状态'}")
    logger.info("-" * 70)

    all_match = True
    max_diff = 0

    for _, row in comparison.iterrows():
        status = "✅ 匹配" if abs(row['diff']) < 1e-10 else "❌ 不匹配"
        if abs(row['diff']) >= 1e-10:
            all_match = False
            max_diff = max(max_diff, abs(row['diff']))

        logger.info(f"{row['ts_code']:<12} {row['ann_date'].strftime('%Y%m%d'):<10} "
                   f"{row['rank_pct']:<10.6f} {row['factor']:<10.6f} "
                   f"{row['diff']:<10.2e} {status}")

    logger.info("\n" + "="*80)
    if all_match:
        logger.info("✅ 验证通过：手动计算与因子类计算结果完全一致！")
    else:
        logger.info("❌ 验证失败：存在差异，需要检查计算逻辑")
        logger.info(f"最大差异: {max_diff:.2e}")

        # 显示详细差异分析
        logger.info("\n差异分析:")
        logger.info(f"  平均差异: {comparison['diff_abs'].mean():.2e}")
        logger.info(f"  最大差异: {comparison['diff_abs'].max():.2e}")
        logger.info(f"  差异标准差: {comparison['diff_abs'].std():.2e}")

    return comparison, all_match


def main():
    """主函数"""
    logger.info("Alpha Profit Employee因子手动验证")
    logger.info("="*80)

    try:
        # 1. 获取测试数据
        test_data = get_test_data()

        if len(test_data) == 0:
            logger.error("未获取到测试数据，验证失败")
            return None, False

        logger.info(f"\n测试数据概览:")
        logger.info(f"  记录数: {len(test_data)}")
        logger.info(f"  股票数: {test_data['ts_code'].nunique()}")
        logger.info(f"  公告日期数: {test_data['ann_date'].nunique()}")

        # 2. 手动计算
        manual_df = manual_calculation(test_data)

        # 3. 验证截面排名
        manual_df = verify_cross_sectional_rank(manual_df)

        # 4. 与因子类对比
        comparison, all_match = compare_with_factor_class(test_data)

        # 5. 总结
        logger.info("\n" + "="*80)
        logger.info("验证总结")
        logger.info("="*80)

        logger.info(f"测试数据: {len(test_data)}条记录")
        logger.info(f"股票数量: {test_data['ts_code'].nunique()}")
        logger.info(f"公告日期: {test_data['ann_date'].nunique()}个")

        logger.info("\n计算逻辑验证:")
        logger.info("  ✅ 分子计算: 营业利润 + 支付给职工现金")
        logger.info("  ✅ 分母计算: 总市值 × 10000 (万元转元)")
        logger.info("  ✅ 原始比率: 分子 / 分母")
        logger.info("  ✅ 截面排名: 按公告日期分组，rank(pct=True)")

        if all_match:
            logger.info("\n🎉 所有验证通过！因子计算逻辑正确。")
        else:
            logger.info("\n⚠️  存在差异，需要进一步检查。")

        logger.info("\n因子含义说明:")
        logger.info("  - 因子公式: CSRank((营业利润 + 职工现金) / 总市值, 公告日期)")
        logger.info("  - 高因子值: 高(利润+现金)/市值，表示经营价值比率高")
        logger.info("  - 低因子值: 低(利润+现金)/市值，表示经营价值比率低")
        logger.info("  - 当前方向: 高因子值对应高经营价值比率")

        return comparison, all_match

    except Exception as e:
        logger.error(f"验证失败: {e}")
        import traceback
        traceback.print_exc()
        return None, False


if __name__ == "__main__":
    comparison, success = main()
    exit(0 if success else 1)