# Alpha006因子库架构说明

## 📋 项目概述

**项目名称**: Alpha006增强因子库
**版本**: v2.0
**创建日期**: 2026-01-05
**项目路径**: `/home/zcy/alpha因子库`

---

## 🏗️ 架构设计

### 五层架构体系

```
factors/
├── 📁 core/              # 核心基础层
│   ├── base_factor.py        # 因子基类（抽象类）
│   ├── factor_registry.py    # 因子注册器（统一接口）
│   ├── data_validator.py     # 数据验证器
│   └── normalization.py      # 标准化工具
│
├── 📁 formula/           # 因子公式库
│   ├── formula_template.md   # 公式文档模板
│   ├── alpha_peg.md          # 估值因子公式
│   ├── alpha_010.md          # 趋势因子公式
│   ├── alpha_038.md          # 强度因子公式
│   ├── alpha_120cq.md        # 位置因子公式
│   ├── cr_qfq.md             # 动量因子公式
│   └── alpha_pluse.md        # 量能因子公式
│
├── 📁 calculation/       # 因子计算库
│   ├── __init__.py
│   ├── alpha_peg.py          # 估值因子实现
│   ├── alpha_010.py          # 趋势因子实现
│   ├── alpha_038.py          # 强度因子实现
│   ├── alpha_120cq.py        # 位置因子实现
│   ├── cr_qfq.py             # 动量因子实现
│   ├── alpha_pluse.py        # 量能因子实现
│   └── multi_factor.py       # 多因子合成
│
├── 📁 evaluation/        # 因子评估库
│   ├── __init__.py
│   ├── metrics.py            # 评价指标计算（IC/ICIR/分组回测）
│   ├── backtest.py           # 因子回测引擎
│   ├── analysis.py           # 因子分析工具
│   └── report.py             # 评估报告生成器
│
├── 📁 testing/           # 因子测试库
│   ├── __init__.py
│   ├── unit_test.py          # 单元测试
│   ├── integration_test.py   # 集成测试
│   ├── performance_test.py   # 性能测试
│   └── validation.py         # 逻辑验证
│
├── 📁 research/          # 因子研究工具
│   ├── __init__.py
│   ├── discovery.py          # 因子发现
│   ├── correlation.py        # 相关性分析
│   ├── ic_analysis.py        # IC时序分析
│   └── factor_combine.py     # 因子组合优化
│
├── 📁 documentation/     # 文档库
│   ├── __init__.py
│   ├── generator.py          # 文档生成器
│   ├── factor_dictionary.md  # 因子字典
│   ├── formula_guide.md      # 公式指南
│   ├── calculation_guide.md  # 计算指南
│   ├── evaluation_guide.md   # 评估指南
│   └── usage_examples.md     # 使用示例
│
├── 📁 utils/             # 工具函数
│   ├── __init__.py
│   ├── data_loader.py        # 数据加载
│   ├── data_processor.py     # 数据处理
│   ├── outlier_handler.py    # 异常值处理
│   └── validator.py          # 验证器
│
├── 📁 templates/         # 模板文件
│   ├── __init__.py
│   ├── factor_class_template.py      # 因子类模板
│   ├── formula_doc_template.md       # 公式文档模板
│   ├── test_template.py              # 测试模板
│   └── evaluation_template.py        # 评估模板
│
├── 📁 valuation/         # 估值因子（现有）
│   └── VAL_GROW_行业_Q.py    # alpha_peg（行业优化版）
│
├── 📁 price/             # 价格因子（现有）
│   ├── PRI_TREND_4D_V2.py   # alpha_010
│   ├── PRI_STR_10D_V2.py    # alpha_038
│   └── PRI_POS_120D_V2.py   # alpha_120cq
│
├── 📁 momentum/          # 动量因子（现有）
│   └── MOM_CR_20D_V2.py     # cr_qfq
│
├── 📁 volume/            # 量能因子（现有）
│   └── VOL_EXP_20D_V2.py    # alpha_pluse
│
├── 📁 alpha101/          # Alpha101框架
│   ├── alpha101_base.py
│   ├── alpha101_calculator.py
│   └── alpha101_formulas.py
│
├── 📁 industry/          # 行业中性化
│   ├── industry_neutralization_real.py
│   ├── industry_adjustment.py
│   └── industry_mapping.py
│
└── 📁 __init__.py        # 统一入口
```

---

## 🔧 核心组件详解

### 1. 因子基类 (BaseFactor)

**文件**: `factors/core/base_factor.py`

**功能**:
- 定义因子计算的标准接口
- 提供基础验证和统计方法
- 支持参数管理和缓存

**关键方法**:
```python
get_default_params()    # 获取默认参数
calculate(data)         # 计算因子值（需实现）
validate_data(data)     # 数据验证
get_factor_stats()      # 获取统计信息
```

### 2. 因子注册器 (FactorRegistry)

**文件**: `factors/core/factor_registry.py`

**功能**:
- 统一因子管理
- 插件式注册机制
- 版本控制

**使用方式**:
```python
# 注册因子
FactorRegistry.register('alpha_peg', AlphaPegFactor, 'valuation')

# 获取因子
factor = FactorRegistry.get_factor('alpha_peg', version='standard')
```

### 3. 评估体系 (Evaluation)

**文件**: `factors/evaluation/`

**核心指标**:
- **IC (信息系数)**: 因子与未来收益的相关性
- **ICIR (信息比率)**: IC的稳定性
- **分组回测**: 因子分组后的收益差异
- **换手率**: 交易成本影响
- **稳定性**: 时序稳定性

**综合评分算法**:
```
总分 = ICIR×40% + 稳定性×30% + 分组差异×20% + 换手率×10%
```

---

## 📊 因子生命周期

### 完整流程

```
1. 因子发现
   └─> 研究工具 → 假设生成 → 初步验证

2. 因子定义
   └─> 数学公式 → 参数定义 → 逻辑说明

3. 因子实现
   └─> 代码编写 → 单元测试 → 数据验证

4. 因子评估
   └─> IC分析 → 分组回测 → 综合评分

5. 因子优化
   └─> 参数调优 → 版本管理 → 性能优化

6. 因子应用
   └─> 策略集成 → 回测验证 → 实盘监控

7. 因子维护
   └─> 定期评估 → 失效检测 → 版本更新
```

### 因子状态

```python
FACTOR_STATUS = {
    'RESEARCH': '研究中',      # 阶段1-2
    'DEVELOPING': '开发中',    # 阶段3
    'TESTING': '测试中',       # 阶段4
    'VALIDATED': '已验证',     # 阶段5
    'PRODUCTION': '生产中',    # 阶段6
    'DEPRECATED': '已废弃',    # 维护阶段
}
```

---

## 🚀 使用指南

### 快速开始

#### 1. 计算单因子

```python
from factors.core.factor_registry import FactorRegistry

# 获取因子
factor = FactorRegistry.get_factor('alpha_010', version='standard')

# 准备数据
data = pd.DataFrame({
    'ts_code': ['000001.SZ', '000002.SZ'],
    'trade_date': ['20240101', '20240102'],
    'close': [10.5, 20.3],
    # ... 其他必需字段
})

# 计算因子
result = factor.calculate(data)
print(result)
```

#### 2. 完整评估

```python
from factors.evaluation import FactorEvaluationReport

# 1. 计算因子
factor = FactorRegistry.get_factor('alpha_010')
factor_df = factor.calculate(data)

# 2. 获取价格数据
price_df = load_price_data()

# 3. 运行评估
report = FactorEvaluationReport('alpha_010')
metrics = report.run_full_evaluation(
    factor_df=factor_df,
    price_df=price_df,
    hold_days=20,
    n_groups=5
)

# 4. 生成报告
report_text = report.generate_report()
print(report_text)
```

#### 3. 因子研究

```python
from factors.research import FactorCorrelationAnalyzer, ICAnalyzer

# 相关性分析
analyzer = FactorCorrelationAnalyzer(factor_df)
corr_matrix = analyzer.calculate_correlation()
report = analyzer.generate_analysis_report()

# IC分析
ic_analyzer = ICAnalyzer(ic_series)
analysis = ic_analyzer.generate_ic_analysis_report()
```

---

## 📚 文档体系

### 文档链结构

```
docs/
├── 因子字典 (factor_dictionary.md)
├── 公式指南 (formula_guide.md)
├── 计算指南 (calculation_guide.md)
├── 评估指南 (evaluation_guide.md)
├── 使用示例 (usage_examples.md)
└── 技术文档
    ├── 数据库结构.md
    ├── 参数配置说明.md
    ├── 性能优化指南.md
    └── 常见问题解答.md
```

### 文档生成

```python
from factors.documentation import FactorDocGenerator

# 生成单因子文档
doc = FactorDocGenerator.generate_factor_doc(
    factor_name='alpha_peg',
    formula='pe_ttm / dt_netprofit_yoy',
    params={'outlier_sigma': 3.0},
    logic='PEG比率 = 市盈率 / 盈利增长率'
)

# 生成因子字典
dictionary = FactorDocGenerator.generate_factor_dictionary()
```

---

## 🎯 核心优势

### 1. **标准化**
- 统一的因子接口
- 标准化的公式文档
- 规范化的评估体系

### 2. **可扩展性**
- 插件式因子注册
- 模块化架构设计
- 灵活的参数配置

### 3. **可维护性**
- 完整的文档链
- 自动化测试
- 版本管理

### 4. **可追溯性**
- 计算过程透明
- 评估结果可复现
- 因子演化历史

---

## 🔍 关键文件说明

| 文件 | 作用 | 重要性 |
|------|------|--------|
| `core/base_factor.py` | 因子基类 | ⭐⭐⭐⭐⭐ |
| `core/factor_registry.py` | 因子注册器 | ⭐⭐⭐⭐⭐ |
| `evaluation/metrics.py` | 评价指标 | ⭐⭐⭐⭐⭐ |
| `evaluation/report.py` | 评估报告 | ⭐⭐⭐⭐ |
| `utils/data_loader.py` | 数据加载 | ⭐⭐⭐ |
| `templates/factor_class_template.py` | 因子模板 | ⭐⭐⭐⭐ |

---

## 📈 版本演进

### v1.0 (原始版本)
- 6个核心因子
- 基础回测系统
- 零散文档

### v2.0 (当前版本 - 建设中)
- 完整5层架构
- 标准化接口
- 完整评估体系
- 系统化文档

### v3.0 (规划中)
- 20+ 因子库
- 智能因子发现
- 机器学习集成
- 实时监控

---

## 🛠️ 开发规范

### 代码规范
1. 所有因子必须继承 `BaseFactor`
2. 必须实现 `calculate()` 方法
3. 必须包含数据验证
4. 必须有完整的参数说明

### 文档规范
1. 每个因子必须有公式文档
2. 必须包含数学公式
3. 必须说明参数含义
4. 必须提供使用示例

### 测试规范
1. 单元测试覆盖率 > 80%
2. 必须测试边界情况
3. 必须测试异常处理
4. 必须测试性能

---

## 📞 联系与维护

**维护者**: 项目团队
**更新日期**: 2026-01-05
**下次评估**: 2026-02-05

---

**文档说明**: 此文档为架构总览，详细使用说明请参考各子模块文档。
