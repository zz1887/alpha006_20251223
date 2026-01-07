# 策略文件迁移指南

## 当前需要迁移的文件

### 1. 策略配置文件
**源位置**: `/config/strategies/`
**目标位置**: `/strategies/configs/`

- `six_factor_monthly.py` → `six_factor_monthly_v1.py` ✓ (已创建)
- `six_factor_monthly_optimized_v1.py` → `six_factor_monthly_v2.py` (待迁移)
- 其他配置文件...

### 2. 策略执行脚本
**源位置**: `/scripts/`
**目标位置**: `/strategies/runners/`

- `run_strategy.py` → `run_strategy.py` ✓ (已创建新版本)
- `run_strategy3.py` → `run_strategy3.py` ✓ (已创建新版本)
- `run_six_factor.py` → `run_six_factor.py` ✓ (已创建新版本)
- `run_six_factor_backtest.py` → 保留为兼容模式
- `run_six_factor_backtest_fixed.py` → 保留为兼容模式
- `run_six_factor_backtest_optimized.py` → 保留为兼容模式

### 3. 策略实现类
**源位置**: `/code/`
**目标位置**: `/strategies/implementations/`

- `calculate_strategy3_20251229.py` → `strategy3_calculator.py`
- `factor_v1.py`, `factor_v2.py`, `factor_v3.py` → 保留在 `/factors/` 目录
- `backtest_v3.py` 系列 → 保留在 `/code/` 或迁移到 `/strategies/implementations/`

### 4. AlphaPEG 相关
**源位置**: `/code/`
**目标位置**: `/strategies/implementations/`

- `calc_alpha_peg.py` → `alpha_peg_factor.py`
- `calc_alpha_peg_industry.py` → `alpha_peg_industry.py`
- `backtest_alpha_peg_industry.py` → `alpha_peg_backtest.py`

## 迁移步骤

### 1. 配置文件迁移
```bash
# 复制并重命名配置文件
cp /config/strategies/six_factor_monthly_optimized_v1.py /strategies/configs/six_factor_monthly_v2.py

# 更新文件头部注释和导入路径
```

### 2. 策略实现迁移
```bash
# 复制策略实现类
cp /code/calculate_strategy3_20251229.py /strategies/implementations/strategy3_calculator.py

# 更新导入路径
sed -i 's/from core\./from ..core./g' /strategies/implementations/strategy3_calculator.py
```

### 3. 更新现有脚本（可选）
保留现有脚本作为兼容层，但更新内部实现以调用新框架：

```python
# 在现有脚本中添加
import sys
sys.path.insert(0, '/home/zcy/alpha006_20251223')

from strategies.base.strategy_runner import StrategyRunner

# 替换原有逻辑
success = StrategyRunner.run_strategy('six_factor_monthly', start_date, end_date, version)
```

## 新框架使用方式

### 统一调用接口
```bash
# 列出所有策略
python strategies/runners/run_strategy.py --list

# 查看策略详情
python strategies/runners/run_strategy.py --info six_factor_monthly

# 运行策略
python strategies/runners/run_strategy.py --strategy six_factor_monthly --start 20240601 --end 20251130

# 运行策略3
python strategies/runners/run_strategy.py --strategy strategy3 --start 20240601 --end 20251130 --version standard
```

### 专用运行脚本
```bash
# 六因子策略
python strategies/runners/run_six_factor.py --start 20240601 --end 20251130

# 策略3
python strategies/runners/run_strategy3.py --start 20240601 --end 20251130 --version standard
```

## 兼容性说明

### 保持兼容的旧路径
- `/scripts/run_six_factor_backtest.py` - 继续工作
- `/scripts/run_strategy.py` - 继续工作（但建议使用新路径）
- `/config/strategies/` - 配置文件继续可用

### 推荐使用的新路径
- `/strategies/runners/run_strategy.py` - 统一入口
- `/strategies/runners/run_six_factor.py` - 六因子专用
- `/strategies/runners/run_strategy3.py` - 策略3专用

## 待完成任务

- [ ] 迁移 `six_factor_monthly_optimized_v1.py` 到新框架
- [ ] 迁移 AlphaPEG 相关策略实现
- [ ] 创建策略3的完整实现类
- [ ] 更新所有因子计算函数的导入路径
- [ ] 测试新框架的完整功能
- [ ] 编写策略模板，方便创建新策略

## 目录结构对比

### 旧结构（混乱）
```
alpha006_20251223/
├── code/
│   ├── factor_v1.py
│   ├── factor_v2.py
│   ├── factor_v3.py
│   ├── backtest_v3.py
│   ├── calculate_strategy3_20251229.py
│   └── calc_alpha_peg.py
├── scripts/
│   ├── run_strategy.py
│   ├── run_strategy3.py
│   ├── run_six_factor.py
│   └── run_six_factor_backtest.py
├── config/
│   └── strategies/
│       ├── six_factor_monthly.py
│       └── six_factor_monthly_optimized_v1.py
└── factors/
    ├── momentum/
    ├── price/
    ├── valuation/
    └── volume/
```

### 新结构（清晰）
```
alpha006_20251223/
├── strategies/                    # 新增：策略统一管理
│   ├── __init__.py
│   ├── ARCHITECTURE.md
│   ├── base/                     # 基础类
│   ├── configs/                  # 策略配置
│   ├── executors/                # 执行器
│   ├── implementations/          # 策略实现
│   └── runners/                  # 运行脚本
├── factors/                      # 保持：因子计算
│   ├── momentum/
│   ├── price/
│   ├── valuation/
│   └── volume/
├── core/                         # 保持：核心工具
├── config/                       # 保持：其他配置
└── scripts/                      # 保持：兼容旧脚本
```

## 优势

1. **统一管理**: 所有策略相关文件集中管理
2. **清晰分层**: 配置-执行-实现分离
3. **易于扩展**: 新策略只需添加对应文件
4. **向后兼容**: 旧脚本继续工作
5. **规范命名**: 统一的命名规范