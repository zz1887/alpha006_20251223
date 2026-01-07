# alpha_peg因子执行清单

**快速开始**: 按顺序执行以下命令即可完成完整流程

---

## 一、基础计算

### 1.1 计算行业优化版因子
```bash
python3 code/calc_alpha_peg_industry.py
```
**输出**: `results/factor/alpha_peg_industry_sigma3.0.csv`

### 1.2 验证因子逻辑
```bash
python3 code/test_alpha_peg.py
```
**验证**: 检查计算准确性

### 1.3 版本对比（可选）
```bash
python3 code/compare_alpha_peg_versions.py
```
**输出**: 对比报告和统计结果

---

## 二、运行回测

### 2.1 执行完整回测
```bash
python3 code/backtest_alpha_peg_industry.py
```
**输出文件**:
- `results/factor/alpha_peg_industry_backtest_YYYYMMDD_HHMMSS.csv`
- `results/backtest/ic_values_YYYYMMDD_HHMMSS.csv`
- `results/backtest/quantile_returns_YYYYMMDD_HHMMSS.csv`
- `results/backtest/cumulative_returns_YYYYMMDD_HHMMSS.csv`
- `results/backtest/backtest_summary_YYYYMMDD_HHMMSS.txt`

### 2.2 验证结果可复现性
```bash
python3 code/verify_backtest.py
```
**输出**: `results/backtest/verification_report_YYYYMMDD_HHMMSS.txt`

---

## 三、Python代码示例

### 3.1 完整流程
```python
from code.calc_alpha_peg_industry import calc_alpha_peg_industry
from code.backtest_alpha_peg_industry import run_backtest

# 1. 计算因子
df = calc_alpha_peg_industry(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    normalization=None
)

# 2. 运行回测
results = run_backtest(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    quantiles=5,
    holding_days=10
)

# 3. 查看结果
print(f"IC均值: {results['summary']['ic_mean']:.4f}")
print(f"数据量: {results['summary']['total_records']:,}")
```

### 3.2 仅计算因子
```python
from code.calc_alpha_peg_industry import calc_alpha_peg_industry

# 基础版（无标准化）
df = calc_alpha_peg_industry(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    normalization=None
)

# 跨行业可比（z-score标准化）
df_zscore = calc_alpha_peg_industry(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    normalization='zscore'
)

# 分组排序（rank标准化）
df_rank = calc_alpha_peg_industry(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    normalization='rank'
)
```

### 3.3 仅运行回测
```python
from code.backtest_alpha_peg_industry import run_backtest

# 标准回测
results = run_backtest(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    quantiles=5,
    holding_days=10
)

# 调整参数
results_short = run_backtest(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=2.5,  # 更严格
    quantiles=3,        # 3层分组
    holding_days=5      # 短周期
)
```

---

## 四、参数调整指南

### 4.1 异常值阈值
```python
# 严格过滤（防御性行业）
outlier_sigma=2.5

# 标准过滤（默认）
outlier_sigma=3.0

# 宽松过滤（高成长行业）
outlier_sigma=3.5
```

### 4.2 分层数量
```python
# 3层（保守）
quantiles=3

# 5层（标准）
quantiles=5

# 10层（精细）
quantiles=10
```

### 4.3 持有周期
```python
# 短期（3天）
holding_days=3

# 中期（5天）
holding_days=5

# 标准（10天）
holding_days=10

# 长期（20天）
holding_days=20
```

---

## 五、查看结果

### 5.1 查看因子数据
```bash
# 查看最新因子文件
ls -lt results/factor/ | head -5

# 查看前10行
head -n 10 results/factor/alpha_peg_industry_backtest_*.csv

# 统计信息
wc -l results/factor/alpha_peg_industry_backtest_*.csv
```

### 5.2 查看回测结果
```bash
# 查看IC值
cat results/backtest/ic_values_*.csv | head -20

# 查看分层收益
cat results/backtest/quantile_returns_*.csv | head -20

# 查看累计收益
cat results/backtest/cumulative_returns_*.csv | head -20

# 查看汇总报告
cat results/backtest/backtest_summary_*.txt
```

### 5.3 Python查看
```python
import pandas as pd

# 读取IC数据
ic = pd.read_csv('results/backtest/ic_values_*.csv')
print(f"IC均值: {ic['rank_ic'].mean():.4f}")

# 读取分层收益
qr = pd.read_csv('results/backtest/quantile_returns_*.csv')
print(qr.groupby('quantile')['return'].mean())

# 读取累计收益
cr = pd.read_csv('results/backtest/cumulative_returns_*.csv')
print(f"总收益: {cr['cumulative_return'].iloc[-1]:.4f}")
```

---

## 六、常见问题

### Q1: 数据连接失败
```bash
# 检查数据库配置
cat code/db_connection.py

# 测试连接
python3 -c "from db_connection import db; print('连接成功')"
```

### Q2: 行业数据文件不存在
```bash
# 检查文件路径
ls -l /mnt/c/Users/mm/PyCharmMiscProject/获取数据代码/industry_cache.csv

# 如果不存在，需要先生成行业映射
```

### Q3: 回测结果为空
```python
# 检查数据完整性
from code.verify_backtest import check_data_completeness
report = check_data_completeness('20250101', '20250630')
print(report)
```

### Q4: 如何重新运行
```bash
# 删除旧结果
rm results/factor/alpha_peg_industry_backtest_*.csv
rm results/backtest/*.csv
rm results/backtest/*.txt

# 重新运行
python3 code/backtest_alpha_peg_industry.py
```

---

## 七、完整执行脚本

创建文件 `run_all.sh`:
```bash
#!/bin/bash

echo "=== alpha_peg因子完整执行流程 ==="
echo ""

echo "步骤1: 计算因子..."
python3 code/calc_alpha_peg_industry.py

echo ""
echo "步骤2: 运行回测..."
python3 code/backtest_alpha_peg_industry.py

echo ""
echo "步骤3: 验证结果..."
python3 code/verify_backtest.py

echo ""
echo "=== 执行完成 ==="
echo "查看结果: cat results/backtest/backtest_summary_*.txt"
```

执行:
```bash
chmod +x run_all.sh
./run_all.sh
```

---

## 八、文档索引

### 核心文档
- `docs/alpha_peg_backtest_guide.md` - 回测详细指南
- `docs/factor_dictionary.md` - 因子字典
- `docs/alpha_peg_data_source.md` - 数据源说明
- `docs/alpha_peg_project_summary.md` - 项目总结

### 快速参考
- `docs/alpha_peg_quick_start.md` - 快速开始
- `README.md` - 项目总览

### 验证文档
- `docs/alpha_peg_comparison_report.md` - 版本对比

---

## 九、关键检查点

运行前确认:
- [ ] 数据库连接正常
- [ ] 行业数据文件存在
- [ ] 时间范围正确（20250101-20250630）
- [ ] 磁盘空间充足

运行后检查:
- [ ] 因子文件生成
- [ ] IC值为正
- [ ] 分层单调
- [ ] 验证报告通过

---

## 十、联系与支持

**项目目录**: `/home/zcy/alpha006_20251223/`
**更新时间**: 2025-12-24
**文档版本**: v1.0

如遇问题，请按以下顺序排查:
1. 查看 `docs/alpha_peg_backtest_guide.md` 常见问题
2. 运行 `code/verify_backtest.py` 检查数据完整性
3. 检查数据库连接配置

---

**祝您使用顺利！** 🚀
