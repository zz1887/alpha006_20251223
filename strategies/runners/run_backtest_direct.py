#!/usr/bin/env python
# 直接运行回测的脚本

import sys
import os
import io

# 设置标准输出为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目路径
sys.path.append('/home/zcy/alpha006_20251223')

# 切换到正确的工作目录
os.chdir('/home/zcy/alpha006_20251223/strategies/runners')

print("开始执行回测...")
print("工作目录:", os.getcwd())

try:
    from enhanced_strategy_executor import run_enhanced_backtest
    print("✅ 导入成功")

    # 执行回测
    tracker, file_paths = run_enhanced_backtest(
        start_date='2024-10-01',
        end_date='2025-12-01',
        rebalance_day=6,
        output_dir='/home/zcy/alpha006_20251223/results/backtest'
    )

    print("\n" + "="*80)
    print("回测执行完成！")
    print("="*80)

    # 显示关键结果
    metrics = tracker.get_performance_metrics()
    print("\n📊 关键指标:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}" if '收益率' in key or '回撤' in key or '比率' in key or '胜率' in key else f"  {key}: {value:,.2f}")
        else:
            print(f"  {key}: {value}")

    print(f"\n📁 结果文件:")
    for key, path in file_paths.items():
        if path:
            print(f"  {key}: {path}")

except Exception as e:
    print(f"❌ 执行失败: {e}")
    import traceback
    traceback.print_exc()