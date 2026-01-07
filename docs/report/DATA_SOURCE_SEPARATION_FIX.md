# 数据源分离问题修复说明

## 问题背景

用户指出：
> 注意000300.SH只在stock_database.index_daily_zzsz数据库中有数据，而stock_database.daily_kline数据库中只有个股数据，没有000300.SH数据

## 数据源分析

### 当前数据库结构

```sql
-- daily_kline: 个股数据
SELECT COUNT(*) FROM daily_kline WHERE trade_date = '20240628';
-- 结果: ~5000只股票

SELECT COUNT(*) FROM daily_kline WHERE ts_code = '000300.SH';
-- 结果: 0 (没有指数数据)

-- index_daily_zzsz: 指数数据
SELECT COUNT(*) FROM index_daily_zzsz WHERE ts_code = '000300.SH' AND trade_date = '20240628';
-- 结果: 1

-- index_basic: 指数基本信息
SELECT * FROM index_basic WHERE ts_code = '000300.SH';
-- 结果: 1条记录（沪深300基本信息）
```

### 问题根源

**数据源分离导致的问题**:

1. **个股数据源**: `daily_kline` (用于股票筛选和因子计算)
2. **指数数据源**: `index_daily_zzsz` (用于基准收益计算)

**潜在风险**:
- 两个表的交易日可能不完全一致
- `daily_kline` 中的交易日可能在 `index_daily_zzsz` 中不存在
- 反之亦然

## 修复方案

### 原始代码问题

```python
# 原始代码
def get_benchmark_return(self, rebalance_date: str) -> float:
    # 使用daily_kline的get_nearest_trading_day
    actual_rebalance_date = self.get_nearest_trading_day(rebalance_date)

    # 但查询index_daily_zzsz
    sql = "SELECT close FROM index_daily_zzsz WHERE trade_date = %s"
    # 如果actual_rebalance_date在index_daily_zzsz中不存在，查询失败
```

### 修复版代码

```python
def get_benchmark_return_fixed(self, current_date: str, next_rebalance_date: str) -> float:
    """
    修复: 为指数数据单独处理日期
    """

    # 1. 为指数数据定义专门的日期查找函数
    def get_nearest_index_day(date: str) -> str:
        """在index_daily_zzsz中查找最近的交易日"""
        # 先往前找
        sql = """
        SELECT trade_date FROM index_daily_zzsz
        WHERE ts_code = %s AND trade_date <= %s
        ORDER BY trade_date DESC LIMIT 1
        """
        data = db.execute_query(sql, (self.benchmark, date))
        if data:
            return data[0]['trade_date']

        # 往后找
        sql = """
        SELECT trade_date FROM index_daily_zzsz
        WHERE ts_code = %s AND trade_date >= %s
        ORDER BY trade_date ASC LIMIT 1
        """
        data = db.execute_query(sql, (self.benchmark, date))
        if data:
            return data[0]['trade_date']

        return date

    # 2. 分别处理两个日期
    actual_current = get_nearest_index_day(current_date)
    actual_next = get_nearest_index_day(next_rebalance_date)

    # 3. 计算基准收益
    sql = """
    SELECT trade_date, close FROM index_daily_zzsz
    WHERE ts_code = %s AND trade_date IN (%s, %s)
    ORDER BY trade_date
    """
    data = db.execute_query(sql, (self.benchmark, actual_current, actual_next))

    if len(data) >= 2:
        return data[1]['close'] / data[0]['close'] - 1
```

## 关键改进点

### 1. 数据源分离处理

| 数据类型 | 数据表 | 处理函数 | 说明 |
|---------|--------|---------|------|
| 个股数据 | daily_kline | get_nearest_trading_day() | 用于股票筛选、因子计算 |
| 指数数据 | index_daily_zzsz | get_nearest_index_day() | 用于基准收益计算 |

### 2. 日期对齐策略

```python
# 投资组合收益计算
投资组合收益 = get_next_month_return_fixed(current_date, next_rebalance_date)
# 使用: daily_kline中的个股数据

# 基准收益计算
基准收益 = get_benchmark_return_fixed(current_date, next_rebalance_date)
# 使用: index_daily_zzsz中的指数数据

# 两者使用相同的逻辑: 从current_date到next_rebalance_date
```

### 3. 容错处理

```python
def get_nearest_index_day(date: str) -> str:
    # 如果date在index_daily_zzsz中不存在
    # 1. 先往前找最近的交易日
    # 2. 如果往前没有，往后找
    # 3. 如果都没有，返回原日期（后续会处理错误）
```

## 验证方法

### 验证1: 检查所有调仓日期在两个表中都存在

```python
rebalance_dates = ['20240628', '20240731', '20240830', '20240930',
                   '20241031', '20241129', '20241231']

for date in rebalance_dates:
    # 检查daily_kline
    sql1 = "SELECT COUNT(*) FROM daily_kline WHERE trade_date = %s"
    count1 = db.execute_query(sql1, (date,))[0]['cnt']

    # 检查index_daily_zzsz
    sql2 = "SELECT COUNT(*) FROM index_daily_zzsz WHERE ts_code = '000300.SH' AND trade_date = %s"
    count2 = db.execute_query(sql2, (date,))[0]['cnt']

    print(f"{date}: 个股={count1}, 指数={count2}")
```

### 验证2: 检查时间对齐

```python
# 对于每个调仓期，验证:
# - 投资组合持仓周期 = 基准收益周期
# - 两者都使用相同的起始和结束日期
```

## 修复文件

**文件**: `/home/zcy/alpha006_20251223/scripts/run_six_factor_backtest_fixed.py`

**关键修改**:
1. `get_benchmark_return_fixed()` - 添加指数数据专用日期处理
2. `get_nearest_trading_day()` - 添加注释说明仅用于个股
3. `get_next_month_return_fixed()` - 使用下个调仓日而非次日

## 运行验证

```bash
# 运行修复版回测
python3 /home/zcy/alpha006_20251223/scripts/run_six_factor_backtest_fixed.py

# 预期结果:
# 1. 7个调仓期全部包含
# 2. 所有周期时间对齐
# 3. 基准收益计算正常
```

## 总结

**核心问题**: 数据源分离导致日期不一致
**解决方案**: 为指数数据单独处理日期查找
**验证重点**: 确保所有7个调仓期都能正常计算

修复后的代码能够正确处理数据源分离的情况，确保回测结果的准确性。
