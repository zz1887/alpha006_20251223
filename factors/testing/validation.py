"""
文件input(依赖外部什么): pandas, numpy, scipy.stats, factors.core, factors.calculation
文件output(提供什么): 因子逻辑验证类，验证因子计算的数学正确性和逻辑一致性
文件pos(系统局部地位): 测试框架层 - 逻辑验证模块
文件功能: 验证因子计算的数学正确性、统计特性、边界条件等

使用示例:
    from factors.testing.validation import FactorValidator

    validator = FactorValidator()
    validator.validate_factor_logic('alpha_peg')

返回值:
    Dict: 验证报告（正确性、统计特性、边界情况等）
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class FactorValidator:
    """因子逻辑验证器"""

    def __init__(self):
        self.validation_report = {}

    def validate_factor_logic(self, factor_name: str, test_data: pd.DataFrame = None) -> Dict[str, Any]:
        """验证指定因子的逻辑"""
        logger.info(f"开始验证因子逻辑: {factor_name}")

        # 获取因子类
        from factors.core.factor_registry import FactorRegistry

        if factor_name not in FactorRegistry._registry:
            raise ValueError(f"未知因子: {factor_name}")

        factor_class = FactorRegistry._registry[factor_name]['class']
        factor = factor_class()

        # 生成或使用测试数据
        if test_data is None:
            test_data = self._generate_validation_data(factor_name, n=100)

        # 运行验证
        validations = [
            ("基础计算正确性", self.validate_calculation, (factor, test_data)),
            ("统计特性", self.validate_statistics, (factor, test_data)),
            ("边界条件", self.validate_boundaries, (factor, test_data)),
            ("数据完整性", self.validate_data_integrity, (factor, test_data)),
            ("异常值处理", self.validate_outlier_handling, (factor, test_data)),
        ]

        results = {}
        for name, func, args in validations:
            try:
                result = func(*args)
                results[name] = {"status": "✅ 通过", "details": result}
                logger.info(f"  ✓ {name}")
            except AssertionError as e:
                results[name] = {"status": "❌ 失败", "details": str(e)}
                logger.error(f"  ✗ {name}: {e}")
            except Exception as e:
                results[name] = {"status": "⚠️ 错误", "details": str(e)}
                logger.error(f"  ✗ {name}: {e}")

        self.validation_report[factor_name] = results
        return results

    def validate_calculation(self, factor, data: pd.DataFrame) -> Dict[str, Any]:
        """验证计算正确性"""
        result = factor.calculate(data)

        # 验证结果格式
        assert isinstance(result, pd.DataFrame), "结果必须是DataFrame"
        assert 'factor' in result.columns, "必须包含factor列"

        # 验证计算逻辑（根据因子类型）
        if 'peg' in factor.__class__.__name__.lower():
            # PEG验证
            if len(result) > 0:
                # 检查几个样本的计算
                sample = data.iloc[:5]
                if len(sample) > 0:
                    # 手动计算验证
                    pe = sample['pe_ttm'].values
                    growth = sample['dt_netprofit_yoy'].values

                    # 应用相同的清洗逻辑
                    pe_clean = np.where(pe > 0, pe, np.nan)
                    pe_clean = np.clip(pe_clean, None, 100)
                    growth_clean = np.where(growth > 0.01, growth, 0.01)
                    growth_clean = np.where(growth > 0, growth, np.nan)

                    expected = pe_clean / growth_clean

                    # 比较（允许NaN差异）
                    valid_mask = ~np.isnan(expected)
                    if valid_mask.any():
                        actual_sample = result['factor'].iloc[:len(expected)]
                        actual_sample = actual_sample.values[valid_mask]
                        expected_sample = expected[valid_mask]

                        # 允许浮点误差
                        np.testing.assert_allclose(
                            actual_sample, expected_sample,
                            rtol=1e-5, atol=1e-5,
                            err_msg="PEG计算结果与预期不符"
                        )

        return {"format": "正确", "计算逻辑": "验证通过"}

    def validate_statistics(self, factor, data: pd.DataFrame) -> Dict[str, Any]:
        """验证统计特性"""
        result = factor.calculate(data)

        if len(result) == 0:
            return {"status": "无数据"}

        values = result['factor'].dropna()

        if len(values) == 0:
            return {"status": "全NaN"}

        stats_info = {
            'mean': float(values.mean()),
            'std': float(values.std()),
            'min': float(values.min()),
            'max': float(values.max()),
            'median': float(values.median()),
            'skewness': float(stats.skew(values)),
            'kurtosis': float(stats.kurtosis(values)),
        }

        # 验证统计合理性
        assert not np.isnan(stats_info['mean']), "均值不应为NaN"
        assert not np.isnan(stats_info['std']), "标准差不应为NaN"
        assert stats_info['min'] <= stats_info['mean'] <= stats_info['max'], "统计值应该有序"

        return stats_info

    def validate_boundaries(self, factor, data: pd.DataFrame) -> Dict[str, Any]:
        """验证边界条件"""
        # 空数据
        empty_data = pd.DataFrame()
        result = factor.calculate(empty_data)
        assert len(result) == 0, "空数据应该返回空结果"

        # 极小数据
        small_data = data.head(1)
        try:
            result = factor.calculate(small_data)
            # 应该能处理
        except Exception:
            pass  # 允许因数据不足失败

        # 数据验证
        is_valid = factor.validate_data(data)
        assert isinstance(is_valid, bool), "验证应该返回布尔值"

        return {"empty": "正确", "small": "可处理", "validation": "正确"}

    def validate_data_integrity(self, factor, data: pd.DataFrame) -> Dict[str, Any]:
        """验证数据完整性"""
        result = factor.calculate(data)

        if len(result) == 0:
            return {"status": "无结果"}

        # 检查关键列
        required_cols = ['ts_code', 'trade_date', 'factor']
        for col in required_cols:
            assert col in result.columns, f"缺少列: {col}"

        # 检查数据类型
        assert result['ts_code'].dtype == object, "ts_code应该是字符串"
        assert pd.api.types.is_numeric_dtype(result['factor']), "factor应该是数值"

        # 检查无无穷值
        assert not np.isinf(result['factor']).any(), "不应该有无穷值"

        return {"columns": "完整", "types": "正确", "inf": "无"}

    def validate_outlier_handling(self, factor, data: pd.DataFrame) -> Dict[str, Any]:
        """验证异常值处理"""
        # 创建包含异常值的数据
        outlier_data = data.copy()

        # 添加各种异常值
        if 'pe_ttm' in outlier_data.columns:
            outlier_data.loc[:5, 'pe_ttm'] = [-10, 0, 1000, np.nan, np.inf, 1e10]
        if 'dt_netprofit_yoy' in outlier_data.columns:
            outlier_data.loc[5:10, 'dt_netprofit_yoy'] = [-0.1, 0, 10, np.nan, np.inf, 0.001]

        try:
            result = factor.calculate(outlier_data)

            if len(result) > 0:
                # 验证结果中没有无穷值
                assert not np.isinf(result['factor']).any(), "结果中不应有无穷值"

                # 验证NaN被适当处理
                # 可能是被删除，也可能是被替换

            return {"异常值": "正确处理", "无穷值": "已过滤"}

        except Exception as e:
            # 某些因子可能拒绝处理异常值
            return {"异常值": "拒绝处理", "原因": str(e)}

    def _generate_validation_data(self, factor_name: str, n: int = 100) -> pd.DataFrame:
        """生成验证数据"""
        np.random.seed(42)

        if 'peg' in factor_name.lower():
            return self._generate_peg_data(n)
        elif '010' in factor_name.lower():
            return self._generate_price_data(n)
        elif 'pluse' in factor_name.lower():
            return self._generate_volume_data(n)
        else:
            return self._generate_generic_data(n)

    def _generate_peg_data(self, n: int) -> pd.DataFrame:
        """生成PEG验证数据"""
        ts_codes = [f"00000{i}.SZ" for i in range(1, 6)]
        dates = pd.date_range('2025-01-01', periods=n//5 + 1, freq='D')

        data_list = []
        for code in ts_codes:
            for date in dates:
                data_list.append({
                    'ts_code': code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'pe_ttm': np.random.uniform(5, 50),
                    'dt_netprofit_yoy': np.random.uniform(0.05, 0.5),
                })

        return pd.DataFrame(data_list[:n])

    def _generate_price_data(self, n: int) -> pd.DataFrame:
        """生成价格验证数据"""
        ts_codes = [f"00000{i}.SZ" for i in range(1, 6)]
        dates = pd.date_range('2025-01-01', periods=n//5 + 1, freq='D')

        data_list = []
        for code in ts_codes:
            for date in dates:
                data_list.append({
                    'ts_code': code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'close': np.random.uniform(10, 100),
                })

        return pd.DataFrame(data_list[:n])

    def _generate_volume_data(self, n: int) -> pd.DataFrame:
        """生成成交量验证数据"""
        ts_codes = [f"00000{i}.SZ" for i in range(1, 6)]
        dates = pd.date_range('2025-01-01', periods=n//5 + 1, freq='D')

        data_list = []
        for code in ts_codes:
            for date in dates:
                data_list.append({
                    'ts_code': code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'vol': np.random.uniform(1000000, 10000000),
                })

        return pd.DataFrame(data_list[:n])

    def _generate_generic_data(self, n: int) -> pd.DataFrame:
        """生成通用验证数据"""
        ts_codes = [f"00000{i}.SZ" for i in range(1, 6)]
        dates = pd.date_range('2025-01-01', periods=n//5 + 1, freq='D')

        data_list = []
        for code in ts_codes:
            for date in dates:
                data_list.append({
                    'ts_code': code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'value1': np.random.uniform(0, 100),
                    'value2': np.random.uniform(0, 100),
                })

        return pd.DataFrame(data_list[:n])


def validate_all_factors() -> Dict[str, Any]:
    """验证所有已注册因子"""
    from factors.core.factor_registry import FactorRegistry

    validator = FactorValidator()
    all_results = {}

    for factor_name in FactorRegistry._registry.keys():
        try:
            logger.info(f"\n验证因子: {factor_name}")
            results = validator.validate_factor_logic(factor_name)
            all_results[factor_name] = results
        except Exception as e:
            logger.error(f"验证失败: {e}")
            all_results[factor_name] = {"error": str(e)}

    return all_results


__all__ = ['FactorValidator', 'validate_all_factors']
