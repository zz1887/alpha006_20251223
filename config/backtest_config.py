"""
回测配置 - config/backtest_config.py

功能:
- 回测时间区间配置
- 策略参数配置
- 交易成本配置
- 市场环境配置
"""

from typing import Dict, Any

# ==================== 回测时间区间配置 ====================
BACKTEST_PERIODS = {
    '2024Q1': {
        'name': '2024年熊转牛',
        'start': '20240301',
        'end': '20240930',
        'market_env': '熊转牛'
    },
    '2025Q1': {
        'name': '2025年震荡市',
        'start': '20250101',
        'end': '20250630',
        'market_env': '震荡'
    },
    '2025Q2': {
        'name': '2025年强势市',
        'start': '20250701',
        'end': '20251015',
        'market_env': '牛市'
    },
    'custom': {
        'name': '自定义区间',
        'start': None,
        'end': None,
        'market_env': '未知'
    },
}

# ==================== 策略参数配置 ====================
STRATEGY_PARAMS = {
    'industry_rank': {
        'top_n': 3,
        'holding_days': 20,
        'outlier_sigma': 3.0,
        'normalization': None,
        'industry_specific': True,
    },
}

# ==================== 交易成本配置 ====================
TRADING_COSTS = {
    'commission': 0.0005,   # 佣金 0.05%
    'stamp_tax': 0.002,     # 印花税 0.2%
    'slippage': 0.001,      # 滑点 0.1%
    'total': 0.0035,        # 总成本 0.35%
}

# ==================== 资金配置 ====================
CAPITAL_CONFIG = {
    'initial': 1000000.0,   # 初始资金
    'risk_free_rate': 0.02, # 无风险利率
}

# ==================== 因子参数配置 ====================
FACTOR_PARAMS = {
    'alpha_peg': {
        'outlier_sigma': 3.0,
        'normalization': None,
        'industry_specific': True,
        'columns': ['ts_code', 'trade_date', 'l1_name', 'pe_ttm', 'dt_netprofit_yoy', 'alpha_peg', 'industry_rank'],
    },
}

# ==================== 行业特定阈值 ====================
INDUSTRY_THRESHOLD = {
    '银行': 2.5,
    '公用事业': 2.5,
    '交通运输': 2.5,
    '电子': 3.5,
    '电力设备': 3.5,
    '医药生物': 3.5,
    '计算机': 3.5,
}

# ==================== 数据库配置 (WSL Ubuntu) ====================
DATABASE_CONFIG = {
    'type': 'mysql',
    'user': 'root',
    'password': '12345678',
    'host': '172.31.112.1',  # Windows主机IP
    'port': 3306,
    'db_name': 'stock_database',
    'charset': 'utf8mb4',
}

# ==================== 路径配置 (WSL Ubuntu) ====================
PATH_CONFIG = {
    'project_root': '/home/zcy/alpha006_20251223',
    'industry_data': '/mnt/c/Users/mm/PyCharmMiscProject/获取数据代码/industry_cache.csv',
    'data_raw': '/home/zcy/alpha006_20251223/data/raw',
    'data_processed': '/home/zcy/alpha006_20251223/data/processed',
    'data_cache': '/home/zcy/alpha006_20251223/data/cache',
    'results_factor': '/home/zcy/alpha006_20251223/results/factor',
    'results_backtest': '/home/zcy/alpha006_20251223/results/backtest',
    'results_reports': '/home/zcy/alpha006_20251223/results/reports',
    'results_visual': '/home/zcy/alpha006_20251223/results/visual',
    'logs': '/home/zcy/alpha006_20251223/logs',
    'temp': '/home/zcy/alpha006_20251223/temp',
}

# ==================== 数据库表名配置 ====================
TABLE_NAMES = {
    'daily_basic': 'daily_basic',
    'fina_indicator': 'fina_indicator',
    'daily_kline': 'daily_kline',
    'index_daily_zzsz': 'index_daily_zzsz',
}

# ==================== 策略预设配置 ====================
STRATEGY_PRESETS = {
    't20_standard': {
        'name': 'T+20标准策略',
        'params': {
            'top_n': 3,
            'holding_days': 20,
            'outlier_sigma': 3.0,
            'normalization': None,
        },
        'description': '每行业前3名，持有20天，行业优化版'
    },
    't10_short': {
        'name': 'T+10短线策略',
        'params': {
            'top_n': 3,
            'holding_days': 10,
            'outlier_sigma': 3.0,
            'normalization': None,
        },
        'description': '每行业前3名，持有10天'
    },
    't5_quick': {
        'name': 'T+5快线策略',
        'params': {
            'top_n': 3,
            'holding_days': 5,
            'outlier_sigma': 3.0,
            'normalization': None,
        },
        'description': '每行业前3名，持有5天'
    },
    't30_long': {
        'name': 'T+30长线策略',
        'params': {
            'top_n': 3,
            'holding_days': 30,
            'outlier_sigma': 3.0,
            'normalization': None,
        },
        'description': '每行业前3名，持有30天'
    },
    'conservative': {
        'name': '保守策略',
        'params': {
            'top_n': 2,
            'holding_days': 20,
            'outlier_sigma': 2.5,
            'normalization': None,
        },
        'description': '每行业前2名，严格筛选'
    },
    'aggressive': {
        'name': '激进策略',
        'params': {
            'top_n': 5,
            'holding_days': 20,
            'outlier_sigma': 3.5,
            'normalization': None,
        },
        'description': '每行业前5名，宽松筛选'
    },
}

# ==================== 因子版本配置 ====================
FACTOR_VERSIONS = {
    'basic': {
        'name': '基础版',
        'params': {
            'outlier_sigma': 3.0,
            'normalization': None,
            'industry_specific': False
        }
    },
    'industry_optimized': {
        'name': '行业优化版',
        'params': {
            'outlier_sigma': 3.0,
            'normalization': None,
            'industry_specific': True
        }
    },
    'zscore': {
        'name': 'Z-score标准化',
        'params': {
            'outlier_sigma': 3.0,
            'normalization': 'zscore',
            'industry_specific': True
        }
    },
    'rank': {
        'name': '排名标准化',
        'params': {
            'outlier_sigma': 3.0,
            'normalization': 'rank',
            'industry_specific': True
        }
    },
}

# ==================== 输出配置 ====================
OUTPUT_CONFIG = {
    'save_factor': True,
    'save_trades': True,
    'save_nav': True,
    'save_report': True,
    'save_visual': False,
    'print_progress': True,
}

# ==================== 日志配置 ====================
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': '/home/zcy/alpha006_20251223/logs/backtest.log',
}
