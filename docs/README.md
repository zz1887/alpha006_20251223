# Alpha006因子项目文档

欢迎来到Alpha006因子项目！这是一个基于换手率、量能和波动率的股票因子策略开发项目。

## 📚 文档导航

### 1. [项目总览](project_summary.md)
- 项目信息和核心指标
- 因子定义和回测结果
- 项目结构说明
- 关键发现和改进建议

### 2. [因子版本记录](factor_versions.md)
- v1.0: 基础版本（固定参数）
- v2.0: 动态倍数版本（未运行）
- v3.0: 方差统计版本 ⭐（推荐版本）

### 3. [README](../README.md)
- 快速开始指南
- 环境配置
- 使用说明

## 🎯 快速了解

### 核心因子逻辑
```python
alpha_006 = cond1 & cond2 & vol_shrink

# cond1: 换手率在1倍标准差范围内
# cond2: 5日均值在60日均值的1倍标准差范围内（轻微放量）
# vol_shrink: 波动率收缩
```

### 回测表现
- **年化收益率**: 5.05%
- **超额收益**: +0.60%/周期
- **周期胜率**: 50%
- **交易数**: 1,765笔

## 📁 项目目录

```
alpha006_20251223/
├── code/                    # 代码文件
├── data/                    # 原始数据
├── results/                 # 结果文件
│   ├── factor/              # 因子结果
│   └── backtest/            # 回测结果
├── docs/                    # 文档（本目录）
└── README.md                # 项目说明
```

## 📊 结果文件

### 因子结果 (`results/factor/`)
- `alpha006_results_v3.csv` - 完整因子数据（96MB）
- `alpha006_daily_stats_v3.csv` - 每日信号统计

### 回测结果 (`results/backtest/`)
- `backtest_results.csv` - 周期回测统计

## 🔍 如何查看结果

### 1. 查看因子数据
```bash
# 查看前几行
head -n 5 results/factor/alpha006_results_v3.csv

# 统计信号数量
python3 -c "
import pandas as pd
df = pd.read_csv('results/factor/alpha006_results_v3.csv')
print(f'总信号: {df[\"alpha006\"].sum()}')
"
```

### 2. 查看回测结果
```bash
# 查看详细统计
cat results/backtest/backtest_results.csv
```

### 3. 运行因子计算
```bash
cd code
python3 alpha006_factor_v3.py
```

### 4. 运行回测
```bash
cd code
python3 backtest_v3.py
```

## 🎯 下一步建议

### 立即可做
1. 阅读 `project_summary.md` 了解全貌
2. 查看 `factor_versions.md` 对比版本差异
3. 分析 `backtest_results.csv` 了解周期表现

### 优化方向
1. **参数调优**: 测试不同标准差倍数
2. **增加过滤**: 提升胜率和盈亏比
3. **扩展回测**: 更长时间范围验证
4. **信号分析**: 详细盈亏分布研究

## 📞 项目状态

- ✅ 数据库连接配置完成
- ✅ v3因子计算完成（20240801-20250301）
- ✅ 回测验证完成
- 🔄 参数优化进行中
- 📋 文档完善中

---

**最后更新**: 2025-12-24
**项目版本**: v3.0 (方差统计版)
**项目状态**: ✅ 因子开发 + 回测验证完成