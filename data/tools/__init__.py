"""
文件input(依赖外部什么): sqlalchemy, pandas, core.config
文件output(提供什么): 数据工具统一导入接口
文件pos(系统局部地位): 数据工具层，提供数据库连接和数据检查功能
文件功能:
    1. 数据库连接管理（db连接池）
    2. 数据库结构检查（表、字段、索引）
    3. 连接测试（连通性、性能）
    4. 数据查询工具（SQL执行、结果处理）

使用示例:
    from data.tools import db, inspect_database, test_connection

    # 使用数据库连接
    data = db.query("SELECT * FROM daily_basic LIMIT 10")

    # 检查数据库结构
    schema = inspect_database()

    # 测试连接
    is_ok = test_connection()

返回值:
    Connection: 数据库连接实例
    Dict: 数据库结构信息
    bool: 连接状态

工具功能:
    1. db - 数据库连接实例（支持查询、更新）
    2. inspect_database - 检查数据库表结构和索引
    3. test_connection - 测试数据库连接状态和性能
"""

from .db_connection import db
from .inspect_db import inspect_database
from .test_connection import test_connection

__all__ = ['db', 'inspect_database', 'test_connection']
