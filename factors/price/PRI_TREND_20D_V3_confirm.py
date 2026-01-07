"""alpha006因子 - 增加价格趋势确认版本

核心改进：
1. 增加价格趋势确认：close > ma_5
2. 保留原有波动率和换手率条件
3. 测试不同阈值组合
"""

import pandas as pd
import numpy as np
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
    """
    recent_data = index_data[index_data['trade_date'] <= trade_date].tail(window)

    if len(recent_data) < window:
        return 'non_bull'

    close = recent_data['close'].values
    ma20 = recent_data['close'].mean()

    close_last = float(close[-1])
    close_first = float(close[0])
    ma20_float = float(ma20)

    price_vs_ma = close_last / ma20_float - 1
    trend_slope = (close_last - close_first) / close_first

    if price_vs_ma > 0.02 and trend_slope > 0.01:
        return 'bull'

    return 'non_bull'


def get_price_data(ts_codes, start_date, end_date):
    """批量获取股票价格数据"""
    print(f"  获取 {len(ts_codes)} 只股票的价格数据...")

    all_data = []
    batch_size = 500

    for i in range(0, len(ts_codes), batch_size):
        batch = ts_codes[i:i+batch_size]
        codes_str = ','.join([f"'{code}'" for code in batch])

        sql = f"""
            SELECT ts_code, trade_date, close
            FROM daily_kline
            WHERE ts_code IN ({codes_str})
              AND trade_date >= %s AND trade_date <= %s
            ORDER BY ts_code, trade_date
        """
        data = db.execute_query(sql, (start_date, end_date))
        all_data.extend(data)

    df = pd.DataFrame(all_data)
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    df['close'] = df['close'].astype(float)

    # 转换为宽格式
    price_wide = df.pivot(index='trade_date', columns='ts_code', values='close')

    return price_wide


def calculate_ma5_for_stock(prices):
    """计算5日均线"""
    return prices.rolling(5, min_periods=5).mean()


def calculate_factor_with_price_confirm(start_date='20240801', end_date='20250301'):
    """
    计算带价格确认的因子

    新增条件：close > ma_5
    """

    print(f"\n{'='*70}")
    print("计算带价格确认的因子")
    print(f"{'='*70}\n")

    # 获取基础数据
    st_stocks = get_st_stocks()
    issue_dates = load_new_share_data()
    index_data = get_index_data(start_date, end_date)

    # 获取因子计算所需数据
    print("步骤1: 获取因子数据...")
    sql = """
        SELECT ts_code, trade_date, turnover_rate_f, atr_bfq
        FROM stk_factor_pro
        WHERE trade_date >= %s AND trade_date <= %s
        ORDER BY ts_code, trade_date
    """
    data = db.execute_query(sql, (start_date, end_date))
    factor_df = pd.DataFrame(data)
    factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'], format='%Y%m%d')
    factor_df = factor_df.sort_values(['ts_code', 'trade_date'])

    # 获取所有需要计算的股票代码
    ts_codes = factor_df['ts_code'].unique()
    print(f"  共 {len(ts_codes)} 只股票需要计算\n")

    # 获取价格数据
    print("步骤2: 获取价格数据（计算ma_5）...")
    price_data = get_price_data(ts_codes, start_date, end_date)
    print(f"  获取到 {len(price_data)} 个交易日的价格数据\n")

    # 定义版本
    versions = {
        'v2': {'lower': 0.3, 'upper': 1.0, 'name': 'factor_v3_opt_0.3_1.0_price_confirm'},
        'v3': {'lower': 0.5, 'upper': 1.0, 'name': 'factor_v3_opt_0.5_1.0_price_confirm'},
        'v4': {'lower': 1.0, 'upper': 2.0, 'name': 'factor_v3_opt_1.0_2.0_price_confirm'},
        'v5': {'lower': 0.3, 'upper': 2.0, 'name': 'factor_v3_opt_0.3_2.0_price_confirm'},
    }

    all_results = {}

    # 对每个版本进行计算
    for v_key, v_info in versions.items():
        print(f"步骤3.{v_key[-1]}: 计算版本 {v_key} ({v_info['name']})")
        print(f"  阈值: {v_info['lower']}-{v_info['upper']}σ")

        results = []
        stock_count = 0

        for ts_code, group in factor_df.groupby('ts_code'):
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

            # 获取该股票的价格数据
            if ts_code not in price_data.columns:
                continue

            stock_prices = price_data[ts_code].dropna()
            if len(stock_prices) < 20:  # 需要至少20天数据
                continue

            # 计算ma_5
            ma_5 = calculate_ma5_for_stock(stock_prices)

            # 创建价格DataFrame
            price_df = pd.DataFrame({
                'close': stock_prices,
                'ma_5': ma_5
            }).reset_index()

            # 合并因子数据和价格数据
            group_merged = group.merge(
                price_df,
                on=['trade_date'],
                how='left'
            )

            # 计算基础统计量
            group_merged = group_merged.sort_values('trade_date').copy()

            # 14日换手率统计
            group_merged['turnover_14_mean'] = group_merged['turnover_rate_f'].rolling(14, min_periods=14).mean()
            group_merged['turnover_14_std'] = group_merged['turnover_rate_f'].rolling(14, min_periods=14).std()

            # 60日换手率统计
            group_merged['turnover_60_mean'] = group_merged['turnover_rate_f'].rolling(60, min_periods=60).mean()
            group_merged['turnover_60_std'] = group_merged['turnover_rate_f'].rolling(60, min_periods=60).std()
            group_merged['turnover_5_mean'] = group_merged['turnover_rate_f'].rolling(5, min_periods=5).mean()

            # 波动率统计
            group_merged['atr_5_mean'] = group_merged['atr_bfq'].rolling(5, min_periods=5).mean()
            group_merged['atr_20_mean'] = group_merged['atr_bfq'].rolling(20, min_periods=20).mean()

            # 计算偏离度
            turnover_deviation = (group_merged['turnover_rate_f'] - group_merged['turnover_14_mean']) / group_merged['turnover_14_std']
            trend_deviation = (group_merged['turnover_5_mean'] - group_merged['turnover_60_mean']) / group_merged['turnover_60_std']

            # 波动率收缩
            vol_shrink = (group_merged['atr_5_mean'] < group_merged['atr_20_mean'] * 0.8)

            # 价格趋势确认（新增）
            price_confirm = group_merged['close'] > group_merged['ma_5']

            # 阈值
            lower = v_info['lower']
            upper = v_info['upper']

            # 最终条件
            cond1 = (turnover_deviation >= lower) & (turnover_deviation <= upper) & turnover_deviation.notna()
            cond2 = (trend_deviation >= lower) & (trend_deviation <= upper) & trend_deviation.notna()
            cond3 = vol_shrink
            cond4 = price_confirm

            group_merged['alpha006'] = (cond1 & cond2 & cond3 & cond4).astype(int)

            # 保留结果
            result_cols = [
                'ts_code', 'trade_date', 'turnover_rate_f', 'turnover_14_mean', 'turnover_14_std',
                'atr_bfq', 'atr_5_mean', 'atr_20_mean', 'turnover_5_mean', 'turnover_60_mean',
                'turnover_60_std', 'close', 'ma_5', 'alpha006'
            ]

            existing_cols = [col for col in result_cols if col in group_merged.columns]
            results.append(group_merged[existing_cols])

            stock_count += 1
            if stock_count % 100 == 0:
                print(f"    已处理 {stock_count} 只股票...")

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
    """保存结果"""
    print(f"\n{'='*70}")
    print("保存结果文件")
    print(f"{'='*70}\n")

    for v_key, v_info in versions.items():
        if v_key in all_results:
            filename = f"/home/zcy/alpha006_20251223/results/factor/{v_info['name']}_results.csv"
            all_results[v_key]['data'].to_csv(filename, index=False)
            print(f"  → {v_info['name']}_results.csv")

    print("\n✓ 所有结果已保存！\n")


def compare_with_original():
    """与原版本对比"""
    print(f"\n{'='*70}")
    print("与原版本对比")
    print(f"{'='*70}\n")

    # 读取原版本结果
    original_file = '/home/zcy/alpha006_20251223/results/factor/factor_v3_opt_0.3_1.0_results.csv'
    try:
        original = pd.read_csv(original_file)
        original_signals = original['alpha006'].sum()
        print(f"原0.3-1.0版本: {original_signals:,} 个信号")
    except:
        original_signals = 0
        print(f"原0.3-1.0版本: 文件不存在")

    # 读取新版本结果
    versions = {
        'v2': 'factor_v3_opt_0.3_1.0_price_confirm_results.csv',
        'v3': 'factor_v3_opt_0.5_1.0_price_confirm_results.csv',
        'v4': 'factor_v3_opt_1.0_2.0_price_confirm_results.csv',
        'v5': 'factor_v3_opt_0.3_2.0_price_confirm_results.csv',
    }

    print("\n带价格确认的新版本:")
    for v_key, filename in versions.items():
        filepath = f"/home/zcy/alpha006_20251223/results/factor/{filename}"
        try:
            df = pd.read_csv(filepath)
            signals = df['alpha006'].sum()
            ratio = signals / len(df)
            reduction = (original_signals - signals) / original_signals if original_signals > 0 else 0

            print(f"  {v_key}: {signals:,} 信号 ({ratio:.3%}) - 减少 {reduction:.1%}")
        except Exception as e:
            print(f"  {v_key}: 读取失败 - {e}")

    print()


if __name__ == "__main__":
    # 计算带价格确认的因子
    all_results, versions = calculate_factor_with_price_confirm('20240801', '20250301')

    # 保存结果
    save_results(all_results, versions)

    # 对比分析
    compare_with_original()

    print("="*70)
    print("计算完成！")
    print("="*70)
