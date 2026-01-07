"""
策略运行器

统一调度策略执行，提供统一的调用接口
"""

import importlib
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class StrategyRunner:
    """策略运行器"""

    # 策略映射表
    STRATEGY_MAP = {
    "MFM_5F_M_AGG": {"config": "strategies.configs.MFM_5F_M_AGG", "executor": "strategies.executors.MFM_5F_executor", "description": "多因子5月度激进策略"},

    "MFM_5F_M_CON": {"config": "strategies.configs.MFM_5F_M_CON", "executor": "strategies.executors.MFM_5F_executor", "description": "多因子5月度保守策略"},

        'six_factor_monthly': {'config': 'strategies.configs.SFM_6F_M_V1', 'executor': 'strategies.executors.SFM_6F_executor', 'description': '六因子月末智能调仓策略 - 标准版',
            'executor': 'strategies.executors.six_factor_executor',
            'description': '六因子月末智能调仓策略',
        },
        'six_factor_monthly_v2': {'config': 'strategies.configs.SFM_6F_M_V2', 'executor': 'strategies.executors.SFM_6F_executor', 'description': '六因子月末智能调仓策略 - 优化版',
            'executor': 'strategies.executors.six_factor_executor',
            'description': '六因子月末智能调仓策略 - 优化版',
        },
        'strategy3': {'config': 'strategies.configs.MFM_5F_M_V1', 'executor': 'strategies.executors.MFM_5F_executor', 'description': '多因子综合得分策略 - 标准版',
            'executor': 'strategies.executors.strategy3_executor',
            'description': '多因子综合得分策略',
        },
        # 兼容旧名称
        'six_factor': {
            'config': 'strategies.configs.six_factor_monthly_v1',
            'executor': 'strategies.executors.six_factor_executor',
            'description': '六因子策略(兼容模式)',
        },
    }

    @classmethod
    def get_config_module(cls, strategy_name: str) -> Optional[str]:
        """获取策略配置模块路径"""
        if strategy_name not in cls.STRATEGY_MAP:
            return None
        return cls.STRATEGY_MAP[strategy_name]['config']

    @classmethod
    def list_strategies(cls) -> Dict[str, str]:
        """列出所有可用策略"""
        return {name: info['description'] for name, info in cls.STRATEGY_MAP.items()}

    @classmethod
    def get_strategy_info(cls, strategy_name: str) -> Optional[Dict[str, Any]]:
        """获取策略信息"""
        if strategy_name not in cls.STRATEGY_MAP:
            return None
        return cls.STRATEGY_MAP[strategy_name]

    @classmethod
    def load_config(cls, strategy_name: str) -> Optional[Dict[str, Any]]:
        """
        加载策略配置

        Args:
            strategy_name: 策略名称

        Returns:
            策略配置字典
        """
        if strategy_name not in cls.STRATEGY_MAP:
            logger.error(f"未知策略: {strategy_name}")
            return None

        strategy_info = cls.STRATEGY_MAP[strategy_name]
        config_module = strategy_info['config']

        try:
            module = importlib.import_module(config_module)

            # 尝试获取配置
            if hasattr(module, 'get_strategy_config'):
                return module.get_strategy_config()
            elif hasattr(module, 'get_strategy_params'):
                return {'params': module.get_strategy_params()}
            else:
                # 直接返回模块中的配置
                return {name: getattr(module, name) for name in dir(module) if name.isupper()}

        except Exception as e:
            logger.error(f"加载策略配置失败: {e}")
            return None

    @classmethod
    def run_strategy(cls, strategy_name: str, start_date: str, end_date: str, version: str = 'standard', **kwargs) -> bool:
        """
        运行策略

        Args:
            strategy_name: 策略名称
            start_date: 开始日期
            end_date: 结束日期
            version: 策略版本
            **kwargs: 其他参数

        Returns:
            是否成功
        """
        if strategy_name not in cls.STRATEGY_MAP:
            logger.error(f"未知策略: {strategy_name}")
            return False

        strategy_info = cls.STRATEGY_MAP[strategy_name]
        executor_module = strategy_info['executor']

        print("\n" + "="*80)
        print(f"策略执行: {strategy_info['description']}")
        print("="*80)
        print(f"策略名称: {strategy_name}")
        print(f"时间区间: {start_date} - {end_date}")
        print(f"策略版本: {version}")
        print("="*80 + "\n")

        try:
            # 动态导入执行器
            executor_class = importlib.import_module(executor_module)

            # 获取执行器类（通常命名为 StrategyExecutor）
            if hasattr(executor_class, 'execute'):
                # 函数式调用
                result = executor_class.execute(start_date, end_date, version=version, **kwargs)
                return result
            else:
                # 类式调用
                executor_cls_name = ''.join(word.capitalize() for word in strategy_name.split('_')) + 'Executor'
                if hasattr(executor_class, executor_cls_name):
                    executor_cls = getattr(executor_class, executor_cls_name)
                    executor = executor_cls(start_date, end_date, version=version, **kwargs)
                    result = executor.execute()
                    return result

            logger.error(f"执行器 {executor_module} 没有可用的 execute 方法")
            return False

        except Exception as e:
            logger.error(f"策略执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    @classmethod
    def run_batch(cls, strategies: list, start_date: str, end_date: str, **kwargs) -> Dict[str, bool]:
        """
        批量运行多个策略

        Args:
            strategies: 策略名称列表
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数

        Returns:
            各策略执行结果
        """
        results = {}
        for strategy in strategies:
            print(f"\n{'='*60}")
            print(f"开始执行策略: {strategy}")
            print(f"{'='*60}")
            success = cls.run_strategy(strategy, start_date, end_date, **kwargs)
            results[strategy] = success

        return results