#!/usr/bin/env python3
"""
Quick test to see if the basic functionality works
"""

import sys
sys.path.insert(0, '/home/zcy/alpha006_20251223')

# Test just the parameters parsing
from scripts.run_hold_days_optimize import parse_arguments

# Simulate command line args
sys.argv = ['script', '--start', '20240101', '--end', '20250901', '--days', '10,60', '--step', '1', '--top-n', '3']

args = parse_arguments()
print(f"Parsed args: {args}")

# Generate hold_days_range
days_range = args.days.split(',')
start_day = int(days_range[0])
end_day = int(days_range[1])
hold_days_range = list(range(start_day, end_day + 1, args.step))

print(f"Hold days range: {hold_days_range}")
print(f"Number of tests: {len(hold_days_range)}")

# Test if we can import the modules
try:
    from backtest.engine.vbt_data_preparation import VBTDataPreparation
    from backtest.engine.vbt_backtest_engine import VBTBacktestEngine
    print("✓ Modules imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")

# Test if we can create a simple data preparation
try:
    print("\n=== Testing Data Preparation ===")
    preparer = VBTDataPreparation('20240101', '20240110')  # Just 10 days
    print("✓ DataPreparation created")
except Exception as e:
    print(f"✗ DataPreparation failed: {e}")