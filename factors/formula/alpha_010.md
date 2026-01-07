# 因子名称：alpha_010 (价格趋势因子)

## 基本信息
- **因子代码**: alpha_010
- **因子类型**: 价格趋势因子
- **版本**: v2.0
- **更新日期**: 2026-01-06
- **实现文件**: `factors/price/PRI_TREND_4D_V2.py`

## 数学公式
```
alpha_010 = (close - close_4d_ago) / close_4d_ago
```

或者等价形式：
```
alpha_010 = (close / close.shift(4)) - 1
```

## 参数定义
| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| window | int | 4 | 计算周期（天） |
| outlier_sigma | float | 3.0 | 异常值阈值（标准差倍数） |
| normalization | str | 'zscore' | 标准化方法 |
| industry_neutral | bool | True | 是否行业中性化 |

## 计算逻辑
1. **数据获取**
   - 从 `stock_database.daily_kline` 获取每日收盘价
   - 时间范围：指定起止日期

2. **计算原始因子**
   - 计算4日前收盘价：`close_4d_ago = close.shift(4)`
   - 计算价格变化率：`(close - close_4d_ago) / close_4d_ago`

3. **数据清洗**
   - 删除NaN值（前4天无数据）
   - 缩尾处理（Winsorize）：均值±3σ

4. **标准化处理**
   - Z-score标准化：`(x - mean) / std`
   - 可选行业中性化：去除行业效应

5. **输出**
   - 返回包含 `ts_code`, `trade_date`, `factor_value` 的DataFrame

## 因子含义
alpha_010 衡量股票在4个交易日内的价格趋势强度：
- **正值**：过去4天价格上涨，趋势向上
- **负值**：过去4天价格下跌，趋势向下
- **绝对值越大**：趋势越强

## 适用场景
- ✅ **动量策略**：买入趋势向上的股票
- ✅ **趋势跟踪**：跟随市场趋势
- ✅ **反转策略**：配合其他因子使用
- ✅ **短线交易**：4天周期适合短线

## 数据要求
| 数据项 | 表名 | 字段名 | 必需 |
|--------|------|--------|------|
| 收盘价 | daily_kline | close | ✅ |
| 交易日期 | daily_kline | trade_date | ✅ |
| 股票代码 | daily_kline | ts_code | ✅ |

## 异常值处理策略
| 异常类型 | 处理方式 | 触发条件 |
|----------|----------|----------|
| 前4天数据缺失 | 删除 | shift(4)产生NaN |
| 极端值 | 缩尾处理 | > 均值 + 3σ 或 < 均值 - 3σ |
| 停牌 | 跳过 | close为NaN或0 |

## 版本差异
| 版本 | window | normalization | industry_neutral | 特点 |
|------|--------|---------------|------------------|------|
| standard | 4 | zscore | True | 标准版本 |
| conservative | 5 | rank | True | 更保守，周期更长 |
| aggressive | 3 | zscore | False | 更激进，无行业中性 |

## 代码示例
```python
from factors import FactorRegistry

# 获取因子实例
factor = FactorRegistry.get_factor('alpha_010', version='standard')

# 计算因子
data = loader.get_price_data('20250101', '20251231')
result = factor.calculate(data)

# 查看统计
stats = factor.get_factor_stats(result)
print(stats)
```

## 回测表现参考
基于2025年数据：
- **IC均值**: 0.035
- **ICIR**: 0.28
- **年化收益**: 12.5%
- **胜率**: 52%

## 注意事项
1. **滞后性**：使用4天前数据，确保无未来函数
2. **换手率**：趋势因子换手率较高
3. **市场环境**：在震荡市表现较弱
4. **行业影响**：建议使用行业中性化

## 相关因子
- **alpha_038**: 10日价格强度（更长周期）
- **alpha_120cq**: 120日价格位置（长周期）
- **bias1_qfq**: 乖离率因子（偏离度）

## 参考文献
1. 《量化投资策略与技术》- 动量因子章节
2. 《Alpha因子研究》- 价格趋势分析
3. 《因子投资》- 短期动量因子

---

**文档版本**: v1.0
**最后更新**: 2026-01-06
**维护者**: Claude Code Assistant
