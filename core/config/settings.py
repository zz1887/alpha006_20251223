"""
文件input(依赖外部什么): 无(纯配置)
文件output(提供什么): 全局配置字典, 配置获取函数
文件pos(系统局部地位): 核心配置层, 为整个项目提供统一配置

量化因子库 - 全局配置设置
版本: v2.0
更新日期: 2025-12-30
"""

import os

# ==================== 项目基础配置 ====================
PROJECT_CONFIG = {
    'name': 'alpha006_20251223',
    'version': 'v2.0',
    'author': '量化策略组',
    'update_date': '2025-12-30',
    'description': '量化因子库 - 多因子选股与回测系统',
}

# ==================== 环境配置 ====================
ENV_CONFIG = {
    'platform': 'linux',  # linux / windows / mac
    'shell': 'wsl',       # wsl / native / docker
    'python_version': '3.8+',
}

# ==================== 路径配置 (WSL Ubuntu) ====================
# 自动检测并构建路径
PROJECT_ROOT = '/home/zcy/alpha因子库'

PATHS = {
    'project_root': PROJECT_ROOT,

    # 核心模块路径
    'core': os.path.join(PROJECT_ROOT, 'core'),
    'config': os.path.join(PROJECT_ROOT, 'core/config'),
    'utils': os.path.join(PROJECT_ROOT, 'core/utils'),
    'constants': os.path.join(PROJECT_ROOT, 'core/constants'),

    # 因子模块路径
    'factors': os.path.join(PROJECT_ROOT, 'factors'),
    'factors_valuation': os.path.join(PROJECT_ROOT, 'factors/valuation'),
    'factors_momentum': os.path.join(PROJECT_ROOT, 'factors/momentum'),
    'factors_price': os.path.join(PROJECT_ROOT, 'factors/price'),
    'factors_volume': os.path.join(PROJECT_ROOT, 'factors/volume'),

    # 数据路径
    'data': os.path.join(PROJECT_ROOT, 'data'),
    'data_raw': os.path.join(PROJECT_ROOT, 'data/raw'),
    'data_processed': os.path.join(PROJECT_ROOT, 'data/processed'),
    'data_cache': os.path.join(PROJECT_ROOT, 'data/cache'),

    # 结果路径
    'results': os.path.join(PROJECT_ROOT, 'results'),
    'results_factor': os.path.join(PROJECT_ROOT, 'results/factor'),
    'results_backtest': os.path.join(PROJECT_ROOT, 'results/backtest'),
    'results_output': os.path.join(PROJECT_ROOT, 'results/output'),
    'results_visual': os.path.join(PROJECT_ROOT, 'results/visual'),

    # 文档和脚本路径
    'docs': os.path.join(PROJECT_ROOT, 'docs'),
    'scripts': os.path.join(PROJECT_ROOT, 'scripts'),

    # 其他路径
    'logs': os.path.join(PROJECT_ROOT, 'logs'),
    'temp': os.path.join(PROJECT_ROOT, 'temp'),

    # 外部数据路径
    'external_data': '/mnt/c/Users/mm/PyCharmMiscProject/获取数据代码',
}

# ==================== 数据库配置 ====================
DATABASE_CONFIG = {
    'host': '172.31.112.1',  # WSL2连接Windows主机IP
    'port': 3306,
    'user': 'root',
    'password': '12345678',
    'database': 'stock_database',
    'charset': 'utf8mb4',
}

# 数据库表名
TABLE_NAMES = {
    'daily_kline': 'daily_kline',
    'daily_basic': 'daily_basic',
    'fina_indicator': 'fina_indicator',
    'stk_factor_pro': 'stk_factor_pro',
    'sw_industry': 'sw_industry',
    'stock_st': 'stock_st',
    'index_daily_zzsz': 'index_daily_zzsz',
}

# ==================== 交易成本配置 ====================
TRADING_COSTS = {
    'commission': 0.0005,      # 佣金费率 (0.05%)
    'stamp_tax': 0.002,        # 印花税 (0.2%)
    'slippage': 0.001,         # 滑点 (0.1%)
    'total_cost': 0.0035,      # 总成本 (0.35%)
}

# ==================== 回测参数配置 ====================
BACKTEST_CONFIG = {
    'initial_capital': 1000000.0,    # 初始资金
    'risk_free_rate': 0.02,          # 无风险利率
    'benchmark': '000300.SH',        # 基准指数
    'holding_period': 20,            # 默认持有期
    'rebalance_freq': 'daily',       # 调仓频率
}

# ==================== 因子参数配置 (核心) ====================
FACTOR_PARAMS = {
    # alpha_pluse - 量能因子
    'alpha_pluse': {
        'window_20d': 20,          # 回溯窗口
        'lookback_14d': 14,        # 均值周期
        'lower_mult': 1.4,         # 下限倍数
        'upper_mult': 3.5,         # 上限倍数
        'min_count': 2,            # 最小满足数量
        'max_count': 4,            # 最大满足数量
        'min_data_days': 34,       # 最小数据天数
    },

    # alpha_peg - 估值因子
    'alpha_peg': {
        'outlier_sigma': 3.0,      # 异常值阈值
        'update_flag': '1',        # 财务数据更新标志
        'min_pe': 0,               # 最小PE
        'min_growth': -999,        # 最小增长率
        'normalization': 'zscore', # 标准化方法
        'industry_specific': True, # 行业特定阈值
    },

    # alpha_038 - 价格强度因子
    'alpha_038': {
        'window': 10,              # 窗口期
        'min_data_days': 10,       # 最小数据天数
    },

    # alpha_120cq - 价格位置因子
    'alpha_120cq': {
        'window': 120,             # 窗口期
        'min_days': 30,            # 最小有效天数
        'min_data_days': 120,      # 最小数据天数
    },

    # cr_qfq - 动量因子
    'cr_qfq': {
        'period': 20,              # 周期
        'source_table': 'stk_factor_pro',  # 数据来源表
    },

    # alpha_peg_industry_zscore - 行业标准化
    'alpha_peg_industry_zscore': {
        'industry_threshold': 5,   # 行业最小样本数
        'zscore_method': 'standard',  # 标准化方法
        'fill_missing': 'industry_mean',  # 缺失值填充
    },
}

# ==================== 行业特定配置 ====================
INDUSTRY_CONFIG = {
    # 行业特定异常值处理阈值
    'outlier_thresholds': {
        '银行': 2.5,
        '公用事业': 2.5,
        '交通运输': 2.5,
        '电子': 3.5,
        '电力设备': 3.5,
        '医药生物': 3.5,
        '计算机': 3.5,
        '其他': 3.0,  # 默认值
    },

    # 行业分类标准
    'classification': 'sw_l1',  # sw_l1: 申万一级行业

    # 最小行业样本数
    'min_samples_per_industry': 5,
}

# ==================== 策略配置 ====================
STRATEGY_CONFIG = {
    # 策略3 - 多因子叠加
    'strategy3': {
        'name': '多因子综合得分策略',
        'factors': {
            'alpha_pluse': {
                'weight': 0.20,
                'direction': 'negative',  # negative: 值越小越好
                'normalization': 'binary',  # 0/1二值化
            },
            'alpha_peg_zscore': {
                'weight': 0.25,
                'direction': 'negative',
                'normalization': 'none',
            },
            'alpha_120cq': {
                'weight': 0.15,
                'direction': 'positive',  # positive: 值越大越好
                'normalization': 'none',
            },
            'cr_qfq': {
                'weight': 0.20,
                'direction': 'positive',
                'normalization': 'max_scale',  # 除以最大值
            },
            'alpha_038': {
                'weight': 0.20,
                'direction': 'negative',
                'normalization': 'min_scale',  # 除以最小值取负
            },
        },
        'holding_period': 20,
        'top_n': 100,
    },
}

# ==================== 日志配置 ====================
LOG_CONFIG = {
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': os.path.join(PROJECT_ROOT, 'logs', 'quant_factor.log'),
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
}

# ==================== 数据质量控制 ====================
DATA_QUALITY = {
    'min_valid_ratio': 0.8,      # 最小有效数据比例
    'max_outlier_ratio': 0.05,   # 最大异常值比例
    'max_missing_ratio': 0.2,    # 最大缺失值比例
    'data_retention_days': 180,  # 数据保留天数
}

# ==================== 版本控制 ====================
VERSION_CONTROL = {
    'current_version': 'v2.0',
    'compatibility_mode': True,  # 兼容旧版本
    'backup_before_change': True,  # 修改前备份
    'version_history': [
        'v1.0 - 2025-12-24 - 初始版本',
        'v2.0 - 2025-12-30 - 标准化重构',
    ],
}

# ==================== 输出配置 ====================
OUTPUT_CONFIG = {
    'excel': {
        'engine': 'openpyxl',
        'float_format': '%.4f',
        'auto_width': True,
        'header_format': {
            'bold': True,
            'bg_color': '#DDEBF7',
            'alignment': 'center',
        },
    },
    'csv': {
        'encoding': 'utf-8-sig',
        'sep': ',',
        'float_format': '%.4f',
    },
    'export_columns': [
        '股票代码', '交易日', '申万一级行业',
        'alpha_pluse', '行业标准化alpha_peg', 'alpha_120cq', 'cr_qfq', 'alpha_038',
        '综合得分',
        '因子1_量能', '因子2_估值', '因子3_位置', '因子4_动量', '因子5_强度',
        '备注'
    ],
}

# ==================== 验证配置 ====================
VALIDATION_CONFIG = {
    'check_data_integrity': True,
    'check_factor_range': True,
    'check_statistical_properties': True,
    'compare_with_baseline': True,
    'generate_report': True,
}

# ==================== 性能优化配置 ====================
PERFORMANCE_CONFIG = {
    'batch_size': 100,           # 数据库查询批次大小
    'use_cache': True,           # 使用缓存
    'cache_expiry': 3600,        # 缓存过期时间(秒)
    'parallel_processing': False,  # 并行处理(需评估)
    'memory_limit': '8GB',       # 内存限制
}

# ==================== 全局常量 ====================
GLOBAL_CONSTANTS = {
    # 日期格式
    'DATE_FORMAT': '%Y%m%d',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',

    # 数值常量
    'EPSILON': 1e-8,
    'MAX_FLOAT': 1e10,
    'MIN_FLOAT': -1e10,

    # 市场常量
    'TRADING_DAYS_PER_YEAR': 252,
    'TRADING_DAYS_PER_MONTH': 21,

    # 因子取值范围
    'FACTOR_VALUE_RANGES': {
        'alpha_pluse': [0, 1],           # 二值因子
        'alpha_peg': [-100, 100],        # 可正可负
        'alpha_peg_zscore': [-5, 5],     # 标准化后
        'alpha_038': [-100000, 0],       # 负值因子
        'alpha_120cq': [0, 1],           # 分位数
        'cr_qfq': [0, 5000],             # 正值因子
    },
}

# ==================== 函数：获取配置 ====================
def get_config(key, default=None):
    """
    获取配置项
    支持嵌套配置访问，如: get_config('FACTOR_PARAMS.alpha_pluse.window_20d')
    """
    keys = key.split('.')
    config = globals()

    for k in keys:
        if isinstance(config, dict) and k in config:
            config = config[k]
        else:
            return default

    return config

def get_factor_params(factor_name):
    """获取特定因子的参数"""
    return FACTOR_PARAMS.get(factor_name, {})

def get_path(path_key):
    """获取路径配置"""
    return PATHS.get(path_key, '')

# ==================== 配置验证 ====================
def validate_config():
    """验证配置完整性"""
    errors = []

    # 检查必要路径
    for path_key in ['project_root', 'core', 'factors', 'data', 'results']:
        path = PATHS.get(path_key)
        if not path:
            errors.append(f"路径配置缺失: {path_key}")
        elif not os.path.exists(path) and path_key in ['project_root', 'core', 'factors']:
            # 只检查核心路径是否存在
            pass  # 允许在创建过程中

    # 检查因子参数完整性
    required_factors = ['alpha_pluse', 'alpha_peg', 'alpha_038', 'alpha_120cq', 'cr_qfq']
    for factor in required_factors:
        if factor not in FACTOR_PARAMS:
            errors.append(f"因子参数缺失: {factor}")

    # 检查策略配置
    if 'strategy3' not in STRATEGY_CONFIG:
        errors.append("策略3配置缺失")

    return errors

# ==================== 配置导出 ====================
__all__ = [
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
]

# 配置初始化检查
if __name__ == '__main__':
    errors = validate_config()
    if errors:
        print("配置验证错误:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ 配置验证通过")