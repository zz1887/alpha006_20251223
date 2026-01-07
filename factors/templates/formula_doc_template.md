# 因子名称：因子英文名

## 基本信息
- **因子代码**: factor_code
- **因子类型**: 估值/动量/质量/成长/量能/波动率
- **版本**: v1.0
- **更新日期**: 2025-12-30
- **创建者**: 作者名

## 数学公式
```
factor = 计算公式表达式

示例：
factor = pe_ttm / dt_netprofit_yoy
```

## 参数定义
| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| outlier_sigma | float | 3.0 | 异常值阈值（标准差倍数） |
| normalization | str | None | 标准化方法：None/zscore/rank |
| industry_neutral | bool | False | 是否启用行业中性化 |
| lookback_period | int | 20 | 回看周期 |

## 计算逻辑
### 步骤1: 数据获取
- 从数据表获取必需字段
- 时间范围：根据回测周期确定
- 股票池：全A股/特定板块

### 步骤2: 数据预处理
1. 数据类型转换
2. 空值处理
3. 数据排序

### 步骤3: 核心计算
1. 应用数学公式
2. 计算每日因子值

### 步骤4: 异常值处理
1. 识别异常值（> 均值 ± 3σ）
2. 缩尾处理或剔除

### 步骤5: 标准化（可选）
1. Z-score标准化：(x - μ) / σ
2. 秩标准化：分位数排名

### 步骤6: 行业中性化（可选）
1. 计算行业均值
2. 因子值减去行业均值

## 因子含义
### 经济学解释
详细解释因子的经济学含义和理论基础

### 金融逻辑
说明因子为什么有效，背后的市场逻辑

### 预期效果
- 高值代表什么
- 低值代表什么
- 预期与收益率的关系

## 适用场景
- [ ] 成长股筛选
- [ ] 价值投资
- [ ] 动量策略
- [ ] 反转策略
- [ ] 风险控制
- [ ] 行业轮动
- [ ] 市场择时

## 数据要求
| 数据项 | 表名 | 字段名 | 必需 | 更新频率 |
|--------|------|--------|------|----------|
| 市盈率 | daily_basic | pe_ttm | ✅ | 日频 |
| 净利润增长率 | fina_indicator | dt_netprofit_yoy | ✅ | 季频 |
| 行业分类 | sw_industry | l1_name | 可选 | 静态 |
| 成交量 | daily_basic | vol | 可选 | 日频 |

## 异常值处理策略
| 异常类型 | 处理方式 | 触发条件 | 备注 |
|----------|----------|----------|------|
| PE空值/非正 | 跳过 | pe_ttm <= 0 | 无法计算 |
| 增长率空值/零值 | 跳过 | dt_netprofit_yoy = 0 | 避免除零 |
| 极大值 | 缩尾处理 | > 均值 + 3σ | 防止极端值影响 |
| 极小值 | 缩尾处理 | < 均值 - 3σ | 防止极端值影响 |

## 版本差异
| 版本 | outlier_sigma | normalization | industry_neutral | 适用场景 | 预期ICIR |
|------|---------------|---------------|------------------|----------|----------|
| standard | 3.0 | None | False | 基础使用 | 0.05-0.10 |
| conservative | 2.5 | zscore | True | 保守投资 | 0.08-0.12 |
| aggressive | 3.5 | rank | True | 激进投资 | 0.10-0.15 |

## 代码示例
### 基础使用
```python
from factors import FactorRegistry

# 获取因子实例
factor = FactorRegistry.get_factor('factor_code', version='standard')

# 计算因子
data = pd.DataFrame({
    'ts_code': ['000001.SZ', '000001.SZ'],
    'trade_date': ['20240101', '20240102'],
    'pe_ttm': [10, 12],
    'dt_netprofit_yoy': [0.2, 0.25]
})

result = factor.calculate(data)
print(result)
```

### 完整评估
```python
from factors.evaluation import FactorEvaluationReport

# 1. 计算因子
factor = FactorRegistry.get_factor('factor_code')
factor_df = factor.calculate(data)

# 2. 获取价格数据
price_df = load_price_data()

# 3. 运行评估
report = FactorEvaluationReport('factor_code')
metrics = report.run_full_evaluation(factor_df, price_df, hold_days=20)

# 4. 生成报告
report_text = report.generate_report()
print(report_text)
```

### 批量测试
```python
from factors.research import FactorDiscovery

# 测试不同参数版本
versions = ['standard', 'conservative', 'aggressive']
results = {}

for version in versions:
    factor = FactorRegistry.get_factor('factor_code', version=version)
    factor_df = factor.calculate(data)

    # 评估
    effectiveness = FactorDiscovery.calculate_factor_effectiveness(
        factor_df, forward_returns
    )
    results[version] = effectiveness

print(results)
```

## 性能指标
### 历史回测统计（示例）
| 指标 | 数值 | 说明 |
|------|------|------|
| IC均值 | 0.05 | 信息系数 |
| ICIR | 0.12 | 信息比率 |
| 分组1-5差 | 15% | 收益区分度 |
| 换手率 | 25% | 交易成本影响 |
| 稳定性得分 | 85/100 | 时序稳定性 |
| 综合评分 | 78/100 | 整体质量 |

### 不同市场环境表现
| 市场环境 | IC均值 | ICIR | 说明 |
|----------|--------|------|------|
| 牛市 | 0.06 | 0.15 | 表现优秀 |
| 熊市 | 0.04 | 0.10 | 表现稳定 |
| 震荡市 | 0.05 | 0.11 | 表现良好 |

## 风险提示
1. **数据质量风险**: 依赖财务数据准确性
2. **失效风险**: 市场结构变化可能导致因子失效
3. **行业风险**: 未行业中性化可能受行业影响
4. **过拟合风险**: 参数优化需谨慎

## 参考文献
1. 作者名, "论文/书籍标题", 出版年份
2. 作者名, "因子研究报告", 日期
3. 相关技术文档链接

## 更新日志
### v1.0 (2025-12-30)
- 初始版本
- 完成基础计算逻辑
- 通过初步测试

---

**文档维护**: 请定期更新此文档以反映因子的任何变更
**最后更新**: 2025-12-30
