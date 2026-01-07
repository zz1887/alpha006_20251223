"""alpha006因子 - 多版本优化对比实验

实验目标：
1. 测试不同标准差区间对主力吸筹的识别效果
2. 对比固定阈值与市场状态自适应阈值的表现
3. 找出最优的主力吸筹识别参数

版本说明：
- v1/v2/v3/v4: 固定阈值版本
- v5: 市场状态自适应版本（牛市/非牛市）
"""

import pandas as pd
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.utils.db_connection import db


def load_new_share_data():
    """读取新股数据"""
    csv_path = "/home/zcy/alpha006_20251223/data/new_share_increment_20251031221906.csv"
    try:
        df = pd.read_csv(csv_path)
        issue_map = dict(zip(df['ts_code'], df['issue_date']))
        return issue_map
    except Exception as e:
        print(f"读取新股数据失败: {e}")
        return {}


def get_st_stocks():
    """获取ST股票列表"""
    sql = "SELECT ts_code FROM stock_st WHERE type = 'ST'"
    st_data = db.execute_query(sql)
    st_stocks = set([row['ts_code'] for row in st_data])
    return st_stocks


def get_index_data(start_date, end_date):
    """获取000001.SH指数数据"""
    sql = """
        SELECT trade_date, close
        FROM index_daily_zzsz
        WHERE ts_code = '000001.SH'
          AND trade_date >= %s AND trade_date <= %s
        ORDER BY trade_date
    """
    data = db.execute_query(sql, (start_date, end_date))
    df = pd.DataFrame(data)
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    return df


def get_market_status(trade_date, index_data, window=20):
    """
    判断市场状态（牛市/非牛市）

    牛市标准：
    - 价格在20日均线上方2%以上
    - 20日趋势向上1%以上

    非牛市：其他所有情况（熊市+震荡）
    """
    recent_data = index_data[index_data['trade_date'] <= trade_date].tail(window)

    if len(recent_data) < window:
        return 'non_bull'  # 数据不足，默认非牛市

    close = recent_data['close'].values
    ma20 = recent_data['close'].mean()

    # 转换为float处理
    close_last = float(close[-1])
    close_first = float(close[0])
    ma20_float = float(ma20)

    price_vs_ma = close_last / ma20_float - 1  # 当前价相对于20日均线的偏离
    trend_slope = (close_last - close_first) / close_first  # 20日趋势

    # 牛市条件
    if price_vs_ma > 0.02 and trend_slope > 0.01:
        return 'bull'

    return 'non_bull'


def calculate_factor_for_stock(group, index_data, version, market_adaptive=False, price_confirm=False):
    """
    为单个股票计算因子

    版本说明：
    - version 'v1': 保留作为参考（原V3逻辑）
    - version 'v2': 0.3-1.0（温和吸筹）
    - version 'v3': 0.5-1.0（保守吸筹）
    - version 'v4': 1.0-2.0（明显放量）
    - version 'v5': 0.3-2.0（宽松）
    - version 'v6': 市场自适应（牛市0.3-0.8，非牛市0.5-1.2）

    新增参数：
    - price_confirm: 是否增加价格趋势确认（close > ma_5）
    """

    group = group.sort_values('trade_date').copy()

    # === 基础统计量计算 ===
    # 14日换手率统计
    group['turnover_14_mean'] = group['turnover_rate_f'].rolling(14, min_periods=14).mean()
    group['turnover_14_std'] = group['turnover_rate_f'].rolling(14, min_periods=14).std()

    # 60日换手率统计
    group['turnover_60_mean'] = group['turnover_rate_f'].rolling(60, min_periods=60).mean()
    group['turnover_60_std'] = group['turnover_rate_f'].rolling(60, min_periods=60).std()
    group['turnover_5_mean'] = group['turnover_rate_f'].rolling(5, min_periods=5).mean()

    # 波动率统计
    group['atr_5_mean'] = group['atr_bfq'].rolling(5, min_periods=5).mean()
    group['atr_20_mean'] = group['atr_bfq'].rolling(20, min_periods=20).mean()

    # 计算偏离度
    turnover_deviation = (group['turnover_rate_f'] - group['turnover_14_mean']) / group['turnover_14_std']
    trend_deviation = (group['turnover_5_mean'] - group['turnover_60_mean']) / group['turnover_60_std']

    # 波动率收缩
    vol_shrink = (group['atr_5_mean'] < group['atr_20_mean'] * 0.8)

    # === 价格趋势确认（新增）===
    if price_confirm:
        # 需要从daily_kline获取价格数据来计算ma_5
        # 这里先标记需要价格数据，后续补充
        need_price_data = True
    else:
        need_price_data = False

    # === 根据版本选择阈值 ===
    if market_adaptive:
        # 市场自适应版本（v6）
        group['alpha006'] = 0
        for idx, row in group.iterrows():
            if pd.isna(turnover_deviation[idx]) or pd.isna(trend_deviation[idx]):
                continue

            market_status = get_market_status(row['trade_date'], index_data)

            if market_status == 'bull':
                lower, upper = 0.3, 0.8
            else:  # non_bull
                lower, upper = 0.5, 1.2

            cond1 = (turnover_deviation[idx] >= lower) & (turnover_deviation[idx] <= upper)
            cond2 = (trend_deviation[idx] >= lower) & (trend_deviation[idx] <= upper)

            if cond1 and cond2 and vol_shrink[idx]:
                group.at[idx, 'alpha006'] = 1

    else:
        # 固定阈值版本
        if version == 'v2':
            lower, upper = 0.3, 1.0
        elif version == 'v3':
            lower, upper = 0.5, 1.0
        elif version == 'v4':
            lower, upper = 1.0, 2.0
        elif version == 'v5':
            lower, upper = 0.3, 2.0
        else:  # v1 - 原V3逻辑作为基准
            lower, upper = 0.0, 1.0

        cond1 = (turnover_deviation >= lower) & (turnover_deviation <= upper) & turnover_deviation.notna()
        cond2 = (trend_deviation >= lower) & (trend_deviation <= upper) & trend_deviation.notna()

        group['alpha006'] = (cond1 & cond2 & vol_shrink).astype(int)

    return group


def calculate_all_versions(start_date='20240801', end_date='20250301'):
    """计算所有版本的因子"""

    print(f"{'='*60}")
    print(f"开始计算所有版本因子: {start_date} ~ {end_date}")
    print(f"{'='*60}\n")

    # 获取基础数据
    st_stocks = get_st_stocks()
    issue_dates = load_new_share_data()
    index_data = get_index_data(start_date, end_date)

    # 获取交易数据
    sql = """
        SELECT ts_code, trade_date, turnover_rate_f, atr_bfq
        FROM stk_factor_pro
        WHERE trade_date >= %s AND trade_date <= %s
        ORDER BY ts_code, trade_date
    """
    data = db.execute_query(sql, (start_date, end_date))
    df = pd.DataFrame(data)
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    df = df.sort_values(['ts_code', 'trade_date'])

    print(f"获取到 {len(df)} 条基础数据\n")

    # 版本定义
    versions = {
        'v1': {'name': 'factor_v3_original', 'desc': '原V3（基准）', 'market_adaptive': False},
        'v2': {'name': 'factor_v3_opt_0.3_1.0', 'desc': '0.3-1.0（温和吸筹）', 'market_adaptive': False},
        'v3': {'name': 'factor_v3_opt_0.5_1.0', 'desc': '0.5-1.0（保守吸筹）', 'market_adaptive': False},
        'v4': {'name': 'factor_v3_opt_1.0_2.0', 'desc': '1.0-2.0（明显放量）', 'market_adaptive': False},
        'v5': {'name': 'factor_v3_opt_0.3_2.0', 'desc': '0.3-2.0（宽松）', 'market_adaptive': False},
        'v6': {'name': 'factor_v3_market_adaptive', 'desc': '自适应（牛市/非牛市）', 'market_adaptive': True}
    }

    all_results = {}

    # 对每个版本进行计算
    for v_key, v_info in versions.items():
        print(f"[{v_info['name']}] {v_info['desc']}")

        results = []
        stock_count = 0

        for ts_code, group in df.groupby('ts_code'):
            # 过滤ST股票
            if ts_code in st_stocks:
                continue

            # 过滤新股
            if ts_code in issue_dates:
                try:
                    issue_date = pd.to_datetime(str(issue_dates[ts_code]), format='%Y%m%d')
                    min_trade_date = group['trade_date'].min()
                    if (min_trade_date - issue_date).days < 365:
                        continue
                except:
                    pass

            # 计算因子
            result_group = calculate_factor_for_stock(
                group, index_data, v_key, v_info['market_adaptive']
            )

            # 保留结果列
            result_cols = [
                'ts_code', 'trade_date', 'turnover_rate_f', 'turnover_14_mean', 'turnover_14_std',
                'atr_bfq', 'atr_5_mean', 'atr_20_mean', 'turnover_5_mean', 'turnover_60_mean',
                'turnover_60_std', 'alpha006'
            ]

            # 只保留存在的列
            existing_cols = [col for col in result_cols if col in result_group.columns]
            results.append(result_group[existing_cols])

            stock_count += 1
            if stock_count % 100 == 0:
                print(f"  已处理 {stock_count} 只股票...")

        if results:
            final_result = pd.concat(results, ignore_index=True)
            signal_count = final_result['alpha006'].sum()
            signal_ratio = signal_count / len(final_result)

            all_results[v_key] = {
                'data': final_result,
                'signal_count': signal_count,
                'signal_ratio': signal_ratio,
                'total_data': len(final_result)
            }

            print(f"  ✓ 完成 - 信号数: {signal_count:,} ({signal_ratio:.4%})")
            print(f"  数据量: {len(final_result):,} 条\n")
        else:
            print(f"  ✗ 无结果\n")

    return all_results, versions


def save_results(all_results, versions):
    """保存所有版本的结果"""

    print("保存结果文件...")

    for v_key, v_info in versions.items():
        if v_key in all_results:
            filename = f"/home/zcy/alpha006_20251223/results/factor/{v_info['name']}_results.csv"
            all_results[v_key]['data'].to_csv(filename, index=False)
            print(f"  → {v_info['name']}_results.csv")

    print("\n所有结果已保存！\n")


if __name__ == "__main__":
    # 执行计算
    all_results, versions = calculate_all_versions('20240801', '20250301')

    # 保存结果
    save_results(all_results, versions)

    # 生成简要对比
    print(f"\n{'='*60}")
    print("各版本信号统计对比")
    print(f"{'='*60}")
    print(f"{'版本':<25} {'信号数':>10} {'比例':>10} {'数据量':>10}")
    print("-"*60)

    for v_key, v_info in versions.items():
        if v_key in all_results:
            result = all_results[v_key]
            print(f"{v_info['name']:<25} {result['signal_count']:>10,} {result['signal_ratio']:>9.3%} {result['total_data']:>10,}")

    print(f"{'='*60}\n")
