"""
Pytest配置和全局Fixtures

功能: 提供测试环境配置和共享测试数据
版本: v2.4 (Phase 6)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.utils.data_loader import DataLoader
from factors import FactorRegistry


@pytest.fixture(scope="session")
def sample_factor_data():
    """生成标准测试因子数据"""
    np.random.seed(42)

    dates = pd.date_range('2025-01-01', '2025-03-31', freq='D')
    stocks = [f'{i:06d}.SH' for i in range(1, 51)]

    data = []
    for date in dates:
        for stock in stocks:
            data.append({
                'ts_code': stock,
                'trade_date': date.strftime('%Y%m%d'),
                'factor': np.random.normal(0.5, 0.2)
            })

    return pd.DataFrame(data)


@pytest.fixture(scope="session")
def sample_price_data():
    """生成标准测试价格数据"""
    np.random.seed(42)

    dates = pd.date_range('2025-01-01', '2025-04-30', freq='D')
    stocks = [f'{i:06d}.SH' for i in range(1, 51)]

    data = []
    for date in dates:
        for stock in stocks:
            base_price = 100 + np.random.normal(0, 10)
            data.append({
                'ts_code': stock,
                'trade_date': date.strftime('%Y%m%d'),
                'close': base_price,
                'open': base_price * (1 + np.random.normal(0, 0.02)),
                'high': base_price * (1 + abs(np.random.normal(0, 0.03))),
                'low': base_price * (1 - abs(np.random.normal(0, 0.03))),
                'volume': np.random.randint(1000000, 10000000)
            })

    return pd.DataFrame(data)


@pytest.fixture(scope="session")
def sample_forward_returns(sample_price_data):
    """生成前瞻收益率数据（T+20）"""
    price_df = sample_price_data.copy()
    price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])

    # 计算T+20日的前瞻收益率
    price_df = price_df.sort_values(['ts_code', 'trade_date'])
    price_df['future_close'] = price_df.groupby('ts_code')['close'].shift(-20)
    price_df['forward_return'] = (price_df['future_close'] - price_df['close']) / price_df['close']

    # 只保留有效数据
    forward_returns = price_df[['ts_code', 'trade_date', 'forward_return']].dropna()
    forward_returns['trade_date'] = forward_returns['trade_date'].dt.strftime('%Y%m%d')
    forward_returns = forward_returns.set_index(['ts_code', 'trade_date'])

    return forward_returns


@pytest.fixture(scope="session")
def financial_test_data():
    """生成财务数据测试集（用于alpha_profit_employee因子）"""
    np.random.seed(42)

    dates = ['20250331', '20250630', '20250930', '20251231']
    stocks = [f'{i:06d}.SH' for i in range(1, 21)]

    data = []
    for date in dates:
        for stock in stocks:
            # 模拟累计财务数据
            if date == '20250331':
                operate_profit = 100000000 + np.random.randint(-20000000, 20000000)
                c_paid_to_for_empl = 50000000 + np.random.randint(-10000000, 10000000)
            elif date == '20250630':
                operate_profit = 250000000 + np.random.randint(-30000000, 30000000)
                c_paid_to_for_empl = 120000000 + np.random.randint(-15000000, 15000000)
            elif date == '20250930':
                operate_profit = 400000000 + np.random.randint(-40000000, 40000000)
                c_paid_to_for_empl = 200000000 + np.random.randint(-20000000, 20000000)
            else:  # 20251231
                operate_profit = 600000000 + np.random.randint(-50000000, 50000000)
                c_paid_to_for_empl = 300000000 + np.random.randint(-25000000, 25000000)

            data.append({
                'ts_code': stock,
                'ann_date': date,
                'operate_profit': operate_profit,
                'c_paid_to_for_empl': c_paid_to_for_empl,
                'total_mv': np.random.randint(500000, 5000000)  # 万元
            })

    return pd.DataFrame(data)


@pytest.fixture(scope="session")
def factor_registry():
    """因子注册器实例"""
    return FactorRegistry


@pytest.fixture(scope="function", autouse=True)
def setup_test_env():
    """每个测试函数的自动环境设置"""
    # 设置随机种子以确保可重复性
    np.random.seed(42)

    # 清理临时数据
    yield

    # 测试后清理（如果需要）


@pytest.fixture
def mock_db_connection():
    """模拟数据库连接（用于不依赖真实数据库的测试）"""
    class MockDB:
        def execute_query(self, query):
            # 返回模拟数据
            return []

    return MockDB()


@pytest.fixture
def tolerance():
    """数值比较容差"""
    return {
        'decimal': 1e-6,      # 小数容差
        'percent': 0.001,     # 百分比容差
        'absolute': 1e-4      # 绝对容差
    }