# 🚀 Alpha006项目快速使用指南

**最后更新**: 2026-01-03
**版本**: v2.2 + AI技能库 + MCP支持

---

## 📋 今日新增功能

### ✅ AI技能库 (skills/)
- **6个专业技能**: PostgreSQL, CCXT, Telegram Bot, Claude工具等
- **1个元技能**: 可创建新技能的技能
- **总大小**: 3.9MB，42个文件

### ✅ MCP服务器 (mcp_servers/)
- **文件系统MCP**: 文件搜索、读取、写入
- **策略管理MCP**: 策略查看、因子管理、执行

---

## 🎯 场景化使用指南

### 场景1: 数据库优化

#### 问题描述
"我的Alpha006因子查询很慢，需要优化"

#### 解决方案
```bash
# 方法1: 直接使用Claude + 技能
# 在Claude中说:
"使用postgresql技能，帮我优化Alpha006的因子查询"

# 方法2: 使用MCP查看当前查询
# 在Claude中说:
"读取core/utils/data_loader.py，分析数据库查询部分"
"搜索所有包含SELECT的SQL语句"

# 方法3: 手动查看
cat skills/postgresql/SKILL.md  # 查看PostgreSQL优化技巧
cat core/utils/data_loader.py   # 查看当前查询实现
```

#### 预期结果
Claude会基于postgresql技能提供：
- 索引优化建议
- 查询重写方案
- 性能调优技巧

---

### 场景2: 交易集成

#### 问题描述
"我想连接交易所，实时获取数据并执行策略"

#### 解决方案
```bash
# 方法1: 使用CCXT技能
# 在Claude中说:
"使用ccxt技能，连接币安和OKX，获取BTC/USDT深度数据"

# 方法2: 集成到Alpha006
# 在Claude中说:
"使用ccxt技能，创建一个脚本，获取交易所数据并存储到MySQL"
"然后用Alpha006策略分析这些数据"

# 方法3: 查看示例
cat skills/ccxt/SKILL.md  # 查看CCXT使用模式
```

#### 预期结果
- 统一的交易所API接口
- 实时数据获取脚本
- 与Alpha006框架的集成方案

---

### 场景3: 自动化通知

#### 问题描述
"策略执行后想通过Telegram接收通知"

#### 解决方案
```bash
# 方法1: 创建通知Bot
# 在Claude中说:
"使用telegram-dev技能，创建一个交易通知Bot"
"当策略执行完成时发送回测结果"

# 方法2: 集成到现有流程
# 在Claude中说:
"修改scripts/run_strategy.py，执行完成后调用Telegram Bot发送通知"

# 方法3: 查看完整指南
cat skills/telegram-dev/SKILL.md
```

#### 预期结果
- Telegram Bot自动部署
- 策略执行结果实时推送
- 错误告警机制

---

### 场景4: 创建新因子/策略

#### 问题描述
"我想创建一个新的量化因子"

#### 解决方案
```bash
# 方法1: 使用元技能创建
# 在Claude中说:
"使用claude-skills技能，为我的新因子创建一个技能"
"因子逻辑: [描述你的因子想法]"

# 方法2: 手动创建框架
# 在Claude中说:
"在factors/目录下创建一个新的因子文件"
"实现标准的因子接口"

# 方法3: 参考现有因子
cat factors/valuation/factor_alpha_peg.py  # 查看完整实现
cat skills/claude-skills/SKILL.md          # 查看技能创建规范
```

#### 预期结果
- 标准化的因子文件结构
- 完整的文档和测试
- 与Alpha006框架的无缝集成

---

### 场景5: 项目文件管理

#### 问题描述
"我需要快速找到和修改项目中的配置文件"

#### 解决方案
```bash
# 使用MCP文件系统
# 在Claude中说:

# 1. 搜索文件
"搜索所有包含alpha_peg的Python文件"
"查找config目录下的所有配置文件"

# 2. 查看内容
"读取strategies/configs/six_factor_monthly_v1.py"
"显示core/utils/db_connection.py的前30行"

# 3. 修改文件
"修改backtest_config.py，将交易成本从0.35%改为0.4%"
"更新策略配置，增加一个新的因子权重"

# 4. 项目分析
"获取项目摘要"
"列出所有策略及其配置"
```

#### 预期结果
- 快速定位文件
- 直接在Claude中查看和修改
- 项目结构一目了然

---

### 场景6: 策略执行与分析

#### 问题描述
"我想运行六因子策略并分析结果"

#### 解决方案
```bash
# 方法1: 使用MCP策略管理
# 在Claude中说:
"列出所有可用策略"
"显示six_factor_monthly策略的详细信息"
"运行六因子策略，时间20240601-20251130"

# 方法2: 命令行执行
cd /home/zcy/alpha006_20251223
python3 scripts/strategy/unified_runner.py --list
python3 scripts/strategy/unified_runner.py --strategy six_factor_monthly --info
python3 scripts/strategy/unified_runner.py --strategy six_factor_monthly --start 20240601 --end 20251130

# 方法3: 查看策略文档
cat strategies/configs/six_factor_monthly_v1.py
cat skills/postgresql/SKILL.md  # 如需优化数据库查询
```

#### 预期结果
- 策略执行日志
- 回测结果文件
- 性能指标分析

---

## 🔧 日常工作流程

### 每日工作开始

```bash
# 1. 检查项目状态
cd /home/zcy/alpha006_20251223
python3 mcp_servers/test_mcp.py  # 验证MCP

# 2. 查看可用技能
cat skills/技能库说明.md

# 3. 查看可用策略
python3 scripts/strategy/unified_runner.py --list
```

### 因子开发流程

```bash
# 1. 使用元技能创建新因子
# 在Claude中说:
"使用claude-skills技能，创建一个基于[你的思路]的因子"

# 2. 实现因子逻辑
# 编辑: factors/your_factor.py

# 3. 测试因子
python3 -c "from factors import your_factor; print('OK')"

# 4. 更新文档
# 更新: factors/ARCHITECTURE.md
```

### 策略执行流程

```bash
# 1. 查看策略配置
python3 scripts/strategy/unified_runner.py --strategy six_factor_monthly --info

# 2. 运行策略
python3 scripts/strategy/unified_runner.py --strategy six_factor_monthly --start 20250101 --end 20250630

# 3. 分析结果
cat results/backtest/summary_*.txt

# 4. 优化调整
# 在Claude中说:
"分析回测结果，提出优化建议"
```

---

## 💡 高级使用技巧

### 技能组合使用

```bash
# 场景: 从数据获取到策略执行的完整流程

# 1. 使用ccxt获取实时数据
# "使用ccxt技能，获取最近30天的BTC/USDT日线数据"

# 2. 使用postgresql存储
# "使用postgresql技能，设计表结构存储这些数据"

# 3. 使用Alpha006分析
# "将这些数据导入Alpha006框架，计算alpha_peg因子"

# 4. 使用telegram通知
# "创建Bot，每天发送因子分析报告"
```

### MCP高级查询

```bash
# 项目分析
"分析strategies目录的结构，画出依赖关系图"
"找出所有包含alpha_038的文件"
"比较v1和v2策略配置的差异"

# 代码审查
"检查factors/valuation/目录下的所有因子实现"
"验证策略配置文件的语法正确性"

# 批量操作
"列出所有需要更新的策略配置"
"批量修改所有策略的交易成本参数"
```

### Claude Code最佳实践

```bash
# 1. 使用技能库
# 在Claude中直接引用:
@skills/postgresql/SKILL.md
@skills/ccxt/SKILL.md

# 2. 结合项目文档
@README.md
@strategies/configs/six_factor_monthly_v1.py

# 3. 使用MCP工具
# 自动可用，无需手动导入
```

---

## 📊 常用命令速查

### 项目操作
```bash
cd /home/zcy/alpha006_20251223  # 进入项目
ls -la                          # 查看目录
find . -name "*.py" | wc -l     # 统计Python文件
```

### 策略操作
```bash
# 列出策略
python3 scripts/strategy/unified_runner.py --list

# 策略详情
python3 scripts/strategy/unified_runner.py --strategy <name> --info

# 运行策略
python3 scripts/strategy/unified_runner.py --strategy <name> --start <date> --end <date>
```

### MCP测试
```bash
# 测试文件系统MCP
echo '{"method": "get_project_summary", "params": {}}' | python3 -m mcp_servers.filesystem_server

# 测试策略MCP
echo '{"method": "list_strategies", "params": {}}' | python3 -m mcp_servers.strategy_server

# 完整测试
python3 mcp_servers/test_mcp.py
```

### 技能查看
```bash
# 查看技能库说明
cat skills/技能库说明.md

# 查看具体技能
cat skills/postgresql/SKILL.md
cat skills/ccxt/SKILL.md
cat skills/claude-skills/SKILL.md

# 查看导入报告
cat SKILLS导入完成.md
```

---

## 🎯 推荐使用模式

### 模式1: 对话式开发
```
你: "我想创建一个基于动量的因子"
Claude: [使用claude-skills技能分析需求]
Claude: [创建因子框架]
Claude: [测试并验证]
```

### 模式2: 问题诊断
```
你: "策略回测结果异常"
Claude: [使用MCP查看策略配置]
Claude: [使用postgresql技能分析数据质量]
Claude: [使用ccxt技能验证市场数据]
Claude: [给出诊断和修复方案]
```

### 模式3: 自动化工作流
```
你: "每天自动执行策略并通知我"
Claude: [使用telegram-dev创建Bot]
Claude: [集成到策略执行脚本]
Claude: [设置定时任务]
```

---

## 🔍 故障排除

### MCP无法连接
```bash
# 检查配置
cat ~/.claude/claude.json | grep mcpServers

# 测试MCP
python3 mcp_servers/test_mcp.py

# 重启Claude Code
# 重新加载配置
```

### 技能无法使用
```bash
# 检查技能目录
ls -la skills/

# 查看技能说明
cat skills/技能库说明.md

# 验证技能文件
cat skills/postgresql/SKILL.md
```

### 导入路径错误
```bash
# 确保在项目根目录
cd /home/zcy/alpha006_20251223

# 测试导入
python3 -c "from strategies.base.strategy_runner import StrategyRunner; print('OK')"

# 检查Python路径
python3 -c "import sys; print(sys.path)"
```

---

## 📚 相关文档

| 文档 | 用途 |
|------|------|
| `README.md` | 项目整体架构和使用 |
| `skills/技能库说明.md` | 技能库详细使用指南 |
| `SKILLS导入完成.md` | 已导入技能清单 |
| `MCP_README.md` | MCP服务器完整文档 |
| `MCP安装指南.md` | MCP配置和故障排除 |
| `strategies/README.md` | 策略框架说明 |

---

## ✅ 每日检查清单

- [ ] MCP服务器正常运行
- [ ] 技能库可用
- [ ] 策略框架正常
- [ ] 数据库连接正常
- [ ] 文档更新到最新

---

## 🚀 立即开始

### 新用户快速上手
```bash
# 1. 验证环境
python3 mcp_servers/test_mcp.py

# 2. 查看可用技能
cat skills/技能库说明.md

# 3. 尝试第一个任务
# 在Claude中说: "列出所有可用策略"
```

### 老用户升级使用
```bash
# 1. 了解新功能
cat SKILLS导入完成.md
cat MCP安装指南.md

# 2. 配置MCP
cp mcp_config.json ~/.claude/claude.json

# 3. 尝试新工作流
# 在Claude中说: "使用postgresql技能，优化我的查询"
```

---

**提示**: 所有技能和MCP功能都可以在Claude对话中直接使用，无需额外配置！

**最后更新**: 2026-01-03
**状态**: ✅ 所有功能可用
