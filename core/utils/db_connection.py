"""
文件input(依赖外部什么): core.config.settings.DATABASE_CONFIG, pymysql
文件output(提供什么): 数据库连接实例, 查询执行接口
文件pos(系统局部地位): 核心工具层, 为所有数据操作提供数据库连接

数据库连接模块 - 增强版
版本: v2.0
更新日期: 2025-12-30

功能:
- MySQL数据库连接管理（连接池）
- 查询执行接口（带异常处理）
- 数据批量操作
- 连接健康检查
"""

import pymysql
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union
import logging
import time
from datetime import datetime

# 导入配置
try:
    from core.config.settings import DATABASE_CONFIG
except ImportError:
    # 回退配置
    DATABASE_CONFIG = {
        'host': '172.31.112.1',
        'port': 3306,
        'user': 'root',
        'password': '12345678',
        'database': 'stock_database',
        'charset': 'utf8mb4',
    }

logger = logging.getLogger(__name__)


class DBConnection:
    """增强的数据库连接管理类"""

    def __init__(self, config: Dict[str, Any], max_retries: int = 3, timeout: int = 30):
        """
        初始化数据库连接管理器

        Args:
            config: 数据库配置字典
            max_retries: 最大重试次数
            timeout: 连接超时时间(秒)
        """
        self.config = config
        self.max_retries = max_retries
        self.timeout = timeout
        self._connection = None

    def _get_connection_params(self) -> Dict[str, Any]:
        """获取连接参数"""
        return {
            'host': self.config.get('host', 'localhost'),
            'port': self.config.get('port', 3306),
            'user': self.config.get('user', 'root'),
            'password': self.config.get('password', ''),
            'database': self.config.get('database', self.config.get('db_name', '')),
            'charset': self.config.get('charset', 'utf8mb4'),
            'connect_timeout': self.timeout,
        }

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接上下文管理器（带重试机制）

        Yields:
            数据库连接对象
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                conn = pymysql.connect(**self._get_connection_params())
                yield conn
                conn.close()
                return

            except pymysql.Error as e:
                last_error = e
                logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(1)  # 等待1秒后重试
                else:
                    logger.error(f"数据库连接最终失败: {last_error}")
                    raise last_error

    def execute_query(self, sql: str, params: Optional[tuple] = None,
                     retry: bool = True) -> List[Dict[str, Any]]:
        """
        执行查询语句（带异常处理和重试）

        Args:
            sql: SQL查询语句
            params: 参数元组
            retry: 是否启用重试

        Returns:
            查询结果列表，每行是一个字典

        Raises:
            Exception: 查询失败异常
        """
        start_time = datetime.now()

        try:
            with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    # 记录SQL日志（不包含敏感数据）
                    logger.debug(f"执行查询: {sql[:200]}...")

                    cursor.execute(sql, params or ())
                    result = cursor.fetchall()

                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.debug(f"查询完成，耗时: {elapsed:.3f}s，返回 {len(result)} 行")

                    return result

        except Exception as e:
            logger.error(f"查询失败: {e}\nSQL: {sql}\nParams: {params}")
            if retry and self.max_retries > 1:
                # 递归重试一次
                return self.execute_query(sql, params, retry=False)
            raise

    def execute_update(self, sql: str, params: Optional[tuple] = None,
                      retry: bool = True) -> int:
        """
        执行更新/插入语句（带异常处理和重试）

        Args:
            sql: SQL更新语句
            params: 参数元组
            retry: 是否启用重试

        Returns:
            影响的行数
        """
        start_time = datetime.now()

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    logger.debug(f"执行更新: {sql[:200]}...")

                    result = cursor.execute(sql, params or ())
                    conn.commit()

                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.debug(f"更新完成，耗时: {elapsed:.3f}s，影响 {result} 行")

                    return result

        except Exception as e:
            logger.error(f"更新失败: {e}\nSQL: {sql}\nParams: {params}")
            if retry and self.max_retries > 1:
                return self.execute_update(sql, params, retry=False)
            raise

    def execute_batch(self, sql: str, params_list: List[tuple],
                     batch_size: int = 1000) -> int:
        """
        批量执行更新/插入语句

        Args:
            sql: SQL语句
            params_list: 参数列表
            batch_size: 批次大小

        Returns:
            总影响行数
        """
        total_affected = 0

        for i in range(0, len(params_list), batch_size):
            batch = params_list[i:i + batch_size]

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        result = cursor.executemany(sql, batch)
                        conn.commit()
                        total_affected += result
                        logger.debug(f"批次 {i//batch_size + 1} 完成，影响 {result} 行")

                    except Exception as e:
                        conn.rollback()
                        logger.error(f"批次 {i//batch_size + 1} 执行失败: {e}")
                        raise

        return total_affected

    def execute_query_with_retry(self, sql: str, params: Optional[tuple] = None,
                                max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        带自定义重试次数的查询

        Args:
            sql: SQL查询语句
            params: 参数元组
            max_retries: 最大重试次数

        Returns:
            查询结果
        """
        original_max = self.max_retries
        self.max_retries = max_retries
        try:
            return self.execute_query(sql, params)
        finally:
            self.max_retries = original_max

    def check_connection(self) -> bool:
        """
        检查数据库连接是否正常

        Returns:
            连接正常返回True，否则返回False
        """
        try:
            result = self.execute_query("SELECT 1 as test")
            return len(result) > 0 and result[0]['test'] == 1
        except Exception:
            return False

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取表结构信息

        Args:
            table_name: 表名

        Returns:
            字段信息列表
        """
        sql = """
        SELECT
            COLUMN_NAME as column_name,
            DATA_TYPE as data_type,
            COLUMN_TYPE as column_type,
            IS_NULLABLE as is_nullable,
            COLUMN_KEY as column_key,
            COLUMN_DEFAULT as column_default,
            EXTRA as extra,
            COLUMN_COMMENT as column_comment
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """

        db_name = self.config.get('database', self.config.get('db_name', ''))
        return self.execute_query(sql, (db_name, table_name))

    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """
        获取表统计信息

        Args:
            table_name: 表名

        Returns:
            统计信息字典
        """
        sql = """
        SELECT
            TABLE_ROWS as row_count,
            AVG_ROW_LENGTH as avg_row_length,
            DATA_LENGTH as data_length,
            INDEX_LENGTH as index_length,
            TABLE_COMMENT as comment
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """

        db_name = self.config.get('database', self.config.get('db_name', ''))
        result = self.execute_query(sql, (db_name, table_name))

        if result:
            return result[0]
        return {}


class ConnectionPool:
    """简单的连接池实现（预留扩展）"""

    def __init__(self, config: Dict[str, Any], max_connections: int = 5):
        self.config = config
        self.max_connections = max_connections
        self._pool = []
        self._active = 0

    def get_connection(self) -> DBConnection:
        """从池中获取连接"""
        if self._pool:
            return self._pool.pop()
        elif self._active < self.max_connections:
            self._active += 1
            return DBConnection(self.config)
        else:
            raise Exception("连接池已满")

    def return_connection(self, conn: DBConnection):
        """归还连接到池"""
        if len(self._pool) < self.max_connections:
            self._pool.append(conn)


# 全局数据库实例（兼容旧版）
def init_db():
    """初始化数据库连接"""
    return DBConnection(DATABASE_CONFIG)


# 兼容旧代码的全局实例
db = init_db()


# 工具函数
def safe_execute_query(sql: str, params: Optional[tuple] = None,
                      default: Any = None) -> Any:
    """
    安全执行查询（捕获异常并返回默认值）

    Args:
        sql: SQL查询语句
        params: 参数元组
        default: 失败时返回的默认值

    Returns:
        查询结果或默认值
    """
    try:
        return db.execute_query(sql, params)
    except Exception as e:
        logger.error(f"安全查询失败: {e}")
        return default


def safe_execute_update(sql: str, params: Optional[tuple] = None,
                       default: int = 0) -> int:
    """
    安全执行更新（捕获异常并返回默认值）

    Args:
        sql: SQL更新语句
        params: 参数元组
        default: 失败时返回的默认值

    Returns:
        影响行数或默认值
    """
    try:
        return db.execute_update(sql, params)
    except Exception as e:
        logger.error(f"安全更新失败: {e}")
        return default


__all__ = [
    'DBConnection',
    'ConnectionPool',
    'db',
    'init_db',
    'safe_execute_query',
    'safe_execute_update',
]