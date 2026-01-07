"""
文件input(依赖外部什么): settings.py, params.py
文件output(提供什么): 项目所有配置项统一导入接口
文件pos(系统局部地位): 核心配置层入口，提供全局配置管理
文件功能:
    1. 项目基础配置（路径、环境、数据库）
    2. 因子参数配置（多版本参数管理）
    3. 策略配置（回测、交易、风控）
    4. 数据质量配置（验证阈值、异常值处理）
    5. 版本控制配置（因子版本映射）

使用示例:
    from core.config import get_factor_param, get_path, DATABASE_CONFIG

    # 获取因子参数
    params = get_factor_param('alpha_peg', version='standard')

    # 获取项目路径
    data_path = get_path('data')

    # 数据库配置
    db_config = DATABASE_CONFIG

返回值:
    Dict: 配置字典
    str: 配置项值
    function: 配置获取函数

配置体系:
    1. settings.py - 基础配置（路径、数据库、表名、交易成本）
    2. params.py - 参数配置（因子参数、策略参数、版本映射）
    3. 环境配置 - 开发/测试/生产环境区分
    4. 版本控制 - 因子多版本管理（标准/保守/激进/行业优化）
"""

from .settings import (
    PROJECT_CONFIG,
    ENV_CONFIG,
    PATHS,
    DATABASE_CONFIG,
    TABLE_NAMES,
    TRADING_COSTS,
    BACKTEST_CONFIG,
    FACTOR_PARAMS,
    INDUSTRY_CONFIG,
    STRATEGY_CONFIG,
    LOG_CONFIG,
    DATA_QUALITY,
    VERSION_CONTROL,
    OUTPUT_CONFIG,
    VALIDATION_CONFIG,
    PERFORMANCE_CONFIG,
    GLOBAL_CONSTANTS,
    get_config,
    get_factor_params,
    get_path,
    validate_config,
)

from .params import (
    FACTOR_PARAMS as FACTOR_PARAMS_V2,
    STRATEGY_PARAMS,
    OUTLIER_HANDLING,
    DATA_QUALITY_THRESHOLD,
    VERSION_MAPPING,
    get_factor_param,
    get_strategy_param,
    list_available_factors,
    list_available_strategies,
    list_versions,
    validate_params,
)

__all__ = [
    # settings.py
    'PROJECT_CONFIG',
    'ENV_CONFIG',
    'PATHS',
    'DATABASE_CONFIG',
    'TABLE_NAMES',
    'TRADING_COSTS',
    'BACKTEST_CONFIG',
    'FACTOR_PARAMS',
    'INDUSTRY_CONFIG',
    'STRATEGY_CONFIG',
    'LOG_CONFIG',
    'DATA_QUALITY',
    'VERSION_CONTROL',
    'OUTPUT_CONFIG',
    'VALIDATION_CONFIG',
    'PERFORMANCE_CONFIG',
    'GLOBAL_CONSTANTS',
    'get_config',
    'get_factor_params',
    'get_path',
    'validate_config',

    # params.py
    'FACTOR_PARAMS_V2',
    'STRATEGY_PARAMS',
    'OUTLIER_HANDLING',
    'DATA_QUALITY_THRESHOLD',
    'VERSION_MAPPING',
    'get_factor_param',
    'get_strategy_param',
    'list_available_factors',
    'list_available_strategies',
    'list_versions',
    'validate_params',
]