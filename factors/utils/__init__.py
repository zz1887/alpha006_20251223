"""
工具函数库

提供数据处理和验证的通用工具，包括：
- 数据加载器
- 数据处理器
- 异常值处理器
- 数据验证器

使用示例:
    from factors.utils import DataLoader, DataProcessor

    # 加载数据
    loader = DataLoader(data_source='database')
    data = loader.load_finance_data(
        ts_codes=['000001.SZ', '000002.SZ'],
        start_date='20240101',
        end_date='20241231',
        fields=['pe_ttm', 'dt_netprofit_yoy', 'close']
    )

    # 处理数据
    processor = DataProcessor()
    processed_data = processor.handle_missing_values(data)
"""

from .data_loader import DataLoader
from .data_processor import DataProcessor
from .outlier_handler import OutlierHandler
from .validator import Validator

__all__ = [
    'DataLoader',
    'DataProcessor',
    'OutlierHandler',
    'Validator',
]
