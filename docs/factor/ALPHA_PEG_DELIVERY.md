# alpha_peg因子交付报告

**交付日期**: 2025-12-24
**因子名称**: alpha_peg
**项目**: Alpha006因子项目
**状态**: ✅ 完成交付

---

## 📦 交付内容清单

### 代码文件（2个）
```
code/
├── calc_alpha_peg.py          # 因子计算主程序
└── test_alpha_peg.py          # 逻辑验证脚本
```

### 文档文件（7个）
```
docs/
├── alpha_peg_data_source.md         # 数据来源说明
├── factor_dictionary.md             # 因子字典
├── database_schema.md               # 数据库结构
├── alpha_peg_quick_start.md         # 快速指南
├── FACTOR_INDEX.md                  # 因子索引
├── alpha_peg_development_summary.md # 开发总结
└── [README.md]                      # 已更新
```

### 输出文件（可生成）
```
results/factor/
└── alpha_peg_factor.csv             # 因子结果
```

---

## ✅ 完成清单

### 因子开发
- [x] 因子计算公式定义
- [x] 数据来源确定
- [x] 时间对齐规则设计
- [x] 异常值处理策略
- [x] 代码实现
- [x] 逻辑验证

### 文档编写
- [x] 因子字典（完整定义）
- [x] 数据来源说明（详细）
- [x] 数据库结构文档
- [x] 快速使用指南
- [x] 因子索引
- [x] 开发总结
- [x] README更新

### 质量保证
- [x] 测试数据验证
- [x] 边界情况测试
- [x] 计算准确性验证
- [x] 文档一致性检查

---

## 📊 因子规格

### 基本信息
| 项目 | 内容 |
|------|------|
| 因子名称 | `alpha_peg` |
| 因子类型 | 估值成长因子 |
| 计算公式 | `pe_ttm / dt_netprofit_yoy` |
| 计算频率 | 日频 |
| 标准化 | 无 |

### 数据来源
| 数据项 | 表名 | 字段名 | 更新频率 |
|--------|------|--------|----------|
| 市盈率TTM | `daily_basic` | `pe_ttm` | 日频 |
| 扣非净利润同比增长率 | `fina_indicator` | `dt_netprofit_yoy` | 财报周期 |

### 时间对齐
```
交易日(trade_date) = 公告日(ann_date) + 前向填充
```

### 异常处理
| 异常类型 | 处理方式 |
|----------|----------|
| PE空值/非正 | 跳过 |
| 增长率空值/零值 | 跳过 |
| 负增长 | 保留 |
| 极大值 | 保留 |

---

## 🚀 快速使用

### 1. 运行计算
```bash
cd /home/zcy/alpha006_20251223
python3 code/calc_alpha_peg.py
```

### 2. 查看结果
```python
import pandas as pd
df = pd.read_csv('results/factor/alpha_peg_factor.csv')
print(df.head())
```

### 3. 在策略中使用
```python
from code.calc_alpha_peg import calc_alpha_peg

df = calc_alpha_peg('20240801', '20250305')
low_peg = df[df['alpha_peg'] < 1.0]  # 低估值股票
```

---

## 📖 文档导航

### 新手入门
1. **快速指南** → `docs/alpha_peg_quick_start.md`
2. **因子说明** → `docs/factor_dictionary.md`

### 深入了解
3. **数据来源** → `docs/alpha_peg_data_source.md`
4. **数据库结构** → `docs/database_schema.md`

### 验证与调试
5. **逻辑验证** → `code/test_alpha_peg.py`
6. **开发总结** → `docs/alpha_peg_development_summary.md`

### 快速查找
7. **因子索引** → `docs/FACTOR_INDEX.md`

---

## 🔍 验证步骤

### 步骤1: 验证逻辑
```bash
python3 code/test_alpha_peg.py
```
**预期**: ✅ 所有逻辑验证通过

### 步骤2: 计算因子
```bash
python3 code/calc_alpha_peg.py
```
**预期**: 生成 `results/factor/alpha_peg_factor.csv`

### 步骤3: 检查输出
```python
import pandas as pd
df = pd.read_csv('results/factor/alpha_peg_factor.csv')
print(f"记录数: {len(df):,}")
print(f"字段: {list(df.columns)}")
```
**预期**: 5个字段，数千至数百万条记录

---

## 📈 因子解读

### PEG值含义
| PEG范围 | 估值状态 | 建议 |
|---------|----------|------|
| `< 0.8` | 明显低估 | 重点关注 |
| `0.8 - 1.2` | 估值合理 | 可配置 |
| `1.2 - 1.5` | 略微高估 | 谨慎 |
| `> 1.5` | 明显高估 | 避开 |

### 示例计算
```
股票A:
- pe_ttm = 15.0
- dt_netprofit_yoy = 20.0%
- alpha_peg = 15.0 / 20.0 = 0.75
→ 估值合理偏低

股票B:
- pe_ttm = 30.0
- dt_netprofit_yoy = 15.0%
- alpha_peg = 30.0 / 15.0 = 2.0
→ 估值偏高
```

---

## ⚠️ 注意事项

### 使用前必读
1. **数据依赖**: 需要数据库连接正常
2. **财报滞后**: 财报数据有延迟，非实时
3. **适用范围**: 适用于盈利稳定的成长股
4. **不适用**: 亏损股、周期股、重资产股

### 常见问题
- **空值**: 亏损企业、新股无数据
- **负值**: 负增长时PEG为负，是有效信号
- **极大值**: 高成长低估值时可能出现

---

## 📞 技术支持

### 文档支持
- 所有文档位于 `docs/` 目录
- 使用 `FACTOR_INDEX.md` 快速查找

### 代码支持
- 主程序: `code/calc_alpha_peg.py`
- 测试: `code/test_alpha_peg.py`

### 数据支持
- 数据库配置: `code/db_connection.py`
- 数据结构: `docs/database_schema.md`

---

## 🎯 下一步建议

### 立即执行
1. ✅ 运行测试验证逻辑
2. ✅ 计算全量因子数据
3. ✅ 检查数据质量

### 短期优化
1. 回测验证历史表现
2. 结合其他因子测试
3. 调整阈值优化

### 长期规划
1. 实盘监控因子表现
2. 定期更新财报数据
3. 迭代优化因子逻辑

---

## 📋 交付确认

### 代码完整性
- [x] calc_alpha_peg.py - 完整实现
- [x] test_alpha_peg.py - 完整验证

### 文档完整性
- [x] 数据来源说明
- [x] 因子字典
- [x] 数据库结构
- [x] 快速指南
- [x] 因子索引
- [x] 开发总结
- [x] README更新

### 质量保证
- [x] 逻辑验证通过
- [x] 边界测试通过
- [x] 文档与代码一致
- [x] 命名规范统一

---

## ✨ 特色亮点

### 1. 完整性
- 从需求到交付全流程覆盖
- 代码、文档、测试三位一体

### 2. 准确性
- 严格遵循数据库字段定义
- 精确的时间对齐规则
- 明确的异常值处理

### 3. 可用性
- 3步快速使用指南
- 完整的测试验证
- 丰富的使用示例

### 4. 可维护性
- 清晰的代码结构
- 详细的文档说明
- 规范的命名约定

---

## 🎉 交付总结

**alpha_peg因子开发已完成，可直接投入使用！**

### 核心成果
- ✅ 因子计算代码
- ✅ 完整文档体系
- ✅ 逻辑验证通过
- ✅ 使用指南清晰

### 一句话说明
**alpha_peg = pe_ttm / dt_netprofit_yoy**，用于评估股票估值与成长性的匹配度。

### 快速开始
```bash
python3 code/calc_alpha_peg.py
```

---

**交付人**: Alpha006项目组
**交付日期**: 2025-12-24
**文档版本**: v1.0
**状态**: ✅ 完成
