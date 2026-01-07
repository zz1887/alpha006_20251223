"""
文件input(依赖外部什么): pandas, numpy, sqlalchemy, redis
文件output(提供什么): 核心工具函数统一导入接口
文件pos(系统局部地位): 核心工具层，提供数据库连接、数据加载和数据处理功能
文件功能:
    1. 数据库连接管理（连接池、安全执行）
    2. 数据加载器（财务数据、价格数据、行业数据）
    3. 数据处理器（因子计算、排名、异常值处理）

使用示例:
    from core.utils import DBConnection, DataLoader, calculate_alpha_peg_factor

    # 数据库连接
    db = DBConnection()
    data = db.query("SELECT * FROM daily_basic WHERE ts_code='000001.SZ'")

    # 数据加载
    loader = DataLoader()
    finance_data = loader.load_finance_data(
        ts_codes=['000001.SZ'],
        start_date='20240101',
        end_date='20241231',
        fields=['pe_ttm', 'dt_netprofit_yoy']
    )

    # 因子计算
    factor_df = calculate_alpha_peg_factor(finance_data)

返回值:
    DBConnection: 数据库连接实例
    DataLoader: 数据加载器实例
    pd.DataFrame: 计算结果
    bool: 执行状态

工具分类:
    1. 数据库工具 - 连接管理、查询执行、事务处理
    2. 数据加载 - 财务数据、价格数据、行业数据、缓存管理
    3. 数据处理 - 因子计算、标准化、排名、异常值处理
"""

from .db_connection import (
    DBConnection,
    ConnectionPool,
    db,
    init_db,
    safe_execute_query,
    safe_execute_update,
)

from .data_loader import (
    DataLoader,
    data_loader,
    load_industry_data,
    get_price_data,
    get_index_data,
    validate_data,
    save_to_cache,
    load_from_cache,
)

from .data_processor import (
    calculate_alpha_peg_factor,
    calculate_alpha_pluse_factor,
    calculate_rank,
)

__all__ = [
    # db_connection
    'DBConnection',
    'ConnectionPool',
    'db',
    'init_db',
    'safe_execute_query',
    'safe_execute_update',

    # data_loader
    'DataLoader',
    'data_loader',
    'load_industry_data',
    'get_price_data',
    'get_index_data',
    'validate_data',
    'save_to_cache',
    'load_from_cache',

    # data_processor
    'calculate_alpha_peg_factor',
    'calculate_alpha_pluse_factor',
    'calculate_rank',
]