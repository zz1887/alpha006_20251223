# 开发规范标准 - Development Standards

## 📋 文档更新规范

### 核心要求
**⚠️ 任何功能、架构、写法更新必须在工作结束后更新相关文档**

---

## 一、文件头部注释规范

### 格式要求
每个文件必须包含以下三行注释（必须放在文件最开头）：

```python
"""
文件input(依赖外部什么): [依赖的模块/数据/配置]
文件output(提供什么): [提供的功能/数据/接口]
文件pos(系统局部地位): [在系统中的位置和作用]

[原有文件说明...]
"""
```

### 更新时机
- ✅ 文件被修改时
- ✅ 依赖关系变化时
- ✅ 功能发生变化时

### 示例

**修改前**:
```python
"""
策略统一调用脚本 - Strategy Runner
"""
```

**修改后**:
```python
"""
文件input(依赖外部什么): config.strategies.*, scripts.run_six_factor_backtest
文件output(提供什么): 统一策略调用接口, 自动配置加载
文件pos(系统局部地位): 策略执行层的统一入口, 连接配置和执行器

策略统一调用脚本 - Strategy Runner
"""
```

---

## 二、文件夹架构说明规范

### 文件位置
每个文件夹必须包含 `ARCHITECTURE.md` 文件

### 格式要求
```
# [文件夹名称] 架构说明

职责: [一句话说明]
依赖: [依赖的其他文件夹/模块]
输出: [提供的功能/数据]
```

### 示例

**config/strategies/ARCHITECTURE.md**:
```
# config/strategies 架构说明

职责: 策略配置文件集合
依赖: config/
输出: 各策略的完整配置(SFM等)
```

**scripts/ARCHITECTURE.md**:
```
# scripts 架构说明

职责: 执行脚本入口, 策略调用
依赖: config/, core/, factors/
输出: 统一调用脚本、回测脚本、因子生成脚本
```

---

## 三、根目录README更新规范

### 更新内容
当项目架构发生以下变化时，必须更新根目录README：

1. **新增目录结构**
2. **修改核心流程**
3. **新增主要功能模块**
4. **版本升级**

### 更新位置
在README.md末尾添加或更新"开发规范"章节

---

## 四、完整更新流程

### 工作开始前
1. 阅读相关文件的头部注释
2. 查看文件夹的ARCHITECTURE.md
3. 理解依赖关系

### 工作进行中
1. 按需求修改代码
2. 实时记录依赖变化

### 工作结束后
1. ✅ 更新文件头部注释
2. ✅ 更新文件夹 ARCHITECTURE.md
3. ✅ 更新根目录 README.md（如有架构变更）
4. ✅ 更新相关策略文档（如涉及策略）
5. ✅ 验证所有文档一致性

---

## 五、检查清单

### 文件级别
- [ ] 文件头部有3行注释
- [ ] input/output/pos描述准确
- [ ] 注释在文件最开头

### 文件夹级别
- [ ] 存在 ARCHITECTURE.md
- [ ] 内容在3行以内
- [ ] 职责/依赖/输出描述清晰

### 项目级别
- [ ] 根目录README包含开发规范
- [ ] 策略文档已更新
- [ ] 所有文档相互一致

---

## 六、示例项目结构

```
project/
├── README.md                    # 根文档 + 开发规范
├── DEVELOPMENT_STANDARDS.md     # 本文件
│
├── config/
│   ├── ARCHITECTURE.md          # 配置层说明
│   ├── __init__.py              # 3行注释
│   └── strategies/
│       ├── ARCHITECTURE.md      # 策略配置说明
│       ├── __init__.py          # 3行注释
│       └── six_factor_monthly.py  # 3行注释
│
├── scripts/
│   ├── ARCHITECTURE.md          # 脚本层说明
│   ├── __init__.py              # 3行注释
│   ├── run_strategy.py          # 3行注释
│   └── run_six_factor_backtest.py  # 3行注释
│
├── core/
│   ├── ARCHITECTURE.md          # 核心层说明
│   ├── utils/
│   │   └── db_connection.py     # 3行注释
│   └── config/
│       └── settings.py          # 3行注释
│
├── factors/
│   ├── ARCHITECTURE.md          # 因子层说明
│   ├── __init__.py              # 3行注释
│   └── valuation/
│       └── alpha_peg.py         # 3行注释
│
├── results/
│   ├── ARCHITECTURE.md          # 结果层说明
│   └── backtest/
│       └── ...                  # 回测结果
│
├── data/
│   ├── ARCHITECTURE.md          # 数据层说明
│   └── ...
│
└── docs/
    ├── STRATEGY_GUIDE.md        # 3行注释
    ├── QUICK_START.md           # 3行注释
    └── README_STRATEGY.md       # 3行注释
```

---

## 七、常见问题

### Q: 什么情况下需要更新文档？
A: 任何代码修改，包括：
- 修改函数逻辑
- 更改依赖关系
- 新增功能模块
- 调整文件结构

### Q: 注释写在哪里？
A: 文件最开头，import语句之前

### Q: 文件夹说明必须吗？
A: 是的，每个文件夹都必须有 ARCHITECTURE.md

### Q: 如何保持一致性？
A: 每次工作结束后，按检查清单逐一验证

---

## 八、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2025-12-31 | 初始版本，建立文档规范 |

---

**最后更新**: 2025-12-31
**状态**: ✅ 强制执行
**适用范围**: 所有项目文件
