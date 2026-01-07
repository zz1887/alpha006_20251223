"""
向后兼容层

确保现有的脚本和代码能够继续工作，同时使用新的策略框架
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/home/zcy/alpha006_20251223')

# 兼容旧的导入路径
def setup_backward_compatibility():
    """
    设置向后兼容

    这个函数应该在项目启动时调用，确保旧的导入路径仍然有效
    """

    # 1. 使旧的脚本路径能够导入新框架
    import strategies.base.strategy_runner as new_runner

    # 2. 创建兼容的模块别名
    sys.modules['scripts.run_strategy'] = new_runner
    sys.modules['config.strategies.six_factor_monthly'] = __import__('strategies.configs.six_factor_monthly_v1', fromlist=[''])

    # 3. 提供兼容的函数
    from strategies.base.strategy_runner import StrategyRunner

    # 兼容的函数签名
    def run_strategy_old(strategy_name, start_date, end_date, version='standard'):
        """旧的run_strategy函数兼容"""
        return StrategyRunner.run_strategy(strategy_name, start_date, end_date, version)

    def run_six_factor_old(start_date, end_date, version='standard'):
        """旧的六因子运行函数"""
        return StrategyRunner.run_strategy('six_factor_monthly', start_date, end_date, version)

    # 注入到全局命名空间
    globals()['run_strategy'] = run_strategy_old
    globals()['run_six_factor'] = run_six_factor_old

    return True

# 提供快速导入的便捷函数
def import_old_config(module_name):
    """
    导入旧配置文件并转换为新格式

    Args:
        module_name: 旧模块名，如 'config.strategies.six_factor_monthly'

    Returns:
        配置字典
    """
    try:
        # 尝试导入旧模块
        module = __import__(module_name, fromlist=[''])

        # 如果有get_strategy_config函数，直接使用
        if hasattr(module, 'get_strategy_config'):
            return module.get_strategy_config()

        # 否则转换模块内容
        config = {}
        for name in dir(module):
            if name.isupper() and not name.startswith('_'):
                config[name.lower()] = getattr(module, name)

        return config

    except ImportError:
        # 如果旧模块不存在，尝试新路径
        new_module_name = module_name.replace('config.strategies.', 'strategies.configs.')
        try:
            module = __import__(new_module_name, fromlist=[''])
            if hasattr(module, 'get_strategy_config'):
                return module.get_strategy_config()
        except ImportError:
            return None

# 自动设置兼容性
if __name__ == '__main__':
    setup_backward_compatibility()
    print("向后兼容层已设置")
    print("旧脚本应该可以继续工作")