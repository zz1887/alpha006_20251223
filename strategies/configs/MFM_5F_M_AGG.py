"""
多因子综合得分策略配置 - 激进版

策略名称: MFM_5F_M_AGG
策略版本: v1.0-aggressive
创建日期: 2025-12-30
优化日期: 2026-01-03

策略特点:
- 多因子综合得分计算
- 激进配置: 重量能，宽筛选
- 行业标准化处理
- 动态阈值调整

调用方式:
    python strategies/runners/run_strategy.py --strategy MFM_5F_M_AGG --start 20240601 --end 20251130
"""

from typing import Dict, Any

# ==================== 策略基础信息 ====================
STRATEGY_INFO = {
    'name': '多因子5月度激进策略',
    'code': 'MFM_5F_M_AGG',
    'version': 'v1.0-aggressive',
    'author': '量化策略组',
    'create_date': '2025-12-30',
    'description': '基于5因子的激进型月度策略',
}

# ==================== 因子配置 (激进版) ====================
FACTOR_CONFIG = {
    'factors': {
        'VOL_EXP_20D_V2': {
            'name': '量能扩张因子',
            'weight': 0.20,
            'direction': 'positive',
            'normalization': 'binary',
            'threshold': 1,
        },
        'VAL_GROW_行业_Q': {
            'name': '估值增长因子',
            'weight': 0.20,
            'direction': 'negative',
            'normalization': 'zscore',
            'industry_specific': True,
        },
        'PRI_STR_10D_V2': {
            'name': '价格强度因子',
            'weight': 0.20,
            'direction': 'positive',
            'normalization': 'none',
        },
        'PRI_POS_120D_V2': {
            'name': '价格位置因子',
            'weight': 0.20,
            'direction': 'positive',
            'normalization': 'none',
        },
        'MOM_CR_20D_V2': {
            'name': '动量因子',
            'weight': 0.20,
            'direction': 'positive',
            'normalization': 'max_scale',
        },
    },

    'calculation_params': {
        'VOL_EXP_20D_V2': {
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.4,
            'upper_mult': 3.5,
            'min_count': 2,
            'max_count': 4,
            'min_data_days': 34,
        },
        'VAL_GROW_行业_Q': {
            'outlier_sigma': 3.5,
            'min_pe': 0,
            'min_growth': -999,
            'normalization': 'zscore',
            'industry_specific': True,
            'min_industry_samples': 5,
        },
        'PRI_STR_10D_V2': {
            'window': 10,
            'min_data_days': 10,
        },
        'PRI_POS_120D_V2': {
            'window': 120,
            'min_days': 30,
            'min_data_days': 120,
        },
        'MOM_CR_20D_V2': {
            'period': 20,
            'source_table': 'stk_factor_pro',
        },
    },
}

# ==================== 股票池过滤条件 (激进) ====================
FILTER_CONFIG = {
    'base_filters': {
        'min_amount': 30000,
        'min_market_cap': 50000000,
        'exclude_st': True,
        'exclude_suspension': True,
    },
    'industry_filter': {
        'enabled': True,
        'min_samples': 5,
    },
}

# ==================== 选股配置 ====================
SELECTION_CONFIG = {
    'method': 'top_n_by_factor',
    'top_n': 20,
    'max_holdings': 50,
    'min_holdings': 10,
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
    'holding_period': 20,
}

# ==================== 调仓配置 ====================
REBALANCE_CONFIG = {
    'frequency': 'monthly',
    'monthly_logic': {
        'type': 'smart_nearest',
        'description': '月末为交易日则月末调仓,否则为离月末最近的一天调仓',
    },
}

# ==================== 策略调用接口 ====================
def get_strategy_config() -> Dict[str, Any]:
    """获取完整策略配置"""
    return {
        'info': STRATEGY_INFO,
        'factors': FACTOR_CONFIG,
        'filters': FILTER_CONFIG,
        'selection': SELECTION_CONFIG,
        'rebalance': REBALANCE_CONFIG,
        'trading_cost': TRADING_COST_CONFIG,
        'backtest': BACKTEST_CONFIG,
    }

def get_strategy_params() -> Dict[str, Any]:
    """获取策略运行参数"""
    return {
        'weights': {
            'VOL_EXP_20D_V2': 0.20,
            'VAL_GROW_行业_Q': 0.20,
            'PRI_STR_10D_V2': 0.20,
            'PRI_POS_120D_V2': 0.20,
            'MOM_CR_20D_V2': 0.20,
        },
        'directions': {
            'VOL_EXP_20D_V2': 'positive',
            'VAL_GROW_行业_Q': 'negative',
            'PRI_STR_10D_V2': 'positive',
            'PRI_POS_120D_V2': 'positive',
            'MOM_CR_20D_V2': 'positive',
        },
        'filters': {
            'min_amount': 30000,
            'min_market_cap': 50000000,
            'exclude_st': True,
            'exclude_suspension': True,
        },
        'trading_cost': {
            'commission': 0.0005,
            'stamp_tax': 0.001,
            'slippage': 0.001,
            'total': 0.0025,
        },
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
    'SELECTION_CONFIG',
    'REBALANCE_CONFIG',
    'TRADING_COST_CONFIG',
    'BACKTEST_CONFIG',
    'get_strategy_config',
    'get_strategy_params',
]
