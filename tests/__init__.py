"""
Alpha006因子库 - 测试框架增强版

功能: 提供完整的测试框架，支持单元测试、集成测试、性能测试
版本: v2.4 (Phase 6)
最后更新: 2026-01-07

测试框架架构:
├── tests/
│   ├── unit/           # 单元测试 - 因子计算逻辑验证
│   ├── integration/    # 集成测试 - 端到端流程验证
│   ├── performance/    # 性能测试 - 基准和压力测试
│   ├── fixtures/       # 测试数据和mock对象
│   ├── helpers/        # 测试辅助工具
│   └── reports/        # 测试报告输出

使用示例:
    # 运行所有测试
    python -m pytest tests/

    # 运行单元测试
    python -m pytest tests/unit/

    # 运行集成测试
    python -m pytest tests/integration/

    # 生成详细报告
    python -m pytest tests/ --html=tests/reports/report.html --self-contained-html
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

__version__ = "2.4.0"
__all__ = [
    "unit",
    "integration",
    "performance",
    "fixtures",
    "helpers"
]