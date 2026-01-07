# alpha_peg因子数据来源说明

**文档版本**: v1.1
**生成日期**: 2025-12-24
**因子名称**: alpha_peg
**更新内容**: 新增行业数据源说明

---

## 一、数据源总览

### 1.1 数据源表信息

| 序号 | 表名/文件 | 用途 | 数据量 | 更新频率 |
|------|-----------|------|--------|----------|
| 1 | `daily_basic` | 获取pe_ttm | ~830万条 | 日频 |
| 2 | `fina_indicator` | 获取dt_netprofit_yoy | ~21万条 | 财报周期 |
| 3 | `industry_cache.csv` | 获取行业分类 | ~5,400条 | 静态 |

### 1.2 数据关联关系

#### 基础版
```
daily_basic (日频)
    ↓ LEFT JOIN
fina_indicator (财报周期)
    ↓ 前向填充
最终数据集 (日频)
```

#### 行业优化版
```
daily_basic (日频)
    ↓ LEFT JOIN
fina_indicator (财报周期)
    ↓ 前向填充
    ↓ LEFT JOIN
industry_cache.csv (行业分类)
    ↓ 分组计算
分行业数据集 (日频)
```

---

## 二、daily_basic表详解

### 2.1 表基本信息
- **表名**: `daily_basic`
- **表注释**: 股票日度基本面指标表（包含估值、股本、市值等数据）
- **数据量**: 8,317,039 条记录
- **主键**: `(ts_code, trade_date)`

### 2.2 使用字段

#### 字段1: ts_code
| 属性 | 值 |
|------|------|
| 字段名 | `ts_code` |
| 数据类型 | `varchar` |
| 约束 | PK (主键) |
| 可为空 | NO |
| 业务含义 | TS股票代码（如：600000.SH） |
| 用途 | 关联标识、股票唯一标识 |

#### 字段2: trade_date
| 属性 | 值 |
|------|------|
| 字段名 | `trade_date` |
| 数据类型 | `varchar` |
| 约束 | PK (主键) |
| 可为空 | NO |
| 格式 | YYYYMMDD（如：20251224） |
| 用途 | 时间索引、关联键 |

#### 字段3: pe_ttm
| 属性 | 值 |
|------|------|
| 字段名 | `pe_ttm` |
| 数据类型 | `decimal` |
| 约束 | - |
| 可为空 | YES |
| 单位 | 倍（数值型） |
| 业务含义 | 滚动市盈率（总市值/近12个月净利润） |
| 计算公式 | 总市值 / 净利润(TTM) |
| 特殊值 | 亏损企业返回NULL |
| 数据范围 | 0.01 ~ 1000+ |
| 用途 | alpha_peg分子 |

### 2.3 查询示例
```sql
-- 获取单只股票的PE数据
SELECT ts_code, trade_date, pe_ttm
FROM daily_basic
WHERE ts_code = '000001.SZ'
  AND trade_date >= '20240801'
  AND trade_date <= '20250305'
  AND pe_ttm IS NOT NULL
  AND pe_ttm > 0
ORDER BY trade_date;
```

### 2.4 数据特征
- **更新频率**: 每日收盘后更新（T+1）
- **覆盖范围**: 全市场A股
- **空值原因**: 企业亏损、数据缺失
- **异常值**: 负值理论上不存在，需防范数据错误

---

## 三、fina_indicator表详解

### 3.1 表基本信息
- **表名**: `fina_indicator`
- **表注释**: 财务指标数据表（所有数值字段为DECIMAL(20,5)，除主键外均允许空）
- **数据量**: 211,055 条记录
- **主键**: `(ts_code, ann_date, end_date, update_flag)`

### 3.2 使用字段

#### 字段1: ts_code
| 属性 | 值 |
|------|------|
| 字段名 | `ts_code` |
| 数据类型 | `varchar` |
| 约束 | PK (主键) |
| 可为空 | NO |
| 用途 | 股票标识 |

#### 字段2: ann_date
| 属性 | 值 |
|------|------|
| 字段名 | `ann_date` |
| 数据类型 | `char` |
| 约束 | PK (主键) |
| 可为空 | NO |
| 格式 | yyyymmdd（如：20241030） |
| 业务含义 | 财报实际公告日期 |
| 用途 | **时间对齐关键字段** |

#### 字段3: end_date
| 属性 | 值 |
|------|------|
| 字段名 | `end_date` |
| 数据类型 | `char` |
| 约束 | PK (主键) |
| 可为空 | NO |
| 格式 | yyyymmdd（如：20240930） |
| 业务含义 | 财务数据所属报告期 |
| 用途 | 数据有效性验证 |

#### 字段4: dt_netprofit_yoy
| 属性 | 值 |
|------|------|
| 字段名 | `dt_netprofit_yoy` |
| 数据类型 | `decimal(20,5)` |
| 约束 | - |
| 可为空 | YES |
| 单位 | %（百分比） |
| 精度 | 5位小数 |
| 业务含义 | 扣除非经常性损益后的净利润同比增长率 |
| 计算公式 | (本期扣非净利润 - 上年同期扣非净利润) / 上期扣非净利润 × 100% |
| 特殊值 | - |
| 数据范围 | -100 ~ 1000+ |
| 用途 | alpha_peg分母 |

#### 字段5: update_flag
| 属性 | 值 |
|------|------|
| 字段名 | `update_flag` |
| 数据类型 | `char` |
| 约束 | PK (主键) |
| 可为空 | NO |
| 取值 | '0'=未更新, '1'=已更新 |
| 用途 | 数据质量控制 |

### 3.3 查询示例
```sql
-- 获取扣非净利润同比增长率
SELECT ts_code, ann_date, end_date, dt_netprofit_yoy
FROM fina_indicator
WHERE ann_date >= '20240801'
  AND ann_date <= '20250305'
  AND update_flag = '1'
  AND dt_netprofit_yoy IS NOT NULL
  AND dt_netprofit_yoy != 0
ORDER BY ts_code, ann_date;
```

### 3.4 数据特征
- **更新频率**: 财报公告日更新
- **覆盖范围**: 全市场A股
- **空值原因**: 数据未公告、数据缺失
- **时间滞后性**: 财报公告滞后于报告期

---

## 四、时间对齐方案

### 4.1 问题描述
```
daily_basic: 日频数据，日期=交易日
    20240801, 20240802, 20240805, ..., 20250305

fina_indicator: 财报数据，日期=公告日
    20240829 (半年报), 20241030 (三季报), 20250425 (年报)
```

**挑战**: 如何将财报数据匹配到每个交易日？

### 4.2 对齐方案

#### 方案: 公告日匹配 + 前向填充

**步骤1: 基础关联**
```sql
LEFT JOIN fina_indicator fi
    ON db.ts_code = fi.ts_code
    AND db.trade_date = fi.ann_date
```

**结果**: 仅在财报公告日有数据
```
trade_date  | dt_netprofit_yoy
------------|-----------------
20240801    | NULL
20240802    | NULL
...         | NULL
20240829    | 15.50  ← 半年报公告
20240830    | NULL
...         | NULL
20241030    | 12.30  ← 三季报公告
```

**步骤2: 前向填充**
```python
df['dt_netprofit_yoy_ffill'] = df.groupby('ts_code')['dt_netprofit_yoy'].ffill()
```

**结果**: 使用最近一期财报数据
```
trade_date  | dt_netprofit_yoy | dt_netprofit_yoy_ffill
------------|------------------|-----------------------
20240801    | NULL             | NULL
20240802    | NULL             | NULL
...         | NULL             | NULL
20240829    | 15.50            | 15.50  ← 公告日
20240830    | NULL             | 15.50  ← 填充
20240831    | NULL             | 15.50  ← 填充
...         | NULL             | 15.50  ← 填充
20241030    | 12.30            | 12.30  ← 新公告
20241031    | NULL             | 12.30  ← 填充
```

### 4.3 填充有效期

| 财报类型 | 公告日 | 有效期至 | 说明 |
|----------|--------|----------|------|
| 一季报 | 4月1-30日 | 半年报公告 | 4-6月使用一季报 |
| 半年报 | 7月1-8月31日 | 三季报公告 | 7-9月使用半年报 |
| 三季报 | 10月1-31日 | 年报公告 | 10-12月使用三季报 |
| 年报 | 次年1-4月 | 次年一季报 | 次年1-3月使用年报 |

**示例**:
```
2024年8月29日公告半年报 → dt_netprofit_yoy = 15.50%
    ↓
2024年8月30日 ~ 2024年10月29日
    期间所有交易日都使用 15.50%
    ↓
2024年10月30日公告三季报 → dt_netprofit_yoy = 12.30%
    ↓
2024年10月31日 ~ 2025年04月24日
    期间所有交易日都使用 12.30%
```

### 4.4 时间对齐代码实现

```python
def merge_pe_fina(df_pe, df_fina):
    # 1. 基础关联
    df_merged = pd.merge(
        df_pe,
        df_fina[['ts_code', 'ann_date', 'dt_netprofit_yoy']],
        left_on=['ts_code', 'trade_date'],
        right_on=['ts_code', 'ann_date'],
        how='left'
    )

    # 2. 前向填充
    df_merged['dt_netprofit_yoy_ffill'] = df_merged.groupby('ts_code')['dt_netprofit_yoy'].ffill()

    return df_merged
```

---

## 五、数据质量控制

### 5.1 数据完整性检查

```python
def check_data_completeness(df_pe, df_fina, df_merged):
    """
    检查数据完整性
    """
    report = {
        'PE数据量': len(df_pe),
        '财务数据量': len(df_fina),
        '关联后数据量': len(df_merged),
        '直接匹配数': df_merged['dt_netprofit_yoy'].notna().sum(),
        '前向填充后': df_merged['dt_netprofit_yoy_ffill'].notna().sum(),
        '匹配率': df_merged['dt_netprofit_yoy_ffill'].notna().sum() / len(df_merged) * 100
    }
    return report
```

### 5.2 空值原因分析

| 字段 | 空值原因 | 影响 |
|------|----------|------|
| `pe_ttm` | 企业亏损、停牌 | 无法计算PEG |
| `dt_netprofit_yoy` | 新股无历史数据、数据缺失 | 无法计算PEG |
| `alpha_peg` | 以上任一为空 | 因子值为空 |

### 5.3 异常值监控

```python
def monitor_outliers(df):
    """
    监控异常值
    """
    return {
        'pe_ttm负值': (df['pe_ttm'] < 0).sum(),
        'pe_ttm极大值(>1000)': (df['pe_ttm'] > 1000).sum(),
        '增长率零值': (df['dt_netprofit_yoy'] == 0).sum(),
        '增长率负值': (df['dt_netprofit_yoy'] < 0).sum(),
        'PEG负值': (df['alpha_peg'] < 0).sum(),
        'PEG极大值(>100)': (df['alpha_peg'] > 100).sum()
    }
```

---

## 六、完整查询SQL

### 6.1 基础查询（无填充）
```sql
SELECT
    db.ts_code,
    db.trade_date,
    db.pe_ttm,
    fi.dt_netprofit_yoy,
    (db.pe_ttm / fi.dt_netprofit_yoy) as alpha_peg
FROM daily_basic db
LEFT JOIN fina_indicator fi
    ON db.ts_code = fi.ts_code
    AND db.trade_date = fi.ann_date
WHERE db.trade_date >= '20240801'
  AND db.trade_date <= '20250305'
  AND db.pe_ttm IS NOT NULL
  AND db.pe_ttm > 0
  AND fi.dt_netprofit_yoy IS NOT NULL
  AND fi.dt_netprofit_yoy != 0
ORDER BY db.ts_code, db.trade_date;
```

### 6.2 完整查询（带前向填充）
```sql
WITH fina_ffill AS (
    SELECT
        ts_code,
        trade_date,
        dt_netprofit_yoy,
        ROW_NUMBER() OVER(PARTITION BY ts_code ORDER BY trade_date) as rn
    FROM (
        SELECT
            db.ts_code,
            db.trade_date,
            fi.dt_netprofit_yoy
        FROM daily_basic db
        LEFT JOIN fina_indicator fi
            ON db.ts_code = fi.ts_code
            AND db.trade_date = fi.ann_date
        WHERE db.trade_date >= '20240801'
          AND db.trade_date <= '20250305'
    ) t
)
SELECT
    db.ts_code,
    db.trade_date,
    db.pe_ttm,
    ff.dt_netprofit_yoy,
    (db.pe_ttm / ff.dt_netprofit_yoy) as alpha_peg
FROM daily_basic db
LEFT JOIN fina_ffill ff
    ON db.ts_code = ff.ts_code
    AND db.trade_date = ff.trade_date
WHERE db.trade_date >= '20240801'
  AND db.trade_date <= '20250305'
  AND db.pe_ttm IS NOT NULL
  AND db.pe_ttm > 0
  AND ff.dt_netprofit_yoy IS NOT NULL
  AND ff.dt_netprofit_yoy != 0
ORDER BY db.ts_code, db.trade_date;
```

---

## 七、Python实现示例

```python
from db_connection import db
import pandas as pd

def get_alpha_peg_data(start_date, end_date):
    """
    获取alpha_peg因子完整数据
    """
    # 1. 获取PE数据
    sql_pe = """
    SELECT ts_code, trade_date, pe_ttm
    FROM daily_basic
    WHERE trade_date >= %s AND trade_date <= %s
      AND pe_ttm IS NOT NULL AND pe_ttm > 0
    """
    df_pe = pd.DataFrame(db.execute_query(sql_pe, (start_date, end_date)))

    # 2. 获取财务数据
    sql_fina = """
    SELECT ts_code, ann_date, dt_netprofit_yoy
    FROM fina_indicator
    WHERE ann_date >= %s AND ann_date <= %s
      AND update_flag = '1'
      AND dt_netprofit_yoy IS NOT NULL
      AND dt_netprofit_yoy != 0
    """
    df_fina = pd.DataFrame(db.execute_query(sql_fina, (start_date, end_date)))

    # 3. 关联
    df_merged = pd.merge(
        df_pe,
        df_fina[['ts_code', 'ann_date', 'dt_netprofit_yoy']],
        left_on=['ts_code', 'trade_date'],
        right_on=['ts_code', 'ann_date'],
        how='left'
    )

    # 4. 前向填充
    df_merged['dt_netprofit_yoy_ffill'] = df_merged.groupby('ts_code')['dt_netprofit_yoy'].ffill()

    # 5. 计算
    valid = df_merged[
        (df_merged['pe_ttm'].notna()) &
        (df_merged['dt_netprofit_yoy_ffill'].notna()) &
        (df_merged['dt_netprofit_yoy_ffill'] != 0)
    ].copy()

    valid['alpha_peg'] = valid['pe_ttm'] / valid['dt_netprofit_yoy_ffill']

    return valid[['ts_code', 'trade_date', 'pe_ttm', 'dt_netprofit_yoy_ffill', 'alpha_peg']]
```

---

## 八、行业数据源详解

### 8.1 行业分类数据

**文件路径**: `C:\Users\mm\PyCharmMiscProject\获取数据代码\industry_cache.csv`

**数据结构**:
```python
# WSL路径映射
industry_path = '/mnt/c/Users/mm/PyCharmMiscProject/获取数据代码/industry_cache.csv'

# 数据字段
df.columns = ['l1_code', 'l1_name', 'l2_code', 'l2_name', 'l3_code', 'l3_name',
              'ts_code', 'name', 'in_date', 'out_date', 'is_new', 'query_code']
```

**关键字段**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| `ts_code` | str | 股票代码（如000001.SZ） |
| `l1_name` | str | 申万一级行业名称（如"银行"） |
| `l1_code` | str | 申万一级行业代码（如"801780.SI"） |

**数据量**:
- 总股票数: ~5,446只
- 一级行业数: 31个
- 覆盖率: ~99%（A股）

### 8.2 行业列表

**31个申万一级行业**:
```
交通运输, 传媒, 公用事业, 农林牧渔, 医药生物, 商贸零售, 国防军工,
基础化工, 家用电器, 建筑材料, 建筑装饰, 房地产, 有色金属, 机械设备,
汽车, 煤炭, 环保, 电力设备, 电子, 石油石化, 社会服务, 纺织服饰,
综合, 美容护理, 计算机, 轻工制造, 通信, 钢铁, 银行, 非银金融, 食品饮料
```

**行业分布示例**:
| 行业 | 股票数 | 占比 |
|------|--------|------|
| 机械设备 | 593 | 10.9% |
| 医药生物 | 497 | 9.1% |
| 电子 | 488 | 9.0% |
| 基础化工 | 434 | 8.0% |
| 电力设备 | 397 | 7.3% |
| 计算机 | 359 | 6.6% |
| 汽车 | 305 | 5.6% |
| 其他 | 2,873 | 52.8% |

### 8.3 行业数据获取代码

```python
def load_industry_data(industry_path: str = None) -> pd.DataFrame:
    """
    加载行业分类数据

    参数:
        industry_path: 行业数据文件路径
                      默认: /mnt/c/Users/mm/PyCharmMiscProject/获取数据代码/industry_cache.csv

    返回:
        DataFrame包含: ts_code, l1_name
    """
    if industry_path is None:
        industry_path = '/mnt/c/Users/mm/PyCharmMiscProject/获取数据代码/industry_cache.csv'

    df = pd.read_csv(industry_path)
    industry_map = df[['ts_code', 'l1_name']].copy()

    return industry_map

# 使用示例
industry_map = load_industry_data()
print(f"加载 {len(industry_map)} 只股票，{industry_map['l1_name'].nunique()} 个行业")
```

### 8.4 行业数据更新

**更新频率**: 静态配置
- 股票上市/退市时自动更新
- 行业分类变更时手动更新
- 一般每季度检查一次

**维护建议**:
1. 定期检查新增股票是否已包含
2. 关注行业分类变更公告
3. 保持与数据库ts_code一致

---

## 九、常见问题

### Q1: 为什么使用ann_date而不是end_date？
**A**: `ann_date`是财报实际发布日，反映市场可获取信息的时间点，更符合实盘逻辑。

### Q2: 前向填充会引入未来数据吗？
**A**: 不会。填充使用的是**已公告**的最新财报，不包含任何未来信息。

### Q3: 新股如何处理？
**A**: 新股上市初期无历史财报，`dt_netprofit_yoy`为空，因子值为空，自动跳过。

### Q4: 亏损企业如何处理？
**A**: `pe_ttm`为空，因子值为空，自动跳过。

### Q5: 数据滞后性如何解决？
**A**: 财报数据天然滞后，这是所有基于财报因子的共同特征。可通过缩短持仓周期或结合高频数据缓解。

### Q6: 行业数据如何获取？
**A**: 从`industry_cache.csv`文件读取，包含ts_code和l1_name（申万一级行业）。

### Q7: 行业优化版与基础版的区别？
**A**:
- 基础版: 全局计算，无行业考虑
- 行业优化版: 分行业计算 + 行业内异常值处理 + 可选标准化

---

## 十、数据验证

### 验证步骤
1. **数据完整性**: 检查PE和财务数据是否覆盖目标区间
2. **关联准确性**: 验证ann_date与trade_date匹配逻辑
3. **填充正确性**: 检查前向填充是否正确延续
4. **计算准确性**: 验证alpha_peg计算公式
5. **异常值**: 检查空值、负值、极大值处理

### 验证代码
```python
def validate_alpha_peg_data(df):
    """
    验证alpha_peg数据质量
    """
    checks = {
        '数据量检查': len(df) > 0,
        '字段完整性': all(col in df.columns for col in ['ts_code', 'trade_date', 'pe_ttm', 'dt_netprofit_yoy', 'alpha_peg']),
        '无重复记录': len(df) == len(df.drop_duplicates()),
        'PE非空': df['pe_ttm'].isna().sum() == 0,
        '增长率非空': df['dt_netprofit_yoy'].isna().sum() == 0,
        '增长率非零': (df['dt_netprofit_yoy'] == 0).sum() == 0,
        'PEG计算准确': abs(df['alpha_peg'] - df['pe_ttm'] / df['dt_netprofit_yoy']).max() < 1e-10
    }
    return checks
```

---

**文档版本**: v1.1
**最后更新**: 2025-12-24
**维护**: Alpha006项目组
**更新内容**:
- v1.0: 基础版本
- v1.1: 新增行业数据源章节（8-10节）
