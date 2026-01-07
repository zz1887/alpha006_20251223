"""数据库连接模块"""
import pymysql
from contextlib import contextmanager


class DBConnection:
    def __init__(self, config):
        self.config = config

    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = pymysql.connect(
            host=self.config['host'],
            port=self.config['port'],
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['db_name'],
            charset=self.config['charset']
        )
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, sql, params=None):
        """执行查询"""
        with self.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()

    def execute_update(self, sql, params=None):
        """执行更新"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                result = cursor.execute(sql, params or ())
                conn.commit()
                return result


# 数据库配置
DB_CONFIG = {
    "type": "mysql",
    "user": "root",
    "password": "12345678",
    "host": "172.31.112.1",  # Windows主机IP
    "port": 3306,
    "db_name": "stock_database",
    "charset": "utf8mb4"
}

# 全局数据库实例
db = DBConnection(DB_CONFIG)