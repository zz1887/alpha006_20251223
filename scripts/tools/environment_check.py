#!/usr/bin/env python3
"""
环境验证脚本 - environment_check.py

功能:
- 验证vectorbt库安装和版本
- 检查数据库连接可用性
- 验证核心模块导入
- 检查数据目录和文件
- 测试基础回测功能

使用方法:
    python environment_check.py
"""

import sys
import os
import platform

# 设置项目路径
PROJECT_ROOT = '/home/zcy/alpha006_20251223'
sys.path.insert(0, PROJECT_ROOT)

from datetime import datetime
import pandas as pd

def print_header(title):
    """打印标题"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")

def check_python_environment():
    """检查Python环境"""
    print_header("1. Python环境检查")

    print(f"Python版本: {platform.python_version()}")
    print(f"系统平台: {platform.system()} {platform.release()}")
    print(f"项目路径: {PROJECT_ROOT}")

    return True

def check_dependencies():
    """检查依赖包"""
    print_header("2. 依赖包检查")

    packages = [
        ('vectorbt', '0.25.0'),
        ('pandas', '2.0.0'),
        ('numpy', '1.24.0'),
        ('pymysql', '1.0.0'),
        ('matplotlib', '3.7.0'),
        ('seaborn', '0.12.0')
    ]

    all_ok = True
    for package, min_version in packages:
        try:
            mod = __import__(package)
            version = getattr(mod, '__version__', '未知')
            print(f"✅ {package:12s} 版本: {version}")
        except ImportError:
            print(f"❌ {package:12s} 未安装")
            all_ok = False

    return all_ok

def check_core_modules():
    """检查核心模块"""
    print_header("3. 核心模块检查")

    modules = [
        'core.constants.config',
        'core.utils.db_connection',
        'core.utils.data_loader',
        'core.utils.data_processor',
        'factors.valuation.factor_alpha_peg',
        'backtest.engine.vbt_data_preparation',
        'backtest.engine.vbt_backtest_engine',
        'backtest.engine.backtest_hold_days_optimize',
        'backtest.rules.industry_rank_rule'
    ]

    all_ok = True
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except Exception as e:
            print(f"❌ {module}: {e}")
            all_ok = False

    return all_ok

def check_config():
    """检查配置"""
    print_header("4. 配置检查")

    try:
        from core.constants.config import PATH_CONFIG, COMMISSION, STAMP_TAX, SLIPPAGE

        print("交易成本:")
        print(f"  佣金: {COMMISSION:.4f} ({COMMISSION*100:.2f}%)")
        print(f"  印花税: {STAMP_TAX:.4f} ({STAMP_TAX*100:.2f}%)")
        print(f"  滑点: {SLIPPAGE:.4f} ({SLIPPAGE*100:.2f}%)")
        print(f"  总成本: {COMMISSION + STAMP_TAX + SLIPPAGE:.4f} ({(COMMISSION + STAMP_TAX + SLIPPAGE)*100:.2f}%)")

        print("\n路径配置:")
        for key, path in PATH_CONFIG.items():
            exists = os.path.exists(path) if 'http' not in path else True
            status = "✅" if exists else "⚠️"
            print(f"  {status} {key:15s}: {path}")

        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

def check_database_connection():
    """检查数据库连接"""
    print_header("5. 数据库连接检查")

    try:
        from core.utils.db_connection import db

        # 测试简单查询
        test_sql = "SELECT 1 as test_value"
        result = db.execute_query(test_sql)

        if result and len(result) > 0:
            print(f"✅ 数据库连接正常")
            print(f"  测试查询结果: {result[0]}")
            return True
        else:
            print("❌ 数据库连接异常")
            return False

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def check_data_files():
    """检查数据文件"""
    print_header("6. 数据文件检查")

    from core.constants.config import PATH_CONFIG

    # 检查行业数据文件
    industry_path = PATH_CONFIG['industry_data']
    if os.path.exists(industry_path):
        file_size = os.path.getsize(industry_path) / 1024 / 1024
        print(f"✅ 行业数据文件: {industry_path} ({file_size:.1f} MB)")
    else:
        print(f"❌ 行业数据文件不存在: {industry_path}")
        return False

    # 检查结果目录
    result_dirs = ['results_factor', 'results_backtest', 'results_visual']
    for dir_key in result_dirs:
        dir_path = PATH_CONFIG[dir_key]
        if os.path.exists(dir_path):
            file_count = len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
            print(f"✅ {dir_key:15s}: {dir_path} ({file_count}个文件)")
        else:
            print(f"❌ {dir_key:15s}: 目录不存在")
            return False

    return True

def check_existing_results():
    """检查现有回测结果"""
    print_header("7. 现有结果检查")

    from core.constants.config import PATH_CONFIG

    backtest_dir = PATH_CONFIG['results_backtest']
    if not os.path.exists(backtest_dir):
        print("❌ 回测结果目录不存在")
        return False

    # 查找持仓天数优化结果
    files = os.listdir(backtest_dir)
    hold_days_files = [f for f in files if 'hold_days' in f]

    if hold_days_files:
        print(f"✅ 发现持仓天数优化结果: {len(hold_days_files)}个文件")
        for f in sorted(hold_days_files):
            file_path = os.path.join(backtest_dir, f)
            file_size = os.path.getsize(file_path)
            print(f"  - {f} ({file_size} bytes)")

        # 尝试读取最新结果
        try:
            comparison_files = [f for f in hold_days_files if 'comparison' in f]
            if comparison_files:
                latest = sorted(comparison_files)[-1]
                df = pd.read_csv(os.path.join(backtest_dir, latest))
                print(f"\n  最新结果摘要:")
                print(f"    测试天数: {len(df)}个")
                if 'sharpe_ratio' in df.columns:
                    best_idx = df['sharpe_ratio'].idxmax()
                    best_days = df.loc[best_idx, 'holding_days']
                    best_sharpe = df.loc[best_idx, 'sharpe_ratio']
                    print(f"    最优持仓天数: {best_days}天 (夏普={best_sharpe:.3f})")
        except Exception as e:
            print(f"  ⚠️ 读取结果失败: {e}")
    else:
        print("⚠️ 未发现持仓天数优化结果")

    return True

def test_basic_vbt_function():
    """测试基础vectorbt功能"""
    print_header("8. 基础功能测试")

    try:
        import vectorbt as vbt
        import numpy as np

        # 创建简单测试数据
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        prices = pd.Series(100 + np.arange(10), index=dates)
        entries = pd.Series([True, False, True, False, True, False, True, False, True, False], index=dates)
        exits = ~entries

        # 运行简单回测
        portfolio = vbt.Portfolio.from_signals(
            close=prices,
            entries=entries,
            exits=exits,
            freq='D',
            init_cash=1000000,
            fees=0.0035
        )

        nav = portfolio.value()
        total_return = nav.iloc[-1] / nav.iloc[0] - 1

        print(f"✅ vectorbt基础功能正常")
        print(f"  测试数据: 10个交易日")
        print(f"  交易次数: {len(portfolio.trades.records)}")
        print(f"  最终净值: {nav.iloc[-1]:.0f}")
        print(f"  总收益: {total_return:.2%}")

        return True

    except Exception as e:
        print(f"❌ vectorbt基础功能测试失败: {e}")
        return False

def generate_environment_report():
    """生成环境报告"""
    print_header("环境验证报告")

    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'python_version': platform.python_version(),
        'system': f"{platform.system()} {platform.release()}",
        'project_root': PROJECT_ROOT,
        'checks': {}
    }

    # 运行所有检查
    checks = [
        ('Python环境', check_python_environment),
        ('依赖包', check_dependencies),
        ('核心模块', check_core_modules),
        ('配置', check_config),
        ('数据库连接', check_database_connection),
        ('数据文件', check_data_files),
        ('现有结果', check_existing_results),
        ('基础功能', test_basic_vbt_function)
    ]

    all_passed = True
    for name, func in checks:
        try:
            result = func()
            report['checks'][name] = result
            if not result:
                all_passed = False
        except Exception as e:
            print(f"\n❌ {name} 检查异常: {e}")
            report['checks'][name] = False
            all_passed = False

    # 总结
    print_header("验证总结")
    if all_passed:
        print("✅ 所有检查通过！环境配置正常，可以开始回测任务。")
    else:
        print("❌ 部分检查失败，请根据上述错误信息修复环境。")

    print(f"\n检查时间: {report['timestamp']}")
    print(f"通过率: {sum(report['checks'].values())}/{len(report['checks'])}")

    return report

def main():
    """主函数"""
    print("\n" + "="*80)
    print("ALPHA_PEG因子库 - 环境验证脚本")
    print("="*80)

    try:
        report = generate_environment_report()

        # 保存报告
        report_file = os.path.join(PROJECT_ROOT, 'environment_report.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 环境验证报告\n\n")
            f.write(f"生成时间: {report['timestamp']}\n\n")
            f.write("## 检查结果\n\n")
            for name, result in report['checks'].items():
                status = "✅ 通过" if result else "❌ 失败"
                f.write(f"- {status}: {name}\n")
            f.write(f"\n## 详细信息\n\n")
            f.write(f"- Python版本: {report['python_version']}\n")
            f.write(f"- 系统平台: {report['system']}\n")
            f.write(f"- 项目路径: {report['project_root']}\n")
            f.write(f"- 通过率: {sum(report['checks'].values())}/{len(report['checks'])}\n")

        print(f"\n详细报告已保存: {report_file}")

    except Exception as e:
        print(f"\n❌ 环境验证执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()