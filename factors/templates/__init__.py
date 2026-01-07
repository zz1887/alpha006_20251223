"""
文件input(依赖外部什么): 无
文件output(提供什么): 模板文件统一导入，提供快速创建因子的模板
文件pos(系统局部地位): 模板层入口，提供因子开发、测试、评估的标准模板
文件功能:
    1. 因子类模板（FactorNameFactor）
    2. 测试模板（TestFactorName）
    3. 评估模板（FactorEvaluation）
    4. 公式文档模板（Markdown格式）

使用说明:
    从模板创建新因子：
    1. 复制factor_class_template.py → 新因子.py
    2. 复制test_template.py → 新因子_test.py
    3. 复制evaluation_template.py → 新因子_evaluation.py
    4. 复制formula_doc_template.md → 新因子.md

模板文件:
    - factor_class_template.py: 因子类模板
    - test_template.py: 测试模板
    - evaluation_template.py: 评估模板
    - formula_doc_template.md: 公式文档模板
"""

__all__ = [
    'factor_class_template',
    'test_template',
    'evaluation_template',
]
