# Alpha_PEG因子持仓天数优化指南

## 📖 概述

本模块基于vectorbt库，针对alpha_peg因子进行多持仓天数的对比回测，筛选出收益-风险性价比最优的持仓天数。

## 🎯 核心目标

1. **多天数测试**: 在10-45天范围内测试每个持仓天数的表现
2. **最优筛选**: 基于夏普比率、收益、回撤、换手率等指标筛选最优天数
3. **稳定性验证**: 在不同细分区间验证最优天数的稳定性
4. **行业分析**: 分析最优天数在各行业的表现

## 📁 模块结构

```
backtest/engine/
├── vbt_data_preparation.py      # 数据准备模块
├── vbt_backtest_engine.py       # vectorbt回测引擎
├── backtest_hold_days_optimize.py  # 主优化模块
└── hold_days_analysis.py        # 分析工具

config/
└── hold_days_config.py          # 配置参数

scripts/
└── run_hold_days_optimize.py    # 执行脚本

docs/
└── HOLD_DAYS_OPTIMIZATION_GUIDE.md  # 本文件
```

## 🚀 快速开始

### 1. 命令行执行

```bash
# 默认配置 (20240801-20250930, 10-45天)
python scripts/run_hold_days_optimize.py

# 自定义参数
python scripts/run_hold_days_optimize.py \
  --start 20240801 \
  --end 20250930 \
  --days 10,45 \
  --step 1 \
  --top-n 3 \
  --outlier-sigma 3.0 \
  --initial-capital 1000000

# 快速测试
python scripts/run_hold_days_optimize.py \
  --start 20240801 \
  --end 20240831 \
  --days 5,10 \
  --top-n 2
```

### 2. Python API调用

```python
from backtest.engine.backtest_hold_days_optimize import HoldDaysOptimizer

# 创建优化器
optimizer = HoldDaysOptimizer('20240801', '20250930')

# 运行优化
results = optimizer.run_full_optimization(
    hold_days_range=list(range(10, 46)),
    outlier_sigma=3.0,
    normalization=None,
    top_n=3,
    initial_capital=1000000.0
)

# 查看结果
comparison = results['comparison']
best_days = int(comparison['best_by_sharpe']['holding_days'])
print(f"最优持仓天数: {best_days}天")
```

## 🔧 核心功能

### 1. 数据准备 (vbt_data_preparation.py)

```python
preparer = VBTDataPreparation('20240801', '20250930')
data = preparer.prepare_all(
    outlier_sigma=3.0,
    normalization=None,
    top_n=3
)
```

**功能**:
- 从数据库获取alpha_peg因子数据
- 分行业选择前N名个股
- 生成vectorbt所需的信号矩阵
- 加载价格数据和基准指数

**输出**:
- `factor_df`: 因子数据
- `selected_df`: 选股结果
- `price_df`: 价格数据
- `signal_matrix`: 交易信号矩阵

### 2. 回测引擎 (vbt_backtest_engine.py)

```python
engine = VBTBacktestEngine(price_df, signal_matrix)
result = engine.run_backtest(holding_days=20, initial_capital=1000000.0)
```

**功能**:
- 基于vectorbt运行回测
- 支持N天持有逻辑
- 计算完整绩效指标

**核心指标**:
- 累计收益、年化收益
- 夏普比率、最大回撤
- 换手率、交易次数
- 胜率、盈亏比

### 3. 多天数测试

```python
results_df = engine.run_multiple_hold_days(
    hold_days_range=list(range(10, 46)),
    initial_capital=1000000.0
)
```

### 4. 最优天数筛选

```python
from backtest.engine.vbt_backtest_engine import compare_hold_days_results

comparison = compare_hold_days_results(results_df)

# 最优天数
best_by_sharpe = comparison['best_by_sharpe']
best_by_composite = comparison['best_by_composite']
```

**筛选逻辑**:
- **综合评分**: 夏普40% + 收益30% + 回撤20% + 换手10%
- **单指标最优**: 分别标注各指标最优天数
- **特殊标注**: 换手过高、回撤过大等

### 5. 可视化输出

```python
optimizer.generate_visualizations()
```

**生成图表**:
1. 持仓天数 vs 夏普比率
2. 持仓天数 vs 累计收益
3. 持仓天数 vs 最大回撤
4. 持仓天数 vs 换手率
5. 最优天数 vs 基准收益曲线
6. 综合评分热力图

### 6. 稳定性验证

```python
stability = optimizer.validate_stability()
```

**验证方法**:
- 在2025Q1、Q2、Q3分别测试
- 检查最优天数是否保持一致
- 计算平均超额收益

### 7. 行业维度分析

```python
industry_analysis = optimizer.analyze_by_industry()
```

**输出**:
- 各行业收益贡献
- 交易次数分布
- 行业适配性评估

## 📊 结果解读

### 量化对比表

```csv
holding_days,total_return,annual_return,sharpe_ratio,max_drawdown,turnover,total_trades,备注
10,0.0567,0.0689,1.234,-0.089,0.85,120,-
15,0.0892,0.1089,1.567,-0.102,0.65,90,收益最高
20,0.0923,0.1128,1.678,-0.115,0.55,75,最优
25,0.0856,0.1045,1.456,-0.128,0.48,65,回撤较大
30,0.0789,0.0962,1.234,-0.142,0.42,55,换手最低
```

### 关键指标说明

| 指标 | 说明 | 优秀范围 |
|------|------|----------|
| 夏普比率 | 风险调整后收益 | > 1.5 |
| 累计收益 | 总回报率 | > 8% |
| 年化收益 | 年化回报率 | > 10% |
| 最大回撤 | 最大亏损幅度 | < -15% |
| 换手率 | 交易活跃度 | < 0.8 |
| 胜率 | 盈利交易比例 | > 50% |

### 最优天数判断标准

**综合最优** (推荐):
- 夏普比率 > 1.5
- 累计收益 > 8%
- 最大回撤 < -15%
- 换手率 < 0.8
- 在多个子区间表现稳定

**特殊场景**:
- **高收益但高回撤**: 适合激进策略
- **低换手但低收益**: 适合保守策略
- **不稳定**: 避免使用

## ⚙️ 配置说明

### 持仓天数范围

```python
# 完整测试 (10-45天)
HOLD_DAYS_RANGE_CONFIG['full_test']

# 短期测试 (1-15天)
HOLD_DAYS_RANGE_CONFIG['short_term']

# 快速测试 (关键节点)
HOLD_DAYS_RANGE_CONFIG['quick_test']
```

### 筛选权重

```python
# 夏普优先 (默认)
SCORING_WEIGHTS['sharpe_first']

# 平衡型
SCORING_WEIGHTS['balanced']

# 激进型
SCORING_WEIGHTS['aggressive']
```

### 回测区间

```python
# 完整周期
BACKTEST_PERIODS['full_period']

# 季度验证
BACKTEST_PERIODS['validation_2025Q1']
BACKTEST_PERIODS['validation_2025Q2']

# 月度验证
BACKTEST_PERIODS['monthly_202501']
```

## 📈 输出文件

### 因子结果 (results/factor/)
```
factor_alpha_peg_industry_optimized_[date]_[timestamp].csv
factor_alpha_peg_industry_optimized_[date]_[timestamp]_stats.txt
```

### 回测结果 (results/backtest/)
```
hold_days_comparison_[start]_[end]_[timestamp].csv      # 对比表
hold_days_detailed_[start]_[end]_[timestamp].csv        # 详细结果
hold_days_optimize_report_[start]_[end]_[timestamp].txt # 分析报告
```

### 可视化图表 (results/visual/)
```
hold_days_metrics_[timestamp].png          # 指标趋势图
nav_comparison_[timestamp].png             # 收益曲线对比
heatmap_[timestamp].png                    # 综合评分热力图
```

## 🎓 最佳实践

### 1. 初次运行

```bash
# 快速验证
python scripts/run_hold_days_optimize.py \
  --start 20240801 --end 20240831 \
  --days 5,15 --step 1 --top-n 2
```

### 2. 完整分析

```bash
# 完整周期测试
python scripts/run_hold_days_optimize.py \
  --start 20240801 --end 20250930 \
  --days 10,45 --step 1 --top-n 3
```

### 3. 稳定性验证

```python
# 在不同区间验证
periods = [
    ('20250101', '20250131'),
    ('20250201', '20250228'),
    ('20250301', '20250331')
]

for start, end in periods:
    optimizer = HoldDaysOptimizer(start, end)
    results = optimizer.run_full_optimization(
        hold_days_range=[best_days]
    )
```

## 🔍 故障排查

### 1. 数据不足
**问题**: 信号矩阵和价格矩阵无共同日期
**解决**: 检查日期范围，确保有足够交易日

### 2. 回测结果为0
**问题**: 信号未触发交易
**解决**: 检查信号矩阵是否正确生成

### 3. 内存不足
**问题**: 测试范围过大
**解决**: 分批测试或减少测试天数

### 4. 导入错误
**问题**: 模块路径错误
**解决**: 确保在项目根目录运行

## 📚 参考资料

- [vectorbt官方文档](https://vectorbt.dev/)
- [alpha_peg因子说明](../docs/factor_dictionary.md)
- [回测配置说明](../config/backtest_config.py)

---

**最后更新**: 2025-12-25
**版本**: v1.0
**状态**: ✅ 已验证
