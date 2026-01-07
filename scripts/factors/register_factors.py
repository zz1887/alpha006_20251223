"""
文件input(依赖外部什么): factors.calculation, factors.core.factor_registry, logging
文件output(提供什么): 因子注册脚本，将所有标准因子注册到FactorRegistry
文件pos(系统局部地位): 因子库核心脚本 - 因子注册器

功能:
1. 导入所有标准因子类
2. 注册因子到FactorRegistry
3. 验证注册结果
4. 提供因子列表查询功能

使用示例:
    # 注册所有因子
    python3 scripts/factors/register_factors.py

    # 在代码中使用
    from factors.core.factor_registry import FactorRegistry
    from scripts.factors.register_factors import register_all_factors

    register_all_factors()
    factor = FactorRegistry.get_factor('alpha_peg')
    result = factor.calculate(data)

返回值:
    Dict: 注册的因子信息

纪律要求:
1. 每个代码前必须有头部注释（input/output/pos/功能/使用示例/返回值）
2. 所有函数必须有完整文档字符串
3. 所有异常必须被捕获并记录
4. 使用中文注释和文档
5. 保持代码简洁，避免过度工程化
"""

import logging
from typing import Dict, List, Optional

from factors.core.factor_registry import FactorRegistry

# 导入所有标准因子类
try:
    from factors.calculation import (
        AlphaPegFactor,
        Alpha010Factor,
        Alpha038Factor,
        Alpha120CqFactor,
        CrQfqFactor,
        AlphaPluseFactor,
        Bias1QfqFactor,
        FACTOR_CLASSES,
        AVAILABLE_FACTORS
    )
    IMPORT_SUCCESS = True
except ImportError as e:
    logging.error(f"导入因子类失败: {e}")
    IMPORT_SUCCESS = False
    AlphaPegFactor = None
    Alpha010Factor = None
    Alpha038Factor = None
    Alpha120CqFactor = None
    CrQfqFactor = None
    AlphaPluseFactor = None
    Bias1QfqFactor = None
    FACTOR_CLASSES = {}
    AVAILABLE_FACTORS = []

logger = logging.getLogger(__name__)


def register_all_factors() -> Dict[str, Dict]:
    """
    注册所有标准因子到FactorRegistry

    Returns:
        Dict[str, Dict]: 注册成功的因子信息
            {
                'alpha_peg': {
                    'class': AlphaPegFactor,
                    'category': 'valuation',
                    'status': 'registered'
                },
                ...
            }
    """
    if not IMPORT_SUCCESS:
        logger.error("因子类导入失败，无法注册")
        return {}

    # 清空现有注册表，避免重复
    FactorRegistry.clear()

    # 因子分类映射
    factor_categories = {
        'alpha_peg': 'valuation',
        'alpha_010': 'price',
        'alpha_038': 'price',
        'alpha_120cq': 'price',
        'cr_qfq': 'momentum',
        'alpha_pluse': 'volume',
        'bias1_qfq': 'volume',
    }

    registered_info = {}

    for factor_name, factor_class in FACTOR_CLASSES.items():
        if factor_class is None:
            logger.warning(f"因子 {factor_name} 类为None，跳过注册")
            continue

        try:
            # 注册到FactorRegistry
            category = factor_categories.get(factor_name, 'unknown')
            FactorRegistry.register(factor_name, factor_class, category)

            # 记录注册信息
            registered_info[factor_name] = {
                'class': factor_class,
                'category': category,
                'status': 'registered'
            }

            logger.info(f"成功注册因子: {factor_name} (类别: {category})")

        except Exception as e:
            logger.error(f"注册因子 {factor_name} 失败: {e}")
            registered_info[factor_name] = {
                'class': factor_class,
                'category': factor_categories.get(factor_name, 'unknown'),
                'status': 'failed',
                'error': str(e)
            }

    logger.info(f"因子注册完成: 成功 {len(registered_info)} 个")
    return registered_info


def list_registered_factors() -> List[str]:
    """
    获取已注册因子列表

    Returns:
        List[str]: 已注册因子名称列表
    """
    return FactorRegistry.list_factors()


def list_factors_by_category(category: str) -> List[str]:
    """
    按类别获取因子列表

    Args:
        category: 因子类别 ('valuation', 'price', 'momentum', 'volume')

    Returns:
        List[str]: 指定类别的因子名称列表
    """
    all_factors = FactorRegistry.list_factors()
    return [name for name, info in all_factors.items()
            if info.get('category') == category]


def verify_registration() -> bool:
    """
    验证因子注册是否成功

    Returns:
        bool: 验证结果
    """
    registered = list_registered_factors()
    expected = ['alpha_peg', 'alpha_010', 'alpha_038', 'alpha_120cq',
                'cr_qfq', 'alpha_pluse', 'bias1_qfq']

    missing = set(expected) - set(registered)

    if missing:
        logger.error(f"缺失的因子: {missing}")
        return False

    logger.info("因子注册验证通过: 所有预期因子均已注册")
    return True


def get_factor_info(factor_name: str) -> Optional[Dict]:
    """
    获取指定因子的注册信息

    Args:
        factor_name: 因子名称

    Returns:
        Dict or None: 因子信息
    """
    all_factors = FactorRegistry.list_factors()
    return all_factors.get(factor_name)


def main():
    """主函数 - 执行因子注册"""
    print("=" * 80)
    print("因子注册脚本启动")
    print("=" * 80)

    # 执行注册
    print("\n[1/3] 正在注册因子...")
    registered = register_all_factors()

    print(f"\n注册结果: 成功 {len(registered)} 个因子")
    for name, info in registered.items():
        status_symbol = "✅" if info['status'] == 'registered' else "❌"
        print(f"  {status_symbol} {name} ({info['category']})")

    # 验证注册
    print("\n[2/3] 正在验证注册...")
    verify_result = verify_registration()

    if verify_result:
        print("✅ 验证通过")
    else:
        print("❌ 验证失败，请检查日志")

    # 显示因子列表
    print("\n[3/3] 已注册因子列表:")
    all_factors = list_registered_factors()
    for factor in all_factors:
        info = get_factor_info(factor)
        print(f"  - {factor} (类别: {info['category']})")

    # 按类别显示
    print("\n按类别分组:")
    for category in ['valuation', 'price', 'momentum', 'volume']:
        factors = list_factors_by_category(category)
        if factors:
            print(f"  {category}: {', '.join(factors)}")

    print("\n" + "=" * 80)
    print("因子注册脚本执行完成")
    print("=" * 80)

    return verify_result


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    success = main()
    exit(0 if success else 1)
