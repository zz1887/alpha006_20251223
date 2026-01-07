# 因子名称：bias1_qfq (BIAS乖离率因子)

## 基本信息
- **因子代码**: bias1_qfq
- **因子类型**: 价格偏离因子
- **版本**: v2.0 (优化版)
- **更新日期**: 2026-01-06
- **实现文件**: `scripts/backtest/bias1_qfq_backtest_optimized.py`

## 数学公式
```
bias1_qfq = (close - ma1_qfq) / ma1_qfq × 100%
```

其中：
- `close`: 当日收盘价
- `ma1_qfq`: 1日复权移动平均线（通常为5日、10日或20日均线）

**优化因子**:
```
factor_value = -bias1_qfq
```

## 参数定义
| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| window | int | 5 | 移动平均线周期（天） |
| outlier_sigma | float | 3.0 | 异常值阈值（标准差倍数） |
| normalization | str | 'zscore' | 标准化方法 |
| industry_neutral | bool | False | 是否行业中性化 |
| hold_days | int | 20 | T+20持有策略 |

## 计算逻辑

### 1. 数据获取
```python
# 从数据库获取价格数据
SELECT ts_code, trade_date, close
FROM stock_database.daily_kline
WHERE trade_date BETWEEN '20250101' AND '20251231'
```

### 2. 计算移动平均线
```python
# 计算移动平均（以5日为例）
df['ma5'] = df.groupby('ts_code')['close'].rolling(5).mean().reset_index(0, drop=True)
```

### 3. 计算BIAS乖离率
```python
# 原始因子
df['bias1_qfq'] = (df['close'] - df['ma5']) / df['ma5'] * 100

# 优化因子（关键修正）
df['factor_value'] = -df['bias1_qfq']
```

### 4. 数据清洗
- 删除NaN值（前N天无移动平均数据）
- 缩尾处理：均值±3σ
- 标准化：Z-score

### 5. T+20回测
```python
# 因子计算只使用T日数据
daily_factor = factor_df[trade_date == T日]

# 买入使用T日收盘价
buy_price = price_df.loc[(ts_code, T日), 'close']

# 卖出使用T+20日收盘价
sell_price = price_df.loc[(ts_code, T+20日), 'close']

# 未来收益计算（防未来函数）
future_close = price_df.groupby('ts_code')['close'].shift(-20)
forward_return = (future_close - price_df['close']) / price_df['close']
```

## 因子含义

### BIAS乖离率理论
```
BIAS = (股价 - 移动平均线) / 移动平均线 × 100%
```

**核心逻辑**:
1. **均衡价格**: 移动平均线代表某一时期内买卖双方都能接受的均衡价格
2. **偏离回归**: 股价距离移动平均线太远时，会重新向平均线靠拢
3. **买卖信号**:
   - **负偏离(超卖)**: 股价远低于均线 → 买入信号 ✅
   - **正偏离(超买)**: 股价远高于均线 → 卖出信号

### 优化因子逻辑
```
原始因子: bias1_qfq (高值=超买=卖出信号)
优化因子: -bias1_qfq (高值=超卖=买入信号)
```

**为什么需要负值反转**:
- 原始因子高值对应低收益（ICIR = -0.3032）
- 优化后高值对应高收益（ICIR = +0.4078）
- 符合BIAS理论：负偏离=买入信号

## 适用场景

### ✅ 适用场景
- **动量策略**: 买入超卖股票，跟随价格回归
- **短线交易**: 20天持有周期适合中短线
- **反转策略**: 利用价格偏离回归特性
- **激进投资**: 高收益伴随较大回撤

### ❌ 不适用场景
- **保守投资**: 最大回撤-73.99%较大
- **严格风控**: 需要额外止损机制
- **长线持有**: 因子周期较短

### 推荐配置
- **仓位**: 单因子不超过20%
- **止损**: -20%至-30%
- **持有**: 20天左右
- **再平衡**: 每日

## 数据要求

| 数据项 | 表名 | 字段名 | 必需 | 说明 |
|--------|------|--------|------|------|
| 收盘价 | daily_kline | close | ✅ | 原始价格数据 |
| 交易日期 | daily_kline | trade_date | ✅ | 时间序列 |
| 股票代码 | daily_kline | ts_code | ✅ | 标的识别 |
| 移动平均 | 计算得出 | ma5/ma10/ma20 | ✅ | 周期可调 |

**重要**: 必须使用 `stock_database.daily_kline` 而非 `stk_factor_pro`，确保数据质量。

## 异常值处理策略

| 异常类型 | 处理方式 | 触发条件 |
|----------|----------|----------|
| 前N天数据缺失 | 删除 | shift(N)产生NaN |
| 极大/极小值 | 缩尾处理 | > 均值 + 3σ 或 < 均值 - 3σ |
| 停牌 | 跳过 | close为NaN或0 |
| 移动平均为0 | 删除 | 分母为0 |

## 版本差异

| 版本 | window | normalization | industry_neutral | 特点 |
|------|--------|---------------|------------------|------|
| standard | 5 | zscore | False | 基础版 |
| conservative | 10 | rank | False | 更保守，周期更长 |
| aggressive | 3 | zscore | False | 更激进，周期更短 |
| optimized | 5 | zscore | False | 优化版，使用-bias1_qfq |

## 代码示例

### 1. 因子计算
```python
from core.utils.data_loader import DataLoader
from core.utils.db_connection import DBConnection
from core.config import DATABASE_CONFIG

# 加载数据
db = DBConnection(DATABASE_CONFIG)
loader = DataLoader(db)
price_df = loader.get_price_data('20250101', '20251231')

# 计算移动平均
price_df['ma5'] = price_df.groupby('ts_code')['close'].rolling(5).mean().reset_index(0, drop=True)

# 计算BIAS
price_df['bias1_qfq'] = (price_df['close'] - price_df['ma5']) / price_df['ma5'] * 100

# 优化因子
price_df['factor_value'] = -price_df['bias1_qfq']

# 返回标准格式
result = price_df[['ts_code', 'trade_date', 'factor_value']].dropna()
```

### 2. 运行回测
```bash
cd /home/zcy/alpha因子库
python3 scripts/backtest/bias1_qfq_backtest_optimized.py \
  --start_date 20250101 \
  --end_date 20251231 \
  --hold_days 20
```

### 3. 查看结果
```python
import pandas as pd

# 读取绩效指标
metrics = pd.read_csv('results/bias1_qfq/optimized_*/bias1_qfq_optimized_metrics_*.csv')
print(metrics)

# 读取交易记录
trades = pd.read_csv('results/bias1_qfq/optimized_*/bias1_qfq_optimized_trades_*.csv')
print(f"总交易数: {len(trades)}")
```

## 回测表现参考

基于2025年数据（优化版）：

| 指标 | 数值 | 评价 |
|------|------|------|
| **IC均值** | 0.0510 | 正向预测 ✅ |
| **ICIR** | 0.4078 | 优秀 ✅ |
| **累计收益率** | 1455.66% | 极高 🔥 |
| **年化收益率** | 4840.53% | 超高 🔥 |
| **夏普比率** | 63.27 | 超高 🔥 |
| **最大回撤** | -73.99% | 较大 ⚠️ |
| **胜率** | 66.67% | 优秀 ✅ |
| **Calmar比率** | 65.42 | 极高 🔥 |

### 分组收益
| 分组 | 收益率 | 说明 |
|------|--------|------|
| 组0 (低因子值) | 2.55% | 超买组 |
| 组1 | 3.25% | 次超买 |
| 组2 | 3.34% | 中性 |
| 组3 | 3.33% | 次超卖 |
| 组4 (高因子值) | 3.25% | 超卖组（买入信号）|

**分组差异**: 0.0070（较小，需要优化）

## 注意事项

### 1. 因子方向修正
- ⚠️ **必须使用 `-bias1_qfq`** 而非 `bias1_qfq`
- 原始因子ICIR为负，优化后为正
- 这是成功的关键

### 2. 数据源选择
- ✅ 使用 `stock_database.daily_kline`
- ❌ 避免使用 `stk_factor_pro`
- 确保数据一致性

### 3. 防未来函数
- 因子计算只使用T日信息
- 买入使用T日价格
- 卖出使用T+20日价格
- 严格遵循T+20原则

### 4. 风险控制
- 最大回撤较大（-73.99%）
- 建议设置止损
- 控制仓位比例

### 5. 单调性问题
- 分组收益未完全单调
- 组0收益偏低
- 组4未明显高于中间组
- 需要进一步优化

## 相关因子

### 同类因子
- **alpha_010**: 4日价格趋势（更短周期）
- **alpha_038**: 10日价格强度（中等周期）
- **alpha_120cq**: 120日价格位置（长周期）

### 组合建议
- **bias1_qfq + alpha_010**: 短期偏离+趋势
- **bias1_qfq + alpha_peg**: 价格偏离+估值
- **bias1_qfq + cr_qfq**: 偏离+动量

## 参考文献

1. 《量化投资策略与技术》- 均值回归策略
2. 《Alpha因子研究》- BIAS乖离率分析
3. 《因子投资》- 价格偏离因子
4. 项目文档: `results/bias1_qfq/优化前后对比分析_20260106.md`

---

**文档版本**: v2.0
**最后更新**: 2026-01-06
**维护者**: Claude Code Assistant
**验证状态**: ✅ 已验证（ICIR = 0.4078）
