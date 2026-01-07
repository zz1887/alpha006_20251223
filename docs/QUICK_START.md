"""
文件input(依赖外部什么): scripts/run_strategy.py, test_connection.py
文件output(提供什么): 5分钟快速上手指南
文件pos(系统局部地位): 策略文档层, 提供快速使用指南

快速开始 - Quick Start

一句话命令:
cd /home/zcy/alpha006_20251223
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
"""

# 快速开始 - Quick Start

## 🎯 一句话命令

```bash
cd /home/zcy/alpha006_20251223
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

---

## 📋 完整流程

### 步骤1: 检查环境

```bash
# 检查Python路径
which python3

# 检查数据库连接
python test_connection.py
```

### 步骤2: 运行策略

```bash
# 基础命令
python scripts/run_strategy.py --strategy six_factor_monthly --start 20240601 --end 20251130

# 简写
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

### 步骤3: 查看结果

```bash
# 查看最新结果目录
ls -lt results/backtest/ | head -5

# 查看结果摘要
cat results/backtest/six_factor_20240601_20251130_*/backtest_log.txt
```

---

## 📊 常用命令速查

### 策略操作

```bash
# 列出所有策略
python scripts/run_strategy.py --list

# 查看策略详情
python scripts/run_strategy.py --info six_factor_monthly

# 运行策略
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

### 数据库测试

```bash
# 测试连接
python test_connection.py

# 使用db测试
python /tmp/test_db.py
```

### 结果管理

```bash
# 查看所有结果
ls results/backtest/

# 查看最新结果
ls -lt results/backtest/ | head -10

# 查看结果文件
ls results/backtest/six_factor_20240601_20251130_20251231_234653/
```

---

## 🎲 常用时间区间

### 测试区间
```bash
# 3个月快速测试
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20240831

# 6个月测试
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20241130
```

### 完整区间
```bash
# 2024年至今
python scripts/run_strategy.py -s six_factor_monthly --start 20240101 --end 20251231

# 202406-202511 (已完成)
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

---

## 📁 结果文件说明

### 必看文件

1. **backtest_log.txt** - 执行日志和性能摘要
2. **performance_metrics.xlsx** - 详细性能指标
3. **cumulative_returns.png** - 累计收益曲线

### 查看命令

```bash
# 查看日志
cat results/backtest/six_factor_20240601_20251130_*/backtest_log.txt

# 查看性能指标 (需要pandas)
python -c "import pandas as pd; df=pd.read_excel('results/backtest/six_factor_20240601_20251130_*/performance_metrics.xlsx'); print(df)"
```

---

## 🔧 故障排查

### 问题1: 命令找不到

```bash
# 确认在正确目录
pwd  # 应该显示 /home/zcy/alpha006_20251223

# 确认文件存在
ls scripts/run_strategy.py
```

### 问题2: 数据库连接失败

```bash
# 测试连接
python test_connection.py

# 检查配置
python -c "from core.config.settings import DATABASE_CONFIG; print(DATABASE_CONFIG)"
```

### 问题3: 无输出

```bash
# 检查Python版本
which python3
python3 --version

# 使用绝对路径
/usr/bin/python3 /home/zcy/alpha006_20251223/scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

---

## 💡 小贴士

1. **第一次运行前**: 先用3个月数据测试
2. **查看进度**: 日志会实时显示进度
3. **结果保存**: 自动保存到 `results/backtest/`
4. **时间格式**: 必须是 YYYYMMDD (8位数字)

---

## 📝 完整示例

```bash
# 1. 进入项目目录
cd /home/zcy/alpha006_20251223

# 2. 测试环境
python test_connection.py

# 3. 运行策略 (3个月测试)
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20240831

# 4. 查看结果
ls -lt results/backtest/ | head -1
cat results/backtest/six_factor_20240601_20240831_*/backtest_log.txt

# 5. 运行完整回测
python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

---

## 🎉 开始使用

```bash
# 一句话启动
cd /home/zcy/alpha006_20251223 && python scripts/run_strategy.py -s six_factor_monthly --start 20240601 --end 20251130
```

**祝你使用愉快!** 🚀
