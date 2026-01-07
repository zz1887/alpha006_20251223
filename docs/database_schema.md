# Alpha006因子项目 - 数据库数据结构文档

**文档版本**: v1.0
**生成日期**: 2025-12-24
**数据库**: stock_database
**连接方式**: MySQL (172.31.112.1:3306)

---

## 📋 数据库表清单（共24张表）

| 序号 | 表名 | 表注释 | 行数 | 因子相关度 |
|------|------|--------|------|------------|
| 1 | **daily_kline** | 股票日线行情表（开盘/最高/最低/收盘价、成交量、涨跌幅等） | 7,043,800 | ⭐⭐⭐⭐⭐ |
| 2 | **stk_factor_pro** | 股票因子综合表（含价格、复权、技术指标等全量因子） | 6,519,389 | ⭐⭐⭐⭐⭐ |
| 3 | **daily_basic** | 股票日度基本面指标表（估值、股本、市值等） | 8,317,039 | ⭐⭐⭐⭐⭐ |
| 4 | **index_daily_zzsz** | 指数日线数据表（中证深证，用于基准对比） | 7,430,281 | ⭐⭐⭐⭐⭐ |
| 5 | **new_share** | 新股发行数据表（用于过滤新股） | N/A | ⭐⭐⭐⭐ |
| 6 | **stock_st** | 股票ST状态记录表（用于过滤ST股票） | 253,523 | ⭐⭐⭐⭐ |
| 7 | **cyq_chips** | 筹码分布表（成本价格及占比） | N/A | ⭐⭐⭐ |
| 8 | **cyq_perf** | 筹码因子表（历史高低价、成本分位、胜率等） | 8,116,678 | ⭐⭐⭐ |
| 9 | **moneyflow_ths** | 同花顺股票资金流数据（资金流入流出） | 952,776 | ⭐⭐⭐ |
| 10 | **fina_indicator** | 财务指标数据表（167个财务指标） | 211,055 | ⭐⭐ |
| 11 | **income** | 股票利润表数据 | 134,494 | ⭐⭐ |
| 12 | **balancesheet** | 股票资产负债表数据 | 138,025 | ⭐⭐ |
| 13 | **cashflow** | 股票现金流量表 | 134,708 | ⭐⭐ |
| 14 | **express** | 股票业绩快报表 | 15,760 | ⭐⭐ |
| 15 | **report_rc** | 股票研报预测数据表 | 429,198 | ⭐⭐ |
| 16 | **index_basic** | 指数基本信息表 | 13,754 | ⭐ |
| 17 | **moneyflow_cnt_ths** | 同花顺板块资金流统计表 | 94,772 | ⭐ |
| 18 | **moneyflow_ind_ths** | 同花顺行业板块资金流数据表 | 34,976 | ⭐ |
| 19 | **sw_index_daily** | 申万指数日线数据 | 391,543 | ⭐ |
| 20 | **sw_industry** | 申万行业表 | 10,446 | ⭐ |
| 21 | **limit_up_down_list** | 涨跌停列表 | 88,550 | ⭐ |
| 22 | **fina_indicator_custom** | 自定义财务指标 | 165,405 | ⭐ |
| 23 | **ths_moneyflow** | 同花顺资金流（未分类） | 920,266 | ⭐ |
| 24 | **bak_daily** | 股票日常交易数据备份表 | 6,636,909 | ⭐ |

---

## 🔑 核心表详细结构（因子代码编写必备）

### 1. daily_kline - 日线行情表

**表注释**: 股票日线行情表（含开盘/最高/最低/收盘价、成交量、涨跌幅等，保留3位小数）

| 字段名 | 数据类型 | 约束 | 可为空 | 默认值 | 业务含义 | 因子用途 |
|--------|----------|------|--------|--------|----------|----------|
| ts_code | varchar | PK | NO | - | 股票代码（如：000001.SZ、600000.SH） | 股票唯一标识 |
| trade_date | char | PK | NO | - | 交易日期（格式：yyyymmdd，如：20251030） | 时间序列索引 |
| open | decimal | - | NO | - | 开盘价（元，保留3位小数） | 价格计算 |
| high | decimal | - | NO | - | 最高价（元，保留3位小数） | 波动率计算 |
| low | decimal | - | NO | - | 最低价（元，保留3位小数） | 波动率计算 |
| close | decimal | - | NO | - | 收盘价（元，保留3位小数） | **核心价格字段** |
| pre_close | decimal | - | NO | - | 昨收价（除权价，前复权） | 涨跌幅计算 |
| change | decimal | - | NO | - | 涨跌额（元） | - |
| pct_chg | decimal | - | NO | - | 涨跌幅（%，保留3位小数） | - |
| vol | decimal | - | NO | - | 成交量（手，1手=100股） | **成交量计算** |
| amount | decimal | - | NO | - | 成交额（千元） | - |
| adj_factor | decimal | - | NO | 1.00000 | 复权因子（前复权/后复权） | 复权计算 |

**主键**: (ts_code, trade_date)
**索引**: ts_code, trade_date

---

### 2. stk_factor_pro - 股票因子综合表

**表注释**: 股票因子综合表（含价格、复权、技术指标等全量因子）

| 字段名 | 数据类型 | 约束 | 可为空 | 默认值 | 业务含义 | 因子用途 |
|--------|----------|------|--------|--------|----------|----------|
| ts_code | varchar | PK | NO | - | 股票代码 | 股票唯一标识 |
| trade_date | varchar | PK | NO | - | 交易日期（YYYYMMDD） | 时间索引 |
| close | double | - | YES | - | 收盘价 | **核心价格字段** |
| close_qfq | double | - | YES | - | 收盘价（前复权） | **推荐使用** |
| close_hfq | double | - | YES | - | 收盘价（后复权） | - |
| turnover_rate_f | double | - | YES | - | 换手率（自由流通股） | **核心换手率字段** |
| volume_ratio | double | - | YES | - | 量比 | - |
| atr_bfq | double | - | YES | - | 真实波动N日平均值（N=20） | **核心波动率字段** |
| atr_hfq | double | - | YES | - | 真实波动N日平均值（后复权） | - |
| atr_qfq | double | - | YES | - | 真实波动N日平均值（前复权） | - |
| ma_qfq_5 | double | - | YES | - | 5日简单移动平均（前复权） | **价格趋势确认** |
| ma_qfq_10 | double | - | YES | - | 10日简单移动平均（前复权） | 趋势判断 |
| ma_qfq_20 | double | - | YES | - | 20日简单移动平均（前复权） | 趋势判断 |
| ma_qfq_60 | double | - | YES | - | 60日简单移动平均（前复权） | 长期趋势 |
| ema_qfq_5 | double | - | YES | - | 5日指数移动平均（前复权） | - |
| ema_qfq_20 | double | - | YES | - | 20日指数移动平均（前复权） | - |
| macd_qfq | double | - | YES | - | MACD指标（前复权） | - |
| macd_dif_qfq | double | - | YES | - | MACD DIF（前复权） | - |
| macd_dea_qfq | double | - | YES | - | MACD DEA（前复权） | - |
| rsi_qfq_6 | double | - | YES | - | RSI 6日（前复权） | - |
| rsi_qfq_12 | double | - | YES | - | RSI 12日（前复权） | - |
| rsi_qfq_24 | double | - | YES | - | RSI 24日（前复权） | - |
| kdj_qfq | double | - | YES | - | KDJ指标（前复权） | - |
| kdj_k_qfq | double | - | YES | - | KDJ K值（前复权） | - |
| kdj_d_qfq | double | - | YES | - | KDJ D值（前复权） | - |
| boll_mid_qfq | double | - | YES | - | BOLL中轨（前复权） | - |
| boll_upper_qfq | double | - | YES | - | BOLL上轨（前复权） | - |
| boll_lower_qfq | double | - | YES | - | BOLL下轨（前复权） | - |
| obv_qfq | double | - | YES | - | 能量潮（前复权） | - |
| ... | ... | ... | ... | ... | ... | ... |

**主键**: (ts_code, trade_date)
**字段数量**: 261个
**推荐字段**: close_qfq, turnover_rate_f, atr_qfq, ma_qfq_5/10/20/60

---

### 3. daily_basic - 日度基本面指标表

**表注释**: 股票日度基本面指标表（包含估值、股本、市值等数据）

| 字段名 | 数据类型 | 约束 | 可为空 | 默认值 | 业务含义 | 因子用途 |
|--------|----------|------|--------|--------|----------|----------|
| ts_code | varchar | PK | NO | - | TS股票代码 | 股票唯一标识 |
| trade_date | varchar | PK | NO | - | 交易日期（YYYYMMDD） | 时间索引 |
| close | decimal | - | YES | - | 当日收盘价 | 价格参考 |
| turnover_rate | decimal | - | YES | - | 换手率（%） | 备用换手率 |
| turnover_rate_f | decimal | - | YES | - | 换手率（自由流通股） | **核心换手率字段** |
| volume_ratio | decimal | - | YES | - | 量比 | - |
| pe | decimal | - | YES | - | 市盈率（总市值/净利润） | 估值过滤 |
| pe_ttm | decimal | - | YES | - | 市盈率（TTM） | 估值过滤 |
| pb | decimal | - | YES | - | 市净率 | 估值过滤 |
| ps | decimal | - | YES | - | 市销率 | 估值过滤 |
| dv_ratio | decimal | - | YES | - | 股息率（%） | - |
| total_share | decimal | - | YES | - | 总股本（万股） | 市值计算 |
| float_share | decimal | - | YES | - | 流通股本（万股） | 流通市值 |
| free_share | decimal | - | YES | - | 自由流通股本（万） | **换手率计算基准** |
| total_mv | decimal | - | YES | - | 总市值（万元） | 市值过滤 |
| circ_mv | decimal | - | YES | - | 流通市值（万元） | 流通市值 |

**主键**: (ts_code, trade_date)
**推荐字段**: turnover_rate_f, free_share

---

### 4. index_daily_zzsz - 指数日线数据表

**表注释**: 指数日线数据表（中证深证）

| 字段名 | 数据类型 | 约束 | 可为空 | 默认值 | 业务含义 | 因子用途 |
|--------|----------|------|--------|--------|----------|----------|
| ts_code | varchar | PK | NO | - | TS指数代码（如000300.SH） | 基准标识 |
| trade_date | varchar | PK | NO | - | 交易日期（YYYYMMDD） | 时间索引 |
| close | decimal | - | YES | - | 收盘点位 | **基准收益率计算** |
| open | decimal | - | YES | - | 开盘点位 | - |
| high | decimal | - | YES | - | 最高点位 | - |
| low | decimal | - | YES | - | 最低点位 | - |
| pre_close | decimal | - | YES | - | 昨日收盘点 | - |
| change | decimal | - | YES | - | 涨跌点 | - |
| pct_chg | decimal | - | YES | - | 涨跌幅（%） | - |
| vol | decimal | - | YES | - | 成交量 | - |
| amount | decimal | - | YES | - | 成交额 | - |

**主键**: (ts_code, trade_date)
**常用指数**: 000300.SH (沪深300), 000001.SH (上证指数)

---

### 5. new_share - 新股发行数据表

**表注释**: 新股发行数据表（含发行总量、价格、中签率等）

| 字段名 | 数据类型 | 约束 | 可为空 | 默认值 | 业务含义 | 因子用途 |
|--------|----------|------|--------|--------|----------|----------|
| ts_code | varchar | PK | NO | - | TS股票代码 | 股票标识 |
| sub_code | varchar | - | NO | - | 申购代码 | - |
| name | varchar | - | NO | - | 新股名称 | - |
| ipo_date | char | - | NO | - | 上网发行日期（yyyymmdd） | - |
| issue_date | char | - | NO | - | 上市日期（yyyymmdd） | **过滤新股** |
| amount | decimal | - | NO | - | 发行总量（万股） | - |
| price | decimal | - | NO | - | 发行价格（元/股） | - |
| pe | decimal | - | NO | - | 市盈率（倍） | - |
| ballot | decimal | - | NO | - | 中签率（%） | - |

**主键**: ts_code
**用途**: 过滤上市不足1年的新股

---

### 6. stock_st - ST股票状态记录表

**表注释**: 股票ST状态记录表（trade_date为YYYYMMDD字符串）

| 字段名 | 数据类型 | 约束 | 可为空 | 默认值 | 业务含义 | 因子用途 |
|--------|----------|------|--------|--------|----------|----------|
| ts_code | varchar | PK | NO | - | 股票代码 | 股票标识 |
| name | varchar | - | NO | - | 股票名称 | - |
| trade_date | varchar | PK | NO | - | 交易日期（YYYYMMDD） | 时间索引 |
| type | varchar | - | NO | - | 类型标识（ST、*ST、DELIST等） | **ST标识** |
| type_name | varchar | - | NO | - | 类型名称（实施ST、撤销ST等） | - |

**主键**: (ts_code, trade_date)
**用途**: 过滤ST股票

---

### 7. cyq_perf - 筹码因子表

**表注释**: 股票因子表（含历史高低价、成本分位、胜率等因子）

| 字段名 | 数据类型 | 约束 | 可为空 | 默认值 | 业务含义 | 因子用途 |
|--------|----------|------|--------|--------|----------|----------|
| ts_code | varchar | PK | NO | - | 股票代码 | 股票标识 |
| trade_date | varchar | PK | NO | - | 交易日期（YYYYMMDD） | 时间索引 |
| his_low | double | - | YES | - | 历史最低价 | - |
| his_high | double | - | YES | - | 历史最高价 | - |
| cost_5pct | double | - | YES | - | 5分位成本 | **筹码支撑** |
| cost_15pct | double | - | YES | - | 15分位成本 | 筹码支撑 |
| cost_50pct | double | - | YES | - | 50分位成本 | 平均成本 |
| cost_85pct | double | - | YES | - | 85分位成本 | 压力位 |
| cost_95pct | double | - | YES | - | 95分位成本 | 强压力位 |
| weight_avg | double | - | YES | - | 加权平均成本 | 核心成本 |
| winner_rate | double | - | YES | - | 胜率 | **获利盘比例** |

**主键**: (ts_code, trade_date)
**用途**: 筹码分布分析

---

### 8. moneyflow_ths - 同花顺股票资金流数据

**表注释**: 同花顺股票资金流数据（适配高频交易资金特性）

| 字段名 | 数据类型 | 约束 | 可为空 | 默认值 | 业务含义 | 因子用途 |
|--------|----------|------|--------|--------|----------|----------|
| trade_date | varchar | PK | NO | - | 交易日期（YYYYMMDD） | 时间索引 |
| ts_code | varchar | PK | NO | - | 股票代码 | 股票标识 |
| name | varchar | - | NO | - | 股票名称 | - |
| pct_change | decimal | - | NO | - | 涨跌幅（%） | - |
| latest | decimal | - | NO | - | 最新价（元） | - |
| net_amount | decimal | - | NO | - | 资金净流入（万元） | **主力资金流向** |
| net_d5_amount | decimal | - | NO | - | 5日主力净额（万元） | 短期资金趋势 |
| buy_lg_amount | decimal | - | NO | - | 今日大单净流入额（万元） | 大单动向 |
| buy_lg_amount_rate | decimal | - | NO | - | 今日大单净流入占比（%） | - |
| buy_md_amount | decimal | - | NO | - | 今日中单净流入额（万元） | 中单动向 |
| buy_md_amount_rate | decimal | - | NO | - | 今日中单净流入占比（%） | - |
| buy_sm_amount | decimal | - | NO | - | 今日小单净流入额（万元） | 小单动向 |
| buy_sm_amount_rate | decimal | - | NO | - | 今日小单净流入占比（%） | - |

**主键**: (trade_date, ts_code)
**用途**: 资金流向分析

---

## 🎯 Alpha006因子核心字段汇总

### 必需字段（直接使用）

| 字段来源 | 字段名 | 用途 | 备注 |
|----------|--------|------|------|
| daily_kline | close | 收盘价 | 基础价格 |
| daily_kline | vol | 成交量 | 计算换手率 |
| stk_factor_pro | turnover_rate_f | 自由流通股换手率 | **核心换手率** |
| stk_factor_pro | atr_bfq/atr_qfq | 真实波动率（20日） | **核心波动率** |
| stk_factor_pro | close_qfq | 前复权收盘价 | 价格趋势 |
| stk_factor_pro | ma_qfq_5 | 5日均线 | 价格确认 |
| stk_factor_pro | ma_qfq_20 | 20日均线 | 趋势判断 |
| stk_factor_pro | ma_qfq_60 | 60日均线 | 长期趋势 |

### 辅助字段（过滤使用）

| 字段来源 | 字段名 | 用途 | 备注 |
|----------|--------|------|------|
| new_share | issue_date | 过滤新股 | 上市<365天 |
| stock_st | type | 过滤ST股票 | type='ST' |
| index_daily_zzsz | close | 基准收益率 | 000300.SH |
| daily_basic | free_share | 自由流通股本 | 换手率计算 |
| cyq_perf | cost_5pct/weight_avg | 筹码成本 | 可选 |
| moneyflow_ths | net_amount | 资金流向 | 可选 |

---

## 📊 数据量与更新频率

### 数据量统计
- **日线数据**: ~700万条（daily_kline）
- **因子数据**: ~650万条（stk_factor_pro）
- **基本面数据**: ~830万条（daily_basic）
- **指数数据**: ~740万条（index_daily_zzsz）

### 更新频率
- **日线数据**: 每日收盘后更新（T+1）
- **因子数据**: 每日收盘后更新（T+1）
- **基本面数据**: 每日更新
- **财务数据**: 季度/年度更新
- **新股数据**: 实时更新

### 数据时间范围
- **最早日期**: 2005年左右（取决于实际数据）
- **最新日期**: 2025年12月（当前）
- **推荐回测区间**: 2024-08-01 至 2025-03-05（已验证）

---

## 💻 SQL查询示例

### 示例1: 获取单只股票的因子数据
```sql
SELECT
    ts_code,
    trade_date,
    close_qfq,
    turnover_rate_f,
    atr_qfq,
    ma_qfq_5,
    ma_qfq_20,
    ma_qfq_60
FROM stk_factor_pro
WHERE ts_code = '000001.SZ'
  AND trade_date >= '20240801'
ORDER BY trade_date;
```

### 示例2: 批量获取多只股票的价格数据
```sql
SELECT
    ts_code,
    trade_date,
    close,
    vol
FROM daily_kline
WHERE ts_code IN ('000001.SZ', '600000.SH', '000001.SZ')
  AND trade_date >= '20240801'
ORDER BY ts_code, trade_date;
```

### 示例3: 过滤ST股票和新股
```sql
-- 获取非ST、上市满1年的股票
SELECT DISTINCT ts_code
FROM stk_factor_pro
WHERE ts_code NOT IN (
    SELECT ts_code FROM stock_st
    WHERE type = 'ST' AND trade_date >= '20240801'
)
AND ts_code NOT IN (
    SELECT ts_code FROM new_share
    WHERE issue_date >= '20240801'
);
```

### 示例4: 获取指数基准数据
```sql
SELECT
    trade_date,
    close,
    pct_chg
FROM index_daily_zzsz
WHERE ts_code = '000300.SH'
  AND trade_date >= '20240801'
ORDER BY trade_date;
```

### 示例5: Alpha006因子计算所需数据
```sql
SELECT
    fp.ts_code,
    fp.trade_date,
    fp.close_qfq,
    fp.turnover_rate_f,
    fp.atr_qfq,
    fp.ma_qfq_5,
    fp.ma_qfq_20,
    fp.ma_qfq_60,
    dk.vol,
    dk.amount
FROM stk_factor_pro fp
LEFT JOIN daily_kline dk
    ON fp.ts_code = dk.ts_code
    AND fp.trade_date = dk.trade_date
WHERE fp.trade_date >= '20240801'
  AND fp.trade_date <= '20250305'
ORDER BY fp.ts_code, fp.trade_date;
```

---

## ⚠️ 注意事项

### 1. 日期格式
- **daily_kline**: trade_date为char(8)，格式'yyyymmdd'（如'20251030'）
- **stk_factor_pro**: trade_date为varchar(8)，格式'YYYYMMDD'
- **index_daily_zzsz**: trade_date为varchar(8)，格式'YYYYMMDD'
- **建议**: 在Python中统一转换为datetime格式处理

### 2. 复权选择
- **推荐**: 使用 `close_qfq`（前复权）或 `close_hfq`（后复权）
- **避免**: 使用未复权的 `close`（会导致跳空缺口）
- **注意**: atr_qfq/ma_qfq 等带_qfq后缀的字段已复权

### 3. 换手率选择
- **推荐**: `turnover_rate_f`（自由流通股换手率）
- **备选**: `daily_basic.turnover_rate_f`
- **计算**: 成交量 / 自由流通股本

### 4. 波动率选择
- **推荐**: `atr_qfq`（前复权ATR，N=20）
- **备选**: `atr_bfq`（未复权ATR）
- **注意**: atr_qfq 已包含复权调整

### 5. 数据缺失处理
- **新股**: 上市前无数据，需过滤
- **停牌**: 停牌日无数据，需向前填充或跳过
- **ST**: 可能流动性差，建议过滤

### 6. 主键约束
- 所有表的主键都是 `(ts_code, trade_date)` 的组合
- 查询时务必使用这两个字段作为条件
- 避免笛卡尔积

---

## 🔧 数据库连接配置

```python
# code/db_connection.py
DB_CONFIG = {
    "type": "mysql",
    "user": "root",
    "password": "12345678",
    "host": "172.31.112.1",  # Windows主机IP（WSL2环境）
    "port": 3306,
    "db_name": "stock_database",
    "charset": "utf8mb4"
}
```

**连接测试**:
```python
from db_connection import db

# 测试连接
result = db.execute_query("SELECT COUNT(*) as cnt FROM daily_kline")
print(f"daily_kline记录数: {result[0]['cnt']:,}")
```

---

## 📈 因子开发建议

### 推荐数据源优先级
1. **stk_factor_pro** - 技术指标最全，已预计算
2. **daily_kline** - 原始价格数据，用于补充
3. **daily_basic** - 换手率备用源
4. **index_daily_zzsz** - 基准对比
5. **new_share + stock_st** - 过滤条件

### 性能优化建议
- 批量查询使用 IN 语句，分批处理（每批500只股票）
- 使用 trade_date 作为分区条件，减少扫描范围
- 避免全表扫描，务必带时间范围条件
- 复杂计算先在数据库预处理，再用Python分析

### 数据质量检查
```python
# 检查数据完整性
def check_data_quality():
    # 1. 检查缺失值
    sql = "SELECT COUNT(*) as missing FROM stk_factor_pro WHERE turnover_rate_f IS NULL"

    # 2. 检查异常值
    sql = "SELECT COUNT(*) as outliers FROM stk_factor_pro WHERE turnover_rate_f > 100"

    # 3. 检查日期连续性
    sql = """
        SELECT COUNT(DISTINCT trade_date) as date_count
        FROM stk_factor_pro
        WHERE trade_date BETWEEN '20240801' AND '20250305'
    """
```

---

**文档维护**: 本文档由程序自动生成，如数据库结构变更，请重新运行获取脚本更新。

**最后更新**: 2025-12-24
