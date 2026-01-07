"""
因子参数配置 - 独立参数管理
版本: v2.0
更新日期: 2025-12-30

说明:
- 所有因子参数集中管理
- 支持多版本配置（保守/平衡/激进）
- 支持参数动态调整
"""

# ==================== 因子参数配置 ====================
FACTOR_PARAMS = {
    # alpha_pluse - 量能因子
    # 核心逻辑: 20日内满足「交易量=14日均值的1.4-3.5倍」的交易日数量∈[2,4]则=1，否则=0
    'alpha_pluse': {
        'standard': {  # 标准版
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.4,
            'upper_mult': 3.5,
            'min_count': 2,
            'max_count': 4,
            'min_data_days': 34,
        },
        'conservative': {  # 保守版
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.5,
            'upper_mult': 3.0,
            'min_count': 3,
            'max_count': 4,
            'min_data_days': 34,
        },
        'aggressive': {  # 激进版
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.3,
            'upper_mult': 4.0,
            'min_count': 2,
            'max_count': 5,
            'min_data_days': 34,
        },
    },

    # alpha_peg - 估值因子
    # 核心逻辑: PE_TTM / 单季净利润同比增长率
    'alpha_peg': {
        'standard': {  # 基础版
            'outlier_sigma': 3.0,
            'update_flag': '1',
            'min_pe': 0,
            'min_growth': -999,
            'normalization': None,
            'industry_specific': False,
        },
        'conservative': {  # 保守版
            'outlier_sigma': 2.5,
            'update_flag': '1',
            'min_pe': 0,
            'min_growth': -999,
            'normalization': None,
            'industry_specific': True,
        },
        'aggressive': {  # 激进版
            'outlier_sigma': 3.5,
            'update_flag': '1',
            'min_pe': 0,
            'min_growth': -999,
            'normalization': None,
            'industry_specific': True,
        },
    },

    # alpha_peg_industry_zscore - 行业标准化
    # 标准化方法: (alpha_peg - 行业均值) / 行业标准差
    'alpha_peg_industry_zscore': {
        'standard': {
            'industry_threshold': 5,  # 行业最小样本数
            'zscore_method': 'standard',
            'fill_missing': 'industry_mean',
            'outlier_handling': True,
        },
        'conservative': {
            'industry_threshold': 8,
            'zscore_method': 'robust',  # 使用中位数和MAD
            'fill_missing': 'global_mean',
            'outlier_handling': True,
        },
        'aggressive': {
            'industry_threshold': 3,
            'zscore_method': 'standard',
            'fill_missing': 'zero',
            'outlier_handling': False,
        },
    },

    # alpha_038 - 价格强度因子
    # 核心逻辑: (-1 × rank(Ts_Rank(close, 10))) × rank(close/open)
    'alpha_038': {
        'standard': {
            'window': 10,
            'min_data_days': 10,
            'close_open_ratio': True,
        },
        'conservative': {
            'window': 15,
            'min_data_days': 15,
            'close_open_ratio': True,
        },
        'aggressive': {
            'window': 5,
            'min_data_days': 5,
            'close_open_ratio': True,
        },
    },

    # alpha_120cq - 价格位置因子
    # 核心逻辑: 当日收盘价在120日有效交易日序列中的分位数
    'alpha_120cq': {
        'standard': {
            'window': 120,
            'min_days': 30,
            'min_data_days': 120,
            'method': 'quantile',  # 分位数方法
        },
        'conservative': {
            'window': 180,
            'min_days': 50,
            'min_data_days': 180,
            'method': 'quantile',
        },
        'aggressive': {
            'window': 60,
            'min_days': 20,
            'min_data_days': 60,
            'method': 'quantile',
        },
    },

    # cr_qfq - 动量因子
    # 核心逻辑: CR指标(N=20)，基于前复权的HIGH/LOW/CLOSE计算
    'cr_qfq': {
        'standard': {
            'period': 20,
            'source_table': 'stk_factor_pro',
            'normalization': 'max_scale',
        },
        'conservative': {
            'period': 30,
            'source_table': 'stk_factor_pro',
            'normalization': 'max_scale',
        },
        'aggressive': {
            'period': 10,
            'source_table': 'stk_factor_pro',
            'normalization': 'max_scale',
        },
    },

    # alpha_010 - 短周期价格趋势因子
    # 核心逻辑: 4日Δclose的ts_min/ts_max三元规则 + 全市场rank
    # 计算公式: Δclose = close_t - close_{t-1}
    # 三元规则: ts_min>0或ts_max<0取Δclose，否则取-Δclose
    # 最终: rank(规则取值) 得到alpha_010
    'alpha_010': {
        'standard': {
            'window': 4,
            'min_data_days': 5,  # 4+1
        },
        'conservative': {
            'window': 6,
            'min_data_days': 7,  # 6+1
        },
        'aggressive': {
            'window': 3,
            'min_data_days': 4,  # 3+1
        },
    },
}

# ==================== 策略参数配置 ====================
STRATEGY_PARAMS = {
    # 策略3 - 多因子综合得分
    'strategy3': {
        'standard': {
            'name': '多因子综合得分策略',
            'weights': {
                'alpha_pluse': 0.20,
                'alpha_peg_zscore': 0.25,
                'alpha_120cq': 0.15,
                'cr_qfq': 0.20,
                'alpha_038': 0.20,
            },
            'directions': {
                'alpha_pluse': 'negative',
                'alpha_peg_zscore': 'negative',
                'alpha_120cq': 'positive',
                'cr_qfq': 'positive',
                'alpha_038': 'negative',
            },
            'normalizations': {
                'alpha_pluse': 'binary',      # 1 - alpha_pluse
                'alpha_peg_zscore': 'none',   # -alpha_peg_zscore
                'alpha_120cq': 'none',        # 直接使用
                'cr_qfq': 'max_scale',        # / max
                'alpha_038': 'min_scale',     # - / min
            },
            'holding_period': 20,
            'top_n': 100,
            'min_stocks': 50,
        },
        'conservative': {
            'name': '保守型多因子策略',
            'weights': {
                'alpha_pluse': 0.15,
                'alpha_peg_zscore': 0.35,
                'alpha_120cq': 0.10,
                'cr_qfq': 0.15,
                'alpha_038': 0.25,
            },
            'holding_period': 30,
            'top_n': 50,
        },
        'aggressive': {
            'name': '激进型多因子策略',
            'weights': {
                'alpha_pluse': 0.25,
                'alpha_peg_zscore': 0.15,
                'alpha_120cq': 0.20,
                'cr_qfq': 0.25,
                'alpha_038': 0.15,
            },
            'holding_period': 10,
            'top_n': 200,
        },
    },

    # 六大因子选股策略
    'six_factor': {
        'standard': {
            'name': '六大因子综合选股策略',
            'filters': {
                'alpha_pluse': 1,              # 量能因子必须为1
                'min_amount': 50_000,          # 最小成交额5万（适配当前数据）
                'min_market_cap': 100_000_000, # 最小市值1亿（适配当前数据）
                'exclude_st': True,            # 剔除ST
                'exclude_suspension': True,    # 剔除停牌
            },
            'factor_thresholds': {
                'alpha_peg': 0.30,             # alpha_peg前30%
                'alpha_010': 0.30,             # alpha_010前30%
                'alpha_038': 0.30,             # alpha_038前30%
                'alpha_120cq_low': 0.20,       # alpha_120cq下限
                'alpha_120cq_high': 0.80,      # alpha_120cq上限
                'cr_qfq': 0.40,                # cr_qfq前40%
            },
            'weights': {
                'alpha_peg': 0.20,
                'alpha_010': 0.20,
                'alpha_038': 0.20,
                'alpha_120cq': 0.15,
                'cr_qfq': 0.15,
                'alpha_pluse': 0.10,           # 量能因子
            },
            'directions': {
                'alpha_peg': 'negative',       # 越小越好
                'alpha_010': 'positive',       # 越大越好（修正）
                'alpha_038': 'positive',       # 越大越好（修正：公式已含-1）
                'alpha_120cq': 'positive',     # 越大越好
                'cr_qfq': 'positive',          # 越大越好
                'alpha_pluse': 'positive',     # 越大越好（0或1）
            },
            'top_n': 100,                      # 输出前100名
        },
        'conservative': {
            'name': '保守型六大因子策略',
            'filters': {
                'alpha_pluse': 1,
                'min_amount': 100_000,         # 更严格：10万
                'min_market_cap': 200_000_000, # 更严格：2亿
                'exclude_st': True,
                'exclude_suspension': True,
            },
            'factor_thresholds': {
                'alpha_peg': 0.20,             # 更严格：前20%
                'alpha_010': 0.20,
                'alpha_038': 0.20,
                'alpha_120cq_low': 0.30,       # 更严格：[0.3, 0.7]
                'alpha_120cq_high': 0.70,
                'cr_qfq': 0.30,
            },
            'weights': {
                'alpha_peg': 0.25,             # 估值权重更高
                'alpha_010': 0.15,
                'alpha_038': 0.15,
                'alpha_120cq': 0.20,           # 位置权重更高
                'cr_qfq': 0.15,
                'alpha_pluse': 0.10,
            },
            'directions': {
                'alpha_peg': 'negative',
                'alpha_010': 'positive',  # 修正
                'alpha_038': 'positive',  # 修正
                'alpha_120cq': 'positive',
                'cr_qfq': 'positive',
                'alpha_pluse': 'positive',
            },
            'top_n': 50,
        },
        'aggressive': {
            'name': '激进型六大因子策略',
            'filters': {
                'alpha_pluse': 1,
                'min_amount': 20_000,          # 更宽松：2万
                'min_market_cap': 50_000_000,  # 更宽松：0.5亿
                'exclude_st': True,
                'exclude_suspension': True,
            },
            'factor_thresholds': {
                'alpha_peg': 0.40,             # 更宽松：前40%
                'alpha_010': 0.40,
                'alpha_038': 0.40,
                'alpha_120cq_low': 0.10,       # 更宽松：[0.1, 0.9]
                'alpha_120cq_high': 0.90,
                'cr_qfq': 0.50,
            },
            'weights': {
                'alpha_peg': 0.15,
                'alpha_010': 0.25,             # 趋势权重更高
                'alpha_038': 0.15,
                'alpha_120cq': 0.10,
                'cr_qfq': 0.20,                # 动量权重更高
                'alpha_pluse': 0.15,           # 量能权重更高
            },
            'directions': {
                'alpha_peg': 'negative',
                'alpha_010': 'positive',  # 修正
                'alpha_038': 'positive',  # 修正
                'alpha_120cq': 'positive',
                'cr_qfq': 'positive',
                'alpha_pluse': 'positive',
            },
            'top_n': 200,
        },
        # 优化版本V1 - 基于202406-202412回测数据优化
        'optimized_v1': {
            'name': '六大因子策略 - 优化版V1',
            'description': '基于7个月回测数据优化，alpha_010+5%, alpha_peg-5%',
            'optimization_date': '2026-01-01',
            'filters': {
                'alpha_pluse': 1,
                'min_amount': 50_000,
                'min_market_cap': 100_000_000,
                'exclude_st': True,
                'exclude_suspension': True,
            },
            'factor_thresholds': {
                'alpha_peg': 0.30,
                'alpha_010': 0.30,
                'alpha_038': 0.30,
                'alpha_120cq_low': 0.20,
                'alpha_120cq_high': 0.80,
                'cr_qfq': 0.40,
            },
            'weights': {
                'alpha_peg': 0.15,      # 优化: -5% (牛市贡献弱)
                'alpha_010': 0.25,      # 优化: +5% (牛市表现佳)
                'alpha_038': 0.20,      # 保持
                'alpha_120cq': 0.15,    # 保持
                'cr_qfq': 0.15,         # 保持
                'alpha_pluse': 0.10,    # 保持
            },
            'directions': {
                'alpha_peg': 'negative',
                'alpha_010': 'positive',
                'alpha_038': 'positive',
                'alpha_120cq': 'positive',
                'cr_qfq': 'positive',
                'alpha_pluse': 'positive',
            },
            'top_n': 100,
        },
        # 优化版本V2 - 基于202406-202501回测数据优化
        'optimized_v2': {
            'name': '六大因子策略 - 优化版V2',
            'description': '基于完整周期优化，调整权重+降低换手率',
            'optimization_date': '2026-01-01',
            'filters': {
                'alpha_pluse': 1,
                'min_amount': 50_000,
                'min_market_cap': 100_000_000,
                'exclude_st': True,
                'exclude_suspension': True,
            },
            'factor_thresholds': {
                'alpha_peg': 0.30,
                'alpha_010': 0.30,
                'alpha_038': 0.30,
                'alpha_120cq_low': 0.20,
                'alpha_120cq_high': 0.80,
                'cr_qfq': 0.40,
            },
            'weights': {
                'alpha_peg': 0.15,      # 降低: 0.20 -> 0.15 (IC不稳定)
                'alpha_010': 0.25,      # 提高: 0.20 -> 0.25 (短期趋势有效)
                'alpha_038': 0.20,      # 保持: 0.20
                'alpha_120cq': 0.15,    # 降低: 0.20 -> 0.15 (长期位置)
                'cr_qfq': 0.25,         # 提高: 0.20 -> 0.25 (动量因子)
            },
            'directions': {
                'alpha_peg': 'negative',
                'alpha_010': 'positive',
                'alpha_038': 'positive',
                'alpha_120cq': 'positive',
                'cr_qfq': 'positive',
            },
            'min_hold_days': 5,        # 新增: 最少持有5天
            'rebalance_freq': '1M',    # 保持月度调仓
            'top_n': 100,
        },
    },
}

# ==================== 异常值处理配置 ====================
OUTLIER_HANDLING = {
    'standard': {
        'method': 'sigma',  # 3σ原则
        'threshold': 3.0,
        'action': 'clip',   # 截断处理
    },
    'conservative': {
        'method': 'sigma',
        'threshold': 2.5,
        'action': 'clip',
    },
    'aggressive': {
        'method': 'sigma',
        'threshold': 3.5,
        'action': 'clip',
    },
    'robust': {
        'method': 'iqr',    # 四分位距
        'threshold': 1.5,
        'action': 'clip',
    },
}

# ==================== 数据质量阈值 ====================
DATA_QUALITY_THRESHOLD = {
    'min_valid_ratio': 0.8,      # 最小有效数据比例
    'max_outlier_ratio': 0.05,   # 最大异常值比例
    'max_missing_ratio': 0.2,    # 最大缺失值比例
    'min_stock_count': 500,      # 最小股票数量
}

# ==================== 版本配置映射 ====================
VERSION_MAPPING = {
    'alpha_pluse': {
        'standard': FACTOR_PARAMS['alpha_pluse']['standard'],
        'conservative': FACTOR_PARAMS['alpha_pluse']['conservative'],
        'aggressive': FACTOR_PARAMS['alpha_pluse']['aggressive'],
    },
    'alpha_peg': {
        'standard': FACTOR_PARAMS['alpha_peg']['standard'],
        'conservative': FACTOR_PARAMS['alpha_peg']['conservative'],
        'aggressive': FACTOR_PARAMS['alpha_peg']['aggressive'],
    },
    'alpha_038': {
        'standard': FACTOR_PARAMS['alpha_038']['standard'],
        'conservative': FACTOR_PARAMS['alpha_038']['conservative'],
        'aggressive': FACTOR_PARAMS['alpha_038']['aggressive'],
    },
    'alpha_120cq': {
        'standard': FACTOR_PARAMS['alpha_120cq']['standard'],
        'conservative': FACTOR_PARAMS['alpha_120cq']['conservative'],
        'aggressive': FACTOR_PARAMS['alpha_120cq']['aggressive'],
    },
    'cr_qfq': {
        'standard': FACTOR_PARAMS['cr_qfq']['standard'],
        'conservative': FACTOR_PARAMS['cr_qfq']['conservative'],
        'aggressive': FACTOR_PARAMS['cr_qfq']['aggressive'],
    },
    'alpha_010': {
        'standard': FACTOR_PARAMS['alpha_010']['standard'],
        'conservative': FACTOR_PARAMS['alpha_010']['conservative'],
        'aggressive': FACTOR_PARAMS['alpha_010']['aggressive'],
    },
}

# ==================== 工具函数 ====================
def get_factor_param(factor_name, version='standard', param_name=None):
    """
    获取因子参数

    Args:
        factor_name: 因子名称
        version: 版本 (standard/conservative/aggressive)
        param_name: 参数名 (None表示返回所有参数)

    Returns:
        参数值或参数字典
    """
    if factor_name not in FACTOR_PARAMS:
        raise ValueError(f"未知因子: {factor_name}")

    if version not in FACTOR_PARAMS[factor_name]:
        raise ValueError(f"未知版本: {version}")

    params = FACTOR_PARAMS[factor_name][version]

    if param_name is None:
        return params
    else:
        return params.get(param_name)

def get_strategy_param(strategy_name, version='standard', param_name=None):
    """
    获取策略参数
    """
    if strategy_name not in STRATEGY_PARAMS:
        raise ValueError(f"未知策略: {strategy_name}")

    if version not in STRATEGY_PARAMS[strategy_name]:
        raise ValueError(f"未知版本: {version}")

    params = STRATEGY_PARAMS[strategy_name][version]

    if param_name is None:
        return params
    else:
        return params.get(param_name)

def list_available_factors():
    """列出所有可用因子"""
    return list(FACTOR_PARAMS.keys())

def list_available_strategies():
    """列出所有可用策略"""
    return list(STRATEGY_PARAMS.keys())

def list_versions(factor_or_strategy_name):
    """列出因子或策略的所有版本"""
    if factor_or_strategy_name in FACTOR_PARAMS:
        return list(FACTOR_PARAMS[factor_or_strategy_name].keys())
    elif factor_or_strategy_name in STRATEGY_PARAMS:
        return list(STRATEGY_PARAMS[factor_or_strategy_name].keys())
    else:
        raise ValueError(f"未知因子或策略: {factor_or_strategy_name}")

# ==================== 配置验证 ====================
def validate_params():
    """验证参数配置完整性"""
    errors = []

    # 检查因子参数
    for factor_name, versions in FACTOR_PARAMS.items():
        if 'standard' not in versions:
            errors.append(f"因子 {factor_name} 缺少标准版配置")

        for version_name, params in versions.items():
            if not isinstance(params, dict):
                errors.append(f"因子 {factor_name} 版本 {version_name} 配置格式错误")

    # 检查策略参数
    for strategy_name, versions in STRATEGY_PARAMS.items():
        if 'standard' not in versions:
            errors.append(f"策略 {strategy_name} 缺少标准版配置")

        for version_name, params in versions.items():
            if not isinstance(params, dict):
                errors.append(f"策略 {strategy_name} 版本 {version_name} 配置格式错误")

    return errors

# ==================== 配置导出 ====================
__all__ = [
    'FACTOR_PARAMS',
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

# 配置初始化检查
if __name__ == '__main__':
    errors = validate_params()
    if errors:
        print("参数配置验证错误:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ 参数配置验证通过")

        # 示例：获取参数
        print("\n示例参数:")
        print(f"alpha_pluse 标准版: {get_factor_param('alpha_pluse', 'standard')}")
        print(f"strategy3 标准版权重: {get_strategy_param('strategy3', 'standard', 'weights')}")