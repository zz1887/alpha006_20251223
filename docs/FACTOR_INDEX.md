# Alpha006因子项目 - 因子索引

**文档版本**: v1.0
**更新日期**: 2025-12-24

---

## 📋 因子清单

| 因子名称 | 类型 | 计算公式 | 状态 | 文档 |
|----------|------|----------|------|------|
| **alpha_peg** | 估值成长 | pe_ttm / dt_netprofit_yoy | ✅ 新增 | [详情](#alpha_peg) |
| alpha006_v1 | 吸筹信号 | turnover + atr + ma | ⚠️ 失效 | [原项目](../README.md) |
| alpha006_v2 | 吸筹信号 | 动态阈值 | ⚠️ 失效 | [原项目](../README.md) |
| alpha006_v3 | 吸筹信号 | 方差法 | ⚠️ 失效 | [原项目](../README.md) |

---

## alpha_peg

### 基本信息
- **因子名称**: `alpha_peg`
- **因子类型**: 估值成长因子
- **计算频率**: 日频
- **标准化**: 否

### 计算公式
```
alpha_peg = pe_ttm / dt_netprofit_yoy
```

### 数据来源
| 数据项 | 表名 | 字段名 |
|--------|------|--------|
| 市盈率 | `daily_basic` | `pe_ttm` |
| 增长率 | `fina_indicator` | `dt_netprofit_yoy` |

### 因子含义
PEG比率（市盈率相对盈利增长比率），用于评估股票估值与成长性的匹配度。

**解读**:
- `alpha_peg < 1`: 估值低于成长性，可能被低估
- `alpha_peg = 1`: 估值与成长性匹配，合理
- `alpha_peg > 1`: 估值高于成长性，可能被高估

### 适用场景
- 成长股筛选
- 价值投资
- 风险控制
- 行业轮动

### 异常值处理
| 异常类型 | 处理方式 |
|----------|----------|
| PE空值/非正 | 跳过 |
| 增长率空值/零值 | 跳过 |
| 负增长 | 保留 |
| 极大值 | 保留 |

### 时间对齐
```
交易日(trade_date) = 公告日(ann_date) + 前向填充
```

### 代码使用
```python
from code.calc_alpha_peg import calc_alpha_peg

df = calc_alpha_peg('20240801', '20250305')
```

### 相关文档
- 📄 [数据来源说明](alpha_peg_data_source.md)
- 📄 [因子字典详情](factor_dictionary.md)
- 📄 [快速指南](alpha_peg_quick_start.md)
- 📄 [数据库结构](database_schema.md)
- 💻 [代码实现](../code/calc_alpha_peg.py)
- ✅ [逻辑验证](../code/test_alpha_peg.py)

---

## 📚 文档导航

### 核心文档
1. **[alpha_peg数据来源说明](alpha_peg_data_source.md)** - 数据字段、时间对齐、SQL示例
2. **[因子字典](factor_dictionary.md)** - 完整因子定义
3. **[快速指南](alpha_peg_quick_start.md)** - 3步快速使用
4. **[数据库结构](database_schema.md)** - 全库表结构

### 代码文件
1. **[calc_alpha_peg.py](../code/calc_alpha_peg.py)** - 因子计算主程序
2. **[test_alpha_peg.py](../code/test_alpha_peg.py)** - 逻辑验证

### 原项目文档
1. **[README.md](../README.md)** - 项目总览
2. **[final_summary_20251224.md](final_summary_20251224.md)** - 原项目总结
3. **[modification_analysis.md](modification_analysis.md)** - 修改分析

---

## 🔍 快速查找

### 想要计算alpha_peg因子？
→ 查看 [快速指南](alpha_peg_quick_start.md)

### 想要了解数据来源？
→ 查看 [数据来源说明](alpha_peg_data_source.md)

### 想要查看完整定义？
→ 查看 [因子字典](factor_dictionary.md)

### 想要验证逻辑？
→ 运行 `python3 code/test_alpha_peg.py`

### 想要了解数据库？
→ 查看 [数据库结构](database_schema.md)

---

## 📞 联系与维护

**因子开发**: Alpha006项目组
**最后更新**: 2025-12-24
**文档版本**: v1.0

---

## 📝 更新日志

### 2025-12-24
- ✅ 新增 `alpha_peg` 因子
- ✅ 完成因子计算代码
- ✅ 完成逻辑验证
- ✅ 完成文档体系
- ✅ 更新README

---

**提示**: 按 `Ctrl+F` 搜索关键词快速定位
