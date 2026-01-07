#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚宽策略V3数据库版 - 2025年12月31日选股执行脚本

功能：
1. 执行2025年12月31日的选股
2. 使用聚宽策略V3数据库版进行筛选
3. 生成详细的选股结果报告
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging

# 添加项目路径
sys.path.append('/home/zcy/alpha006_20251223')

# 导入策略核心模块
from strategies.runners.聚宽策略V3_数据库版 import (
    Context, Portfolio, initialize, process_stock_universe_all, g
)
from core.config.settings import DATABASE_CONFIG, TABLE_NAMES
from core.utils.db_connection import DBConnection

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/zcy/alpha006_20251223/logs/selection_20251231.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# 初始化数据库连接
db = DBConnection(DATABASE_CONFIG)


def check_trading_date(date_str):
    """检查指定日期是否为交易日"""
    try:
        sql = f"""
        SELECT COUNT(*) as cnt
        FROM {TABLE_NAMES['daily_kline']}
        WHERE trade_date = %s
        """
        result = db.execute_query(sql, (date_str,))
        if result and result[0]['cnt'] > 0:
            return True
        return False
    except Exception as e:
        log.error(f"检查交易日失败: {str(e)}")
        return False


def get_nearest_trading_date(target_date):
    """获取最接近的交易日"""
    try:
        # 先检查目标日期
        target_str = target_date.strftime('%Y%m%d')
        if check_trading_date(target_str):
            return target_date

        # 向前查找
        for i in range(1, 10):
            check_date = target_date - timedelta(days=i)
            check_str = check_date.strftime('%Y%m%d')
            if check_trading_date(check_str):
                log.info(f"目标日期{target_str}非交易日，使用最近交易日: {check_str}")
                return check_date

        # 向后查找
        for i in range(1, 10):
            check_date = target_date + timedelta(days=i)
            check_str = check_date.strftime('%Y%m%d')
            if check_trading_date(check_str):
                log.info(f"目标日期{target_str}非交易日，使用最近交易日: {check_str}")
                return check_date

        raise ValueError("无法找到有效交易日")
    except Exception as e:
        log.error(f"查找交易日失败: {str(e)}")
        raise


def run_selection(target_date):
    """执行选股"""
    log.info("="*80)
    log.info(f"开始执行选股 - 目标日期: {target_date.strftime('%Y-%m-%d')}")
    log.info("="*80)

    # 1. 验证并调整日期
    try:
        actual_date = get_nearest_trading_date(target_date)
        log.info(f"实际执行日期: {actual_date.strftime('%Y-%m-%d')}")
    except Exception as e:
        log.error(f"日期验证失败: {str(e)}")
        return None

    # 2. 创建上下文
    context = Context(actual_date)

    # 3. 初始化策略参数
    log.info("初始化策略参数...")
    initialize(context)

    # 4. 执行选股
    log.info("开始执行选股流程...")

    # 计算因子数据时间范围
    params = g.params
    factor_start_date = (actual_date - pd.Timedelta(days=params['cr20_long_period'] + 15)).strftime('%Y%m%d')
    factor_end_date = actual_date.strftime('%Y%m%d')

    log.info(f"因子数据范围: {factor_start_date} 至 {factor_end_date}")

    # 执行统一筛选
    qualified_stocks = process_stock_universe_all(
        context,
        start_date=factor_start_date,
        end_date=factor_end_date,
        index_code='000300.SH'
    )

    return qualified_stocks


def format_results(qualified_stocks, target_date):
    """格式化选股结果"""
    if not qualified_stocks:
        return pd.DataFrame(), pd.DataFrame()

    # 转换为DataFrame
    df = pd.DataFrame(qualified_stocks)

    # 排序
    df = df.sort_values('score', ascending=False)

    # 详细结果（包含所有字段）
    detailed_df = df.copy()

    # 简要结果（关键字段）
    summary_df = df[[
        'code', 'score', 'avg_turnover', 'recent_peg',
        'cr20_short', 'cr20_growth', 'price_quantile',
        'pulse_count', 'ma60_slope', 'outperform_index'
    ]].copy()

    # 添加日期列
    date_str = target_date.strftime('%Y-%m-%d')
    detailed_df['selection_date'] = date_str
    summary_df['selection_date'] = date_str

    return summary_df, detailed_df


def save_results(summary_df, detailed_df, target_date):
    """保存选股结果"""
    date_str = target_date.strftime('%Y%m%d')
    results_dir = '/home/zcy/alpha006_20251223/results'

    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    # 保存简要结果
    summary_file = f"{results_dir}/selection_summary_{date_str}.csv"
    summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
    log.info(f"简要结果已保存: {summary_file}")

    # 保存详细结果
    detailed_file = f"{results_dir}/selection_detailed_{date_str}.csv"
    detailed_df.to_csv(detailed_file, index=False, encoding='utf-8-sig')
    log.info(f"详细结果已保存: {detailed_file}")

    # 生成报告
    report_file = f"{results_dir}/selection_report_{date_str}.md"
    generate_report(summary_df, detailed_df, target_date, report_file)
    log.info(f"报告已保存: {report_file}")

    return summary_file, detailed_file, report_file


def generate_report(summary_df, detailed_df, target_date, report_file):
    """生成选股报告"""
    date_str = target_date.strftime('%Y-%m-%d')

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 聚宽策略V3选股报告 - {date_str}\n\n")
        f.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 概览
        f.write("## 1. 选股概览\n\n")
        f.write(f"- 目标日期: {date_str}\n")
        f.write(f"- 筛选结果: {len(summary_df)} 只股票\n")
        f.write(f"- 策略版本: 聚宽策略V3数据库版\n")
        f.write(f"- 统一标准: 创业板和主板使用相同筛选条件\n\n")

        if len(summary_df) > 0:
            # 简要结果表格
            f.write("## 2. 选股结果（按得分排序）\n\n")
            f.write("| 序号 | 股票代码 | 得分 | 平均换手率(%) | PEG | CR20 | CR20增长(%) | 价格分位(%) | 脉冲次数 | MA60斜率 | 跑赢指数(%) |\n")
            f.write("|------|----------|------|---------------|-----|------|-------------|-------------|----------|----------|-------------|\n")

            for idx, row in summary_df.iterrows():
                f.write(f"| {len(f.write.__self__.getvalue().split('\\n')[-1])} | {row['code']} | {row['score']:.1f} | {row['avg_turnover']:.2f} | {row['recent_peg']:.2f} | {row['cr20_short']:.1f} | {row['cr20_growth']:.1f} | {row['price_quantile']:.1f} | {row['pulse_count']:.0f} | {row['ma60_slope']:.1f} | {row['outperform_index']:.1f} |\n")

            # 统计信息
            f.write("\n## 3. 统计信息\n\n")
            f.write(f"- 得分分布:\n")
            score_dist = summary_df['score'].value_counts().sort_index(ascending=False)
            for score, count in score_dist.items():
                f.write(f"  - 得分 {score}: {count} 只\n")

            f.write(f"\n- 平均指标:\n")
            f.write(f"  - 平均得分: {summary_df['score'].mean():.2f}\n")
            f.write(f"  - 平均换手率: {summary_df['avg_turnover'].mean():.2f}%\n")
            f.write(f"  - 平均PEG: {summary_df['recent_peg'].mean():.2f}\n")
            f.write(f"  - 平均CR20: {summary_df['cr20_short'].mean():.1f}\n")
            f.write(f"  - 平均CR20增长: {summary_df['cr20_growth'].mean():.1f}%\n")

            # 详细数据
            f.write("\n## 4. 详细数据\n\n")
            f.write("以下为完整详细数据，可查看CSV文件获取全部字段:\n\n")
            f.write("- 简要结果: `selection_summary_YYYYMMDD.csv`\n")
            f.write("- 详细结果: `selection_detailed_YYYYMMDD.csv`\n\n")

            # 策略参数
            f.write("## 5. 策略参数\n\n")
            f.write("```\n")
            for key, value in g.params.items():
                f.write(f"{key}: {value}\n")
            f.write("```\n\n")

        else:
            f.write("## 2. 选股结果\n\n")
            f.write("⚠️ 未筛选出符合条件的股票\n\n")
            f.write("可能原因:\n")
            f.write("- 市场条件不满足\n")
            f.write("- 数据异常\n")
            f.write("- 筛选条件过于严格\n")

        f.write("\n---\n")
        f.write(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")


def main():
    """主函数"""
    try:
        # 目标日期
        target_date = datetime(2025, 12, 31)

        # 执行选股
        qualified_stocks = run_selection(target_date)

        if qualified_stocks is None:
            log.error("选股执行失败")
            return False

        # 格式化结果
        summary_df, detailed_df = format_results(qualified_stocks, target_date)

        # 保存结果
        if len(summary_df) > 0:
            summary_file, detailed_file, report_file = save_results(summary_df, detailed_df, target_date)

            log.info("\n" + "="*80)
            log.info("选股执行完成！")
            log.info(f"结果文件:")
            log.info(f"  - 简要结果: {summary_file}")
            log.info(f"  - 详细结果: {detailed_file}")
            log.info(f"  - 分析报告: {report_file}")
            log.info("="*80)

            # 显示前10只股票
            log.info("\n前10只选股结果:")
            for idx, row in summary_df.head(10).iterrows():
                log.info(f"  {row['code']}: 得分={row['score']:.1f}, PEG={row['recent_peg']:.2f}, CR20={row['cr20_short']:.1f}")
        else:
            log.warning("未筛选出符合条件的股票")

        return True

    except Exception as e:
        log.error(f"执行失败: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)