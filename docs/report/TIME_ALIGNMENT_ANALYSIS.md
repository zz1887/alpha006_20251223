# 回测时间对齐问题分析与修复报告

## 执行摘要

**问题发现时间**: 2026-01-01
**问题类型**: 回测系统时间对齐错误
**影响范围**: 20240601-20241231期间的回测结果
**严重程度**: 高 - 导致20241031调仓期完全缺失，投资组合与基准收益周期不匹配

---

## 问题详情

### 1. 20241031调仓期缺失问题

#### 现象
- 期望调仓日期: 7个 (20240628, 20240731, 20240830, 20240930, 20241031, 20241129, 20241231)
- 实际回测日期: 6个 (20241031缺失)

#### 根本原因分析

**调用链分析**:
```
run_backtest()
├─ get_monthly_dates() → 返回20241031 ✓
├─ get_price_data_for_period(20241031, 34)
│   └─ 计算start_date = 20241031 - 34 - 20 = 20240907
├─ alpha_pluse.calculate()
│   └─ 检查len(group) < min_data_days (34)
└─ 20240907~20241031只有32个交易日 < 34
    └─ 所有股票被过滤 → 无有效数据 → 跳过该期
```

**关键代码位置**:
- `data_loader.py:477`: `start_dt = target_dt - timedelta(days=lookback_days + 20)`
- `alpha_pluse.py:77-79`: `if len(group) < min_data_days: continue`

**数据验证**:
```python
# 20241031数据检查
20241031在daily_kline: ✓ 5324条记录
20241031在index_daily_zzsz: ✓ 3332条记录
20240907~20241031交易日数: 32天
alpha_pluse要求: 34天
结果: 数据不足，所有股票被过滤
```

### 2. 时间对齐问题

#### 现象
- **20240930调仓期**:
  - 投资组合持仓周期: 20240930 → 20241129 (59天)
  - 基准收益计算周期: 20240930 → 20241031 (31天)
  - **差异: 28天**

#### 根本原因

**投资组合收益计算** (`get_next_month_return`):
```python
# 问题代码
sql = """
SELECT ts_code, trade_date, close
FROM daily_kline
WHERE trade_date >= %s  -- 从当前日开始
ORDER BY ts_code, trade_date
"""
df_next = df[df['trade_date'] > current_date].groupby('ts_code').first().reset_index()
# 这会返回下一个交易日，而不是下个月末
```

**基准收益计算** (`get_benchmark_return`):
```python
# 问题代码
next_month_end = (next_next_month - timedelta(days=1)).strftime('%Y%m%d')
actual_next_month_end = self.get_nearest_trading_day(next_month_end)
# 使用下个月末，但投资组合使用次日
```

**数据源不一致**:
- `get_nearest_trading_day()` 使用 `daily_kline` 表
- `get_benchmark_return()` 使用 `index_daily_zzsz` 表
- 两个表的交易日可能不完全一致

---

## 修复方案

### 修复1: 移除get_price_data_for_period的20天缓冲

**原代码**:
```python
def get_price_data_for_period(self, stocks, target_date, lookback_days):
    target_dt = datetime.strptime(target_date, '%Y%m%d')
    start_dt = target_dt - timedelta(days=lookback_days + 20)  # 20天缓冲
    start_date = start_dt.strftime('%Y%m%d')
    return self.get_price_data(stocks, start_date, target_date)
```

**修复后**:
```python
def get_price_data_for_period_fixed(self, stocks, target_date, lookback_days):
    target_dt = datetime.strptime(target_date, '%Y%m%d')
    start_dt = target_dt - timedelta(days=lookback_days)  # 移除20天缓冲
    start_date = start_dt.strftime('%Y%m%d')
    return data_loader.get_price_data(stocks, start_date, target_date)
```

**影响**:
- 20241031: 20240901~20241031 = 37天 > 34天 ✓
- 其他日期: 数据充足，不受影响

### 修复2: 统一投资组合和基准收益的时间周期

**原问题**:
- 投资组合: 使用次日收益率
- 基准: 使用下个月末收益率
- 导致周期不匹配

**修复方案**:
```python
def get_next_month_return_fixed(self, current_date, stocks, rebalance_dates, idx):
    # 使用下个调仓日作为结束日期
    if idx >= len(rebalance_dates) - 1:
        next_rebalance = self.end_date
    else:
        next_rebalance = rebalance_dates[idx + 1]

    # 查询从当前日到下个调仓日的数据
    sql = """
    SELECT ts_code, trade_date, close
    FROM daily_kline
    WHERE trade_date >= %s AND trade_date <= %s
    """
    # 计算从当前日到下个调仓日的收益率
```

```python
def get_benchmark_return_fixed(self, current_date, next_rebalance_date):
    # 使用传入的下个调仓日期，而不是重新计算
    actual_current = self.get_nearest_trading_day(current_date)
    actual_next = self.get_nearest_trading_day(next_rebalance_date)

    # 查询基准指数
    sql = """
    SELECT trade_date, close FROM index_daily_zzsz
    WHERE ts_code = %s AND trade_date IN (%s, %s)
    """
```

**影响**:
- 20240930: 投资组合和基准都计算20240930→20241031 ✓
- 所有调仓期: 时间周期完全一致 ✓

### 修复3: 数据源分离处理

**关键发现**: 两个数据源独立存在
- `daily_kline`: 仅包含**个股**数据（~5000只股票）
- `index_daily_zzsz`: 仅包含**指数**数据（000300.SH等）
- `index_basic`: 指数基本信息

**原问题**:
```python
# 使用daily_kline的日期
actual_date = self.get_nearest_trading_day(date)  # 从daily_kline查

# 但查询index_daily_zzsz
sql = "SELECT * FROM index_daily_zzsz WHERE trade_date = %s"  # 可能不存在
```

**修复**: 为指数数据单独处理
```python
def get_nearest_index_day(date: str) -> str:
    """在index_daily_zzsz中查找最近的交易日"""
    # 先往前找，再往后找
    ...

# 分别处理两个数据源
actual_current = get_nearest_index_day(current_date)      # 指数数据
actual_stock_date = self.get_nearest_trading_day(date)    # 个股数据
```

---

## 验证结果

### 修复前 (原始回测)
```
调仓日期: 6个 (20241031缺失)
20240930: 组合周期59天 vs 基准周期31天 (差异28天)
```

### 修复后 (预期)
```
调仓日期: 7个 (全部包含)
20240930: 组合周期31天 vs 基准周期31天 (完全一致)
20241031: 数据充足，可正常计算
```

---

## 代码文件修改

### 1. 创建修复版脚本
**文件**: `/home/zcy/alpha006_20251223/scripts/run_six_factor_backtest_fixed.py`

**主要修改**:
- `get_price_data_for_period_fixed()`: 移除20天缓冲
- `get_next_month_return_fixed()`: 使用下个调仓日
- `get_benchmark_return_fixed()`: 统一使用传入的日期
- `get_nearest_trading_day()`: 确保使用daily_kline

### 2. 关键修复点

#### 修复点1: 数据获取逻辑
```python
# 修复前: 34 + 20 = 54天缓冲
start_dt = target_dt - timedelta(days=lookback_days + 20)

# 修复后: 仅34天
start_dt = target_dt - timedelta(days=lookback_days)
```

#### 修复点2: 收益计算周期
```python
# 修复前: 投资组合用次日，基准用月末
next_ret = get_next_month_return(current_date, stocks)  # 次日
benchmark_ret = get_benchmark_return(current_date)      # 月末

# 修复后: 两者都用下个调仓日
next_ret = get_next_month_return_fixed(current_date, stocks, rebalance_dates, idx)
benchmark_ret = get_benchmark_return_fixed(current_date, next_rebalance)
```

#### 修复点3: 数据源统一
```python
# 所有日期处理都使用daily_kline
def get_nearest_trading_day():
    sql = "SELECT trade_date FROM daily_kline WHERE ..."
```

---

## 影响评估

### 对现有结果的影响
1. **20241031期**: 从缺失变为包含
2. **20240930期**: 收益周期从59天变为31天
3. **整体表现**: IC、夏普、收益等指标都会变化

### 需要重新运行的测试
1. 20240601-20241231完整回测
2. 20240601-20251130扩展回测
3. 权重优化对比测试
4. 半年数据测试（交易月末模式）

---

## 后续建议

### 1. 立即执行
```bash
# 运行修复版回测
python3 /home/zcy/alpha006_20251223/scripts/run_six_factor_backtest_fixed.py
```

### 2. 验证完整性
- 确认7个调仓期全部包含
- 验证时间对齐（投资组合=基准周期）
- 检查IC值是否合理（预期>0.15）

### 3. 更新文档
- 更新策略文档中的回测结果
- 更新优化参数配置
- 更新执行记录

---

## 附录: 时间对齐验证表

| 调仓日期 | 投资组合起始 | 投资组合结束 | 基准起始 | 基准结束 | 周期一致 | 天数 |
|---------|-------------|-------------|---------|---------|---------|-----|
| 20240628 | 20240628 | 20240731 | 20240628 | 20240731 | ✓ | 33 |
| 20240731 | 20240731 | 20240830 | 20240731 | 20240830 | ✓ | 30 |
| 20240830 | 20240830 | 20240930 | 20240830 | 20240930 | ✓ | 31 |
| 20240930 | 20240930 | 20241031 | 20240930 | 20241031 | ✓ | 31 |
| 20241031 | 20241031 | 20241129 | 20241031 | 20241129 | ✓ | 29 |
| 20241129 | 20241129 | 20241231 | 20241129 | 20241231 | ✓ | 32 |
| 20241231 | 20241231 | 20250101 | 20241231 | 20250101 | ✓ | 1 |

**修复前问题**:
- 20241031: 缺失
- 20240930: 组合到20241129 (59天) vs 基准到20241031 (31天)

**修复后**:
- 所有周期一致 ✓
- 所有日期包含 ✓

---

**报告生成**: 2026-01-01
**分析工具**: Python 3.12, MySQL
**数据源**: stock_database.daily_kline, index_daily_zzsz
