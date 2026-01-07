# 策略创建模板

## 创建新策略的步骤

### 1. 创建配置文件
在 `/strategies/configs/` 目录下创建配置文件，命名格式：`{策略名}_v{版本}.py`

```python
# strategies/configs/my_strategy_v1.py

from typing import Dict, Any

# 策略基础信息
STRATEGY_INFO = {
    'name': '策略名称',
    'code': 'CODE',
    'version': 'v1.0',
    'author': '作者',
    'create_date': '2026-01-03',
    'description': '策略描述',
}

# 因子配置
FACTOR_CONFIG = {
    'factors': {
        'factor_name': {
            'name': '因子名称',
            'weight': 0.2,
            'direction': 'positive',  # positive/negative
            'normalization': 'none',  # none/zscore/binary/max_scale
        },
    },
    'calculation_params': {
        'factor_name': {
            'param1': 10,
            'param2': 20,
        },
    },
}

# 其他配置...
FILTER_CONFIG = {}
REBALANCE_CONFIG = {}
TRADING_COST_CONFIG = {}
BACKTEST_CONFIG = {}

def get_strategy_config() -> Dict[str, Any]:
    """获取完整策略配置"""
    return {
        'info': STRATEGY_INFO,
        'factors': FACTOR_CONFIG,
        'filters': FILTER_CONFIG,
        'rebalance': REBALANCE_CONFIG,
        'trading_cost': TRADING_COST_CONFIG,
        'backtest': BACKTEST_CONFIG,
    }

def get_strategy_params() -> Dict[str, Any]:
    """获取策略运行参数"""
    return {
        'weights': {k: v['weight'] for k, v in FACTOR_CONFIG['factors'].items()},
        'directions': {k: v['direction'] for k, v in FACTOR_CONFIG['factors'].items()},
    }
```

### 2. 创建执行器
在 `/strategies/executors/` 目录下创建执行器，命名格式：`{策略名}_executor.py`

```python
# strategies/executors/my_strategy_executor.py

import sys
sys.path.insert(0, '/home/zcy/alpha006_20251223')

from strategies.configs.my_strategy_v1 import get_strategy_config

def execute(start_date: str, end_date: str, version: str = 'standard', **kwargs) -> bool:
    """
    执行策略回测

    Args:
        start_date: 开始日期
        end_date: 结束日期
        version: 策略版本
        **kwargs: 其他参数

    Returns:
        是否成功
    """
    try:
        # 1. 加载配置
        config = get_strategy_config()

        # 2. 获取交易日期
        # 3. 运行回测
        # 4. 保存结果

        return True
    except Exception as e:
        print(f"执行失败: {e}")
        return False
```

### 3. 创建运行脚本（可选）
在 `/strategies/runners/` 目录下创建专用运行脚本

```python
# strategies/runners/run_my_strategy.py

import argparse
from strategies.executors.my_strategy_executor import execute

def main():
    parser = argparse.ArgumentParser(description='我的策略运行脚本')
    parser.add_argument('--start', '-s', type=str, required=True)
    parser.add_argument('--end', '-e', type=str, required=True)
    parser.add_argument('--version', '-v', type=str, default='standard')

    args = parser.parse_args()

    success = execute(args.start, args.end, args.version)
    exit(0 if success else 1)

if __name__ == '__main__':
    main()
```

### 4. 注册策略
在 `/strategies/base/strategy_runner.py` 中注册策略

```python
STRATEGY_MAP = {
    'my_strategy': {
        'config': 'strategies.configs.my_strategy_v1',
        'executor': 'strategies.executors.my_strategy_executor',
        'description': '我的策略描述',
    },
    # ... 其他策略
}
```

### 5. 测试策略
```bash
# 使用统一接口
python strategies/runners/run_strategy.py --strategy my_strategy --start 20240601 --end 20251130

# 或使用专用脚本
python strategies/runners/run_my_strategy.py --start 20240601 --end 20251130
```

## 策略命名规范

### 配置文件
- `{策略名}_v{版本}.py`
- 例: `six_factor_monthly_v1.py`, `six_factor_monthly_v2.py`

### 执行器
- `{策略名}_executor.py`
- 例: `six_factor_executor.py`, `strategy3_executor.py`

### 运行脚本
- `run_{策略名}.py`
- 例: `run_six_factor.py`, `run_strategy3.py`

### 策略名称
- 使用小写字母和下划线
- 简洁明了，反映策略特点
- 例: `six_factor_monthly`, `alpha_peg_t10`, `momentum_rotation`

## 策略开发最佳实践

### 1. 配置与实现分离
- 配置文件只包含参数
- 执行器包含业务逻辑
- 易于参数调优

### 2. 版本管理
- 同一策略支持多版本
- 版本号在配置文件中定义
- 通过参数切换版本

### 3. 错误处理
- 执行器必须返回布尔值
- 详细的错误日志
- 异常捕获和处理

### 4. 结果保存
- 自动创建输出目录
- 保存收益数据、性能指标
- 生成摘要报告

### 5. 文档注释
- 每个文件必须有文档字符串
- 关键函数要有参数说明
- 策略逻辑要有清晰描述

## 策略示例

### 简单示例：动量轮动策略
```python
# 配置
FACTOR_CONFIG = {
    'factors': {
        'momentum': {'weight': 1.0, 'direction': 'positive', 'normalization': 'rank'},
    }
}

# 执行器逻辑
def execute(start_date, end_date, version):
    # 1. 获取所有股票
    # 2. 计算动量因子
    # 3. 选前N名
    # 4. 每月轮动
    # 5. 回测
    pass
```

### 复杂示例：多因子复合
```python
# 配置
FACTOR_CONFIG = {
    'factors': {
        'value': {'weight': 0.3, 'direction': 'negative'},
        'momentum': {'weight': 0.3, 'direction': 'positive'},
        'quality': {'weight': 0.2, 'direction': 'positive'},
        'growth': {'weight': 0.2, 'direction': 'positive'},
    }
}

# 执行器逻辑
def execute(start_date, end_date, version):
    # 1. 计算所有因子
    # 2. 行业标准化
    # 3. 因子合成
    # 4. 分层回测
    # 5. 性能分析
    pass
```

## 调试技巧

### 1. 查看可用策略
```bash
python strategies/runners/run_strategy.py --list
```

### 2. 查看策略详情
```bash
python strategies/runners/run_strategy.py --info six_factor_monthly
```

### 3. 测试小范围数据
```bash
python strategies/runners/run_six_factor.py --start 20240601 --end 20240701
```

### 4. 检查输出结果
```bash
ls -la results/strategies/
```

## 常见问题

### Q: 如何添加新因子？
A: 在 `/factors/` 目录下创建因子实现，然后在配置中引用

### Q: 如何调整权重？
A: 修改配置文件中的 `weight` 参数，无需改动代码

### Q: 如何支持新市场？
A: 修改数据加载逻辑，保持策略框架不变

### Q: 如何批量测试？
A: 使用 `StrategyRunner.run_batch()` 方法

## 下一步

1. 阅读现有策略实现学习模式
2. 使用模板创建新策略
3. 测试并验证结果
4. 文档化策略逻辑