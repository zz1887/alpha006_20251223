# 量化因子库重构指南

**重构版本**: v2.0
**重构日期**: 2025-12-30
**重构原则**: 最小改动 + 最大优化
**适用环境**: WSL Ubuntu / Linux

---

## 一、重构概述

### 1.1 重构目标

| 指标 | 重构前 | 重构后 | 改进幅度 |
|------|--------|--------|----------|
| 文件数量 | ~50+ 脚本 | ~15 核心脚本 | ↓ 70% |
| 代码重复率 | ~40% | <10% | ↓ 75% |
| 参数管理 | 多处硬编码 | 集中配置 | 100% |
| 异常处理 | 缺失 | 完整 | 100% |
| 文档完整性 | 分散重复 | 统一完善 | 100% |
| 因子字典 | 简略 | 标准化 | 100% |

### 1.2 重构范围

#### ✅ 保留的核心功能
1. **因子计算逻辑**（不修改公式）
2. **数据读取流程**（保持数据库接口）
3. **Excel输出格式**（保持兼容性）
4. **回测核心算法**（保持收益计算）
5. **20250919多因子计算**（核心验证案例）

#### 🔧 优化的冗余内容
1. **重复脚本**（合并为通用脚本）
2. **测试残留**（删除test_*.py）
3. **临时文件**（清理results临时输出）
4. **注释代码**（删除废弃逻辑）
5. **冗余打印**（简化日志输出）

#### ➕ 新增的标准化内容
1. **配置管理层**（config/）
2. **通用工具层**（core/utils/）
3. **因子计算层**（factors/）
4. **执行脚本层**（scripts/）
5. **标准文档层**（docs/）

---

## 二、新目录结构

```
alpha006_20251223/
├── core/                           # 核心工具层
│   ├── config/                     # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py             # 全局配置
│   │   └── params.py               # 因子参数
│   ├── utils/                      # 通用工具
│   │   ├── __init__.py
│   │   ├── db_connection.py        # 数据库连接
│   │   ├── data_loader.py          # 数据加载
│   │   ├── data_processor.py       # 数据处理
│   │   └── logger.py               # 日志工具
│   └── constants/                  # 常量定义
│       ├── __init__.py
│       └── config.py               # 表名、字段常量
│
├── factors/                        # 因子模块
│   ├── __init__.py
│   ├── base.py                     # 因子基类
│   ├── valuation/                  # 估值因子
│   │   ├── __init__.py
│   │   └── alpha_peg.py            # PEG因子
│   ├── momentum/                   # 动量因子
│   │   ├── __init__.py
│   │   └── alpha_pluse.py          # 量能因子
│   ├── price/                      # 价格因子
│   │   ├── __init__.py
│   │   ├── alpha_038.py            # 价格强度
│   │   └── alpha_120cq.py          # 价格位置
│   └── volume/                     # 量能因子
│       ├── __init__.py
│       └── cr_qfq.py               # CR指标
│
├── scripts/                        # 执行脚本
│   ├── __init__.py
│   ├── run_factor_generation.py    # 因子计算
│   ├── run_backtest.py             # 回测执行
│   ├── run_optimization.py         # 参数优化
│   └── run_strategy3.py            # 策略3计算
│
├── data/                           # 数据目录
│   ├── raw/                        # 原始数据
│   ├── processed/                  # 处理数据
│   ├── cache/                      # 缓存数据
│   └── README.md
│
├── docs/                           # 文档目录
│   ├── factor_dictionary.md        # 因子字典
│   ├── REFACTORING_GUIDE.md        # 重构指南
│   ├── PROJECT_ANALYSIS_REPORT.md  # 项目分析
│   └── archive/                    # 历史文档
│
├── results/                        # 结果输出
│   ├── factor/                     # 因子结果
│   ├── backtest/                   # 回测结果
│   ├── output/                     # 输出文件
│   └── visual/                     # 可视化
│
├── temp/                           # 临时目录
├── config/                         # 配置目录（兼容旧版）
├── code/                           # 代码目录（归档旧代码）
├── logs/                           # 日志目录
└── README.md                       # 项目说明
```

---

## 三、核心变更说明

### 3.1 配置管理统一化

#### 旧版问题
```python
# 多处重复定义
window_20d = 20
lookback_14d = 14
lower_mult = 1.4
upper_mult = 3.5
```

#### 新版方案
```python
# core/config/params.py
FACTOR_PARAMS = {
    'alpha_pluse': {
        'window_20d': 20,
        'lookback_14d': 14,
        'lower_mult': 1.4,
        'upper_mult': 3.5,
        'min_count': 2,
        'max_count': 4,
    },
    'alpha_038': {
        'window': 10,
    },
    'alpha_120cq': {
        'window': 120,
        'min_days': 30,
    },
    'alpha_peg': {
        'outlier_sigma': 3.0,
        'update_flag': '1',
    },
    'cr_qfq': {
        'period': 20,
    }
}
```

### 3.2 因子计算模块化

#### 旧版问题
```
code/calculate_factors_20250919.py          # 基础计算
code/calculate_factors_with_industry_zscore.py  # 行业标准化
code/calculate_multi_factors_20250919.py    # 多因子计算
code/calculate_strategy3_20251229.py        # 策略3计算
code/calculate_alpha_120cq.py               # alpha_120cq单独计算
```

#### 新版方案
```python
# factors/valuation/alpha_peg.py
class AlphaPEGFactor:
    def __init__(self, params=None):
        self.params = params or FACTOR_PARAMS['alpha_peg']

    def calculate(self, df_pe, df_fina):
        """计算原始alpha_peg"""
        # 统一逻辑

    def calculate_industry_zscore(self, df_peg, df_industry):
        """计算行业Z-Score"""
        # 统一逻辑

    def select_top_n_by_industry(self, df, top_n=3):
        """按行业选股"""
        # 统一逻辑
```

### 3.3 异常处理完整化

#### 旧版问题
```python
# 缺少异常处理
def calculate(self, df_price):
    # 缺少参数验证
    # 缺少数据类型检查
    # 缺少空值处理
    # 缺少异常捕获
```

#### 新版方案
```python
def calculate(self, df_price):
    """计算因子（带完整异常处理）"""
    try:
        # 参数验证
        if df_price is None or len(df_price) == 0:
            raise ValueError("输入数据为空")

        # 数据类型检查
        required_cols = ['ts_code', 'trade_date', 'close']
        for col in required_cols:
            if col not in df_price.columns:
                raise ValueError(f"缺少必要列: {col}")

        # 空值处理
        if df_price['close'].isna().any():
            df_price = df_price.dropna(subset=['close'])

        # 计算逻辑
        result = self._calculate_logic(df_price)

        return result

    except Exception as e:
        logger.error(f"因子计算失败: {str(e)}")
        return pd.DataFrame()
```

---

## 四、因子计算流程标准化

### 4.1 标准计算流程

```python
# scripts/run_factor_generation.py
from core.utils.db_connection import db
from core.config.params import FACTOR_PARAMS
from factors.valuation.alpha_peg import AlphaPEGFactor
from factors.momentum.alpha_pluse import AlphaPluseFactor

def main():
    # 1. 数据准备
    stocks = get_tradable_stocks(target_date)
    price_data = get_price_data(stocks, date_range)
    fina_data = get_fina_data(stocks)
    industry_data = get_industry_data(stocks)

    # 2. 因子计算
    alpha_peg = AlphaPEGFactor(FACTOR_PARAMS['alpha_peg'])
    df_peg = alpha_peg.calculate(price_data, fina_data)
    df_peg_zscore = alpha_peg.calculate_industry_zscore(df_peg, industry_data)

    alpha_pluse = AlphaPluseFactor(FACTOR_PARAMS['alpha_pluse'])
    df_pluse = alpha_pluse.calculate(price_data)

    # 3. 数据合并
    df_merged = merge_factors([df_peg_zscore, df_pluse, ...])

    # 4. 结果输出
    export_to_excel(df_merged, output_path)
```

### 4.2 策略3计算流程

```python
# scripts/run_strategy3.py
def calculate_strategy3_score(df):
    """
    策略3综合得分公式:
    综合得分 = 0.20 * (1 - alpha_pluse) +
              0.25 * (-行业标准化alpha_peg) +
              0.15 * alpha_120cq +
              0.20 * (cr_qfq / cr_qfq.max()) +
              0.20 * (-alpha_038 / alpha_038.min())
    """
    # 1. 因子标准化
    factor_1 = 1 - df['alpha_pluse']  # 量能（反向）
    factor_2 = -df['行业标准化alpha_peg']  # 估值（负向）
    factor_3 = df['alpha_120cq']  # 位置（正向）
    factor_4 = df['cr_qfq'] / df['cr_qfq'].max()  # 动量（标准化）
    factor_5 = -df['alpha_038'] / df['alpha_038'].min()  # 强度（负向）

    # 2. 加权求和
    df['综合得分'] = (
        0.20 * factor_1 +
        0.25 * factor_2 +
        0.15 * factor_3 +
        0.20 * factor_4 +
        0.20 * factor_5
    )

    return df
```

---

## 五、数据管理规范

### 5.1 数据版本管理

```python
# core/config/settings.py
DATA_VERSION = "v2.0"
TARGET_DATE = "20251229"

# 数据路径
PATHS = {
    'raw': 'data/raw/',
    'processed': 'data/processed/',
    'cache': 'data/cache/',
    'output': 'results/output/',
    'factor': 'results/factor/',
    'backtest': 'results/backtest/',
}
```

### 5.2 数据质量检查

```python
def data_quality_check(df, factor_name):
    """数据质量检查清单"""
    checks = {
        '完整性': df.notna().mean() > 0.8,
        '异常值比例': (df.abs() > 3*df.std()).mean() < 0.05,
        '值域合理': df.min() > -1000 and df.max() < 1000,
        '统计特征': abs(df.mean()) < 10 and df.std() < 5,
    }

    return all(checks.values())
```

---

## 六、执行流程

### 6.1 重构执行步骤

#### 阶段1：清理冗余（1小时）
```bash
# 删除测试脚本和临时文件
rm code/test_*.py
rm code/verify_*.py
rm code/quick_test.py

# 清理results目录
rm results/output/~$*.xlsx
rm results/output/*_backup_*.xlsx
```

#### 阶段2：迁移核心代码（2小时）
```bash
# 迁移配置文件
cp config/backtest_config.py core/config/
cp config/hold_days_config.py core/config/

# 迁移工具函数
cp core/utils/data_processor.py core/utils/
cp core/utils/data_loader.py core/utils/
cp core/utils/db_connection.py core/utils/

# 迁移因子模块
cp code/calculate_strategy3_20251229.py scripts/run_strategy3.py
```

#### 阶段3：标准化改造（2小时）
```bash
# 创建标准化配置
python scripts/create_standard_config.py

# 创建因子基类
python scripts/create_factor_base.py

# 验证因子计算
python scripts/run_strategy3.py
```

#### 阶段4：文档完善（1小时）
```bash
# 生成因子字典
python scripts/generate_factor_dict.py

# 生成重构报告
python scripts/generate_refactoring_report.py
```

#### 阶段5：功能验证（1小时）
```bash
# 运行20250919多因子计算（验证兼容性）
python scripts/run_factor_generation.py --date 20250919

# 运行20251229策略3计算（验证新功能）
python scripts/run_strategy3.py --date 20251229

# 生成验证报告
python scripts/verify_functionality.py
```

---

## 七、兼容性保证

### 7.1 向后兼容策略

1. **保留旧接口**：在`code/`目录下保留关键旧脚本作为备份
2. **渐进式迁移**：新旧代码并行运行，验证一致性
3. **数据格式不变**：Excel输出格式保持完全一致
4. **参数映射**：新旧参数名称自动映射

### 7.2 验证方法

```python
# 验证新旧结果一致性
def verify_compatibility(old_result, new_result):
    """验证新旧结果是否一致"""
    # 检查列名
    assert set(old_result.columns) == set(new_result.columns)

    # 检查数据（允许微小浮点误差）
    for col in old_result.columns:
        if col in ['股票代码', '交易日', '申万一级行业', '备注']:
            continue
        diff = (old_result[col] - new_result[col]).abs().max()
        assert diff < 0.0001, f"列{col}差异过大: {diff}"

    return True
```

---

## 八、风险控制

### 8.1 低风险操作（必须完成）
- ✅ 文件清理（删除空文件、测试残留）
- ✅ 目录结构调整
- ✅ 配置文件统一
- ✅ 文档整理

### 8.2 中风险操作（建议完成）
- ⚠️ 代码合并（重复逻辑提取）
- ⚠️ 异常处理补充
- ⚠️ 因子模块标准化

### 8.3 高风险操作（谨慎操作）
- ❌ 修改核心计算公式
- ❌ 改变数据处理流程
- ❌ 调整回测逻辑

---

## 九、预期收益

### 9.1 可维护性提升
- 文件数量减少 **70%**
- 代码重复率降低 **75%**
- 新增因子开发时间减少 **50%**

### 9.2 协作效率提升
- 因子字典标准化，新人上手时间减少 **70%**
- 配置集中管理，参数调整效率提升 **80%**
- 文档完善，沟通成本降低 **60%**

### 9.3 代码质量提升
- 异常处理覆盖率 **100%**
- 参数管理统一化 **100%**
- 模块化程度提升 **90%**

---

## 十、快速参考

### 10.1 常用命令

```bash
# 运行策略3计算
python scripts/run_strategy3.py --date 20251229

# 运行因子生成
python scripts/run_factor_generation.py --date 20250919

# 运行回测
python scripts/run_backtest.py --strategy strategy3 --period 20250919-20251229

# 查看因子字典
cat docs/factor_dictionary.md

# 查看重构指南
cat docs/REFACTORING_GUIDE.md
```

### 10.2 因子调用示例

```python
# 单因子调用
from factors.valuation.alpha_peg import AlphaPEGFactor

factor = AlphaPEGFactor(params={'outlier_sigma': 3.0})
result = factor.calculate_by_period('20250901', '20250919')
selected = factor.select_top_n_by_industry(result, top_n=3)

# 多因子组合
from core.utils.data_processor import calculate_rank

score = (
    0.20 * (1 - alpha_pluse) +
    0.25 * (-alpha_peg_zscore) +
    0.15 * alpha_120cq +
    0.20 * (cr_qfq / cr_qfq.max()) +
    0.20 * (-alpha_038 / alpha_038.min())
)
```

---

## 十一、维护说明

### 11.1 更新频率
- 因子逻辑变更时及时更新
- 数据结构变化时同步更新
- 每季度进行一次全面审查

### 11.2 维护团队
- **主维护**: 量化策略组
- **审核**: 技术负责人
- **文档**: 策略研究员

### 11.3 联系方式
- 问题反馈: 通过Git Issue提交
- 代码审查: Pull Request流程
- 文档更新: 直接编辑Markdown文件

---

**文档状态**: ✅ 完成标准化
**版本**: v2.0
**更新日期**: 2025-12-30
**下一步**: 执行重构计划

---

## 附录：快速检查清单

### 重构前检查
- [ ] 备份所有原始文件
- [ ] 记录当前运行结果
- [ ] 确认数据库连接正常
- [ ] 检查磁盘空间

### 重构中检查
- [ ] 每步操作后验证功能
- [ ] 保持旧代码可回滚
- [ ] 及时更新文档
- [ ] 记录所有变更

### 重构后验证
- [ ] 运行20250919计算，对比结果
- [ ] 运行20251229计算，验证新功能
- [ ] 检查所有因子输出格式
- [ ] 确认文档完整性

---

**重构完成标志**: 所有检查项✅且功能验证通过