# alpha_peg因子回测指南

**文档版本**: v1.0
**创建日期**: 2025-12-24
**回测周期**: 20250101 ~ 20250630

---

## 一、回测概述

### 1.1 回测目标
基于分行业优化的alpha_peg因子，在2025年1月1日至6月30日期间进行完整回测，验证因子有效性。

### 1.2 核心参数
| 参数 | 值 | 说明 |
|------|------|------|
| **因子版本** | 行业优化版 | 分行业计算 + 3σ异常值处理 |
| **时间范围** | 20250101 ~ 20250630 | 6个月数据 |
| **持有期** | 10天 | T+1买入，持有10天卖出 |
| **交易成本** | 0.35% (单边) | 佣金0.05% + 印花税0.2% + 滑点0.1% |
| **基准指数** | 沪深300 (000300.SH) | 市场基准 |
| **分层数量** | 5层 | Q1(低) ~ Q5(高) |

---

## 二、数据提取

### 2.1 数据源
```python
# 1. PE数据 (daily_basic)
SELECT ts_code, trade_date, pe_ttm
FROM daily_basic
WHERE trade_date >= '20250101' AND trade_date <= '20250630'
  AND pe_ttm IS NOT NULL AND pe_ttm > 0

# 2. 财务数据 (fina_indicator)
SELECT ts_code, ann_date, dt_netprofit_yoy
FROM fina_indicator
WHERE ann_date >= '20250101' AND ann_date <= '20250630'
  AND update_flag = '1'
  AND dt_netprofit_yoy IS NOT NULL AND dt_netprofit_yoy != 0

# 3. 行业数据 (industry_cache.csv)
# 字段: ts_code, l1_name (申万一级行业)
```

### 2.2 时间对齐规则
```
daily_basic.trade_date = fina_indicator.ann_date
    ↓ 前向填充
每日交易日都有对应的dt_netprofit_yoy
```

**示例**:
```
20250102: 无财报公告 → 使用2024年报数据
20250115: 无财报公告 → 使用2024年报数据
20250130: 有财报公告 → 使用2024年报数据
20250131: 无财报公告 → 使用2024年报数据
...
20250430: 有一季报公告 → 更新为2025Q1数据
```

### 2.3 数据过滤规则
**保留条件**:
- `pe_ttm > 0` (正估值)
- `dt_netprofit_yoy != 0` (非零增长)
- `dt_netprofit_yoy` 非空

**跳过情况**:
- 企业亏损 (pe_ttm为空)
- 新股无历史财报
- 数据缺失

---

## 三、因子计算流程

### 3.1 分行业计算步骤

```python
# 步骤1: 数据关联
df_merged = pd.merge(
    df_pe,
    df_fina[['ts_code', 'ann_date', 'dt_netprofit_yoy']],
    left_on=['ts_code', 'trade_date'],
    right_on=['ts_code', 'ann_date'],
    how='left'
)

# 步骤2: 前向填充
df_merged['dt_netprofit_yoy_ffill'] = df_merged.groupby('ts_code')['dt_netprofit_yoy'].ffill()

# 步骤3: 合并行业
df_with_industry = df_merged.merge(industry_map, on='ts_code', how='left')

# 步骤4: 分行业计算
for industry, group in df_with_industry.groupby('l1_name'):
    # 基础计算
    group['alpha_peg_raw'] = group['pe_ttm'] / group['dt_netprofit_yoy']

    # 异常值处理 (3σ原则)
    threshold = get_industry_threshold(industry)  # 2.5~3.5σ
    mean_val = group['alpha_peg_raw'].mean()
    std_val = group['alpha_peg_raw'].std()

    lower = mean_val - threshold * std_val
    upper = mean_val + threshold * std_val

    # 缩尾处理
    group['alpha_peg_raw'] = group['alpha_peg_raw'].clip(lower, upper)

    # 最终因子
    group['alpha_peg'] = group['alpha_peg_raw']
```

### 3.2 行业特定阈值

| 行业类型 | 阈值 | 示例行业 | 原因 |
|----------|------|----------|------|
| **高成长** | 3.5σ | 电子, 电力设备, 医药生物, 计算机 | 容忍高波动 |
| **防御性** | 2.5σ | 银行, 公用事业, 交通运输 | 严格过滤 |
| **周期性** | 3.0σ | 有色金属, 煤炭, 钢铁 | 标准阈值 |
| **其他** | 3.0σ | 默认 | 标准阈值 |

### 3.3 输出字段
| 字段名 | 类型 | 说明 |
|--------|------|------|
| `ts_code` | str | 股票代码 |
| `trade_date` | str | 交易日期 |
| `l1_name` | str | 申万一级行业 |
| `pe_ttm` | float | 市盈率TTM |
| `dt_netprofit_yoy` | float | 扣非净利润增长率 |
| `alpha_peg` | float | PEG因子值 |

---

## 四、回测逻辑

### 4.1 信号生成
```
每日按alpha_peg因子值排序
分为5层 (Q1~Q5)
Q5: 因子值最高（可能被高估）
Q1: 因子值最低（可能被低估）
```

### 4.2 交易规则

**买入**:
- 信号日: T日 (因子计算日)
- 买入日: T+1日 (下一个交易日)
- 买入价格: 开盘价
- 限制: 不买入涨停股

**卖出**:
- 卖出日: T+11日 (持有10天)
- 卖出价格: 收盘价
- 限制:
  - 不卖出跌停股
  - 跌停则顺延最多2天

**交易成本**:
```
单边成本 = 佣金0.05% + 印花税0.2% + 滑点0.1% = 0.35%

买入成本: 0.15% (佣金+滑点)
卖出成本: 0.25% (佣金+印花税+滑点)
往返成本: 0.40%
```

### 4.3 收益计算

**单笔交易收益**:
```
收益率 = (卖出价 - 买入价) / 买入价 - 交易成本
```

**分层收益**:
```
每日每层收益 = 该层所有股票的平均收益率
```

**累计收益**:
```
累计收益 = (1 + 日收益).cumprod() - 1
```

---

## 五、评估指标

### 5.1 信息系数 (IC)

**计算方法**:
```
每日计算:
1. 获取当日所有股票的因子值
2. 获取未来10天的收益率
3. 计算Rank相关系数

Rank IC = corr(rank(因子值), rank(未来收益))
```

**评估标准**:
| IC值 | 评价 |
|------|------|
| > 0.10 | 优秀 |
| 0.05 ~ 0.10 | 良好 |
| 0 ~ 0.05 | 一般 |
| < 0 | 无效 |

**统计指标**:
- IC均值
- IC标准差
- IC显著性比例 (|IC|>0.05)

### 5.2 分层收益 (Quantile Returns)

**计算方法**:
```
每日按因子值分为5层
计算每层的平均收益
```

**评估标准**:
1. **单调性**: Q1 → Q5 收益应递增
2. **多空收益**: Q5 - Q1 > 0
3. **显著性**: Q5显著高于Q1

**示例**:
```
Q1: -0.5%  (低因子值)
Q2:  0.2%
Q3:  0.8%
Q4:  1.2%
Q5:  1.8%  (高因子值)

多空收益: 1.8% - (-0.5%) = 2.3%
单调性: ✓
```

### 5.3 累计收益 (Cumulative Returns)

**计算方法**:
```
Q5层每日平均收益 → 累计复利
vs 沪深300指数
```

**评估指标**:
- 总收益
- 年化收益
- 超额收益 (vs 基准)
- 最大回撤
- 夏普比率

### 5.4 交易统计

**核心指标**:
| 指标 | 计算公式 | 评估标准 |
|------|----------|----------|
| **胜率** | 盈利交易数 / 总交易数 | > 50% |
| **盈亏比** | 平均盈利 / 平均亏损 | > 1.0 |
| **交易次数** | 总交易数 | 越多越好 |
| **平均收益** | 总收益 / 交易次数 | > 0 |

---

## 六、重点行业分析

### 6.1 分析行业
**消费类**:
- 食品饮料
- 家用电器

**科技类**:
- 电子
- 电力设备
- 计算机

**周期类**:
- 机械设备
- 基础化工
- 有色金属

### 6.2 分析维度

**1. 行业IC表现**:
```
各行业独立计算IC
评估行业间因子有效性差异
```

**2. 行业内分层**:
```
在每个行业内独立分5层
计算行业内的多空收益
```

**3. 行业覆盖度**:
```
各行业股票数量
数据完整性
```

**4. 行业对比**:
```
消费 vs 科技 vs 周期
哪个行业因子表现最好？
```

---

## 七、运行指南

### 7.1 基础运行

```python
# 导入
from code.backtest_alpha_peg_industry import run_backtest

# 运行回测
results = run_backtest(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    quantiles=5,
    holding_days=10
)
```

### 7.2 参数调整

**调整异常值阈值**:
```python
results = run_backtest(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=2.5,  # 更严格
    quantiles=5,
    holding_days=10
)
```

**调整分层数量**:
```python
results = run_backtest(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    quantiles=3,  # 3层分组
    holding_days=10
)
```

**调整持有期**:
```python
results = run_backtest(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    quantiles=5,
    holding_days=5  # 缩短至5天
)
```

### 7.3 结果保存

回测自动保存以下文件:
```
results/
├── factor/
│   └── alpha_peg_industry_backtest_YYYYMMDD_HHMMSS.csv
├── backtest/
│   ├── ic_values_YYYYMMDD_HHMMSS.csv
│   ├── quantile_returns_YYYYMMDD_HHMMSS.csv
│   ├── cumulative_returns_YYYYMMDD_HHMMSS.csv
│   └── backtest_summary_YYYYMMDD_HHMMSS.txt
```

---

## 八、结果解读

### 8.1 因子有效性判断

**✅ 有效因子**:
- IC均值 > 0.05
- Q5收益 > Q1收益
- 多空组合(Q5-Q1)为正
- 胜率 > 50%
- 盈亏比 > 1.0

**⚠️ 需谨慎**:
- IC均值 0 ~ 0.05
- 分层收益不单调
- 胜率 45% ~ 50%

**❌ 无效因子**:
- IC均值 < 0
- Q5收益 < Q1收益
- 胜率 < 45%
- 盈亏比 < 1.0

### 8.2 示例解读

```
IC统计:
  Rank IC均值: 0.082  ✅ 良好
  IC显著性: 65%       ✅ 大部分显著

分层收益:
  Q1: 0.5%
  Q2: 0.8%
  Q3: 1.0%
  Q4: 1.3%
  Q5: 1.6%
  多空: 1.1%         ✅ 单调递增

交易统计:
  总交易: 1,234笔
  胜率: 54.2%        ✅ >50%
  盈亏比: 1.23       ✅ >1.0

结论: 因子有效，可继续优化
```

### 8.3 常见问题

**Q1: 为什么IC值很低？**
- 可能原因: 因子逻辑不成立、市场环境变化、数据质量问题
- 解决方案: 检查数据质量、调整参数、增加其他条件

**Q2: 为什么分层不单调？**
- 可能原因: 因子方向反了、异常值影响、样本量不足
- 解决方案: 反转因子、调整异常值阈值、增加样本

**Q3: 为什么胜率低？**
- 可能原因: 持有期过长、市场下跌、因子失效
- 解决方案: 缩短持有期、增加止损、重新设计因子

---

## 九、注意事项

### 9.1 数据质量
1. **完整性**: 确保数据覆盖目标时间段
2. **准确性**: 验证PE和增长率数据
3. **及时性**: 财报公告日是否准确

### 9.2 交易成本
1. **必须考虑**: 0.35%单边成本显著影响收益
2. **滑点**: 流动性差的股票滑点更大
3. **印花税**: 单边0.2%是固定成本

### 9.3 市场环境
1. **2025年1-6月**: 需关注市场整体走势
2. **行业轮动**: 不同行业表现差异
3. **政策影响**: 估值和成长性可能受政策影响

### 9.4 样本外验证
1. **回测≠实盘**: 历史表现不代表未来
2. **过拟合风险**: 避免过度优化参数
3. **持续监控**: 实盘需持续监控因子表现

---

## 十、扩展分析

### 10.1 可选优化方向

**1. 市值中性化**:
```python
# 增加市值因子
df['market_cap'] = get_market_cap()
df['alpha_peg_neutral'] = residual(alpha_peg ~ market_cap)
```

**2. 流动性过滤**:
```python
# 剔除流动性差的股票
df = df[df['turnover'] > 0.01]  # 日换手率>1%
```

**3. 动态持有期**:
```python
# 根据市场状态调整持有期
if market_state == 'bull':
    holding_days = 10
else:
    holding_days = 5
```

**4. 止损机制**:
```python
# 增加止损条件
if return < -0.05:  # 亏损5%止损
    sell_early()
```

### 10.2 对比实验建议

| 实验组 | 参数 | 目的 |
|--------|------|------|
| 基准 | outlier_sigma=3.0, holding_days=10 | 标准配置 |
| 严格 | outlier_sigma=2.5 | 测试严格过滤 |
| 宽松 | outlier_sigma=3.5 | 测试宽松过滤 |
| 短周期 | holding_days=5 | 测试短期表现 |
| 长周期 | holding_days=20 | 测试长期表现 |

---

## 附录

### A. 文件清单

**代码文件**:
- `code/backtest_alpha_peg_industry.py` - 回测主程序
- `code/calc_alpha_peg_industry.py` - 因子计算

**文档文件**:
- `docs/alpha_peg_backtest_guide.md` - 本指南
- `docs/factor_dictionary.md` - 因子字典
- `docs/alpha_peg_data_source.md` - 数据源说明

**结果文件**:
- `results/factor/` - 因子数据
- `results/backtest/` - 回测结果

### B. 快速参考

```python
# 完整回测
from code.backtest_alpha_peg_industry import run_backtest

results = run_backtest(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    quantiles=5,
    holding_days=10
)

# 查看结果
print(f"IC均值: {results['summary']['ic_mean']:.4f}")
print(f"数据量: {results['summary']['total_records']:,}")
```

### C. 联系方式

**项目维护**: Alpha006因子项目组
**更新日期**: 2025-12-24
**文档版本**: v1.0

---

**⚠️ 重要提示**: 回测结果仅供参考，投资有风险，入市需谨慎。
