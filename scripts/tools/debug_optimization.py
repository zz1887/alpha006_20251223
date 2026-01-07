#!/usr/bin/env python3
"""
Debug script to understand why only 3 days were tested
"""

import sys
sys.path.insert(0, '/home/zcy/alpha006_20251223')

from backtest.engine.vbt_data_preparation import VBTDataPreparation
from backtest.engine.vbt_backtest_engine import VBTBacktestEngine

# Test parameters
start_date = '20240101'
end_date = '20250901'
hold_days_range = list(range(10, 61, 1))  # 10-60 days, step=1

print(f"Debug: hold_days_range = {hold_days_range}")
print(f"Debug: length = {len(hold_days_range)}")

# Test data preparation
try:
    print("\n=== Testing Data Preparation ===")
    preparer = VBTDataPreparation(start_date, end_date)
    data = preparer.prepare_all(outlier_sigma=3.0, normalization=None, top_n=3)

    print(f"Data loaded successfully!")
    print(f"Price matrix shape: {data['price_df'].shape}")
    print(f"Signal matrix shape: {data['signal_matrix'].shape}")

    # Test engine
    print("\n=== Testing Engine ===")
    engine = VBTBacktestEngine(data['price_df'], data['signal_matrix'])

    # Test single day
    print("\n=== Testing Single Day (10) ===")
    result = engine.run_backtest(10, 1000000.0)
    if result:
        print(f"✓ Day 10: {result['summary']}")
    else:
        print("✗ Day 10 failed")

    # Test multiple days
    print("\n=== Testing Multiple Days (10,11,12,13,14,15) ===")
    test_range = list(range(10, 16))
    results_df = engine.run_multiple_hold_days(test_range, 1000000.0)
    print(f"Results shape: {results_df.shape}")
    print(f"Results:\n{results_df}")

    # Test full range
    print("\n=== Testing Full Range (10-60) ===")
    print(f"Running {len(hold_days_range)} tests...")
    full_results_df = engine.run_multiple_hold_days(hold_days_range, 1000000.0)
    print(f"Full results shape: {full_results_df.shape}")
    print(f"Full results:\n{full_results_df}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()