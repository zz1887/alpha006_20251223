# 策略执行器 - 数据库版
# 用于执行聚宽策略V3的数据库适配版本

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append('/home/zcy/alpha006_20251223')

# 导入策略
try:
    from strategies.runners.聚宽策略V3_数据库版 import (
        initialize, select_and_adjust, check_market_status,
        Context, Portfolio, Position
    )
except ImportError as e:
    print(f"导入策略失败: {e}")
    print("请确保策略文件存在")
    sys.exit(1)

# 导入项目配置
from core.config.settings import DATABASE_CONFIG
from core.utils.db_connection import DBConnection

# 初始化数据库连接
db = DBConnection(DATABASE_CONFIG)


def run_backtest(start_date, end_date, rebalance_day=6):
    """
    运行回测

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        rebalance_day: 调仓日 (每月几号)
    """
    print("="*80)
    print(f"开始回测: {start_date} 至 {end_date}")
    print(f"调仓日: 每月{rebalance_day}日")
    print("="*80)

    # 转换日期
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    # 初始化策略
    context = Context(start_dt)
    initialize(context)

    # 生成交易日历
    current_dt = start_dt
    trade_count = 0

    while current_dt <= end_dt:
        # 检查是否为交易日
        date_str = current_dt.strftime('%Y%m%d')
        sql = f"SELECT COUNT(*) as cnt FROM daily_kline WHERE trade_date = %s"
        result = db.execute_query(sql, (date_str,))

        if result and result[0]['cnt'] > 0:
            # 是交易日
            context.current_dt = current_dt

            # 检查是否需要调仓
            if current_dt.day == rebalance_day:
                print(f"\n{'='*80}")
                print(f"【{current_dt.strftime('%Y-%m-%d')}】执行调仓")
                print(f"{'='*80}")
                select_and_adjust(context)
                trade_count += 1
            else:
                # 每日监控
                check_market_status(context)

        current_dt += timedelta(days=1)

    print(f"\n{'='*80}")
    print(f"回测完成！共执行{trade_count}次调仓")
    print(f"{'='*80}")


def run_single_day_test(test_date):
    """
    运行单日测试

    Args:
        test_date: 测试日期 (YYYY-MM-DD)
    """
    print("="*80)
    print(f"单日测试: {test_date}")
    print("="*80)

    dt = datetime.strptime(test_date, '%Y-%m-%d')
    context = Context(dt)

    # 初始化
    initialize(context)

    # 执行调仓
    print(f"\n【{test_date}】执行调仓...")
    select_and_adjust(context)

    # 显示持仓
    print(f"\n【{test_date}】持仓详情...")
    if hasattr(context.portfolio, 'positions'):
        for code, pos in context.portfolio.positions.items():
            if pos.total_amount > 0:
                print(f"  {code}: {pos.total_amount}股, 成本: {pos.avg_cost:.2f}")

    print("\n✅ 单日测试完成")


def show_factor_analysis(test_date, stock_code):
    """
    显示因子分析

    Args:
        test_date: 测试日期 (YYYY-MM-DD)
        stock_code: 股票代码
    """
    print("="*80)
    print(f"因子分析: {stock_code} @ {test_date}")
    print("="*80)

    from strategies.runners.聚宽策略V3_数据库版 import (
        get_stock_pool, batch_get_price_data, get_turnover_data,
        get_factor_data_batch
    )

    dt = datetime.strptime(test_date, '%Y-%m-%d')
    context = Context(dt)

    # 获取数据
    print("\n1. 获取股票池...")
    stocks = get_stock_pool(context, debug=False, is_mainboard=False, min_listed_days=365)
    print(f"   创业板股票: {len(stocks)}只")

    if stock_code in stocks:
        print(f"\n2. {stock_code} 在股票池中 ✓")

        # 获取价格数据
        print("\n3. 获取价格数据...")
        price_data = batch_get_price_data([stock_code], dt, 120, debug=False)
        if price_data:
            close_series = price_data['close'][stock_code]
            print(f"   数据长度: {len(close_series)}天")
            print(f"   最近5日收盘价: {close_series.tail().values}")

        # 获取换手率数据
        print("\n4. 获取换手率数据...")
        turnover_data = get_turnover_data([stock_code], dt.date(), 120, debug=False)
        if not turnover_data.empty:
            print(f"   数据长度: {len(turnover_data)}天")
            print(f"   最近5日换手率: {turnover_data[stock_code].tail().values}")

        # 获取因子数据
        print("\n5. 获取因子数据...")
        start_date = (dt - timedelta(days=45)).strftime('%Y%m%d')
        end_date = dt.strftime('%Y%m%d')
        factor_data = get_factor_data_batch([stock_code], start_date, end_date, ['PEG', 'CR20'], debug=False)

        if 'PEG' in factor_data and not factor_data['PEG'].empty:
            print(f"   PEG数据: {len(factor_data['PEG'])}天")
            if stock_code in factor_data['PEG'].columns:
                print(f"   最近PEG: {factor_data['PEG'][stock_code].tail().values}")

        if 'CR20' in factor_data and not factor_data['CR20'].empty:
            print(f"   CR20数据: {len(factor_data['CR20'])}天")
            if stock_code in factor_data['CR20'].columns:
                print(f"   最近CR20: {factor_data['CR20'][stock_code].tail().values}")
    else:
        print(f"\n❌ {stock_code} 不在当前股票池中")
        print(f"   可用股票示例: {stocks[:5] if stocks else '无'}")


def check_database_connection():
    """检查数据库连接"""
    print("="*80)
    print("数据库连接检查")
    print("="*80)

    try:
        # 测试连接
        result = db.execute_query("SELECT COUNT(*) as cnt FROM daily_kline LIMIT 1")
        if result:
            print("✅ 数据库连接正常")

        # 检查核心表数据量
        tables = ['daily_kline', 'daily_basic', 'stk_factor_pro', 'sw_industry']
        for table in tables:
            sql = f"SELECT COUNT(*) as cnt FROM {table} LIMIT 1"
            result = db.execute_query(sql)
            if result:
                print(f"  {table}: 连接正常")

        # 检查最近日期
        sql = "SELECT MAX(trade_date) as max_date FROM daily_kline"
        result = db.execute_query(sql)
        if result and result[0]['max_date']:
            max_date = result[0]['max_date']
            print(f"\n最近交易日期: {max_date}")

        return True

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='聚宽策略V3 - 数据库版执行器')
    parser.add_argument('--mode', type=str, default='test',
                       choices=['test', 'backtest', 'factor', 'dbcheck'],
                       help='运行模式: test(单日测试), backtest(回测), factor(因子分析), dbcheck(数据库检查)')
    parser.add_argument('--date', type=str, default=None,
                       help='测试日期 (YYYY-MM-DD)')
    parser.add_argument('--start', type=str, default=None,
                       help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=None,
                       help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--stock', type=str, default=None,
                       help='股票代码 (用于因子分析)')
    parser.add_argument('--rebalance', type=int, default=6,
                       help='调仓日 (默认6号)')

    args = parser.parse_args()

    if args.mode == 'dbcheck':
        check_database_connection()
        return

    if args.mode == 'test':
        if not args.date:
            # 使用最近一个交易日
            db = DBConnection(DATABASE_CONFIG)
            result = db.execute_query("SELECT MAX(trade_date) as max_date FROM daily_kline")
            if result and result[0]['max_date']:
                max_date = result[0]['max_date']
                test_date = datetime.strptime(max_date, '%Y%m%d').strftime('%Y-%m-%d')
            else:
                test_date = '2025-01-03'
        else:
            test_date = args.date

        run_single_day_test(test_date)

    elif args.mode == 'backtest':
        if not args.start or not args.end:
            print("请指定回测开始和结束日期")
            return

        run_backtest(args.start, args.end, args.rebalance)

    elif args.mode == 'factor':
        if not args.date or not args.stock:
            print("请指定日期和股票代码")
            return

        show_factor_analysis(args.date, args.stock)


if __name__ == '__main__':
    main()
