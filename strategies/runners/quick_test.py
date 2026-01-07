# 快速测试脚本
# 用于验证数据库连接和策略基本功能

import sys
sys.path.append('/home/zcy/alpha006_20251223')

from core.config.settings import DATABASE_CONFIG
from core.utils.db_connection import DBConnection
from datetime import datetime
import pandas as pd

def test_database():
    """测试数据库连接和基本查询"""
    print("="*60)
    print("数据库连接测试")
    print("="*60)

    db = DBConnection(DATABASE_CONFIG)

    try:
        # 1. 测试连接
        print("\n1. 测试连接...")
        result = db.execute_query("SELECT 1 as test")
        print(f"   ✅ 连接正常，测试结果: {result[0]['test']}")

        # 2. 检查核心表
        print("\n2. 检查核心表...")
        tables = ['daily_kline', 'daily_basic', 'stk_factor_pro', 'sw_industry']
        for table in tables:
            result = db.execute_query(f"SELECT COUNT(*) as cnt FROM {table} LIMIT 1")
            print(f"   ✅ {table}: 可访问")

        # 3. 获取最近交易日
        print("\n3. 获取最近交易日...")
        result = db.execute_query("SELECT MAX(trade_date) as max_date FROM daily_kline")
        if result and result[0]['max_date']:
            max_date = result[0]['max_date']
            print(f"   最近交易日: {max_date}")
            return max_date
        else:
            print("   ❌ 无法获取最近交易日")
            return None

    except Exception as e:
        print(f"   ❌ 数据库错误: {e}")
        return None


def test_stock_pool(max_date):
    """测试股票池获取"""
    print("\n" + "="*60)
    print("股票池获取测试")
    print("="*60)

    db = DBConnection(DATABASE_CONFIG)

    try:
        # 获取当日所有股票
        sql = """
        SELECT DISTINCT ts_code
        FROM daily_kline
        WHERE trade_date = %s
        """
        result = db.execute_query(sql, (max_date,))

        if not result:
            print("❌ 无数据")
            return

        all_stocks = [row['ts_code'] for row in result]
        print(f"\n当日总股票数: {len(all_stocks)}")

        # 创业板
        gem_stocks = [s for s in all_stocks if s.startswith('300') or s.startswith('301')]
        print(f"创业板股票: {len(gem_stocks)}只")
        print(f"示例: {gem_stocks[:5]}")

        # 主板
        main_stocks = [s for s in all_stocks if not s.startswith('300') and not s.startswith('301') and not s.startswith('688')]
        print(f"主板股票: {len(main_stocks)}只")
        print(f"示例: {main_stocks[:5]}")

        # 过滤ST
        st_result = db.execute_query("SELECT DISTINCT ts_code FROM stock_st WHERE type = 'ST'")
        st_stocks = set([row['ts_code'] for row in st_result])
        print(f"\nST股票: {len(st_stocks)}只")

        valid_stocks = [s for s in all_stocks if s not in st_stocks]
        print(f"过滤后股票: {len(valid_stocks)}只")

    except Exception as e:
        print(f"❌ 错误: {e}")


def test_price_data(max_date):
    """测试价格数据获取"""
    print("\n" + "="*60)
    print("价格数据获取测试")
    print("="*60)

    db = DBConnection(DATABASE_CONFIG)

    try:
        # 获取几只股票的价格数据
        test_stocks = ['000001.SZ', '000002.SZ', '300001.SZ', '600000.SH']

        # 计算日期范围
        from datetime import timedelta
        end_dt = datetime.strptime(max_date, '%Y%m%d')
        start_dt = end_dt - timedelta(days=10)
        start_date = start_dt.strftime('%Y%m%d')

        placeholders = ','.join(['%s'] * len(test_stocks))
        sql = f"""
        SELECT ts_code, trade_date, close, vol
        FROM daily_kline
        WHERE trade_date >= %s AND trade_date <= %s
          AND ts_code IN ({placeholders})
        ORDER BY ts_code, trade_date
        """
        params = [start_date, max_date] + test_stocks

        result = db.execute_query(sql, params)
        df = pd.DataFrame(result)

        if df.empty:
            print("❌ 无数据")
            return

        print(f"\n获取记录数: {len(df)}")
        print(f"股票数: {df['ts_code'].nunique()}")
        print(f"日期范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")

        # 显示示例数据
        print("\n示例数据:")
        print(df.head(10))

        # 检查数据完整性
        for stock in test_stocks:
            stock_data = df[df['ts_code'] == stock]
            if not stock_data.empty:
                print(f"\n{stock}: {len(stock_data)}天数据，最新价: {stock_data['close'].iloc[-1]}")

    except Exception as e:
        print(f"❌ 错误: {e}")


def test_factor_data(max_date):
    """测试因子数据获取"""
    print("\n" + "="*60)
    print("因子数据获取测试")
    print("="*60)

    db = DBConnection(DATABASE_CONFIG)

    try:
        # 测试CR20因子
        test_stocks = ['000001.SZ', '300001.SZ']

        placeholders = ','.join(['%s'] * len(test_stocks))
        sql = f"""
        SELECT ts_code, trade_date, cr_qfq
        FROM stk_factor_pro
        WHERE trade_date = %s
          AND ts_code IN ({placeholders})
        """
        result = db.execute_query(sql, [max_date] + test_stocks)
        df = pd.DataFrame(result)

        if df.empty:
            print("❌ 无CR20数据")
        else:
            print(f"\nCR20数据: {len(df)}条")
            print(df)

        # 测试换手率
        sql = f"""
        SELECT ts_code, trade_date, turnover_rate_f
        FROM daily_basic
        WHERE trade_date = %s
          AND ts_code IN ({placeholders})
        """
        result = db.execute_query(sql, [max_date] + test_stocks)
        df = pd.DataFrame(result)

        if df.empty:
            print("\n❌ 无换手率数据")
        else:
            print(f"\n换手率数据: {len(df)}条")
            print(df)

        # 测试行业数据
        sql = f"""
        SELECT ts_code, l1_name
        FROM sw_industry
        WHERE ts_code IN ({placeholders})
        """
        result = db.execute_query(sql, test_stocks)
        df = pd.DataFrame(result)

        if df.empty:
            print("\n❌ 无行业数据")
        else:
            print(f"\n行业数据: {len(df)}条")
            print(df)

    except Exception as e:
        print(f"❌ 错误: {e}")


def test_peg_calculation(max_date):
    """测试PEG计算"""
    print("\n" + "="*60)
    print("PEG计算测试")
    print("="*60)

    db = DBConnection(DATABASE_CONFIG)

    try:
        test_stocks = ['000001.SZ', '000002.SZ', '300001.SZ']

        # 1. 获取PE数据
        placeholders = ','.join(['%s'] * len(test_stocks))
        sql_pe = f"""
        SELECT ts_code, trade_date, pe_ttm
        FROM daily_basic
        WHERE trade_date = %s
          AND ts_code IN ({placeholders})
          AND pe_ttm IS NOT NULL
          AND pe_ttm > 0
        """
        data_pe = db.execute_query(sql_pe, [max_date] + test_stocks)
        df_pe = pd.DataFrame(data_pe)

        print(f"PE数据: {len(df_pe)}条")
        if not df_pe.empty:
            print(df_pe)

        # 2. 获取财务数据
        sql_fina = f"""
        SELECT ts_code, ann_date, dt_netprofit_yoy
        FROM fina_indicator
        WHERE ann_date <= %s
          AND ts_code IN ({placeholders})
          AND update_flag = '1'
          AND dt_netprofit_yoy IS NOT NULL
          AND dt_netprofit_yoy != 0
        ORDER BY ts_code, ann_date
        """
        data_fina = db.execute_query(sql_fina, [max_date] + test_stocks)
        df_fina = pd.DataFrame(data_fina)

        print(f"\n财务数据: {len(df_fina)}条")
        if not df_fina.empty:
            # 只显示最近的
            print(df_fina.groupby('ts_code').tail(3))

        # 3. 计算PEG
        if not df_pe.empty and not df_fina.empty:
            df_fina['trade_date'] = df_fina['ann_date']
            df_merged = df_pe.merge(df_fina[['ts_code', 'trade_date', 'dt_netprofit_yoy']],
                                   on=['ts_code', 'trade_date'], how='left')

            # 前向填充
            df_merged = df_merged.sort_values(['ts_code', 'trade_date'])
            df_merged['dt_netprofit_yoy'] = df_merged.groupby('ts_code')['dt_netprofit_yoy'].ffill()

            # 计算PEG
            df_merged['peg'] = df_merged['pe_ttm'] / df_merged['dt_netprofit_yoy']
            df_merged['peg'] = df_merged['peg'].fillna(0)
            df_merged.loc[df_merged['peg'] <= 0, 'peg'] = 0

            print(f"\nPEG计算结果:")
            print(df_merged[['ts_code', 'trade_date', 'pe_ttm', 'dt_netprofit_yoy', 'peg']])

    except Exception as e:
        print(f"❌ 错误: {e}")


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("聚宽策略V3 - 数据库适配版 - 快速测试")
    print("="*60)

    # 1. 测试数据库连接
    max_date = test_database()
    if not max_date:
        print("\n❌ 数据库测试失败，终止")
        return

    # 2. 测试股票池
    test_stock_pool(max_date)

    # 3. 测试价格数据
    test_price_data(max_date)

    # 4. 测试因子数据
    test_factor_data(max_date)

    # 5. 测试PEG计算
    test_peg_calculation(max_date)

    print("\n" + "="*60)
    print("✅ 所有测试完成")
    print("="*60)
    print("\n如果所有测试都通过，可以运行完整策略:")
    print("  python strategy_executor.py --mode test")
    print("  python strategy_executor.py --mode backtest --start 2024-12-01 --end 2025-01-31")


if __name__ == '__main__':
    main()
