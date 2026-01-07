#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行策略执行器测试 - 2025-12-30
"""

import sys
import os
import subprocess
from datetime import datetime

# 设置工作目录
os.chdir('/home/zcy/alpha006_20251223/strategies/runners')

print("="*80)
print("策略执行器测试 - 2025年12月30日")
print("="*80)

# 测试日期
test_date = "2025-12-30"
print(f"\n测试日期: {test_date}")

# 运行策略执行器
print("\n" + "="*60)
print("运行策略执行器...")
print("="*60)

try:
    # 使用subprocess捕获输出
    cmd = ["python", "strategy_executor.py", "--mode", "test", "--date", test_date]

    # 运行命令并捕获输出
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,  # 5分钟超时
        cwd='/home/zcy/alpha006_20251223/strategies/runners'
    )

    print("STDOUT:")
    print(result.stdout if result.stdout else "(无输出)")

    print("\nSTDERR:")
    print(result.stderr if result.stderr else "(无错误)")

    print(f"\n返回码: {result.returncode}")

except subprocess.TimeoutExpired:
    print("❌ 执行超时")
except Exception as e:
    print(f"❌ 执行失败: {e}")

# 检查输出文件
print("\n" + "="*60)
print("检查输出文件...")
print("="*60)

output_files = [
    f"/home/zcy/alpha006_20251223/strategies/runners/选股结果_{test_date.replace('-', '')}.csv",
    f"/home/zcy/alpha006_20251223/strategies/runners/选股结果_{test_date.replace('-', '')}_统一标准.csv"
]

for file_path in output_files:
    if os.path.exists(file_path):
        print(f"✅ 找到文件: {file_path}")
        # 显示文件大小
        size = os.path.getsize(file_path)
        print(f"   文件大小: {size} 字节")

        # 显示前几行内容
        if size > 0:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                print(f"   行数: {len(lines)}")
                if len(lines) > 0:
                    print("   前3行内容:")
                    for i, line in enumerate(lines[:3]):
                        print(f"   {i+1}: {line.strip()}")
    else:
        print(f"❌ 未找到文件: {file_path}")

print("\n" + "="*80)
print("测试完成")
print("="*80)