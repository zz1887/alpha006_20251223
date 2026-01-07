# 量化因子库 v2.0 - 快速参考卡

## 🚀 一键命令

```bash
# 1. 验证重构
python scripts/verify_refactoring.py

# 2. 计算策略3 (20251229)
python scripts/run_strategy3.py --date 20251229 --version standard

# 3. 生成因子
python scripts/run_factor_generation.py --date 20251229 --version standard
```

---

## 📊 因子速查

| 因子 | 类型 | 公式 | 版本 |
|------|------|------|------|
| alpha_pluse | 量能 | 1 if count_20d∈[2,4] else 0 | standard/conservative/aggressive |
| alpha_peg | 估值 | pe_ttm / dt_netprofit_yoy | standard/conservative/aggressive |
| alpha_038 | 价格 | (-1×rank(close_rank))×rank(close/open) | standard/conservative/aggressive |
| alpha_120cq | 位置 | (rank-1)/(N-1) | standard/conservative/aggressive |
| cr_qfq | 动量 | CR指标(N=20) | standard/conservative/aggressive |

---

## 🎯 策略3公式

```
综合得分 = 0.20×(1-alpha_pluse) + 0.25×(-alpha_peg_zscore) + 0.15×alpha_120cq + 0.20×(cr_qfq/max) + 0.20×(-alpha_038/min)
```

**权重分配**:
- 量能: 20% (反向)
- 估值: 25% (负向)
- 位置: 15% (正向)
- 动量: 20% (标准化)
- 强度: 20% (负向)

---

## 📁 关键路径

```
配置: core/config/settings.py
参数: core/config/params.py
工具: core/utils/{db_connection,data_loader,data_processor}.py
因子: factors/{valuation,momentum,price,volume}/
脚本: scripts/run_strategy3.py
文档: docs/factor_dictionary.md
输出: results/output/
```

---

## 🔄 从旧代码迁移

### 旧代码位置
```
code/calculate_strategy3_20251229.py → scripts/run_strategy3.py
code/calculate_alpha_120cq.py → factors/price/alpha_120cq.py
code/calculate_factors_*.py → 已整合到因子模块
```

### 接口变化
```python
# 旧版
from core.utils.db_connection import db
from core.constants.config import TABLE_DAILY_KLINE

# 新版
from core.utils.db_connection import db
from core.config.settings import TABLE_NAMES
# 或
from core.config.params import get_factor_param
```

---

## ✅ 验证清单

- [ ] 配置验证通过
- [ ] 数据库连接正常
- [ ] 因子计算成功
- [ ] 策略3输出正确
- [ ] 结果与旧版一致

---

## 📞 问题排查

### 模块导入失败
```bash
cd /home/zcy/alpha006_20251223
python -c "from core.config.settings import validate_config; print(validate_config())"
```

### 数据库连接失败
```bash
python -c "from core.utils.db_connection import db; print(db.check_connection())"
```

### 因子计算失败
```bash
python scripts/verify_refactoring.py
```

---

## 📝 输出文件命名

```
strategy3_comprehensive_scores_YYYYMMDD_HHMMSS.xlsx  # 完整结果
strategy3_top100_YYYYMMDD_HHMMSS.xlsx                # 前100名
strategy3_summary_YYYYMMDD_HHMMSS.txt                # 统计摘要
```

---

## 🔧 参数版本

| 版本 | 特点 | 适用场景 |
|------|------|----------|
| standard | 标准参数 | 默认推荐 |
| conservative | 严格筛选 | 低风险偏好 |
| aggressive | 宽松筛选 | 高风险偏好 |

---

## 📊 统计示例

```
策略3计算完成 - 20251229
总股票数: 3736
有效数据: 3736
缺失数据: 0

综合得分统计:
  均值: 0.1354
  标准差: 0.2745
  最小值: -3.4239
  最大值: 4.5361

前10名:
301602.SZ 医药生物 得分=4.5361
300814.SZ 电子     得分=3.9981
...
```

---

**版本**: v2.0
**更新**: 2025-12-30
**状态**: ✅ 完成标准化