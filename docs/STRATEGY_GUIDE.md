"""
文件input(依赖外部什么): config/strategies/six_factor_monthly.py, scripts/run_strategy.py
文件output(提供什么): SFM策略完整使用指南
文件pos(系统局部地位): 策略文档层, 提供策略使用和理解文档

策略使用指南 - Strategy Guide

策略名称: SFM (Six-Factor Monthly) - 六因子月末智能调仓策略
策略代码: six_factor_monthly
版本: v1.0
创建日期: 2025-12-31
"""

# 策略使用指南 - Strategy Guide

## 📋 策略概览

### 策略名称: SFM (Six-Factor Monthly) - 六因子月末智能调仓策略

**策略代码**: `six_factor_monthly`
**版本**: v1.0
**创建日期**: 2025-12-31

---

## 🎯 策略特点

### 核心优势
1. **6因子复合选股** - 多维度因子验证
2. **月末智能调仓** - 自动处理非交易日
3. **5组分层回测** - 完整的绩效评估
4. **市值加权配置** - 符合实际投资逻辑

### 因子构成
| 因子名称 | 中文名称 | 权重 | 作用 |
|---------|---------|------|------|
| alpha_pluse | 量能因子 | 10% | 捕捉成交量扩张信号 |
| alpha_peg | 估值因子 | 20% | 行业标准化PE/G |
| alpha_010 | 趋势因子 | 20% | 短期价格趋势 |
| alpha_038 | 强度因子 | 20% | 价格强度 |
| alpha_120cq | 位置因子 | 15% | 价格相对位置 |
| cr_qfq | 动量因子 | 15% | 动量效应 |

---

## 🚀 快速开始

### 基础调用

```bash
cd /home/zcy/alpha006_20251223

# 运行策略
python scripts/run_strategy.py --strategy six_factor_monthly --start 20240601 --end 20251130

# 简写形式
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

### 查看信息

```bash
# 列出所有策略
python scripts/run_strategy.py --list

# 查看策略详情
python scripts/run_strategy.py --info six_factor_monthly

# 直接运行原脚本
python scripts/run_six_factor_backtest.py --start 20240601 --end 20251130 --version standard
```

---

## 📊 结果说明

### 输出目录结构
```
results/backtest/six_factor_20240601_20251130_20251231_234653/
├── README.md                    # 策略说明文档
├── backtest_log.txt            # 详细执行日志
├── backtest_data.xlsx          # 月度收益率数据
├── performance_metrics.xlsx    # 性能指标汇总
├── cumulative_returns.png/pdf  # 累计收益曲线
├── maximum_drawdown_curve.png/pdf  # 最大回撤曲线
├── ic_timeline.png/pdf         # IC时间序列
└── turnover_timeline.png/pdf   # 换手率时间序列
```

### 性能指标解读

| 指标 | 说明 | 优秀标准 |
|------|------|----------|
| 年化收益率 | 年化投资回报率 | > 10% |
| 年化波动率 | 收益波动程度 | < 30% |
| 夏普比率 | 风险调整后收益 | > 1.5 |
| 最大回撤 | 最大亏损幅度 | < -10% |
| 月度胜率 | 正收益月份占比 | > 60% |
| 信息比率(IR) | 超额收益稳定性 | > 1.0 |
| IC值 | 因子预测能力 | > 0.01 |
| ICIR | IC稳定性 | > 0.5 |
| 换手率 | 月均交易频率 | ~90% |

---

## 🔧 策略配置

### 配置文件位置
```
config/strategies/six_factor_monthly.py
```

### 关键参数

#### 1. 调仓逻辑
```python
REBALANCE_CONFIG = {
    'frequency': 'monthly',
    'monthly_logic': {
        'type': 'smart_nearest',
        'description': '月末为交易日则月末调仓,否则为离月末最近的一天调仓',
    }
}
```

#### 2. 股票池过滤
```python
FILTER_CONFIG = {
    'base_filters': {
        'min_amount': 50000,           # 最小成交额(万元)
        'min_market_cap': 100000000,   # 最小流通市值(元)
        'exclude_st': True,            # 剔除ST
        'exclude_suspension': True,    # 剔除停牌
    }
}
```

#### 3. 交易成本
```python
TRADING_COST_CONFIG = {
    'commission': 0.0005,   # 佣金 0.05%
    'stamp_tax': 0.001,     # 印花税 0.1%
    'slippage': 0.001,      # 滑点 0.1%
    'total': 0.0025,        # 总成本 0.25%
}
```

---

## 📈 实际案例

### 案例1: 202406-202511回测

**参数**:
- 时间区间: 20240601 - 20251130
- 调仓频率: 月度
- 交易成本: 0.25%

**结果摘要**:
```
分组   年化收益率  夏普比率    最大回撤   月度胜率
组1    1.26%     3.74      -5.50%    58.82%
组2    2.39%     7.89      -2.65%    76.47%
组3    0.61%     2.38      -3.15%    52.94%
组4    0.20%     0.64      -4.78%    58.82%
组5    0.90%     2.65      -4.79%    52.94%
多空   0.16%     0.63      -5.76%    47.06%
基准   29.40%    30.88     -7.85%    47.06%

IC值: 0.0084, ICIR: 0.0513
平均换手率: 89.77%
```

**调仓日期验证**:
- 20240731 - 月末交易日 ✓
- 20240830 - 月末交易日 ✓
- 20250901 - 9月1日(8月31日周末,调整为9月1日) ✓
- 20251128 - 11月28日(11月30日周末,调整为11月28日) ✓

---

## 🎛️ 进阶使用

### 1. 修改策略参数

编辑 `config/strategies/six_factor_monthly.py`:

```python
# 修改因子权重
FACTOR_CONFIG['factors']['alpha_peg']['weight'] = 0.25  # 提高估值因子权重

# 修改过滤条件
FILTER_CONFIG['base_filters']['min_market_cap'] = 50000000  # 降低市值门槛
```

### 2. 自定义回测区间

```bash
# 2023年全年
python scripts/run_strategy.py -s six_factor_monthly --start 20230101 --end 20231231

# 2025年至今
python scripts/run_strategy.py -s six_factor_monthly --start 20250101 --end 20251231
```

### 3. 不同版本对比

```bash
# 标准版
python scripts/run_six_factor_backtest.py --start 20240601 --end 20251130 --version standard

# 保守版 (如果配置了)
python scripts/run_six_factor_backtest.py --start 20240601 --end 20251130 --version conservative

# 激进版 (如果配置了)
python scripts/run_six_factor_backtest.py --start 20240601 --end 20251130 --version aggressive
```

---

## 🔍 故障排查

### 常见问题

#### 1. 数据库连接失败
```bash
# 测试数据库连接
python test_connection.py

# 检查配置
python -c "from core.config.settings import DATABASE_CONFIG; print(DATABASE_CONFIG)"
```

#### 2. 无数据返回
- 检查日期是否在数据范围内
- 确认股票池过滤条件是否过严
- 查看日志中的警告信息

#### 3. 因子计算失败
- 检查因子数据是否完整
- 确认最小数据天数要求
- 查看日志中的错误详情

---

## 📚 相关文档

- 策略配置: `config/strategies/six_factor_monthly.py`
- 执行脚本: `scripts/run_strategy.py`
- 原始脚本: `scripts/run_six_factor_backtest.py`
- 配置中心: `core/config/settings.py`

---

## 🔄 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2025-12-31 | 初始版本,六因子月末智能调仓策略 |

---

## 📞 联系方式

如有问题或建议,请联系量化策略组。

---

## ⚠️ 风险提示

1. **历史业绩不代表未来**: 回测结果仅供参考
2. **因子失效风险**: 市场环境变化可能导致因子失效
3. **交易成本**: 实际交易中成本可能更高
4. **流动性风险**: 大额交易可能产生冲击成本
5. **模型风险**: 任何模型都有局限性

**投资有风险,入市需谨慎!**
