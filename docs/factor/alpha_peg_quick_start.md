# alpha_peg因子快速使用指南

**版本**: v1.1
**更新**: 2025-12-24

---

## 一、快速开始（3步完成）

### 步骤1: 计算因子
```python
from code.calc_alpha_peg_industry import calc_alpha_peg_industry

# 基础行业优化版
df = calc_alpha_peg_industry(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    normalization=None
)
```

### 步骤2: 运行回测
```python
from code.backtest_alpha_peg_industry import run_backtest

results = run_backtest(
    start_date='20250101',
    end_date='20250630',
    outlier_sigma=3.0,
    quantiles=5,
    holding_days=10
)
```

### 步骤3: 查看结果
```python
# IC值
print(f"IC均值: {results['summary']['ic_mean']:.4f}")

# 分层收益
q_returns = results['quantile_returns'].groupby('quantile')['return'].mean()
print(q_returns)

# 累计收益
cum_ret = results['cumulative_returns']['cumulative_return'].iloc[-1]
print(f"总收益: {cum_ret:.4f}")
```

---

## 二、因子说明

### 计算公式
```
alpha_peg = pe_ttm / dt_netprofit_yoy
```

### 解读
| PEG值 | 含义 | 建议 |
|-------|------|------|
| `< 0.8` | 明显低估 | 重点关注 |
| `0.8 - 1.2` | 估值合理 | 可配置 |
| `> 1.5` | 可能高估 | 谨慎 |

### 数据来源
- **pe_ttm**: daily_basic.pe_ttm (日频)
- **dt_netprofit_yoy**: fina_indicator.dt_netprofit_yoy (财报周期，前向填充)

---

## 三、代码示例

### 3.1 基础使用
```python
from code.calc_alpha_peg import calc_alpha_peg

# 计算指定日期范围
df = calc_alpha_peg('20240801', '20250305')

# 结果字段
# ts_code, trade_date, pe_ttm, dt_netprofit_yoy, alpha_peg
```

### 3.2 自定义输出路径
```python
df = calc_alpha_peg(
    start_date='20240801',
    end_date='20250305',
    output_path='/path/to/custom_output.csv'
)
```

### 3.3 读取并分析
```python
import pandas as pd

# 读取结果
df = pd.read_csv('results/factor/alpha_peg_factor.csv')

# 基本统计
print(f"记录数: {len(df):,}")
print(f"股票数: {df['ts_code'].nunique()}")
print(f"PEG均值: {df['alpha_peg'].mean():.4f}")

# 筛选示例
low_peg = df[df['alpha_peg'] < 1.0]  # 低估
high_growth = df[df['dt_netprofit_yoy'] > 30]  # 高成长
```

---

## 四、常见问题

### Q: 如何验证计算是否正确？
```bash
python3 code/test_alpha_peg.py
```
运行测试脚本，验证逻辑准确性。

### Q: 数据更新频率？
- `pe_ttm`: 每日收盘后更新
- `dt_netprofit_yoy`: 财报公告日更新
- `alpha_peg`: 每日计算（T+1）

### Q: 空值如何处理？
- PE为空（亏损企业）→ 跳过
- 增长率为空 → 跳过
- 增长率为零 → 跳过
- 最终因子值为空 → 不输出

### Q: 负增长如何处理？
保留！负增长是有效信号：
```python
# 负增长示例
pe_ttm = 8.0
dt_netprofit_yoy = -5.0
alpha_peg = 8.0 / -5.0 = -1.6  # 保留
```

---

## 五、完整文档

| 文档 | 说明 |
|------|------|
| `alpha_peg_data_source.md` | 数据来源详细说明 |
| `factor_dictionary.md` | 因子字典（含alpha_peg） |
| `database_schema.md` | 数据库结构 |
| `calc_alpha_peg.py` | 代码实现 |
| `test_alpha_peg.py` | 逻辑验证 |

---

## 六、快速验证

### 验证步骤
1. **检查数据**: 确认数据库连接正常
2. **运行计算**: 执行 `calc_alpha_peg.py`
3. **查看输出**: 检查 `alpha_peg_factor.csv`
4. **验证逻辑**: 运行 `test_alpha_peg.py`

### 预期输出
```
✓ 获取daily_basic数据: X,XXX 条记录
✓ 获取fina_indicator数据: X,XXX 条记录
✓ 结果已保存: results/factor/alpha_peg_factor.csv
  记录数: X,XXX
  股票数: XXX
```

---

## 七、注意事项

⚠️ **重要提示**:
1. 首次使用请先运行测试验证逻辑
2. 确保数据库连接配置正确
3. 财报数据有滞后性，注意时间对齐
4. 不建议对因子结果做标准化处理

---

**最后更新**: 2025-12-24
**维护**: Alpha006项目组
