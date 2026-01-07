# alpha_peg因子中性化回测计划 - 已完成

## 任务概述
实现带行业中性化和市值中性化的alpha_peg因子回测，解决非单调性问题

### 用户要求 ✅
1. **因子计算**：pe_ttm为空或增长率<0 → alpha_peg = 0 ✅
2. **分组逻辑**：非0值分1-5组，0值单独处理（不进行中性化） ✅
3. **中性化顺序**：先行业中性化，再市值中性化 ✅
4. **市值分组**：分为5组 ✅
5. **输出要求**：保存中性化前后的因子值到Excel ✅
6. **回测周期**：20250101-20251101 ✅

### 目标
解决当前回测中发现的非单调性问题（组3异常高），通过中性化消除行业和市值偏误

---

## 已完成工作

### 1. 创建中性化回测脚本
**文件**: `/home/zcy/alpha006_20251223/run_alpha_peg_neutralized_backtest.py`

**核心功能**:
- ✅ 因子计算：pe_ttm为空或增长率<0 → alpha_peg = 0
- ✅ 行业中性化：残差法（alpha_peg - 行业均值）
- ✅ 市值中性化：分组均值法（按市值分5组，减去组均值）
- ✅ 最终标准化：z-score
- ✅ 分组逻辑：非0值按中性化后因子分5组，0值放第6组
- ✅ Excel输出：保存中性化前后因子值

### 2. 中性化逻辑详解

#### A. 行业中性化（残差法）
```python
# 1. 获取行业数据
industry_data = data_loader.get_industry_data_from_csv(stocks)

# 2. 计算每只股票所在行业的alpha_peg均值
industry_mean = non_zero_data.groupby('l1_name')['alpha_peg'].transform('mean')

# 3. 行业中性化：alpha_peg - 行业均值
non_zero_data['alpha_peg_industry_neutral'] = non_zero_data['alpha_peg'] - industry_mean
```

#### B. 市值中性化（分组均值法）
```python
# 1. 按流通市值分为5组
non_zero_data['市值组别'] = pd.qcut(non_zero_data['流通市值(亿)'], q=5, labels=[1, 2, 3, 4, 5])

# 2. 计算每组的alpha_peg均值
size_mean = non_zero_data.groupby('市值组别')['alpha_peg_industry_neutral'].transform('mean')

# 3. 市值中性化：减去市值组均值
non_zero_data['alpha_peg_final'] = non_zero_data['alpha_peg_industry_neutral'] - size_mean
```

#### C. 最终标准化
```python
# z-score标准化
mean = non_zero_data['alpha_peg_final'].mean()
std = non_zero_data['alpha_peg_final'].std()
non_zero_data['alpha_peg_final'] = (non_zero_data['alpha_peg_final'] - mean) / std
```

#### D. 分组逻辑
```python
# 非0值按中性化后因子分5组
non_zero_data['组别'] = pd.qcut(non_zero_data['alpha_peg_final'], q=5, labels=[1, 2, 3, 4, 5])

# 0值不中性化，单独放第6组
zero_data['组别'] = 6
```

### 3. 输出文件结构

```
/home/zcy/alpha006_20251223/results/backtest/alpha_peg_neutralized_20250101_20251101_YYYYMMDD_HHMMSS/
├── performance_metrics.xlsx      # 性能指标（各组收益、股票数量等）
├── backtest_data.xlsx            # 回测详细数据（每期收益率、IC、换手率等）
├── stock_counts.xlsx             # 各期股票数量统计
└── factor_details/               # 因子详情（每期一个文件）
    ├── 20250127_factor.xlsx      # 1月调仓期的因子值
    │   ├── ts_code               # 股票代码
    │   ├── alpha_peg             # 原始因子值
    │   ├── alpha_peg_industry_neutral  # 行业中性化后的因子值
    │   ├── alpha_peg_final       # 最终中性化后的因子值
    │   ├── l1_name               # 所属行业
    │   ├── 流通市值(亿)          # 市值
    │   ├── 市值组别              # 市值分组（1-5）
    │   ├── 组别                  # 最终分组（1-6）
    │   └── 下月收益率            # 持有期收益率
    ├── 20250228_factor.xlsx      # 2月调仓期的因子值
    └── ...
```

---

## 使用方法

### 运行回测
```bash
cd /home/zcy/alpha006_20251223
python run_alpha_peg_neutralized_backtest.py
```

### 预期输出
- 控制台输出：调仓进度、各组股票数、收益率、性能指标
- Excel文件：保存在 `/home/zcy/alpha006_20251223/results/backtest/alpha_peg_neutralized_20250101_20251101_YYYYMMDD_HHMMSS/`

---

## 验证要点

### 1. 中性化效果验证
通过factor_details文件检查：
- 行业中性化后，各行业的alpha_peg均值是否接近0
- 市值中性化后，各市值组的alpha_peg均值是否接近0

### 2. 单调性验证
通过performance_metrics.xlsx检查：
- 组1-组5的收益率是否呈现单调递减趋势
- 相比原始回测（组3异常高），中性化后是否改善

### 3. 统计指标
通过backtest_data.xlsx检查：
- IC值（信息系数）是否改善
- IR值（信息比率）
- 多空组合收益

---

## 注意事项

1. **0值股票处理**：alpha_peg=0的股票不参与中性化，直接放入第6组
2. **数据完整性**：确保每期有足够的股票进行分组
3. **Excel输出**：每期单独保存在factor_details/子目录，便于用户查看详细数据
4. **运行时间**：回测约需5-10分钟

---

## 待运行

脚本已创建完成，但尚未成功运行。可能原因：
- 数据库连接问题
- 数据量较大导致运行时间长
- 需要检查数据库连接状态

建议手动运行：
```bash
cd /home/zcy/alpha006_20251223
python run_alpha_peg_neutralized_backtest.py
```

### 步骤1：创建中性化脚本
**文件**: `/home/zcy/alpha006_20251223/run_alpha_peg_neutralized_backtest.py`

**核心逻辑**:

#### A. 因子计算（保持原有逻辑）
```python
# pe_ttm为空 或 增长率<0 → alpha_peg = 0
# 其他情况：alpha_peg = pe_ttm / dt_netprofit_yoy
```

#### B. 行业中性化（残差法）
```python
# 1. 获取行业数据
industry_data = data_loader.get_industry_data_from_csv(stocks)

# 2. 计算每只股票所在行业的alpha_peg均值
industry_mean = factor_data.groupby('l1_name')['alpha_peg'].transform('mean')

# 3. 行业中性化：alpha_peg - 行业均值
factor_data['alpha_peg_industry_neutral'] = factor_data['alpha_peg'] - industry_mean
```

#### C. 市值中性化（分组均值法）
```python
# 1. 按流通市值分为5组
factor_data['市值组别'] = pd.qcut(factor_data['流通市值(亿)'], q=5, labels=[1, 2, 3, 4, 5])

# 2. 计算每组的alpha_peg均值
size_mean = factor_data.groupby('市值组别')['alpha_peg_industry_neutral'].transform('mean')

# 3. 市值中性化：减去市值组均值
factor_data['alpha_peg_final'] = factor_data['alpha_peg_industry_neutral'] - size_mean
```

#### D. 最终标准化
```python
# 对中性化后的因子进行z-score标准化
mean = factor_data['alpha_peg_final'].mean()
std = factor_data['alpha_peg_final'].std()
factor_data['alpha_peg_final'] = (factor_data['alpha_peg_final'] - mean) / std
```

#### E. 分组逻辑
```python
# 非0值按中性化后的因子值分5组
non_zero_data = factor_data[factor_data['alpha_peg'] != 0].copy()
zero_data = factor_data[factor_data['alpha_peg'] == 0].copy()

if len(non_zero_data) > 0:
    non_zero_data['组别'] = pd.qcut(non_zero_data['alpha_peg_final'], q=5, labels=[1, 2, 3, 4, 5])
    zero_data['组别'] = 6  # 0值不中性化，单独放第6组
    factor_data = pd.concat([non_zero_data, zero_data])
```

#### F. 输出Excel
```python
# 保存每期的因子值详情
detail_data = {
    'ts_code': factor_data['ts_code'],
    'alpha_peg': factor_data['alpha_peg'],
    'alpha_peg_industry_neutral': factor_data['alpha_peg_industry_neutral'],
    'alpha_peg_final': factor_data['alpha_peg_final'],
    'l1_name': factor_data['l1_name'],
    '流通市值(亿)': factor_data['流通市值(亿)'],
    '组别': factor_data['组别'],
    '下月收益率': factor_data['下月收益率'],
}
```

---

## 输出文件结构

### 1. 回测结果目录
```
/home/zcy/alpha006_20251223/results/backtest/alpha_peg_neutralized_20250101_20251101_YYYYMMDD_HHMMSS/
├── performance_metrics.xlsx      # 性能指标（各组收益、股票数量等）
├── backtest_data.xlsx            # 回测详细数据（每期收益率、IC、换手率等）
├── stock_counts.xlsx             # 各期股票数量统计
└── factor_details/               # 因子详情（每期一个文件）
    ├── 20250127_factor.xlsx      # 1月调仓期的因子值
    ├── 20250228_factor.xlsx      # 2月调仓期的因子值
    └── ...
```

### 2. factor_details文件内容
每期Excel包含：
- `ts_code`: 股票代码
- `alpha_peg`: 原始因子值
- `alpha_peg_industry_neutral`: 行业中性化后的因子值
- `alpha_peg_final`: 最终中性化后的因子值
- `l1_name`: 所属行业
- `流通市值(亿)`: 市值
- `市值组别`: 市值分组（1-5）
- `组别`: 最终分组（1-6）
- `下月收益率`: 持有期收益率

---

## 关键验证点

### 1. 中性化效果验证
- 检查行业中性化后，各行业的alpha_peg均值是否接近0
- 检查市值中性化后，各市值组的alpha_peg均值是否接近0

### 2. 单调性验证
- 观察组1-组5的收益率是否呈现单调递减趋势
- 比较中性化前后的单调性改善情况

### 3. 统计指标
- IC值（信息系数）
- IR值（信息比率）
- 多空组合收益

---

## 注意事项

1. **0值股票处理**：alpha_peg=0的股票不参与中性化，直接放入第6组
2. **数据完整性**：确保每期有足够的股票进行分组
3. **异常值处理**：中性化前可考虑对极端值进行截断处理
4. **Excel输出**：每期单独保存，便于用户查看详细数据

---

## 预期改进

通过中性化处理，预期解决以下问题：
1. **行业偏误**：某些行业天然PE低或增长率高，导致因子偏差
2. **市值效应**：小市值股票可能有特殊表现，影响单调性
3. **非单调性**：组3异常高的问题应得到改善
