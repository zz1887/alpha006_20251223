# Alpha101因子库

## 📋 概述

本目录包含从聚宽(JQData)导出的Alpha101因子库，已删除聚宽特定代码，保留因子的核心逻辑。

**版本**: v1.0
**更新日期**: 2026-01-03
**来源**: 聚宽Alpha101因子库

---

## 📁 目录结构

```
factors/alpha101/
├── README.md                    # 本文档
├── ALPHA101_REFERENCE.md        # 101个因子的详细参考文档
├── alpha101_base.py             # 因子计算框架
└── alpha101_usage_example.py    # 使用示例（可选）
```

---

## 🎯 因子统计

### 实现状态
- **已实现**: 77个因子
- **未实现**: 24个因子（需要行业中性化功能）

### 因子分类
| 类别 | 数量 | 示例因子 |
|------|------|----------|
| 趋势类 | 15 | Alpha_001, Alpha_009, Alpha_010, Alpha_019 |
| 量价关系 | 20 | Alpha_002, Alpha_003, Alpha_006, Alpha_012 |
| 波动率 | 8 | Alpha_001, Alpha_018, Alpha_022, Alpha_040 |
| 动量类 | 12 | Alpha_008, Alpha_019, Alpha_025, Alpha_039 |
| 其他 | 22 | Alpha_021, Alpha_028, Alpha_041, Alpha_101 |

---

## 🚀 快速开始

### 1. 基础使用

```python
from factors.alpha101.alpha101_base import calculate_alpha101_factors

# 指定股票代码和时间范围
ts_codes = ['000001.SZ', '000002.SZ', '600519.SH']
start_date = '20240101'
end_date = '20241231'

# 计算因子
result = calculate_alpha101_factors(
    ts_codes=ts_codes,
    start_date=start_date,
    end_date=end_date,
    output_path='/home/zcy/alpha006_20251223/results/factor/alpha101_factors.csv'
)

print(result.head())
```

### 2. 单个因子计算

```python
from factors.alpha101.alpha101_base import Alpha101Calculator

# 创建计算器
calculator = Alpha101Calculator(ts_codes, start_date, end_date)

# 获取单只股票数据
df = calculator.get_stock_data('000001.SZ')

# 计算特定因子
alpha_001 = calculator.alpha_001(df)
alpha_010 = calculator.alpha_010(df)
alpha_038 = calculator.alpha_038(df)

print(f"Alpha_001: {alpha_001.iloc[-1]:.4f}")
print(f"Alpha_010: {alpha_010.iloc[-1]:.4f}")
print(f"Alpha_038: {alpha_038.iloc[-1]:.4f}")
```

### 3. 批量计算特定因子

```python
# 只计算你关心的因子
selected_factors = ['alpha_001', 'alpha_010', 'alpha_038', 'alpha_101']

for ts_code in ts_codes:
    df = calculator.get_stock_data(ts_code)

    for factor_name in selected_factors:
        factor_func = getattr(calculator, factor_name)
        values = factor_func(df)
        # 使用因子值...
```

---

## 📊 数据需求

### 必需数据
| 数据类型 | 表名 | 字段 |
|---------|------|------|
| 价格数据 | daily_kline | ts_code, trade_date, open, high, low, close, volume |
| 日频基础 | daily_basic | ts_code, trade_date, turnover_rate, pe_ttm, etc. |
| 财务数据 | fina_indicator | ts_code, ann_date, net_profit, dt_netprofit_yoy, etc. |

### 衍生数据（自动计算）
- **收益率**: returns
- **平均成交量**: adv5, adv10, adv20, adv40, adv60, adv81, adv120, adv150, adv180
- **VWAP**: (close * volume) / volume

---

## 🔧 基础函数

Alpha101Calculator提供以下基础函数：

### 统计函数
- `rank(series)` - 排名
- `ts_rank(series, window)` - 时间序列排名
- `correlation(x, y, window)` - 滚动相关系数
- `covariance(x, y, window)` - 滚动协方差
- `stddev(series, window)` - 滚动标准差

### 时间序列函数
- `delta(series, period)` - 差分
- `delay(series, period)` - 滞后
- `ts_min(series, window)` - 滚动最小值
- `ts_max(series, window)` - 滚动最大值
- `sum(series, window)` - 滚动求和
- `decay_linear(series, window)` - 线性衰减

### 数学函数
- `scale(series)` - 标准化到[-1, 1]
- `sign(series)` - 符号函数
- `SignedPower(x, p)` - 带符号的幂运算
- `product(series, window)` - 滚动乘积

---

## 📖 因子参考

详细因子文档请查看 `ALPHA101_REFERENCE.md`，包含：
- 每个因子的Inputs
- 每个因子的Outputs
- 每个因子的公式

### 常用因子示例

#### Alpha_001 - 趋势强度
```
公式: (rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5)
用途: 捕捉趋势强度，负收益时看波动率，正收益时看价格
```

#### Alpha_010 - 价格动量
```
公式: rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : (-1*delta(close, 1)))))
用途: 4日价格动量，判断趋势方向
```

#### Alpha_038 - 价格强度
```
公式: ((-1* rank(Ts_Rank(close, 10)))* rank((close / open)))
用途: 结合10日排名和当日涨跌幅
```

#### Alpha_101 - 简单动量
```
公式: ((close - open) / ((high - low) + .001))
用途: 当日价格变动强度
```

---

## ⚠️ 注意事项

### 1. 未实现因子
24个因子未实现，主要原因是：
- 需要行业中性化功能（IndNeutralize）
- 涉及复杂的行业分类

如果需要这些因子，需要先实现行业中性化功能。

### 2. 数据质量
- 确保数据完整，无大量缺失
- 处理异常值（负值、极值）
- 注意停牌股票

### 3. 计算性能
- 因子计算涉及大量滚动计算，耗时较长
- 建议分批处理股票
- 可以使用多进程加速

### 4. 因子使用
- 建议进行标准化处理
- 检查因子有效性（IC, 分组收益）
- 考虑行业中性化

---

## 🔍 因子验证

### 1. 基础统计
```python
# 检查因子统计
print(result['alpha_001'].describe())
print(f"缺失值: {result['alpha_001'].isna().sum()}")
print(f"异常值: {(result['alpha_001'].abs() > 10).sum()}")
```

### 2. 因子IC计算
```python
# 计算未来收益
result['future_returns'] = result.groupby('ts_code')['close'].shift(-5) / result['close'] - 1

# 计算IC
ic = result.groupby('trade_date').apply(
    lambda x: x['alpha_001'].corr(x['future_returns'])
)

print(f"平均IC: {ic.mean():.4f}")
print(f"IC标准差: {ic.std():.4f}")
```

### 3. 分组测试
```python
# 分组统计
result['group'] = pd.qcut(result['alpha_001'], 5, labels=False)
group_stats = result.groupby('group')['future_returns'].mean()
print(group_stats)
```

---

## 📈 扩展建议

### 1. 自定义因子
可以基于Alpha101框架创建新因子：

```python
class MyAlphaCalculator(Alpha101Base):
    def my_custom_factor(self, df: pd.DataFrame) -> pd.Series:
        """自定义因子"""
        # 使用基础函数
        rank_close = self.rank(df['close'])
        delta_volume = self.delta(df['volume'], 5)

        # 返回因子值
        return rank_close * delta_volume
```

### 2. 因子组合
```python
# 简单组合
composite = (
    0.3 * calculator.alpha_001(df) +
    0.3 * calculator.alpha_010(df) +
    0.4 * calculator.alpha_038(df)
)
```

### 3. 行业中性化
```python
# 需要实现行业中性化
def industry_neutralize(factor: pd.Series, industry: pd.Series) -> pd.Series:
    """行业中性化"""
    # 按行业计算均值和标准差
    # 返回残差
    pass
```

---

## 📝 使用示例

### 完整回测流程

```python
from factors.alpha101.alpha101_base import calculate_alpha101_factors

# 1. 计算因子
print("步骤1: 计算Alpha101因子...")
factors = calculate_alpha101_factors(
    ts_codes=['000001.SZ', '000002.SZ', '600519.SH'],
    start_date='20240101',
    end_date='20241231',
    output_path='/home/zcy/alpha006_20251223/results/factor/alpha101_factors.csv'
)

# 2. 选择因子
selected_factors = ['alpha_001', 'alpha_010', 'alpha_038', 'alpha_101']
factor_data = factors[['ts_code', 'trade_date'] + selected_factors].copy()

# 3. 标准化
for col in selected_factors:
    factor_data[f'{col}_norm'] = factor_data.groupby('trade_date')[col].transform(
        lambda x: (x - x.mean()) / x.std()
    )

# 4. 计算综合得分
factor_data['score'] = (
    factor_data['alpha_001_norm'] +
    factor_data['alpha_010_norm'] +
    factor_data['alpha_038_norm'] +
    factor_data['alpha_101_norm']
)

# 5. 选股
factor_data['rank'] = factor_data.groupby('trade_date')['score'].rank(ascending=False)
top_stocks = factor_data[factor_data['rank'] <= 20]

print(f"每日选股数量: {len(top_stocks)}")
print(top_stocks.head())
```

---

## 🎯 推荐使用策略

### 1. 因子选择
推荐优先使用以下因子：
- **Alpha_001**: 趋势强度
- **Alpha_010**: 价格动量
- **Alpha_038**: 价格强度
- **Alpha_041**: 价量关系
- **Alpha_101**: 简单动量

### 2. 数据预处理
```python
# 1. 去除异常值
factors = factors[factors.abs() < 10]

# 2. 填充缺失
factors = factors.fillna(0)

# 3. 标准化
factors = (factors - factors.mean()) / factors.std()
```

### 3. 因子合成
```python
# 等权重合成
composite = (
    factors['alpha_001'] +
    factors['alpha_010'] +
    factors['alpha_038'] +
    factors['alpha_101']
) / 4
```

---

## 🔗 相关文档

- `ALPHA101_REFERENCE.md` - 因子详细参考
- `alpha101_base.py` - 源代码
- `../README.md` - 因子库整体说明

---

## 📞 技术支持

如有问题或建议：
1. 检查数据完整性
2. 查看因子公式文档
3. 验证基础函数实现
4. 测试单个因子计算

---

**文档版本**: v1.0
**最后更新**: 2026-01-03
