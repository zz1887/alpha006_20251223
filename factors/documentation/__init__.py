"""
文件input(依赖外部什么): factors.core, factors.calculation, factors.evaluation
文件output(提供什么): 因子文档库统一导入接口
文件pos(系统局部地位): 文档层入口，提供因子文档自动生成和管理功能
文件功能:
    1. 因子公式文档生成（Markdown格式）
    2. 因子字典自动生成
    3. 使用示例文档生成
    4. 技术文档模板管理

使用示例:
    from factors.documentation import FactorDocGenerator

    # 生成单因子文档
    doc_gen = FactorDocGenerator()
    doc_text = doc_gen.generate_factor_doc(
        factor_name='alpha_peg',
        formula='alpha_peg = pe_ttm / dt_netprofit_yoy',
        params={'outlier_sigma': 3.0, 'normalization': None},
        logic='PEG比率 = 市盈率 / 盈利增长率'
    )

    # 生成完整因子字典
    dictionary = doc_gen.generate_factor_dictionary()

返回值:
    str: 生成的Markdown文档
    Dict: 因子字典数据
    None: 文档保存操作

文档体系:
    1. 因子字典 (factor_dictionary.md)
    2. 公式指南 (formula_guide.md)
    3. 计算指南 (calculation_guide.md)
    4. 评估指南 (evaluation_guide.md)
    5. 使用示例 (usage_examples.md)
"""

from .generator import FactorDocGenerator

__all__ = ['FactorDocGenerator']
