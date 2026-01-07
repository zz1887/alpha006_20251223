# strategies 架构说明

## 目录结构
```
strategies/
├── base/              # 基础策略类和接口
├── configs/           # 策略配置文件
├── executors/         # 策略执行器
├── implementations/   # 策略具体实现
└── runners/           # 策略运行脚本
```

## 职责划分

### base/ - 基础策略层
- **base_strategy.py**: 抽象策略基类，定义策略接口
- **strategy_runner.py**: 策略运行器，统一调度策略执行

### configs/ - 策略配置层
- 存放各策略的配置参数
- 纯配置文件，不包含业务逻辑
- 支持多版本配置（保守、标准、激进）

### executors/ - 策略执行层
- 负责策略的具体执行逻辑
- 连接配置层和实现层
- 处理数据加载、计算、输出

### implementations/ - 策略实现层
- 策略核心算法实现
- 因子计算、组合逻辑
- 可独立调用的策略类

### runners/ - 策略入口层
- 统一的策略调用接口
- 命令行工具
- 批量执行脚本

## 依赖关系
```
runners → executors → implementations → configs
                ↓
              base (公共基础)
```

## 策略命名规范
- **配置文件**: `{策略名}_{版本}.py` (例: `six_factor_monthly_v1.py`)
- **执行器**: `{策略名}_executor.py` (例: `six_factor_executor.py`)
- **实现类**: `{策略名}_strategy.py` (例: `six_factor_strategy.py`)
- **运行脚本**: `run_{策略名}.py` (例: `run_six_factor.py`)

## 已支持策略
1. **six_factor_monthly** - 六因子月末智能调仓策略
2. **strategy3** - 多因子综合得分策略
3. **alpha_peg_t10** - AlphaPEG 10天持有期策略

## 使用方式
```bash
# 统一调用接口
python strategies/runners/run_strategy.py --strategy six_factor_monthly --start 20240601 --end 20251130

# 直接调用特定策略
python strategies/runners/run_six_factor.py --start 20240601 --end 20251130
```

## 版本管理
- 策略版本号在配置文件中定义
- 支持同策略多版本并存
- 通过版本参数切换不同配置