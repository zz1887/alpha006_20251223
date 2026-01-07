"""获取数据库表结构信息"""
from db_connection import db


def get_all_tables():
    """获取所有表名"""
    sql = "SHOW TABLES"
    result = db.execute_query(sql)
    tables = [list(row.values())[0] for row in result]
    return tables


def get_table_structure(table_name):
    """获取表结构"""
    sql = f"DESCRIBE `{table_name}`"
    return db.execute_query(sql)


def get_table_sample_data(table_name, limit=5):
    """获取表的样例数据"""
    sql = f"SELECT * FROM `{table_name}` LIMIT {limit}"
    return db.execute_query(sql)


def inspect_database():
    """检查数据库结构"""
    tables = get_all_tables()
    print(f"数据库中的表: {tables}\n")

    for table in tables:
        print(f"表: {table}")
        print("-" * 50)

        # 表结构
        structure = get_table_structure(table)
        print("字段结构:")
        for field in structure:
            print(f"  {field['Field']}: {field['Type']} ({field['Null']}, {field['Key']})")

        # 样例数据
        sample = get_table_sample_data(table)
        if sample:
            print("\n样例数据:")
            for row in sample:
                print(f"  {row}")

        print("\n")


if __name__ == "__main__":
    inspect_database()