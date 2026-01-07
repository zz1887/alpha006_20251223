# alpha_peg因子项目总结

**项目**: Alpha006因子项目 - alpha_peg因子开发
**日期**: 2025-12-24
**状态**: ✅ 开发完成

---

## 一、项目概述

### 1.1 项目目标
开发基于PE和成长性的估值因子 `alpha_peg`，用于股票筛选和量化策略。

### 1.2 核心公式
```
alpha_peg = pe_ttm / dt_netprofit_yoy
```

### 1.3 创新点
- ✅ **行业优化**: 分行业计算，避免行业间差异
- ✅ **异常值处理**: 行业内3σ原则 + 缩尾处理
- ✅ **可选标准化**: z-score/rank，支持跨行业比较
- ✅ **完整回测**: 含交易成本、基准对比、行业分析

---

## 二、开发历程

### 阶段1: 基础版开发 ✅
**时间**: 2025-12-24 上午
- 完成基础因子计算
- 实现数据关联逻辑
- 完成逻辑验证测试

**文件**:
- `code/calc_alpha_peg.py`
- `code/test_alpha_peg.py`
- `docs/alpha_peg_data_source.md`

### 阶段2: 行业优化版 ✅
**时间**: 2025-12-24 下午
- 实现分行业计算
- 添加行业特定规则
- 完成版本对比验证

**文件**:
- `code/calc_alpha_peg_industry.py`
- `code/compare_alpha_peg_versions.py`
- `docs/factor_dictionary.md` (新增行业优化章节)

### 阶段3: 回测框架 ✅
**时间**: 2025-12-24 晚上
- 实现完整回测逻辑
- 计算IC值、分层收益、累计收益
- 重点行业分析
- 可复现性验证

**文件**:
- `code/backtest_alpha_peg_industry.py`
- `code/verify_backtest.py`
- `docs/alpha_peg_backtest_guide.md`
- 更新 `README.md`

---

## 三、代码清单

### 核心代码
| 文件 | 功能 | 状态 |
|------|------|------|
| `calc_alpha_peg.py` | 基础版计算 | ✅ |
| `calc_alpha_peg_industry.py` | 行业优化版计算 | ✅ |
| `test_alpha_peg.py` | 逻辑验证 | ✅ |
| `compare_alpha_peg_versions.py` | 版本对比 | ✅ |
| `backtest_alpha_peg_industry.py` | 完整回测 | ✅ |
| `verify_backtest.py` | 结果验证 | ✅ |

### 文档清单
| 文档 | 内容 | 状态 |
|------|------|------|
| `alpha_peg_data_source.md` | 数据来源说明 | ✅ |
| `factor_dictionary.md` | 因子字典 | ✅ |
| `alpha_peg_quick_start.md` | 快速指南 | ✅ |
| `alpha_peg_comparison_report.md` | 版本对比 | ✅ |
| `alpha_peg_backtest_guide.md` | 回测指南 | ✅ |
| `alpha_peg_project_summary.md` | 项目总结 | ✅ |
| `database_schema.md` | 数据库结构 | ✅ |

---

## 四、功能特性

### 4.1 因子计算
```python
# 基础版
df = calc_alpha_peg(start_date, end_date)

# 行业优化版
df = calc_alpha_peg_industry(
    start_date, end_date,
    outlier_sigma=3.0,
    normalization=None  # 可选: 'zscore', 'rank'
)
```

**特性**:
- ✅ 时间对齐（交易日=公告日+前向填充）
- ✅ 行业分类（申万一级）
- ✅ 异常值处理（3σ原则）
- ✅ 行业特殊适配（金融/周期/成长/防御）

### 4.2 回测分析
```python
results = run_backtest(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    quantiles=5,
    holding_days=10
)
```

**输出指标**:
- ✅ IC值（信息系数）
- ✅ 分层收益（Q1~Q5）
- ✅ 累计收益（vs 基准）
- ✅ 重点行业分析（消费/科技/周期）
- ✅ 交易统计（胜率、盈亏比）

### 4.3 验证体系
```python
# 数据完整性检查
python3 code/verify_backtest.py

# 验证内容:
# 1. PE/财务/行业/价格/基准数据
# 2. 因子计算准确性
# 3. 回测结果完整性
# 4. 生成验证报告
```

---

## 五、数据流程

### 5.1 数据输入
```
daily_basic (日频PE)
    ↓
fina_indicator (财报增长率)
    ↓
industry_cache.csv (行业分类)
    ↓
daily_kline (价格数据)
    ↓
index_daily_zzsz (基准指数)
```

### 5.2 计算流程
```
1. 数据提取 (20250101-20250630)
   ↓
2. 时间对齐 (trade_date = ann_date + ffill)
   ↓
3. 行业映射 (ts_code → l1_name)
   ↓
4. 分行业计算 (alpha_peg = pe_ttm / dt_netprofit_yoy)
   ↓
5. 异常值处理 (3σ原则 + 缩尾)
   ↓
6. 可选标准化 (z-score/rank)
   ↓
7. 输出因子数据
```

### 5.3 回测流程
```
1. 加载因子数据
   ↓
2. 每日分5层 (Q1~Q5)
   ↓
3. T+1买入 (开盘价)
   ↓
4. 持有10天
   ↓
5. T+11卖出 (收盘价)
   ↓
6. 扣除交易成本 (0.35%)
   ↓
7. 计算IC/分层/累计收益
   ↓
8. 重点行业分析
```

---

## 六、关键参数

### 因子计算参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `start_date` | '20250101' | 开始日期 |
| `end_date` | '20250630' | 结束日期 |
| `outlier_sigma` | 3.0 | 异常值阈值 |
| `normalization` | None | 标准化方法 |

### 回测参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `quantiles` | 5 | 分层数量 |
| `holding_days` | 10 | 持有天数 |
| `commission` | 0.0005 | 佣金 |
| `stamp_tax` | 0.002 | 印花税 |
| `slippage` | 0.001 | 滑点 |

### 行业特定阈值
| 行业类型 | 阈值 | 示例 |
|----------|------|------|
| 高成长 | 3.5σ | 电子, 电力设备, 医药生物, 计算机 |
| 防御性 | 2.5σ | 银行, 公用事业, 交通运输 |
| 周期性 | 3.0σ | 有色金属, 煤炭, 钢铁 |
| 其他 | 3.0σ | 默认 |

---

## 七、输出结果

### 7.1 因子文件
```
results/factor/
├── alpha_peg_factor.csv                    # 基础版
├── alpha_peg_industry_sigma3.0.csv         # 行业优化版
├── alpha_peg_industry_zscore_sigma3.0.csv  # 标准化版
└── alpha_peg_industry_backtest_*.csv       # 回测因子
```

### 7.2 回测文件
```
results/backtest/
├── ic_values_*.csv              # IC值序列
├── quantile_returns_*.csv       # 分层收益
├── cumulative_returns_*.csv     # 累计收益
├── backtest_summary_*.txt       # 汇总报告
└── verification_report_*.txt    # 验证报告
```

### 7.3 典型结果格式

**IC数据**:
```
trade_date,rank_ic,raw_ic,stock_count
20250102,0.082,0.075,156
20250103,0.065,0.058,162
...
```

**分层收益**:
```
trade_date,quantile,return,stock_count
20250102,1,-0.002,31
20250102,2,0.001,31
...
```

**累计收益**:
```
trade_date,avg_return,stock_count,cumulative_return
20250102,0.008,31,0.008
20250103,0.005,28,0.013
...
```

---

## 八、使用建议

### 8.1 适用场景
| 场景 | 推荐配置 | 说明 |
|------|----------|------|
| 跨行业选股 | outlier_sigma=3.0, normalization='zscore' | 消除行业差异 |
| 行业内选股 | outlier_sigma=3.0, normalization=None | 保留行业特性 |
| 风险控制 | outlier_sigma=2.5, normalization=None | 严格过滤 |
| 因子合成 | outlier_sigma=3.0, normalization='rank' | 统一量纲 |

### 8.2 结果解读

**有效因子**:
- IC均值 > 0.05
- Q5收益 > Q1收益
- 胜率 > 50%
- 盈亏比 > 1.0

**需谨慎**:
- IC均值 0~0.05
- 分层不单调
- 胜率接近50%

**无效因子**:
- IC均值 < 0
- Q5收益 < Q1收益
- 胜率 < 45%

### 8.3 优化方向
1. **市值中性化**: 消除市值偏差
2. **流动性过滤**: 剔除低流动性股票
3. **动态持有期**: 根据市场状态调整
4. **止损机制**: 控制回撤
5. **多因子合成**: 结合其他因子

---

## 九、项目文件结构

```
alpha006_20251223/
├── code/
│   ├── db_connection.py
│   ├── calc_alpha_peg.py                    # 基础版
│   ├── calc_alpha_peg_industry.py           # 行业优化版
│   ├── test_alpha_peg.py                    # 逻辑验证
│   ├── compare_alpha_peg_versions.py        # 版本对比
│   ├── backtest_alpha_peg_industry.py       # 回测主程序 ⭐
│   ├── verify_backtest.py                   # 验证脚本 ⭐
│   └── [原项目代码...]
├── docs/
│   ├── alpha_peg_data_source.md             # 数据源
│   ├── factor_dictionary.md                 # 因子字典
│   ├── alpha_peg_quick_start.md             # 快速指南
│   ├── alpha_peg_comparison_report.md       # 对比报告
│   ├── alpha_peg_backtest_guide.md          # 回测指南 ⭐
│   ├── alpha_peg_project_summary.md         # 项目总结 ⭐
│   └── [原项目文档...]
├── results/
│   ├── factor/
│   │   ├── alpha_peg_*.csv                  # 因子结果
│   │   └── alpha_peg_industry_backtest_*.csv # 回测因子 ⭐
│   └── backtest/
│       ├── ic_values_*.csv                  # IC值 ⭐
│       ├── quantile_returns_*.csv           # 分层收益 ⭐
│       ├── cumulative_returns_*.csv         # 累计收益 ⭐
│       ├── backtest_summary_*.txt           # 汇总报告 ⭐
│       └── verification_report_*.txt        # 验证报告 ⭐
└── README.md
```

---

## 十、快速命令

### 计算因子
```bash
# 基础版
python3 code/calc_alpha_peg.py

# 行业优化版
python3 code/calc_alpha_peg_industry.py

# 版本对比
python3 code/compare_alpha_peg_versions.py
```

### 运行回测
```bash
# 完整回测
python3 code/backtest_alpha_peg_industry.py

# 验证结果
python3 code/verify_backtest.py
```

### 查看结果
```bash
# 查看因子数据
ls -lh results/factor/alpha_peg_*.csv

# 查看回测结果
ls -lh results/backtest/

# 查看最新报告
tail -n 50 results/backtest/backtest_summary_*.txt
```

---

## 十一、版本历史

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| v1.0 | 2025-12-24 10:00 | 基础版开发完成 |
| v1.1 | 2025-12-24 15:00 | 行业优化版完成 |
| v1.2 | 2025-12-24 20:00 | 回测框架完成 |
| v1.3 | 2025-12-24 22:00 | 文档完善，项目总结 |

---

## 十二、总结

### ✅ 已完成
1. ✅ 基础因子计算（pe_ttm / dt_netprofit_yoy）
2. ✅ 行业优化（分行业计算 + 3σ处理）
3. ✅ 完整回测框架（含交易成本）
4. ✅ 多维度评估（IC/分层/累计/行业）
5. ✅ 可复现性验证
6. ✅ 完整文档体系

### 📊 核心产出
- **6个代码文件**: 计算、验证、回测、对比
- **6个文档**: 数据源、字典、指南、报告
- **5类结果**: 因子数据、IC、分层、累计、验证

### 🎯 项目价值
1. **系统性**: 从数据到回测的完整流程
2. **专业性**: 行业优化 + 交易成本 + 基准对比
3. **可扩展**: 易于参数调整和功能扩展
4. **可验证**: 完整的验证体系

---

**项目状态**: ✅ 完成
**最后更新**: 2025-12-24 22:00
**维护**: Alpha006项目组
