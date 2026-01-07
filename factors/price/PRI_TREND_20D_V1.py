"""alpha006因子计算 - 优化版本"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.utils.db_connection import db


def load_new_share_data():
    """读取新股数据"""
    csv_path = "/home/zcy/alpha006_20251223/data/new_share_increment_20251031221906.csv"
    try:
        df = pd.read_csv(csv_path)
        # 提取上市日期映射
        issue_map = dict(zip(df['ts_code'], df['issue_date']))
        print(f"成功读取{len(issue_map)}只股票的上市日期")
        return issue_map
    except Exception as e:
        print(f"读取新股数据失败: {e}")
        return {}


def get_st_stocks():
    """获取ST股票列表"""
    sql = "SELECT ts_code FROM stock_st WHERE type = 'ST'"
    st_data = db.execute_query(sql)
    st_stocks = set([row['ts_code'] for row in st_data])
    print(f"ST股票数量: {len(st_stocks)}")
    return st_stocks


def calculate_alpha006_factor_batch(start_date='20240801', end_date='20250801', batch_days=30):
    """分批计算alpha006因子"""
    print(f"\n开始计算因子，时间范围: {start_date} ~ {end_date}")

    # 获取过滤条件
    st_stocks = get_st_stocks()
    issue_dates = load_new_share_data()

    # 分批处理
    start_dt = pd.to_datetime(start_date, format='%Y%m%d')
    end_dt = pd.to_datetime(end_date, format='%Y%m%d')

    all_results = []
    current_dt = start_dt

    while current_dt <= end_dt:
        batch_end = min(current_dt + timedelta(days=batch_days), end_dt)

        batch_start_str = current_dt.strftime('%Y%m%d')
        batch_end_str = batch_end.strftime('%Y%m%d')

        print(f"\n处理批次: {batch_start_str} ~ {batch_end_str}")

        # 获取批次数据
        sql = """
            SELECT ts_code, trade_date, turnover_rate_f, atr_bfq
            FROM stk_factor_pro
            WHERE trade_date >= %s AND trade_date <= %s
            ORDER BY ts_code, trade_date
        """
        data = db.execute_query(sql, (batch_start_str, batch_end_str))

        if not data:
            current_dt = batch_end + timedelta(days=1)
            continue

        df = pd.DataFrame(data)
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')

        # 计算因子（简化版，避免groupby开销）
        df = df.sort_values(['ts_code', 'trade_date'])

        # 按股票分组计算
        results = []
        for ts_code, group in df.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            # 计算波动率收缩
            group['atr_5_mean'] = group['atr_bfq'].rolling(5, min_periods=5).mean()
            group['atr_20_mean'] = group['atr_bfq'].rolling(20, min_periods=20).mean()
            volatility_shrink = (group['atr_5_mean'] < group['atr_20_mean'] * 0.8) & group['atr_20_mean'].notna()

            # 计算换手率条件
            cond1_turnover = (group['turnover_rate_f'] >= 1.2) & (group['turnover_rate_f'] <= 2.0)

            group['turnover_5_mean'] = group['turnover_rate_f'].rolling(5, min_periods=5).mean()
            group['turnover_60_mean'] = group['turnover_rate_f'].rolling(60, min_periods=60).mean()
            cond2_shrink = (group['turnover_5_mean'] < group['turnover_60_mean'] * 0.8) & group['turnover_60_mean'].notna()

            # 应用过滤条件
            is_st = ts_code in st_stocks
            is_new = False

            # 检查是否为新股
            if ts_code in issue_dates:
                try:
                    issue_date = pd.to_datetime(str(issue_dates[ts_code]), format='%Y%m%d')
                    # 检查批次内是否有新股
                    min_trade_date = group['trade_date'].min()
                    if (min_trade_date - issue_date).days < 365:
                        is_new = True
                except:
                    pass

            if is_st or is_new:
                continue

            # 计算最终因子
            alpha006 = (cond1_turnover & volatility_shrink & cond2_shrink).astype(int)

            group['alpha006'] = alpha006
            results.append(group[['ts_code', 'trade_date', 'alpha006']])

        if results:
            batch_result = pd.concat(results, ignore_index=True)
            all_results.append(batch_result)
            print(f"  本批次有效信号: {batch_result['alpha006'].sum()}/{len(batch_result)}")

        current_dt = batch_end + timedelta(days=1)

    if not all_results:
        print("未计算出任何结果")
        return None

    # 合并所有结果
    final_result = pd.concat(all_results, ignore_index=True)

    # 统计
    print(f"\n=== 计算完成 ===")
    print(f"总数据条数: {len(final_result)}")
    print(f"有效信号总数: {final_result['alpha006'].sum()}")
    print(f"信号比例: {final_result['alpha006'].mean():.4f}")

    # 每日统计
    daily_stats = final_result.groupby('trade_date')['alpha006'].agg(['sum', 'count'])
    daily_stats['ratio'] = daily_stats['sum'] / daily_stats['count']
    print(f"\n最近10天统计:")
    print(daily_stats.tail(10))

    return final_result, daily_stats


if __name__ == "__main__":
    # 先测试一周数据
    print("=== 测试一周数据 ===")
    result, stats = calculate_alpha006_factor_batch('20240801', '20240807', 7)

    if result is not None:
        # 保存结果
        output_file = "/home/zcy/alpha006_20251223/results/factor/factor_v1_sample.csv"
        result.to_csv(output_file, index=False)
        print(f"\n样例结果已保存到: {output_file}")

        # 如果样例正常，再计算完整数据
        confirm = input("\n是否计算完整时间段数据？(y/n): ")
        if confirm.lower() == 'y':
            print("\n开始计算完整数据...")
            full_result, full_stats = calculate_alpha006_factor_batch('20240801', '20250801', 30)
            if full_result is not None:
                full_output = "/home/zcy/alpha006_20251223/results/factor/factor_v1_full.csv"
                full_result.to_csv(full_output, index=False)
                print(f"完整结果已保存到: {full_output}")