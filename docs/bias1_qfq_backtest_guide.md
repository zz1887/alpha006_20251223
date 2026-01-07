# Bias1 Qfq 因子回测指南

## 回测目的

对 `stock_database.stk_factor_pro.bias1_qfq` 因子进行完整的T+20回测验证，包括：
- ✅ 因子数据提取与处理
- ✅ T+20回测引擎实现
- ✅ 绩效指标计算（10+指标）
- ✅ 分组收益分析
- ✅ 交易记录生成

## 快速开始

### 基本回测

```bash
cd /home/zcy/alpha因子库
python run_bias1_qfq_backtest.py
```

### 自定义参数

```bash
# 指定时间范围
python run_bias1_qfq_backtest.py --start_date 20240101 --end_date 20241231

# 指定持有天数
python run_bias1_qfq_backtest.py --hold_days 20

# 完整自定义
python run_bias1_qfq_backtest.py --start_date 20240101 --end_date 20241231 --hold_days 20 --output_dir /path/to/output
```

## 回测逻辑详解

### 核心流程

```
1. 数据提取
   ├─ 从 stock_database.stk_factor_pro 提取 bias1_qfq
   ├─ 加载价格数据（开盘价、收盘价）
   └─ 加载基准指数（沪深300）

2. 每日再平衡
   ├─ 获取当日因子值
   ├─ 按因子值排序，选择前20%股票
   ├─ 等权重配置
   └─ 计算持仓

3. 交易执行
   ├─ T日开盘买入
   ├─ 持有N天（默认20天）
   ├─ T+N日收盘卖出
   └─ 扣除交易成本（0.154%）

4. 绩效计算
   ├─ 每日净值
   ├─ 收益指标
   ├─ 风险指标
   └─ 相对指标
```

### 交易成本模型

| 成本项 | 费率 | 说明 |
|--------|------|------|
| 佣金 | 0.05% | 双向收取 |
| 印花税 | 0.2% | 卖出时收取 |
| 过户费 | 0.004% | 双向收取 |
| 滑点 | 0.1% | 预估 |
| **总计** | **0.154%** | 单边成本 |

**注意**: 回测中按单边0.154%扣除（买入+卖出合计0.308%）

## 回测参数

### 默认参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 开始日期 | 20240101 | 回测起始时间 |
| 结束日期 | 20241231 | 回测结束时间 |
| 持有天数 | 20 | T+N卖出 |
| 选股比例 | 20% | 前20%股票 |
| 分组数量 | 5 | 分组分析用 |
| 交易成本 | 0.154% | 单边成本 |

### 参数说明

#### 持有天数 (hold_days)
- **T+20**: 默认值，平衡收益与换手
- **T+10**: 短线策略，换手率高
- **T+30**: 长线策略，换手率低
- **T+5**: 快速轮动，风险较高

#### 选股比例 (top_pct)
- **20%**: 默认值，分散风险
- **10%**: 集中持仓，收益波动大
- **30%**: 分散持仓，收益稳定

## 绩效指标详解

### 基础指标

```
累计收益率 (Total Return):
  - 策略期末价值 / 期初价值 - 1
  - 示例: 1.0640 = 6.40%

年化收益率 (Annualized Return):
  - (1 + 累计收益率)^(252/交易天数) - 1
  - 示例: 12.67%

超额收益 (Excess Return):
  - 策略收益 - 基准收益
  - 示例: 3.37% (策略6.40% - 基准3.03%)
```

### 风险指标

```
年化波动率 (Annualized Volatility):
  - 日收益标准差 × √252
  - 衡量收益波动程度
  - 示例: 10.27%

夏普比率 (Sharpe Ratio):
  - (年化收益 - 无风险利率) / 年化波动率
  - 无风险利率默认2%
  - 优秀: >1.5, 良好: >1.0, 一般: >0.5
  - 示例: 1.012

最大回撤 (Max Drawdown):
  - 累计净值从峰值的最大跌幅
  - 示例: -14.11%

Calmar比率 (Calmar Ratio):
  - 年化收益 / 最大回撤绝对值
  - 示例: 0.898
```

### 相对指标

```
信息比率 (Information Ratio):
  - 超额收益 / 超额波动率
  - 衡量主动管理能力
  - 示例: 0.678

胜率 (Win Rate):
  - 正收益交易次数 / 总交易次数
  - 示例: 54.20%

盈亏比 (Profit/Loss Ratio):
  - 平均盈利 / 平均亏损
  - 示例: 1.29

换手率 (Turnover):
  - 估算值: 252 / 持有天数
  - 示例: 12.6 (T+20)
```

## 输出文件

### 文件结构

```
results/bias1_qfq/
├── bias1_qfq_performance_{日期}.csv    # 每日回测数据
├── bias1_qfq_metrics_{日期}.csv        # 绩效指标
├── bias1_qfq_factor_{日期}.csv         # 因子数据
├── bias1_qfq_groups_{日期}.csv         # 分组收益
└── bias1_qfq_trades_{日期}.csv         # 交易记录
```

### 文件详解

#### 1. performance 文件
包含每日回测数据：
- `trade_date`: 交易日期
- `nav`: 策略净值
- `benchmark_nav`: 基准净值
- `daily_return`: 日收益率
- `benchmark_return`: 基准日收益
- `excess_return`: 超额收益
- `cumulative_return`: 累计收益
- `drawdown`: 回撤

#### 2. metrics 文件
包含绩效指标汇总：
- `总收益率`, `年化收益率`, `超额收益`
- `年化波动率`, `夏普比率`, `最大回撤`
- `信息比率`, `Calmar比率`, `胜率`
- `盈亏比`, `换手率`, `交易次数`

#### 3. factor 文件
包含使用的因子数据：
- `ts_code`: 股票代码
- `trade_date`: 交易日期
- `bias1_qfq`: 因子值
- `group`: 分组（1-5）

#### 4. groups 文件
包含分组收益分析：
- `group`: 分组编号
- `avg_return`: 平均收益
- `return_std`: 收益标准差
- `sample_count`: 样本数
- `cumulative_return`: 累计收益

#### 5. trades 文件
包含交易记录：
- `trade_date`: 交易日期
- `ts_code`: 股票代码
- `action`: 买入/卖出
- `price`: 交易价格
- `shares`: 持仓数量
- `value`: 交易金额

## 使用示例

### 示例1: 完整回测流程

```bash
# 1. 运行回测
cd /home/zcy/alpha因子库
python run_bias1_qfq_backtest.py --start_date 20240101 --end_date 20241231

# 2. 查看绩效指标
cat results/bias1_qfq/bias1_qfq_metrics_20240101_20241231_*.csv

# 3. 查看交易记录
cat results/bias1_qfq/bias1_qfq_trades_20240101_20241231_*.csv | head -20

# 4. 查看分组收益
cat results/bias1_qfq/bias1_qfq_groups_20240101_20241231_*.csv
```

### 示例2: 参数优化测试

```bash
# 测试不同持有天数
for days in 5 10 20 30 60; do
    echo "Testing hold_days=$days"
    python run_bias1_qfq_backtest.py --hold_days $days --start_date 20240101 --end_date 20240630
done

# 比较结果
ls -la results/bias1_qfq/bias1_qfq_metrics_*.csv
```

### 示例3: Python代码调用

```python
from scripts.backtest.bias1_qfq_backtest import Bias1QfqBacktest

# 创建回测实例
backtest = Bias1QfqBacktest(
    start_date='20240101',
    end_date='20241231',
    hold_days=20,
    output_dir='results/bias1_qfq'
)

# 运行回测
results = backtest.run()

# 访问结果
print(f"年化收益: {results['metrics']['年化收益率']:.4f}")
print(f"夏普比率: {results['metrics']['夏普比率']:.4f}")
print(f"最大回撤: {results['metrics']['最大回撤']:.4f}")

# 查看交易记录
trades = results['trades']
print(f"总交易次数: {len(trades)}")
```

## 结果解读

### 绩效判断标准

#### 优秀标准
```
✅ 年化收益 > 15%
✅ 夏普比率 > 1.5
✅ 最大回撤 < 15%
✅ 胜率 > 55%
✅ 信息比率 > 0.8
```

#### 良好标准
```
⚠️ 年化收益 10-15%
⚠️ 夏普比率 1.0-1.5
⚠️ 最大回撤 15-20%
⚠️ 胜率 50-55%
⚠️ 信息比率 0.5-0.8
```

#### 一般标准
```
⚠️ 年化收益 5-10%
⚠️ 夏普比率 0.5-1.0
⚠️ 最大回撤 20-25%
⚠️ 胜率 45-50%
⚠️ 信息比率 0.3-0.5
```

### 分组收益分析

#### 单调性检验
```
理想情况:
分组1 (低因子值): -0.005
分组2: -0.002
分组3: 0.001
分组4: 0.003
分组5 (高因子值): 0.006

判断: ✅ 严格单调递增
```

#### 分组差异
```
高分组收益 - 低分组收益 = 分组差异

优秀: > 2%
良好: 1-2%
一般: 0.5-1%
较差: < 0.5%
```

## 常见问题

### Q1: 回测结果为负收益

**可能原因**:
1. 因子在该时间段失效
2. 交易成本过高
3. 市场整体下跌

**排查方法**:
```bash
# 1. 检查基准收益
# 查看同期沪深300表现

# 2. 缩短时间范围测试
python run_bias1_qfq_backtest.py --start_date 20240601 --end_date 20241231

# 3. 调整持有天数
python run_bias1_qfq_backtest.py --hold_days 10
```

### Q2: 交易次数过少

**原因**: 持有天数过长或数据缺失

**解决**:
```python
# 检查数据完整性
# 减少持有天数
# 延长时间范围
```

### Q3: 换手率异常

**原因**: 持有天数设置问题

**计算**: 换手率 ≈ 252 / hold_days

**正常范围**:
- T+5: 50.4
- T+10: 25.2
- T+20: 12.6
- T+30: 8.4

## 进阶分析

### 1. 分时间段验证

```bash
# 验证2024年上半年
python run_bias1_qfq_backtest.py --start_date 20240101 --end_date 20240630

# 验证2024年下半年
python run_bias1_qfq_backtest.py --start_date 20240701 --end_date 20241231

# 比较两期表现
```

### 2. 不同持有天数对比

```python
from scripts.backtest.bias1_qfq_backtest import Bias1QfqBacktest

results = {}
for days in [5, 10, 20, 30, 60]:
    bt = Bias1QfqBacktest('20240101', '20241231', hold_days=days)
    results[days] = bt.run()['metrics']

# 找出最优持有天数
best_days = max(results.keys(), key=lambda x: results[x]['夏普比率'])
```

### 3. 行业维度分析

```python
# 在回测中添加行业筛选
# 分析不同行业的因子表现
```

## 技术细节

### 数据提取逻辑

```python
# 1. 提取因子数据
factor_sql = """
SELECT ts_code, trade_date, bias1_qfq
FROM stock_database.stk_factor_pro
WHERE trade_date BETWEEN %s AND %s
  AND bias1_qfq IS NOT NULL
ORDER BY trade_date, ts_code
"""

# 2. 提取价格数据
price_sql = """
SELECT ts_code, trade_date, open, close
FROM stock_database.daily
WHERE trade_date BETWEEN %s AND %s
ORDER BY trade_date, ts_code
"""
```

### 回测核心算法

```python
for date in trading_dates:
    # 1. 获取当日因子数据
    today_factor = factor_df[factor_df['trade_date'] == date]

    # 2. 按因子值排序，选择前20%
    selected = today_factor.nlargest(int(len(today_factor) * 0.2), 'bias1_qfq')

    # 3. 计算买入价格
    buy_prices = get_open_price(date, selected['ts_code'])

    # 4. 持有到T+N日
    sell_date = get_next_trading_date(date, hold_days)
    sell_prices = get_close_price(sell_date, selected['ts_code'])

    # 5. 计算收益（扣除成本）
    gross_return = (sell_prices - buy_prices) / buy_prices
    net_return = gross_return - transaction_cost
```

## 性能优化

### 1. 数据缓存
```python
# 避免重复查询数据库
# 使用pandas缓存机制
```

### 2. 向量化计算
```python
# 避免循环，使用pandas向量化操作
# 提高计算效率
```

### 3. 分批处理
```python
# 大数据量时分批处理
# 避免内存溢出
```

## 下一步行动

### 回测通过后
1. ✅ **参数优化**: 测试不同持有天数（5, 10, 20, 30, 60）
2. ✅ **时间段验证**: 验证多个时间段的一致性
3. ✅ **行业分析**: 分析不同行业的因子表现
4. ✅ **实盘模拟**: 进行模拟交易测试
5. ✅ **策略集成**: 与其他因子组合使用

### 回测不通过
1. ❌ 检查因子数据质量
2. ❌ 验证因子逻辑正确性
3. ❌ 尝试不同时间范围
4. ❌ 考虑因子优化或放弃

## 参考资料

### 相关文档
- `BIAS1_QFQ_FACTOR_GUIDE.md` - 完整使用指南
- `bias1_qfq_validation_guide.md` - 验证指南
- `WORK_COMPLETION_SUMMARY.md` - 工作完成总结

### 技术参考
- 因子评价标准（Barra模型）
- T+20回测最佳实践
- 交易成本模型

---

**最后更新**: 2026-01-05
**版本**: v1.0
**状态**: ✅ 完整可用
