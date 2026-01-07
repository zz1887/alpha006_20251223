# 数据层 (data/)

本目录存放所有数据文件，包括原始数据、处理后的数据和缓存数据。

## 目录结构

```
data/
├── raw/              # 原始数据（从数据库导出或外部获取）
├── processed/        # 处理后的数据（清洗、转换后的数据）
├── cache/            # 缓存数据（加速计算的临时数据）
└── README.md         # 本文件
```

## 数据文件说明

### 原始数据 (raw/)
- 从数据库导出的数据文件
- 外部数据源文件
- 保留原始格式，不修改

### 处理后的数据 (processed/)
- 清洗后的数据
- 标准化后的数据
- 因子计算中间结果

### 缓存数据 (cache/)
- 计算结果缓存
- 避免重复计算
- 可定期清理

## 数据来源

### 数据库表
- `daily_basic`: 日频基本面数据（PE_TTM等）
- `fina_indicator`: 财务指标数据（单季净利润增长率）
- `daily_kline`: 日K线数据（开高低收成交量）
- `index_daily_zzsz`: 指数数据（沪深300）

### 外部文件
- `industry_cache.csv`: 行业分类数据（申万一级行业）

## 数据格式规范

### 因子数据
```csv
ts_code,trade_date,l1_name,pe_ttm,dt_netprofit_yoy,alpha_peg,industry_rank
600000.SH,20250102,银行,5.2,15.3,0.3399,1
600001.SH,20250102,电子,45.2,25.6,1.7656,2
...
```

### 价格数据
```csv
ts_code,trade_date,open,high,low,close,vol
600000.SH,20250102,10.5,10.8,10.4,10.6,123456
...
```

### 交易记录
```csv
buy_date,sell_date,ts_code,buy_price,sell_price,return,holding_days
2025-01-02,2025-01-22,600000.SH,10.5,11.2,0.063,20
...
```

## 数据管理建议

1. **原始数据保持不变**: 不要修改原始数据文件
2. **定期清理缓存**: 缓存文件可定期清理以释放空间
3. **版本控制**: 重要数据文件建议加入版本控制
4. **备份**: 关键数据建议定期备份

## 数据路径配置

所有数据路径在 `config/backtest_config.py` 中的 `PATH_CONFIG` 定义：
- `data_raw`: 原始数据路径
- `data_processed`: 处理后数据路径
- `data_cache`: 缓存数据路径
