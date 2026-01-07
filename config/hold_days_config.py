"""
持仓天数优化配置 - config/hold_days_config.py

功能:
- 定义持仓天数优化的参数配置
- 支持快速切换和调整
"""

# ==================== 持仓天数测试范围配置 ====================
HOLD_DAYS_RANGE_CONFIG = {
    'full_test': {
        'name': '完整测试',
        'range': list(range(10, 46)),  # 10-45天
        'step': 1,
        'description': '10-45天完整范围测试'
    },
    'short_term': {
        'name': '短期测试',
        'range': list(range(1, 16)),  # 1-15天
        'step': 1,
        'description': '1-15天短期范围测试'
    },
    'medium_term': {
        'name': '中期测试',
        'range': list(range(10, 31)),  # 10-30天
        'step': 2,
        'description': '10-30天中期范围测试，步长2'
    },
    'quick_test': {
        'name': '快速测试',
        'range': [5, 10, 15, 20, 25, 30, 35, 40, 45],
        'step': 1,
        'description': '关键节点快速测试'
    }
}

# ==================== 回测区间配置 ====================
BACKTEST_PERIODS = {
    'full_period': {
        'start': '20240801',
        'end': '20250930',
        'name': '完整周期',
        'description': '2024年8月-2025年9月'
    },
    'validation_2025Q1': {
        'start': '20250101',
        'end': '20250331',
        'name': '2025Q1验证',
        'description': '2025年第一季度验证'
    },
    'validation_2025Q2': {
        'start': '20250401',
        'end': '20250630',
        'name': '2025Q2验证',
        'description': '2025年第二季度验证'
    },
    'validation_2025Q3': {
        'start': '20250701',
        'end': '20250930',
        'name': '2025Q3验证',
        'description': '2025年第三季度验证'
    },
    'monthly_202501': {
        'start': '20250101',
        'end': '20250131',
        'name': '2025年1月',
        'description': '2025年1月单月验证'
    },
    'monthly_202502': {
        'start': '20250201',
        'end': '20250228',
        'name': '2025年2月',
        'description': '2025年2月单月验证'
    },
    'monthly_202503': {
        'start': '20250301',
        'end': '20250331',
        'name': '2025年3月',
        'description': '2025年3月单月验证'
    }
}

# ==================== 筛选指标权重配置 ====================
SCORING_WEIGHTS = {
    'conservative': {
        'name': '保守型',
        'sharpe_ratio': 0.5,
        'total_return': 0.2,
        'max_drawdown': 0.2,
        'turnover': 0.1,
        'description': '注重风险控制，夏普和回撤权重高'
    },
    'balanced': {
        'name': '平衡型',
        'sharpe_ratio': 0.4,
        'total_return': 0.3,
        'max_drawdown': 0.2,
        'turnover': 0.1,
        'description': '收益与风险平衡'
    },
    'aggressive': {
        'name': '激进型',
        'sharpe_ratio': 0.3,
        'total_return': 0.5,
        'max_drawdown': 0.1,
        'turnover': 0.1,
        'description': '追求高收益，夏普权重降低'
    },
    'sharpe_first': {
        'name': '夏普优先',
        'sharpe_ratio': 0.6,
        'total_return': 0.2,
        'max_drawdown': 0.15,
        'turnover': 0.05,
        'description': '夏普比率最高优先级'
    }
}

# ==================== 因子参数配置 ====================
FACTOR_PARAMS = {
    'alpha_peg': {
        'outlier_sigma': 3.0,
        'normalization': None,
        'industry_specific': True,
        'top_n': 3,
        'description': '标准alpha_peg因子参数'
    },
    'conservative': {
        'outlier_sigma': 2.5,
        'normalization': None,
        'industry_specific': True,
        'top_n': 2,
        'description': '保守版参数'
    },
    'aggressive': {
        'outlier_sigma': 3.5,
        'normalization': None,
        'industry_specific': True,
        'top_n': 5,
        'description': '激进版参数'
    }
}

# ==================== 交易成本配置 ====================
TRADING_COSTS = {
    'standard': {
        'commission': 0.0005,
        'stamp_tax': 0.002,
        'slippage': 0.001,
        'total': 0.0035,
        'description': '标准交易成本'
    },
    'low_cost': {
        'commission': 0.0003,
        'stamp_tax': 0.001,
        'slippage': 0.0005,
        'total': 0.0018,
        'description': '低成本环境'
    },
    'high_cost': {
        'commission': 0.001,
        'stamp_tax': 0.003,
        'slippage': 0.002,
        'total': 0.006,
        'description': '高成本环境'
    }
}

# ==================== 输出配置 ====================
OUTPUT_CONFIG = {
    'save_comparison': True,
    'save_detailed': True,
    'save_visual': True,
    'save_report': True,
    'save_industry': True,
    'save_stability': True,
    'print_summary': True,
    'save_format': 'csv'  # csv or excel
}

# ==================== 默认执行配置 ====================
DEFAULT_EXECUTION_CONFIG = {
    'period': 'full_period',
    'hold_days_range': 'full_test',
    'factor_params': 'alpha_peg',
    'trading_cost': 'standard',
    'scoring_method': 'sharpe_first',
    'initial_capital': 1000000.0,
    'output_dir': 'results/backtest'
}
