# 文档维护检查清单

## 📋 每次工作后的必做事项

### 1. 文件级别检查
```
□ 修改的文件是否添加了3行注释？
□ 注释格式是否正确？
□ input/output/pos是否描述准确？
```

### 2. 文件夹级别检查
```
□ 文件夹是否有 ARCHITECTURE.md？
□ 内容是否在3行以内？
□ 职责/依赖/输出是否清晰？
```

### 3. 项目级别检查
```
□ 根目录README是否更新？
□ 策略文档是否更新？
□ 所有文档是否一致？
```

---

## 📁 需要维护的文档清单

### 核心规范文档
| 文件 | 说明 | 维护频率 |
|------|------|----------|
| `README.md` | 项目整体架构 + 开发规范 | 架构变更时 |
| `DEVELOPMENT_STANDARDS.md` | 详细开发规范 | 规范更新时 |
| `MAINTENANCE_CHECKLIST.md` | 维护检查清单 | 规范更新时 |

### 文件夹架构说明
| 文件 | 说明 | 维护频率 |
|------|------|----------|
| `config/ARCHITECTURE.md` | 配置层说明 | 配置变更时 |
| `config/strategies/ARCHITECTURE.md` | 策略配置说明 | 策略变更时 |
| `scripts/ARCHITECTURE.md` | 脚本层说明 | 脚本变更时 |
| `core/ARCHITECTURE.md` | 核心层说明 | 核心变更时 |
| `factors/ARCHITECTURE.md` | 因子层说明 | 因子变更时 |
| `results/ARCHITECTURE.md` | 结果层说明 | 结果变更时 |
| `data/ARCHITECTURE.md` | 数据层说明 | 数据变更时 |

### 关键文件注释
| 文件 | 说明 | 维护频率 |
|------|------|----------|
| `config/strategies/six_factor_monthly.py` | SFM策略配置 | 配置变更时 |
| `config/strategies/__init__.py` | 策略包入口 | 策略变更时 |
| `scripts/run_strategy.py` | 统一调用脚本 | 脚本变更时 |
| `scripts/run_six_factor_backtest.py` | 回测引擎 | 引擎变更时 |
| `scripts/__init__.py` | 脚本包标识 | 脚本变更时 |
| `core/utils/db_connection.py` | 数据库连接 | 连接变更时 |
| `core/config/settings.py` | 全局配置 | 配置变更时 |
| `factors/__init__.py` | 因子包入口 | 因子变更时 |

### 策略文档
| 文件 | 说明 | 维护频率 |
|------|------|----------|
| `STRATEGY_GUIDE.md` | 完整使用指南 | 策略更新时 |
| `QUICK_START.md` | 快速开始手册 | 策略更新时 |
| `README_STRATEGY.md` | 策略概览 | 策略更新时 |
| `PROJECT_UPDATE_20251231.md` | 更新记录 | 每次更新后 |

---

## 🔍 快速验证命令

### 检查所有文件头部注释
```bash
# 查看关键文件的前5行
head -5 config/strategies/six_factor_monthly.py
head -5 scripts/run_strategy.py
head -5 scripts/run_six_factor_backtest.py
head -5 core/utils/db_connection.py
head -5 core/config/settings.py
```

### 检查所有ARCHITECTURE.md
```bash
# 查看所有架构说明文件
find . -name "ARCHITECTURE.md" -type f
```

### 检查所有__init__.py
```bash
# 查看所有__init__.py文件
find . -name "__init__.py" -type f | xargs head -5
```

---

## 📝 更新日志模板

### 文件更新
```
文件: [文件路径]
日期: [YYYY-MM-DD]
内容: [更新说明]
验证: [是否通过]
```

### 文件夹更新
```
文件夹: [文件夹路径]
日期: [YYYY-MM-DD]
内容: [职责/依赖/输出变更]
验证: [是否通过]
```

### 项目更新
```
版本: [版本号]
日期: [YYYY-MM-DD]
变更: [架构变更说明]
影响: [影响的文件和文档]
验证: [所有文档是否更新完成]
```

---

## ⚠️ 常见错误

### ❌ 错误示例
1. 修改了代码但忘记更新注释
2. 新增了文件夹但没有ARCHITECTURE.md
3. 修改了依赖但没有更新input/output
4. 架构变了但README没更新

### ✅ 正确做法
1. 代码修改 → 立即更新注释
2. 新增文件夹 → 立即创建ARCHITECTURE.md
3. 依赖变化 → 立即更新所有相关注释
4. 架构变化 → 立即更新README和文档

---

## 🎯 每日工作流程

### 开始工作前
1. 查看要修改的文件注释
2. 查看相关文件夹ARCHITECTURE.md
3. 理解当前架构和依赖

### 工作中
1. 按需求修改代码
2. 实时记录变化点

### 工作结束后
1. 更新文件头部注释
2. 更新文件夹ARCHITECTURE.md
3. 更新根目录README（如有架构变更）
4. 更新相关策略文档
5. 运行验证命令检查一致性

---

## 📞 问题反馈

如果发现文档不一致或缺失，请立即：
1. 停止当前工作
2. 补充缺失文档
3. 更新相关注释
4. 验证一致性
5. 继续工作

---

**最后更新**: 2025-12-31
**状态**: ✅ 强制执行
**版本**: v1.0
