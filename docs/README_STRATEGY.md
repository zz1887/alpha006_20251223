"""
文件input(依赖外部什么): config/strategies/six_factor_monthly.py, STRATEGY_GUIDE.md
文件output(提供什么): SFM策略概览文档
文件pos(系统局部地位): 策略文档层, 提供策略快速概览

六因子月末智能调仓策略 - SFM

SFM (Six-Factor Monthly) 是一个基于6因子复合选股的量化策略,
采用月末智能调仓机制,能够自动处理非交易日的调仓问题。
"""

# 六因子月末智能调仓策略 - SFM

## 📖 策略概述

**SFM (Six-Factor Monthly)** 是一个基于6因子复合选股的量化策略,采用月末智能调仓机制,能够自动处理非交易日的调仓问题。

---

## ✨ 核心特性

### 1. 六因子体系
- ✅ **alpha_pluse**: 量能扩张信号 (10%)
- ✅ **alpha_peg**: 行业标准化估值 (20%)
- ✅ **alpha_010**: 短期价格趋势 (20%)
- ✅ **alpha_038**: 价格强度 (20%)
- ✅ **alpha_120cq**: 价格位置 (15%)
- ✅ **cr_qfq**: 动量因子 (15%)

### 2. 智能调仓逻辑
```
月末日期判断:
├─ 是交易日 → 月末调仓
└─ 不是交易日 → 查找最近交易日
    ├─ 向前查找
    ├─ 向后查找
    └─ 选择距离更近的
```

### 3. 5组分层回测
- 组1: 高分组 (预期收益最高)
- 组2: 次高组
- 组3: 中间组
- 组4: 次低组
- 组5: 低分组
- 多空: 组1 - 组5

---

## 🚀 快速使用

### 基础命令
```bash
cd /home/zcy/alpha006_20251223
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

### 查看帮助
```bash
# 列出策略
python scripts/run_strategy.py --list

# 查看详情
python scripts/run_strategy.py --info six_factor_monthly

# 查看帮助
python scripts/run_strategy.py --help
```

---

## 📁 项目结构

```
alpha006_20251223/
├── config/
│   └── strategies/
│       ├── __init__.py
│       └── six_factor_monthly.py      # 策略配置
│
├── scripts/
│   ├── run_strategy.py                # 统一调用脚本
│   └── run_six_factor_backtest.py    # 原始回测脚本
│
├── core/
│   ├── config/
│   │   ├── settings.py                # 全局配置
│   │   └── params.py                  # 参数配置
│   └── utils/
│       ├── db_connection.py           # 数据库连接
│       └── data_loader.py             # 数据加载
│
├── factors/                           # 因子模块
│   ├── valuation/
│   ├── momentum/
│   ├── price/
│   └── volume/
│
├── results/
│   └── backtest/                      # 回测结果
│
├── STRATEGY_GUIDE.md                  # 策略指南
├── QUICK_START.md                     # 快速开始
└── README_STRATEGY.md                 # 本文件
```

---

## 🎯 使用场景

### 场景1: 快速验证
```bash
# 3个月数据快速测试
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20240831
```

### 场景2: 完整回测
```bash
# 202406-202511完整回测
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

### 场景3: 不同区间对比
```bash
# 2023年
python scripts/run_strategy.py -s six_factor_monthly --start 20230101 --end 20231231

# 2024年
python scripts/run_strategy.py -s six_factor_monthly --start 20240101 --end 20241231

# 2025年
python scripts/run_strategy.py -s six_factor_monthly --start 20250101 --end 20251231
```

---

## 📊 结果解读

### 性能指标

| 指标 | 优秀 | 良好 | 一般 |
|------|------|------|------|
| 年化收益率 | >15% | 10-15% | <10% |
| 夏普比率 | >2.0 | 1.0-2.0 | <1.0 |
| 最大回撤 | < -5% | -5%~-10% | > -10% |
| IC值 | >0.02 | 0.01-0.02 | <0.01 |
| ICIR | >1.0 | 0.5-1.0 | <0.5 |

### 预期结果

**理想情况下**:
- 组1 > 组2 > 组3 > 组4 > 组5 (单调递减)
- 多空组合有正收益
- IC值为正且稳定
- 夏普比率 > 1.5

---

## 🔧 配置修改

### 修改因子权重

编辑 `config/strategies/six_factor_monthly.py`:

```python
FACTOR_CONFIG['factors']['alpha_peg']['weight'] = 0.25  # 提高估值因子
FACTOR_CONFIG['factors']['alpha_pluse']['weight'] = 0.15  # 提高量能因子
```

### 修改过滤条件

```python
FILTER_CONFIG['base_filters']['min_market_cap'] = 50000000  # 降低市值门槛
FILTER_CONFIG['base_filters']['min_amount'] = 30000  # 降低成交额要求
```

### 修改调仓逻辑

```python
REBALANCE_CONFIG['monthly_logic']['type'] = 'end_of_month'  # 仅月末
# 或
REBALANCE_CONFIG['monthly_logic']['type'] = 'smart_nearest'  # 智能最近(默认)
```

---

## 📈 实际案例

### 202406-202511 回测结果

```
策略: SFM v1.0
区间: 20240601 - 20251130
调仓: 17次

性能摘要:
┌────────┬──────────┬────────┬─────────┬─────────┐
│  分组  │ 年化收益 │ 夏普   │ 最大回撤 │ 月胜率  │
├────────┼──────────┼────────┼─────────┼─────────┤
│  组1   │  1.26%   │  3.74  │ -5.50%  │ 58.82%  │
│  组2   │  2.39%   │  7.89  │ -2.65%  │ 76.47%  │
│  组3   │  0.61%   │  2.38  │ -3.15%  │ 52.94%  │
│  组4   │  0.20%   │  0.64  │ -4.78%  │ 58.82%  │
│  组5   │  0.90%   │  2.65  │ -4.79%  │ 52.94%  │
│  多空  │  0.16%   │  0.63  │ -5.76%  │ 47.06%  │
│  基准  │ 29.40%   │ 30.88  │ -7.85%  │ 47.06%  │
└────────┴──────────┴────────┴─────────┴─────────┘

IC统计:
- IC均值: 0.0084
- ICIR: 0.0513
- 平均换手率: 89.77%

调仓日期验证:
✓ 20240731 - 月末交易日
✓ 20240830 - 月末交易日
✓ 20250901 - 9月1日(8月31日周末)
✓ 20251128 - 11月28日(11月30日周末)
```

---

## 🎓 学习路径

### 初学者
1. 阅读 `QUICK_START.md` 快速上手
2. 运行3个月测试数据
3. 查看 `backtest_log.txt` 了解流程

### 进阶用户
1. 阅读 `STRATEGY_GUIDE.md` 深入理解
2. 修改策略参数
3. 对比不同时间区间

### 高级用户
1. 研究因子计算逻辑
2. 开发新因子
3. 优化调仓算法

---

## 📚 文档索引

| 文档 | 用途 |
|------|------|
| `QUICK_START.md` | 快速开始,5分钟上手 |
| `STRATEGY_GUIDE.md` | 完整指南,详细说明 |
| `README_STRATEGY.md` | 策略概览,快速查阅 |
| `config/strategies/six_factor_monthly.py` | 策略配置文件 |
| `scripts/run_strategy.py` | 统一调用脚本 |

---

## ⚠️ 注意事项

1. **数据库连接**: 确保MySQL服务正在运行
2. **Python环境**: 使用 `/usr/bin/python3`
3. **数据完整性**: 首次运行可能较慢
4. **磁盘空间**: 结果文件占用空间
5. **时间格式**: 必须是 YYYYMMDD

---

## 🆘 帮助支持

### 常见问题

**Q: 如何修改策略参数?**
A: 编辑 `config/strategies/six_factor_monthly.py`

**Q: 结果保存在哪里?**
A: `results/backtest/six_factor_*/`

**Q: 如何查看历史结果?**
A: `ls results/backtest/`

**Q: 如何测试数据库?**
A: `python test_connection.py`

---

## 📞 联系方式

- 策略开发: 量化策略组
- 项目目录: `/home/zcy/alpha006_20251223`
- 结果目录: `results/backtest/`

---

## 🎉 开始使用

```bash
# 一句话启动
cd /home/zcy/alpha006_20251223 && python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

**祝你回测顺利!** 🚀📊📈
