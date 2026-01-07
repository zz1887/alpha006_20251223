# Alpha101因子参考文档

## 📋 因子索引

本文档包含101个Alpha因子的Inputs、Outputs和公式，来源于聚宽Alpha101因子库。

---

## 因子列表

### Alpha_001
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5)
```

---

### Alpha_002
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1*correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6))
```

---

### Alpha_003
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1*correlation(rank(open), rank(volume), 10))
```

---

### Alpha_004
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1*Ts_Rank(rank(low), 9))
```

---

### Alpha_005
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(rank((open - (sum(vwap, 10) / 10)))*(-1*abs(rank((close - vwap)))))
```

---

### Alpha_006
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1*correlation(open, volume, 10))
```

---

### Alpha_007
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values：符合条件的为公式里的数值，不符合条件的为-1

**公式:**
```
((adv20 < volume) ? ((-1*ts_rank(abs(delta(close, 7)), 60))*sign(delta(close, 7))) : (-1*1))
```

---

### Alpha_008
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1*rank(((sum(open, 5)*sum(returns, 5)) - delay((sum(open, 5)*sum(returns, 5)), 10))))
```

---

### Alpha_009
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1*delta(close, 1))))
```

---

### Alpha_010
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : (-1*delta(close, 1)))))
```

---

### Alpha_011
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3)))*rank(delta(volume, 3)))
```

---

### Alpha_012
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(sign(delta(volume, 1))*(-1 * delta(close, 1)))
```

---

### Alpha_013
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1*rank(covariance(rank(close), rank(volume), 5)))
```

---

### Alpha_014
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((-1*rank(delta(returns, 3)))*correlation(open, volume, 10))
```

---

### Alpha_015
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1*sum(rank(correlation(rank(high), rank(volume), 3)), 3))
```

---

### Alpha_016
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1*rank(covariance(rank(high), rank(volume), 5)))
```

---

### Alpha_017
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为对应的因子值，取值有问题的股票对应值为-0.0

**公式:**
```
((-1*rank(ts_rank(close, 10)))*rank(delta(delta(close, 1), 1)))*rank(ts_rank((volume / adv20), 5)))
```

---

### Alpha_018
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1*rank(((stddev(abs((close - open)), 5) + (close - open)) + correlation(close, open, 10))))
```

---

### Alpha_019
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((-1*sign(((close - delay(close, 7)) + delta(close, 7))))*(1 + rank((1 + sum(returns, 250)))))
```

---

### Alpha_020
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((-1*rank((open - delay(high, 1))))* rank((open - delay(close, 1))))* rank((open - delay(low, 1))))
```

---

### Alpha_021
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，取决于满不满足某些因子中的条件

**公式:**
```
((((sum(close, 8) / 8) + stddev(close, 8)) < (sum(close, 2) / 2)) ? (-1* 1) : (((sum(close, 2) / 2) < ((sum(close, 8) / 8) - stddev(close, 8))) ? 1 : (((1 < (volume / adv20)) or ((volume / adv20) == 1)) ? 1 : (-1* 1))))
```

---

### Alpha_022
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1* (delta(correlation(high, volume, 5), 5)* rank(stddev(close, 20))))
```

---

### Alpha_023
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为对应因子值或0.00，当不满足条件时为0.00

**公式:**
```
(((sum(high, 20) / 20) < high) ? (-1* delta(high, 2)) : 0)
```

---

### Alpha_024
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((((delta((sum(close, 100) / 100), 100) / delay(close, 100)) < 0.05) or ((delta((sum(close, 100) / 100), 100) / delay(close, 100)) == 0.05)) ? (-1* (close - ts_min(close, 100))) : (-1* delta(close, 3)))
```

---

### Alpha_025
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
rank(((((-1* returns)* adv20)* vwap)* (high - close)))
```

---

### Alpha_026
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1* ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3))
```

---

### Alpha_027
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，满足条件为-1，不满足为1

**公式:**
```
((0.5 < rank((sum(correlation(rank(volume), rank(vwap), 6), 2) / 2.0))) ? (-1* 1) : 1)
```

---

### Alpha_028
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
scale(((correlation(adv20, low, 5) + ((high + low) / 2)) - close))
```

---

### Alpha_029
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(min(product(rank(rank(scale(log(sum(ts_min(rank(rank((-1*rank(delta((close - 1), 5))))), 2), 1))))), 1), 5) + ts_rank(delay((-1* returns), 6), 5))
```

---

### Alpha_030
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(((1.0 - rank(((sign((close - delay(close, 1))) + sign((delay(close, 1) - delay(close, 2)))) + sign((delay(close, 2) - delay(close, 3))))))* sum(volume, 5)) / sum(volume, 20))
```

---

### Alpha_031
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((rank(rank(rank(decay_linear((-1* rank(rank(delta(close, 10)))), 10)))) + rank((-1* delta(close, 3)))) + sign(scale(correlation(adv20, low, 12))))
```

---

### Alpha_032
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(scale(((sum(close, 7) / 7) - close)) + (20* scale(correlation(vwap, delay(close, 5), 230))))
```

---

### Alpha_033
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
rank((-1* ((1 - (open / close))^1)))
```

---

### Alpha_034
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
rank(((1 - rank((stddev(returns, 2) / stddev(returns, 5)))) + (1 - rank(delta(close, 1)))))
```

---

### Alpha_035
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((Ts_Rank(volume, 32)* (1 - Ts_Rank(((close + high) - low), 16)))* (1 - Ts_Rank(returns, 32)))
```

---

### Alpha_036
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(((((2.21* rank(correlation((close - open), delay(volume, 1), 15))) + (0.7* rank((open - close)))) + (0.73* rank(Ts_Rank(delay((-1* returns), 6), 5)))) + rank(abs(correlation(vwap, adv20, 6)))) + (0.6* rank((((sum(close, 200) / 200) - open)* (close - open)))))
```

---

### Alpha_037
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(rank(correlation(delay((open - close), 1), close, 200)) + rank((open - close)))
```

---

### Alpha_038
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((-1* rank(Ts_Rank(close, 10)))* rank((close / open)))
```

---

### Alpha_039
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((-1* rank((delta(close, 7)* (1 - rank(decay_linear((volume / adv20), 9))))))* (1 + rank(sum(returns, 250))))
```

---

### Alpha_040
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((-1* rank(stddev(high, 10)))* correlation(high, volume, 10))
```

---

### Alpha_041
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(((high* low)^0.5) - vwap)
```

---

### Alpha_042
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(rank((vwap - close)) / rank((vwap + close)))
```

---

### Alpha_043
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(ts_rank((volume / adv20), 20)* ts_rank((-1* delta(close, 7)), 8))
```

---

### Alpha_044
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1* correlation(high, rank(volume), 5))
```

---

### Alpha_045
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1* ((rank((sum(delay(close, 5), 20) / 20))* correlation(close, volume, 2))* rank(correlation(sum(close, 5), sum(close, 20), 2))))
```

---

### Alpha_046
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1或对应因子值，取决于满不满足某些因子中的条件

**公式:**
```
((0.25 < (((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10))) ? (-1* 1) : (((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < 0) ? 1 : ((-1* 1)* (close - delay(close, 1)))))
```

---

### Alpha_047
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((((rank((1 / close))* volume) / adv20)* ((high* rank((high - close))) / (sum(high, 5) / 5))) - rank((vwap - delay(vwap, 5))))
```

---

### Alpha_048
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
(indneutralize(((correlation(delta(close, 1), delta(delay(close, 1), 1), 250)* delta(close, 1)) / close), IndClass.subindustry) / sum(((delta(close, 1) / delay(close, 1))^2), 250))
```

---

### Alpha_049
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为对应因子值或1，当满足条件时为1

**公式:**
```
(((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < (-1* 0.1)) ? 1 : ((-1* 1)* (close - delay(close, 1))))
```

---

### Alpha_050
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1* ts_max(rank(correlation(rank(volume), rank(vwap), 5)), 5))
```

---

### Alpha_051
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为对应因子值或1，当满足条件时为1

**公式:**
```
(((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < (-1* 0.05)) ? 1 : ((-1* 1)* (close - delay(close, 1))))
```

---

### Alpha_052
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((((-1* ts_min(low, 5)) + delay(ts_min(low, 5), 5))* rank(((sum(returns, 240) - sum(returns, 20)) / 220)))* ts_rank(volume, 5))
```

---

### Alpha_053
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1* delta((((close - low) - (high - close)) / (close - low)), 9))
```

---

### Alpha_054
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((-1* ((low - close)* (open^5))) / ((low - high)* (close^5)))
```

---

### Alpha_055
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(-1* correlation(rank(((close - ts_min(low, 12)) / (ts_max(high, 12) - ts_min(low, 12)))), rank(volume), 6))
```

---

### Alpha_056
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(0 - (1* (rank((sum(returns, 10) / sum(sum(returns, 2), 3)))* rank((returns* cap)))))
```

---

### Alpha_057
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(0 - (1* ((close - vwap) / decay_linear(rank(ts_argmax(close, 30)), 2))))
```

---

### Alpha_058
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
(-1* Ts_Rank(decay_linear(correlation(IndNeutralize(vwap, IndClass.sector), volume, 3.92795), 7.89291), 5.50322))
```

---

### Alpha_059
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
(-1* Ts_Rank(decay_linear(correlation(IndNeutralize(((vwap* 0.728317) + (vwap* (1 - 0.728317))), IndClass.industry), volume, 4.25197), 16.2289), 8.19648))
```

---

### Alpha_060
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(0 - (1* ((2* scale(rank(((((close - low) - (high - close)) / (high - low))* volume)))) - scale(rank(ts_argmax(close, 10))))))
```

---

### Alpha_061
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，当满足条件时为1，否则为-1

**公式:**
```
(rank((vwap - ts_min(vwap, 16.1219))) < rank(correlation(vwap, adv180, 17.9282)))
```

---

### Alpha_062
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，当满足条件时为-1，否则为1

**公式:**
```
((rank(correlation(vwap, sum(adv20, 22.4101), 9.91009)) < rank(((rank(open) + rank(open)) < (rank(((high + low) / 2)) + rank(high)))))*-1)
```

---

### Alpha_063
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
((rank(decay_linear(delta(IndNeutralize(close, IndClass.industry), 2.25164), 8.22237)) - rank(decay_linear(correlation(((vwap* 0.318108) + (open* (1 - 0.318108))), sum(adv180, 37.2467), 13.557), 12.2883))) * -1)
```

---

### Alpha_064
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，当满足条件时为-1，否则为1

**公式:**
```
((rank(correlation(sum(((open* 0.178404) + (low* (1 - 0.178404))), 12.7054), sum(adv120, 12.7054), 16.6208)) < rank(delta(((((high + low) / 2)* 0.178404) + (vwap* (1 - 0.178404))), 3.69741))) * -1)
```

---

### Alpha_065
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，当满足条件时为-1，否则为1

**公式:**
```
((rank(correlation(((open* 0.00817205) + (vwap* (1 - 0.00817205))), sum(adv60, 8.6911), 6.40374)) < rank((open - ts_min(open, 13.635)))) * -1)
```

---

### Alpha_066
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((rank(decay_linear(delta(vwap, 3.51013), 7.23052)) + Ts_Rank(decay_linear(((((low* 0.96633) + (low* (1 - 0.96633))) - vwap) / (open - ((high + low) / 2))), 11.4157), 6.72611)) * -1)
```

---

### Alpha_067
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
((rank((high - ts_min(high, 2.14593)))^rank(correlation(IndNeutralize(vwap, IndClass.sector), IndNeutralize(adv20, IndClass.subindustry), 6.02936))) * -1)
```

---

### Alpha_068
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，当满足条件时为-1，否则为1

**公式:**
```
((Ts_Rank(correlation(rank(high), rank(adv15), 8.91644), 13.9333) < rank(delta(((close* 0.518371) + (low* (1 - 0.518371))), 1.06157))) * -1)
```

---

### Alpha_069
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
((rank(ts_max(delta(IndNeutralize(vwap, IndClass.industry), 2.72412), 4.79344))^Ts_Rank(correlation(((close* 0.490655) + (vwap* (1 - 0.490655))), adv20, 4.92416), 9.0615)) * -1)
```

---

### Alpha_070
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
((rank(delta(vwap, 1.29456))^Ts_Rank(correlation(IndNeutralize(close, IndClass.industry), adv50, 17.8256), 17.9171)) * -1)
```

---

### Alpha_071
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
max(Ts_Rank(decay_linear(correlation(Ts_Rank(close, 3.43976), Ts_Rank(adv180, 12.0647), 18.0175), 4.20501), 15.6948), Ts_Rank(decay_linear((rank(((low + open) - (vwap + vwap)))^2), 16.4662), 4.4388))
```

---

### Alpha_072
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(rank(decay_linear(correlation(((high + low) / 2), adv40, 8.93345), 10.1519)) / rank(decay_linear(correlation(Ts_Rank(vwap, 3.72469), Ts_Rank(volume, 18.5188), 6.86671), 2.95011)))
```

---

### Alpha_073
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(max(rank(decay_linear(delta(vwap, 4.72775), 2.91864)), Ts_Rank(decay_linear(((delta(((open* 0.147155) + (low* (1 - 0.147155))), 2.03608) / ((open* 0.147155) + (low* (1 - 0.147155)))) * -1), 3.33829), 16.7411)) * -1)
```

---

### Alpha_074
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，当满足条件时为-1，否则为1

**公式:**
```
((rank(correlation(close, sum(adv30, 37.4843), 15.1365)) < rank(correlation(rank(((high* 0.0261661) + (vwap* (1 - 0.0261661)))), rank(volume), 11.4791))) * -1)
```

---

### Alpha_075
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，当满足条件时为1，否则为-1

**公式:**
```
(rank(correlation(vwap, volume, 4.24304)) < rank(correlation(rank(low), rank(adv50), 12.4413)))
```

---

### Alpha_076
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
(max(rank(decay_linear(delta(vwap, 1.24383), 11.8259)), Ts_Rank(decay_linear(Ts_Rank(correlation(IndNeutralize(low, IndClass.sector), adv81, 8.14941), 19.569), 17.1543), 19.383)) * -1)
```

---

### Alpha_077
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
min(rank(decay_linear(((((high + low) / 2) + high) - (vwap + high)), 20.0451)), rank(decay_linear(correlation(((high + low) / 2), adv40, 3.1614), 5.64125)))
```

---

### Alpha_078
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(rank(correlation(sum(((low* 0.352233) + (vwap* (1 - 0.352233))), 19.7428), sum(adv40, 19.7428), 6.83313))^rank(correlation(rank(vwap), rank(volume), 5.77492)))
```

---

### Alpha_079
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
(rank(delta(IndNeutralize(((close* 0.60733) + (open* (1 - 0.60733))), IndClass.sector), 1.23438)) < rank(correlation(Ts_Rank(vwap, 3.60973), Ts_Rank(adv150, 9.18637), 14.6644)))
```

---

### Alpha_080
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
((rank(Sign(delta(IndNeutralize(((open* 0.868128) + (high* (1 - 0.868128))), IndClass.industry), 4.04545)))^Ts_Rank(correlation(high, adv10, 5.11456), 5.53756)) * -1)
```

---

### Alpha_081
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
((rank(Log(product(rank((rank(correlation(vwap, sum(adv10, 49.6054), 8.47743))^4)), 14.9655))) < rank(correlation(rank(vwap), rank(volume), 5.07914))) * -1)
```

---

### Alpha_082
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
(min(rank(decay_linear(delta(open, 1.46063), 14.8717)), Ts_Rank(decay_linear(correlation(IndNeutralize(volume, IndClass.sector), ((open* 0.634196) + (open* (1 - 0.634196))), 17.4842), 6.92131), 13.4283)) * -1)
```

---

### Alpha_083
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((rank(delay(((high - low) / (sum(close, 5) / 5)), 2))* rank(rank(volume))) / (((high - low) / (sum(close, 5) / 5)) / (vwap - close)))
```

---

### Alpha_084
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
SignedPower(Ts_Rank((vwap - ts_max(vwap, 15.3217)), 20.7127), delta(close, 4.96796))
```

---

### Alpha_085
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(rank(correlation(((high* 0.876703) + (close* (1 - 0.876703))), adv30, 9.61331))^rank(correlation(Ts_Rank(((high + low) / 2), 3.70596), Ts_Rank(volume, 10.1595), 7.11408)))
```

---

### Alpha_086
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，当满足条件时为-1，否则为1

**公式:**
```
((Ts_Rank(correlation(close, sum(adv20, 14.7444), 6.00049), 20.4195) < rank(((open + close) - (vwap + open)))) * -1)
```

---

### Alpha_087
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
(max(rank(decay_linear(delta(((close* 0.369701) + (vwap* (1 - 0.369701))), 1.91233), 2.65461)), Ts_Rank(decay_linear(abs(correlation(IndNeutralize(adv81, IndClass.industry), close, 13.4132)), 4.89768), 14.4535)) * -1)
```

---

### Alpha_088
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
min(rank(decay_linear(((rank(open) + rank(low)) - (rank(high) + rank(close))), 8.06882)), Ts_Rank(decay_linear(correlation(Ts_Rank(close, 8.44728), Ts_Rank(adv60, 20.6966), 8.01266), 6.65053), 2.61957))
```

---

### Alpha_089
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
(Ts_Rank(decay_linear(correlation(((low* 0.967285) + (low* (1 - 0.967285))), adv10, 6.94279), 5.51607), 3.79744) - Ts_Rank(decay_linear(delta(IndNeutralize(vwap, IndClass.industry), 3.48158), 10.1466), 15.3012))
```

---

### Alpha_090
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
((rank((close - ts_max(close, 4.66719)))^Ts_Rank(correlation(IndNeutralize(adv40, IndClass.subindustry), low, 5.38375), 3.21856)) * -1)
```

---

### Alpha_091
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
((Ts_Rank(decay_linear(decay_linear(correlation(IndNeutralize(close, IndClass.industry), volume, 9.74928), 16.398), 3.83219), 4.8667) - rank(decay_linear(correlation(vwap, adv30, 4.01303), 2.6809))) * -1)
```

---

### Alpha_092
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
min(Ts_Rank(decay_linear(((((high + low) / 2) + close) < (low + open)), 14.7221), 18.8683), Ts_Rank(decay_linear(correlation(rank(low), rank(adv30), 7.58555), 6.94024), 6.80584))
```

---

### Alpha_093
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
(Ts_Rank(decay_linear(correlation(IndNeutralize(vwap, IndClass.industry), adv81, 17.4193), 19.848), 7.54455) / rank(decay_linear(delta(((close* 0.524434) + (vwap* (1 - 0.524434))), 2.77377), 16.2664)))
```

---

### Alpha_094
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((rank((vwap - ts_min(vwap, 11.5783)))^Ts_Rank(correlation(Ts_Rank(vwap, 19.6462), Ts_Rank(adv60, 4.02992), 18.0926), 2.70756)) * -1)
```

---

### Alpha_095
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index为成分股代码，values为1或-1，当满足条件时为1，否则为-1

**公式:**
```
(rank((open - ts_min(open, 12.4105))) < Ts_Rank((rank(correlation(sum(((high + low) / 2), 19.1351), sum(adv40, 19.1351), 12.8742))^5), 11.7584))
```

---

### Alpha_096
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(max(Ts_Rank(decay_linear(correlation(rank(vwap), rank(volume), 3.83878), 4.16783), 8.38151), Ts_Rank(decay_linear(Ts_ArgMax(correlation(Ts_Rank(close, 7.45404), Ts_Rank(adv60, 4.13242), 3.65459), 12.6556), 14.0365), 13.4143)) * -1)
```

---

### Alpha_097
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
((rank(decay_linear(delta(IndNeutralize(((low* 0.721001) + (vwap* (1 - 0.721001))), IndClass.industry), 3.3705), 20.4523)) - Ts_Rank(decay_linear(Ts_Rank(correlation(Ts_Rank(low, 7.87871), Ts_Rank(adv60, 17.255), 4.97547), 18.5925), 15.7152), 6.71659)) * -1)
```

---

### Alpha_098
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
(rank(decay_linear(correlation(vwap, sum(adv5, 26.4719), 4.58418), 7.18088)) - rank(decay_linear(Ts_Rank(Ts_ArgMin(correlation(rank(open), rank(adv15), 20.8187), 8.62571), 6.95668), 8.07206)))
```

---

### Alpha_099
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series: index为成分股代码，values为1或-1，当满足条件时为-1，否则为1

**公式:**
```
((rank(correlation(sum(((high + low) / 2), 19.8975), sum(adv60, 19.8975), 8.8136)) < rank(correlation(low, volume, 6.28259))) * -1)
```

---

### Alpha_100
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- 未实现（包含行业中性化）

**公式:**
```
(0 - (1* (((1.5* scale(indneutralize(indneutralize(rank(((((close - low) - (high - close)) / (high - low))* volume)), IndClass.subindustry), IndClass.subindustry))) - scale(indneutralize((correlation(close, rank(adv20), 5) - rank(ts_argmin(close, 30))), IndClass.subindustry))) * (volume / adv20))))
```

---

### Alpha_101
**Inputs:**
- enddate: 必选参数，计算哪一天的因子
- index: 默认参数，股票指数，默认为所有股票'all'

**Outputs:**
- Series：index 为成分股代码，values为对应的因子值

**公式:**
```
((close - open) / ((high - low) + .001))
```

---

## 📊 因子分类统计

### 实现状态
- **已实现**: 77个因子 (Alpha_001 - Alpha_047, Alpha_049 - Alpha_057, Alpha_060 - Alpha_062, Alpha_064 - Alpha_066, Alpha_068, Alpha_071 - Alpha_075, Alpha_077 - Alpha_078, Alpha_083 - Alpha_086, Alpha_088, Alpha_092, Alpha_094, Alpha_096, Alpha_098, Alpha_099, Alpha_101)
- **未实现**: 24个因子 (Alpha_048, Alpha_058, Alpha_059, Alpha_063, Alpha_067, Alpha_069, Alpha_070, Alpha_076, Alpha_079, Alpha_080, Alpha_081, Alpha_082, Alpha_087, Alpha_089, Alpha_090, Alpha_091, Alpha_093, Alpha_097, Alpha_100)

### 数据需求
- **价格数据**: close, open, high, low, vwap
- **成交量**: volume
- **收益率**: returns
- **平均成交量**: adv20, adv40, adv60, adv81, adv120, adv150, adv180, adv5, adv10, adv15, adv30, adv50, adv81, adv180
- **市值**: cap

### 常用函数
- **统计函数**: stddev, correlation, covariance, rank, ts_rank, ts_argmax, ts_argmin
- **时间序列**: delay, delta, ts_min, ts_max, sum, decay_linear
- **逻辑函数**: sign, SignedPower, scale, abs
- **行业中性化**: IndNeutralize (未实现)

---

## 🔧 使用建议

### 1. 选择因子
- **趋势类**: Alpha_001, Alpha_009, Alpha_010, Alpha_019, Alpha_024
- **量价关系**: Alpha_002, Alpha_003, Alpha_006, Alpha_012, Alpha_014
- **波动率**: Alpha_001, Alpha_018, Alpha_022, Alpha_040
- **动量类**: Alpha_008, Alpha_019, Alpha_025, Alpha_039

### 2. 数据准备
- 需要至少20-250天的历史数据
- 注意处理缺失值和异常值
- 考虑行业中性化（部分因子需要）

### 3. 实现步骤
1. 提取所需数据字段
2. 实现基础函数（rank, ts_rank, correlation等）
3. 逐个实现因子公式
4. 验证计算结果
5. 测试因子有效性

---

## 📝 备注

- 所有因子均来源于聚宽Alpha101因子库
- 已删除聚宽特定的API调用和装饰器
- 保留了原始的Inputs、Outputs和公式描述
- 未实现的因子主要涉及行业中性化功能
- 建议根据实际数据情况选择性实现

---

**文档版本**: v1.0
**更新日期**: 2026-01-03
**来源**: 聚宽Alpha101因子库
