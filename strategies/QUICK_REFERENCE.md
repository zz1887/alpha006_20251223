# 策略框架快速参考

## 🚀 快速开始

### 查看可用策略
```bash
python strategies/runners/run_strategy.py --list
```

### 查看策略详情
```bash
python strategies/runners/run_strategy.py --info six_factor_monthly
```

### 运行策略
```bash
# 统一接口
python strategies/runners/run_strategy.py --strategy six_factor_monthly --start 20240601 --end 20251130

# 专用脚本
python strategies/runners/run_six_factor.py --start 20240601 --end 20251130
python strategies/runners/run_strategy3.py --start 20240601 --end 20251130 --version standard
```

## 📁 目录结构

```
strategies/
├── base/           # 基础类
├── configs/        # 配置
├── executors/      # 执行器
├── runners/        # 运行脚本
└── implementations/# 实现类
```

## 🎯 策略列表

| 策略名称 | 版本 | 描述 |
|---------|------|------|
| `six_factor_monthly` | v1.0 | 六因子月末智能调仓 |
| `six_factor_monthly_v2` | v1.1-optimized | 六因子优化版 |
| `strategy3` | v1.0 | 多因子综合得分 |
| `six_factor` | - | 兼容模式 |

## 🔧 常用命令

### 策略管理
```bash
# 列出策略
python strategies/runners/run_strategy.py --list

# 查看详情
python strategies/runners/run_strategy.py --info <策略名>

# 运行策略
python strategies/runners/run_strategy.py --strategy <策略名> --start <开始> --end <结束> --version <版本>
```

### 版本选择
```bash
# 标准版本
--version standard

# 保守版本
--version conservative

# 激进版本
--version aggressive
```

## 📝 创建新策略

### 1. 配置文件
```python
# strategies/configs/my_strategy_v1.py
from typing import Dict, Any

STRATEGY_INFO = {'name': '我的策略', 'version': 'v1.0', ...}
FACTOR_CONFIG = {'factors': {...}}
# ... 其他配置

def get_strategy_config() -> Dict[str, Any]:
    return {'info': STRATEGY_INFO, 'factors': FACTOR_CONFIG, ...}
```

### 2. 执行器
```python
# strategies/executors/my_strategy_executor.py
def execute(start_date: str, end_date: str, version: str = 'standard', **kwargs) -> bool:
    # 1. 加载配置
    # 2. 获取数据
    # 3. 运行回测
    # 4. 保存结果
    return True
```

### 3. 注册策略
```python
# strategies/base/strategy_runner.py
STRATEGY_MAP = {
    'my_strategy': {
        'config': 'strategies.configs.my_strategy_v1',
        'executor': 'strategies.executors.my_strategy_executor',
        'description': '我的策略描述',
    },
}
```

## 🔍 故障排除

### 配置加载失败
- 检查配置文件语法
- 确认 `get_strategy_config()` 函数存在
- 验证导入路径

### 执行器错误
- 检查 `execute()` 函数签名
- 确认依赖模块已导入
- 验证数据路径

### 导入错误
- 检查 `sys.path` 设置
- 确认模块命名正确
- 验证 `__init__.py` 文件

## 📚 文档位置

- 架构说明: `/strategies/ARCHITECTURE.md`
- 迁移指南: `/strategies/MIGRATION_GUIDE.md`
- 开发模板: `/strategies/TEMPLATE.md`
- 重构总结: `/STRATEGY_RESTRUCTURING_SUMMARY.md`

## 💡 最佳实践

1. **配置分离**: 配置参数与业务逻辑分离
2. **版本管理**: 同一策略支持多版本
3. **命名规范**: 使用统一的命名约定
4. **错误处理**: 执行器必须返回布尔值
5. **文档注释**: 每个文件都要有清晰的文档字符串