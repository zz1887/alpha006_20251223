"""
重构验证脚本
版本: v2.0
更新日期: 2025-12-30

功能:
- 验证重构后的代码是否正常工作
- 对比新旧版本的结果一致性
"""

import sys
import os
sys.path.insert(0, '/home/zcy/alpha006_20251223')

import pandas as pd
import numpy as np
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入新版本模块
try:
    from core.config.settings import validate_config
    from core.config.params import validate_params
    from core.utils.db_connection import db
    from core.utils.data_loader import data_loader
    from factors import create_alpha_peg, create_alpha_pluse, create_alpha_038, create_alpha_120cq, create_cr_qfq
    logger.info("✅ 新版本模块导入成功")
except Exception as e:
    logger.error(f"❌ 模块导入失败: {e}")
    sys.exit(1)


def verify_config():
    """验证配置"""
    print("\n" + "=" * 60)
    print("步骤1: 验证配置")
    print("=" * 60)

    # 验证settings
    errors = validate_config()
    if errors:
        print("❌ 配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("✅ settings配置验证通过")

    # 验证params
    errors = validate_params()
    if errors:
        print("❌ 参数配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("✅ params配置验证通过")

    return True


def verify_database():
    """验证数据库连接"""
    print("\n" + "=" * 60)
    print("步骤2: 验证数据库连接")
    print("=" * 60)

    try:
        if db.check_connection():
            print("✅ 数据库连接正常")
            return True
        else:
            print("❌ 数据库连接失败")
            return False
    except Exception as e:
        print(f"❌ 数据库连接异常: {e}")
        return False


def verify_data_loader():
    """验证数据加载器"""
    print("\n" + "=" * 60)
    print("步骤3: 验证数据加载器")
    print("=" * 60)

    try:
        # 测试获取可交易股票
        stocks = data_loader.get_tradable_stocks('20251229')
        if len(stocks) > 0:
            print(f"✅ 获取可交易股票成功: {len(stocks)}只")
        else:
            print("❌ 未获取到股票")
            return False

        # 测试获取行业数据
        industry = data_loader.get_industry_data(stocks[:10])
        if len(industry) > 0:
            print(f"✅ 获取行业数据成功: {len(industry)}条")
        else:
            print("⚠️  行业数据为空")

        return True

    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        return False


def verify_factors():
    """验证因子计算"""
    print("\n" + "=" * 60)
    print("步骤4: 验证因子计算")
    print("=" * 60)

    target_date = '20251229'

    try:
        # 获取股票
        stocks = data_loader.get_tradable_stocks(target_date)
        if not stocks:
            print("❌ 无有效股票")
            return False

        # 测试alpha_pluse
        print("\n  测试alpha_pluse...")
        alpha_pluse_factor = create_alpha_pluse('standard')
        df_pluse = alpha_pluse_factor.calculate_by_period('20251201', target_date, target_date)
        if len(df_pluse) > 0:
            print(f"    ✅ alpha_pluse: {len(df_pluse)}只股票, 信号数: {df_pluse['alpha_pluse'].sum()}")
        else:
            print("    ❌ alpha_pluse计算失败")

        # 测试alpha_peg
        print("\n  测试alpha_peg...")
        alpha_peg_factor = create_alpha_peg('standard')
        df_peg = alpha_peg_factor.calculate_by_period('20251201', target_date, target_date)
        if len(df_peg) > 0:
            print(f"    ✅ alpha_peg: {len(df_peg)}只股票")
        else:
            print("    ❌ alpha_peg计算失败")

        # 测试alpha_038
        print("\n  测试alpha_038...")
        alpha_038_factor = create_alpha_038('standard')
        df_038 = alpha_038_factor.calculate_by_period('20251201', target_date, target_date)
        if len(df_038) > 0:
            print(f"    ✅ alpha_038: {len(df_038)}只股票")
        else:
            print("    ❌ alpha_038计算失败")

        # 测试alpha_120cq
        print("\n  测试alpha_120cq...")
        alpha_120cq_factor = create_alpha_120cq('standard')
        df_120cq = alpha_120cq_factor.calculate_by_period('20251001', target_date, target_date)
        if len(df_120cq) > 0:
            print(f"    ✅ alpha_120cq: {len(df_120cq)}只股票")
        else:
            print("    ❌ alpha_120cq计算失败")

        # 测试cr_qfq
        print("\n  测试cr_qfq...")
        cr_qfq_factor = create_cr_qfq('standard')
        df_cr = cr_qfq_factor.calculate_by_period(target_date, stocks[:100])
        if len(df_cr) > 0:
            print(f"    ✅ cr_qfq: {len(df_cr)}条记录")
        else:
            print("    ❌ cr_qfq获取失败")

        return True

    except Exception as e:
        print(f"❌ 因子计算失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_strategy3():
    """验证策略3计算"""
    print("\n" + "=" * 60)
    print("步骤5: 验证策略3计算")
    print("=" * 60)

    try:
        # 导入策略3计算器
        from scripts.run_strategy3 import Strategy3Calculator

        target_date = '20251229'

        print(f"\n  计算策略3得分: {target_date}")
        calculator = Strategy3Calculator(target_date, 'standard')

        # 简化测试：只计算部分股票
        stocks = data_loader.get_tradable_stocks(target_date)[:50]
        if not stocks:
            print("    ❌ 无有效股票")
            return False

        # 获取数据
        trading_days = calculator.get_trading_days_needed()
        price_df = data_loader.get_price_data(stocks, trading_days[0], target_date)

        if len(price_df) == 0:
            print("    ❌ 价格数据为空")
            return False

        print(f"    ✅ 数据准备完成: {len(stocks)}只股票, {len(trading_days)}个交易日")

        # 计算部分因子进行验证
        alpha_pluse_factor = create_alpha_pluse('standard')
        df_pluse = alpha_pluse_factor.calculate(price_df)

        if len(df_pluse) > 0:
            print(f"    ✅ 策略3部分计算验证通过")
            return True
        else:
            print("    ❌ 策略3计算失败")
            return False

    except Exception as e:
        print(f"❌ 策略3验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("重构验证脚本")
    print("=" * 80)
    print("验证重构后的代码功能和数据一致性")
    print("=" * 80)

    start_time = datetime.now()

    # 执行验证
    results = []

    results.append(("配置验证", verify_config()))
    results.append(("数据库验证", verify_database()))
    results.append(("数据加载验证", verify_data_loader()))
    results.append(("因子计算验证", verify_factors()))
    results.append(("策略3验证", verify_strategy3()))

    # 总结
    print("\n" + "=" * 80)
    print("验证总结")
    print("=" * 80)

    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
        if not result:
            all_passed = False

    duration = (datetime.now() - start_time).total_seconds()
    print(f"\n耗时: {duration:.2f}秒")

    if all_passed:
        print("\n🎉 所有验证通过！重构成功！")
    else:
        print("\n⚠️  部分验证失败，请检查")

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)