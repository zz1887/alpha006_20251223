#!/usr/bin/env python
# 简化版回测执行器 - 用于测试

import sys
import os
from datetime import datetime, timedelta

# 设置路径
sys.path.append('/home/zcy/alpha006_20251223')
os.chdir('/home/zcy/alpha006_20251223/strategies/runners')

print("="*80)
print("简化版回测执行器")
print("="*80)

# 测试基础导入
try:
    print("\n1. 测试基础配置导入...")
    from core.config.settings import DATABASE_CONFIG, BACKTEST_CONFIG
    print("✅ 配置导入成功")
except Exception as e:
    print(f"❌ 配置导入失败: {e}")
    sys.exit(1)

try:
    print("\n2. 测试数据库连接...")
    from core.utils.db_connection import DBConnection
    db = DBConnection(DATABASE_CONFIG)
    result = db.execute_query("SELECT COUNT(*) as cnt FROM daily_kline LIMIT 1")
    if result:
        print("✅ 数据库连接成功")
    else:
        print("❌ 数据库查询失败")
        sys.exit(1)
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
    sys.exit(1)

try:
    print("\n3. 测试策略导入...")
    from strategies.runners.聚宽策略V3_数据库版 import (
        initialize, select_and_adjust, check_market_status,
        Context, Portfolio, Position, get_current_price
    )
    print("✅ 策略导入成功")
except Exception as e:
    print(f"❌ 策略导入失败: {e}")
    sys.exit(1)

# 测试单日回测
try:
    print("\n4. 测试单日回测...")
    test_date = '2024-10-09'  # 选择一个已知的交易日
    dt = datetime.strptime(test_date, '%Y-%m-%d')

    # 检查是否为交易日
    date_str = dt.strftime('%Y%m%d')
    sql = f"SELECT COUNT(*) as cnt FROM daily_kline WHERE trade_date = %s"
    result = db.execute_query(sql, (date_str,))

    if result and result[0]['cnt'] > 0:
        print(f"✅ {test_date} 是交易日")

        # 初始化策略
        context = Context(dt)
        initialize(context)

        # 设置初始资金
        context.portfolio.total_value = BACKTEST_CONFIG['initial_capital']
        context.portfolio.cash = BACKTEST_CONFIG['initial_capital']
        context.portfolio.max_total_value = BACKTEST_CONFIG['initial_capital']

        print(f"初始状态 - 总资产: {context.portfolio.total_value:,.2f}, 现金: {context.portfolio.cash:,.2f}")

        # 执行调仓
        print(f"执行调仓...")
        select_and_adjust(context)

        # 显示结果
        print(f"调仓后状态 - 总资产: {context.portfolio.total_value:,.2f}, 现金: {context.portfolio.cash:,.2f}")

        # 显示持仓
        print(f"持仓股票:")
        for code, pos in context.portfolio.positions.items():
            if pos.total_amount > 0:
                print(f"  {code}: {pos.total_amount}股, 成本: {pos.avg_cost:.2f}, 市值: {pos.value:.2f}")

        print(f"\n✅ 单日测试成功！")

    else:
        print(f"❌ {test_date} 不是交易日")

except Exception as e:
    print(f"❌ 单日测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("所有测试通过！可以运行完整回测")
print("="*80)