"""
文件input(依赖外部什么): datetime, core.config.params, logging
文件output(提供什么): FactorRegistry类，提供因子注册、发现、获取功能
文件pos(系统局部地位): 因子库核心枢纽，连接配置和因子实现，统一因子调用接口
文件功能:
    1. 因子注册和发现
    2. 统一因子调用接口
    3. 版本管理
    4. 因子信息查询

使用示例:
    from factors.core.factor_registry import FactorRegistry

    # 注册因子
    FactorRegistry.register('alpha_peg', AlphaPegFactor, 'valuation')

    # 获取因子实例
    factor = FactorRegistry.get_factor('alpha_peg', version='standard')
    result = factor.calculate(data)

    # 列出因子
    all_factors = FactorRegistry.list_factors()

参数说明:
    name: 因子名称 (如: 'alpha_010')
    factor_class: 因子类
    category: 因子类别 (如: 'price', 'valuation', 'momentum')
    version: 因子版本 (如: 'standard', 'conservative', 'aggressive')

返回值:
    BaseFactor: 因子实例
    Dict[str, Dict]: 因子信息字典
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import logging


class FactorRegistry:
    """
    因子注册器 - 管理所有因子类

    功能：
    1. 因子注册和发现
    2. 统一因子调用接口
    3. 版本管理
    4. 因子信息查询
    """

    _registry = {}  # 因子注册表
    _logger = logging.getLogger('FactorRegistry')

    @classmethod
    def register(cls, name: str, factor_class, category: str = 'general'):
        """
        注册因子

        Args:
            name: 因子名称 (如: 'alpha_010')
            factor_class: 因子类
            category: 因子类别 (如: 'price', 'valuation', 'momentum')
        """
        if name in cls._registry:
            cls._logger.warning(f"因子 {name} 已存在，将被覆盖")

        cls._registry[name] = {
            'class': factor_class,
            'category': category,
            'created': datetime.now(),
            'description': factor_class.__doc__ or '无描述',
        }

        cls._logger.info(f"注册因子: {name} ({category})")

    @classmethod
    def get_factor(cls, name: str, version: str = 'standard', **kwargs):
        """
        获取因子实例

        Args:
            name: 因子名称
            version: 因子版本
            **kwargs: 覆盖参数

        Returns:
            BaseFactor: 因子实例

        Raises:
            ValueError: 因子未注册
        """
        if name not in cls._registry:
            raise ValueError(f"因子未注册: {name}\n可用因子: {list(cls._registry.keys())}")

        factor_info = cls._registry[name]
        factor_class = factor_info['class']

        # 获取参数配置
        params = cls._get_params(name, version)
        params.update(kwargs)

        return factor_class(params)

    @classmethod
    def _get_params(cls, name: str, version: str) -> Dict[str, Any]:
        """
        获取因子参数配置

        Args:
            name: 因子名称
            version: 版本

        Returns:
            Dict[str, Any]: 参数字典
        """
        try:
            # 尝试从config导入参数
            from core.config.params import get_factor_param
            return get_factor_param(name, version)
        except (ImportError, FileNotFoundError):
            cls._logger.warning(f"未找到参数配置，使用默认参数: {name}/{version}")
            return {}

    @classmethod
    def list_factors(cls, category: Optional[str] = None) -> Dict[str, Dict]:
        """
        列出所有因子

        Args:
            category: 类别过滤，None表示所有

        Returns:
            Dict[str, Dict]: 因子信息字典
        """
        if category:
            return {k: v for k, v in cls._registry.items()
                   if v['category'] == category}
        return cls._registry.copy()

    @classmethod
    def get_factor_info(cls, name: str) -> Dict[str, Any]:
        """
        获取因子详细信息

        Args:
            name: 因子名称

        Returns:
            Dict[str, Any]: 因子信息
        """
        if name not in cls._registry:
            raise ValueError(f"因子未注册: {name}")

        info = cls._registry[name].copy()
        info['created'] = info['created'].isoformat()
        return info

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        检查因子是否已注册

        Args:
            name: 因子名称

        Returns:
            bool: 是否已注册
        """
        return name in cls._registry

    @classmethod
    def clear(cls):
        """清空注册表（主要用于测试）"""
        cls._registry.clear()
        cls._logger.info("注册表已清空")

    @classmethod
    def get_categories(cls) -> List[str]:
        """获取所有因子类别"""
        categories = set()
        for info in cls._registry.values():
            categories.add(info['category'])
        return list(categories)