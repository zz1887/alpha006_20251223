"""
全局常量配置 - core/constants/config.py

功能:
- 交易成本配置
- 回测参数配置
- 行业分类配置
- 因子参数配置
"""

# ==================== 交易成本配置 ====================
COMMISSION = 0.0005      # 佣金费率 (0.05%)
STAMP_TAX = 0.002        # 印花税 (0.2%)
SLIPPAGE = 0.001         # 滑点 (0.1%)
TOTAL_COST = COMMISSION + STAMP_TAX + SLIPPAGE  # 总成本 0.35%

# ==================== 回测参数配置 ====================
DEFAULT_INITIAL_CAPITAL = 1000000.0  # 默认初始资金
RISK_FREE_RATE = 0.02                # 无风险利率 (2%)

# ==================== 行业分类配置 ====================
# 行业特定异常值处理阈值
INDUSTRY_THRESHOLD = {
    '银行': 2.5,
    '公用事业': 2.5,
    '交通运输': 2.5,
    '电子': 3.5,
    '电力设备': 3.5,
    '医药生物': 3.5,
    '计算机': 3.5,
}

# 默认异常值阈值
DEFAULT_OUTLIER_SIGMA = 3.0

# ==================== 因子参数配置 ====================
# alpha_peg因子参数
FACTOR_ALPHA_PEG_PARAMS = {
    'outlier_sigma': 3.0,      # 异常值处理阈值
    'normalization': None,     # 标准化方法: None, 'zscore', 'rank'
    'industry_specific': True, # 是否使用行业特定阈值
}

# alpha_pluse因子参数
FACTOR_ALPHA_PLUSE_PARAMS = {
    'window_20d': 20,          # 回溯窗口
    'lookback_14d': 14,        # 成交量均值计算周期
    'lower_mult': 1.4,         # 下限倍数
    'upper_mult': 3.5,         # 上限倍数
    'min_count': 2,            # 最小满足数量
    'max_count': 4,            # 最大满足数量
}

# 排名选股参数
RANK_SELECT_PARAMS = {
    'top_n': 3,                # 每行业选股数量
    'ascending': True,         # 排序方向 (True: 值越小越好)
    'method': 'first',         # 排名方法
}

# 持有期参数
HOLDING_PERIODS = {
    'short': 5,                # 短期
    'medium': 10,              # 中短期
    'optimal': 20,             # 最优
    'long': 30,                # 长期
}

# ==================== 数据库表名配置 ====================
TABLE_DAILY_BASIC = 'daily_basic'
TABLE_FINA_INDICATOR = 'fina_indicator'
TABLE_DAILY_KLINE = 'daily_kline'
TABLE_INDEX_ZZSZ = 'index_daily_zzsz'
TABLE_INDUSTRY = 'industry_cache'

# ==================== 数据字段映射 ====================
FIELD_MAPPING = {
    'pe_ttm': 'pe_ttm',
    'dt_netprofit_yoy': 'dt_netprofit_yoy',
    'open': 'open',
    'high': 'high',
    'low': 'low',
    'close': 'close',
    'vol': 'vol',
    'trade_date': 'trade_date',
    'ann_date': 'ann_date',
    'ts_code': 'ts_code',
    'l1_name': 'l1_name',
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

# ==================== 市场环境配置 ====================
MARKET_ENVIRONMENTS = {
    'bull': '牛市',
    'bear': '熊市',
    '震荡': '震荡市',
    'unknown': '未知',
}

# ==================== 回测时间区间预设 ====================
BACKTEST_PERIODS = {
    '2024Q1': {'start': '20240301', 'end': '20240930', 'name': '2024年熊转牛'},
    '2025Q1': {'start': '20250101', 'end': '20250630', 'name': '2025年震荡市'},
    '2025Q2': {'start': '20250701', 'end': '20251015', 'name': '2025年强势市'},
    'custom': {'start': None, 'end': None, 'name': '自定义区间'},
}
