"""
文件input(依赖外部什么): 无(纯配置文件)
文件output(提供什么): SFM策略优化版配置参数
文件pos(系统局部地位): 策略配置层, 为执行器提供参数

六因子月末智能调仓策略配置 - 优化版V1
优化时间: 2026-01-01
优化依据: 202406-202412（7个月）回测数据分析

优化内容:
- alpha_010权重: 20% → 25% (+5%)
- alpha_peg权重: 20% → 15% (-5%)
- 优化逻辑: 增强牛市收益捕捉，保持熊市保护

策略名称: SFM (Six-Factor Monthly) - Optimized V1
策略版本: v1.1-optimized
"""

from typing import Dict, Any

# ==================== 策略基础信息 ====================
STRATEGY_INFO = {
    'name': '六因子月末智能调仓策略 - 优化版V1',
    'code': 'SFM-OPT-V1',
    'version': 'v1.1-optimized',
    'author': '量化策略组',
    'create_date': '2026-01-01',
    'description': '基于7个月回测数据优化的6因子策略',
    'optimization_basis': '202406-202412回测分析',
}

# ==================== 因子配置（优化版） ====================
FACTOR_CONFIG = {
    'factors': {
        'alpha_pluse': {
            'name': '量能因子',
            'weight': 0.10,
            'direction': 'positive',
            'normalization': 'binary',
            'threshold': 1,
        },
        'alpha_peg': {
            'name': '估值因子',
            'weight': 0.15,
            'direction': 'negative',
            'normalization': 'zscore',
            'industry_specific': True,
        },
        'alpha_010': {
            'name': '短期趋势因子',
            'weight': 0.25,
            'direction': 'positive',
            'normalization': 'none',
        },
        'alpha_038': {
            'name': '价格强度因子',
            'weight': 0.20,
            'direction': 'positive',
            'normalization': 'none',
        },
        'alpha_120cq': {
            'name': '价格位置因子',
            'weight': 0.15,
            'direction': 'positive',
            'normalization': 'none',
        },
        'cr_qfq': {
            'name': '动量因子',
            'weight': 0.15,
            'direction': 'positive',
            'normalization': 'max_scale',
        },
    },

    'calculation_params': {
        'alpha_pluse': {
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.4,
            'upper_mult': 3.5,
            'min_count': 2,
            'max_count': 4,
            'min_data_days': 34,
        },
        'alpha_peg': {
            'outlier_sigma': 3.0,
            'min_pe': 0,
            'min_growth': -999,
            'normalization': 'zscore',
            'industry_specific': True,
            'min_industry_samples': 5,
        },
        'alpha_038': {
            'window': 10,
            'min_data_days': 10,
        },
        'alpha_120cq': {
            'window': 120,
            'min_days': 30,
            'min_data_days': 120,
        },
        'cr_qfq': {
            'period': 20,
            'source_table': 'stk_factor_pro',
        },
    },
}

# ==================== 股票池过滤条件 ====================
FILTER_CONFIG = {
    'base_filters': {
        'min_amount': 50000,
        'min_market_cap': 100000000,
        'exclude_st': True,
        'exclude_suspension': True,
    },
    'alpha_pluse_filter': {
        'enabled': True,
        'threshold': 1,
    },
    'industry_filter': {
        'enabled': True,
        'min_samples': 5,
    },
}

# ==================== 调仓配置 ====================
REBALANCE_CONFIG = {
    'frequency': 'monthly',
    'monthly_logic': {
        'type': 'smart_nearest',
        'description': '月末为交易日则月末调仓,否则为离月末最近的一天调仓',
        'priority': 'closest',
    },
    'grouping': {
        'n_groups': 5,
        'method': 'quantile',
        'group_1_direction': 'high_score',
    },
    'weighting': {
        'method': 'market_cap',
        'cap_type': 'circulating',
    },
}

# ==================== 交易成本 ====================
TRADING_COST_CONFIG = {
    'commission': 0.0005,
    'stamp_tax': 0.001,
    'slippage': 0.001,
    'total': 0.0025,
}

# ==================== 回测参数 ====================
BACKTEST_CONFIG = {
    'initial_capital': 1000000.0,
    'risk_free_rate': 0.03,
    'benchmark': '000300.SH',
    'holding_period': 21,
}

# ==================== 预期性能指标 ====================
EXPECTED_METRICS = {
    'group_1_sharpe': 1.5,
    'long_short_sharpe': 1.0,
    'ic_mean': 0.01,
    'icir': 0.5,
    'avg_turnover': 0.9,
}

# ==================== 输出配置 ====================
OUTPUT_CONFIG = {
    'save_metrics': True,
    'save_data': True,
    'save_log': True,
    'save_visual': True,
    'save_report': True,
    'print_progress': True,
}

# ==================== 策略调用接口 ====================
def get_strategy_config() -> Dict[str, Any]:
    """获取完整策略配置"""
    return {
        'info': STRATEGY_INFO,
        'factors': FACTOR_CONFIG,
        'filters': FILTER_CONFIG,
        'rebalance': REBALANCE_CONFIG,
        'trading_cost': TRADING_COST_CONFIG,
        'backtest': BACKTEST_CONFIG,
        'expected': EXPECTED_METRICS,
        'output': OUTPUT_CONFIG,
    }

def get_strategy_params() -> Dict[str, Any]:
    """获取策略运行参数（优化版V1）"""
    return {
        # 因子权重（优化版）
        'weights': {
            'alpha_pluse': 0.10,
            'alpha_peg': 0.15,
            'alpha_010': 0.25,
            'alpha_038': 0.20,
            'alpha_120cq': 0.15,
            'cr_qfq': 0.15,
        },
        # 因子方向
        'directions': {
            'alpha_pluse': 'positive',
            'alpha_peg': 'negative',
            'alpha_010': 'positive',
            'alpha_038': 'positive',
            'alpha_120cq': 'positive',
            'cr_qfq': 'positive',
        },
        # 过滤条件
        'filters': {
            'min_amount': 50000,
            'min_market_cap': 100000000,
            'exclude_st': True,
            'exclude_suspension': True,
        },
        # 因子阈值
        'factor_thresholds': {
            'alpha_peg': 0.3,
            'alpha_010': 0.3,
            'alpha_038': 0.3,
            'alpha_120cq_low': 0.2,
            'alpha_120cq_high': 0.8,
            'cr_qfq': 0.4,
        },
        # 交易成本
        'trading_cost': {
            'commission': 0.0005,
            'stamp_tax': 0.001,
            'slippage': 0.001,
            'total': 0.0025,
        },
        # 回测参数
        'backtest': {
            'initial_capital': 1000000.0,
            'risk_free_rate': 0.03,
            'benchmark': '000300.SH',
        },
    }

__all__ = [
    'STRATEGY_INFO',
    'FACTOR_CONFIG',
    'FILTER_CONFIG',
    'REBALANCE_CONFIG',
    'TRADING_COST_CONFIG',
    'BACKTEST_CONFIG',
    'EXPECTED_METRICS',
    'OUTPUT_CONFIG',
    'get_strategy_config',
    'get_strategy_params',
]