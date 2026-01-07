"""
测试运行器 - 一键运行所有测试

功能: 统一运行单元测试、集成测试和性能测试
版本: v2.4 (Phase 6)
"""

import subprocess
import sys
import os
import time
from datetime import datetime

# 添加项目根目录到Python路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def print_header(title):
    """打印标题"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)


def run_unit_tests():
    """运行单元测试"""
    print_header("单元测试 - 11个因子覆盖")

    test_dir = os.path.join(PROJECT_ROOT, 'tests', 'unit')
    if not os.path.exists(test_dir):
        print("❌ 单元测试目录不存在")
        return False

    # 使用pytest运行
    cmd = [
        sys.executable, '-m', 'pytest',
        test_dir,
        '-v',
        '--tb=short',
        '--disable-warnings',
        '--color=yes'
    ]

    print(f"命令: {' '.join(cmd)}")
    print("-" * 80)

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        return False


def run_integration_tests():
    """运行集成测试"""
    print_header("集成测试 - 端到端流程")

    test_file = os.path.join(PROJECT_ROOT, 'tests', 'integration', 'test_end_to_end.py')
    if not os.path.exists(test_file):
        print("❌ 集成测试文件不存在")
        return False

    try:
        # 直接运行Python脚本
        cmd = [sys.executable, test_file]
        print(f"命令: {' '.join(cmd)}")
        print("-" * 80)

        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        return False


def run_performance_tests():
    """运行性能测试"""
    print_header("性能测试 - 基准测试")

    test_file = os.path.join(PROJECT_ROOT, 'tests', 'performance', 'test_benchmark.py')
    if not os.path.exists(test_file):
        print("❌ 性能测试文件不存在")
        return False

    try:
        cmd = [sys.executable, test_file]
        print(f"命令: {' '.join(cmd)}")
        print("-" * 80)

        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        return False


def check_test_coverage():
    """检查测试覆盖率"""
    print_header("测试覆盖检查")

    test_files = [
        'tests/unit/test_alpha_peg.py',
        'tests/unit/test_alpha_010.py',
        'tests/unit/test_alpha_038.py',
        'tests/unit/test_alpha_120cq.py',
        'tests/unit/test_cr_qfq.py',
        'tests/unit/test_alpha_pluse.py',
        'tests/unit/test_bias1_qfq.py',
        'tests/unit/test_alpha_profit_employee.py',
        'tests/unit/test_profit_employee.py',
        'tests/unit/test_alpha_profit_employee_optimized.py',
        'tests/unit/test_profit_employee_optimized.py',
    ]

    print("单元测试文件:")
    for file in test_files:
        full_path = os.path.join(PROJECT_ROOT, file)
        exists = "✅" if os.path.exists(full_path) else "❌"
        print(f"  {exists} {file}")

    integration_files = [
        'tests/integration/test_end_to_end.py',
        'tests/integration/__init__.py',
    ]

    print("\n集成测试文件:")
    for file in integration_files:
        full_path = os.path.join(PROJECT_ROOT, file)
        exists = "✅" if os.path.exists(full_path) else "❌"
        print(f"  {exists} {file}")

    performance_files = [
        'tests/performance/test_benchmark.py',
        'tests/performance/__init__.py',
    ]

    print("\n性能测试文件:")
    for file in performance_files:
        full_path = os.path.join(PROJECT_ROOT, file)
        exists = "✅" if os.path.exists(full_path) else "❌"
        print(f"  {exists} {file}")

    config_files = [
        'tests/__init__.py',
        'tests/conftest.py',
        'tests/pytest.ini',
        'tests/unit/__init__.py',
    ]

    print("\n配置文件:")
    for file in config_files:
        full_path = os.path.join(PROJECT_ROOT, file)
        exists = "✅" if os.path.exists(full_path) else "❌"
        print(f"  {exists} {file}")

    # 统计
    all_files = test_files + integration_files + performance_files + config_files
    existing = sum(1 for f in all_files if os.path.exists(os.path.join(PROJECT_ROOT, f)))
    total = len(all_files)

    print(f"\n📊 覆盖率: {existing}/{total} ({existing/total*100:.1f}%)")

    return existing == total


def generate_summary_report(results):
    """生成测试总结报告"""
    print_header("测试总结报告")

    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python版本: {sys.version.split()[0]}")
    print(f"项目路径: {PROJECT_ROOT}")

    print("\n📊 测试结果:")
    print("-" * 80)

    total_tests = 0
    passed_tests = 0

    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name:<25} {status}")
        total_tests += 1
        if result:
            passed_tests += 1

    print("-" * 80)
    print(f"总计: {passed_tests}/{total_tests} 通过 ({passed_tests/total_tests*100:.1f}%)")

    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！")
        return True
    else:
        print("\n⚠️  部分测试失败，请检查日志")
        return False


def main():
    """主函数"""
    print("="*80)
    print("Alpha因子库 - 测试运行器")
    print("版本: v2.4 (Phase 6)")
    print("="*80)

    # 检查测试文件完整性
    if not check_test_coverage():
        print("\n⚠️  测试文件不完整，继续运行已存在的测试...")

    # 询问运行哪些测试
    print("\n请选择要运行的测试:")
    print("  1. 运行所有测试 (推荐)")
    print("  2. 仅运行单元测试")
    print("  3. 仅运行集成测试")
    print("  4. 仅运行性能测试")
    print("  5. 仅检查测试覆盖")
    print("  0. 退出")

    choice = input("\n请输入选择 (0-5): ").strip()

    if choice == '0':
        print("退出测试运行器")
        return

    start_time = time.time()
    results = {}

    if choice == '1':
        # 运行所有测试
        results['单元测试'] = run_unit_tests()
        results['集成测试'] = run_integration_tests()
        results['性能测试'] = run_performance_tests()

    elif choice == '2':
        results['单元测试'] = run_unit_tests()

    elif choice == '3':
        results['集成测试'] = run_integration_tests()

    elif choice == '4':
        results['性能测试'] = run_performance_tests()

    elif choice == '5':
        check_test_coverage()
        return

    else:
        print("无效选择")
        return

    elapsed = time.time() - start_time

    # 生成总结
    success = generate_summary_report(results)

    print(f"\n⏱️  总耗时: {elapsed:.2f}秒")

    if success:
        print("\n✅ 测试运行完成，所有测试通过！")
    else:
        print("\n⚠️  测试运行完成，部分测试失败")

    # 保存运行日志
    log_file = os.path.join(PROJECT_ROOT, 'tests', 'reports', 'test_run.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"结果: {'通过' if success else '失败'}\n")
        f.write(f"耗时: {elapsed:.2f}秒\n")
        for name, result in results.items():
            f.write(f"{name}: {'通过' if result else '失败'}\n")


if __name__ == "__main__":
    main()
