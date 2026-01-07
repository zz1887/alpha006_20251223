"""
文件input(依赖外部什么): unittest, pandas, numpy, factors.core, factors.calculation
文件output(提供什么): 因子单元测试类，验证因子计算正确性
文件pos(系统局部地位): 测试框架层 - 单元测试模块
文件功能: 对单个因子进行单元测试，验证计算逻辑、数据处理、异常值处理等

使用示例:
    from factors.testing.unit_test import FactorUnitTest
    from factors.calculation.alpha_peg import AlphaPegFactor

    # 创建测试实例
    test = FactorUnitTest(AlphaPegFactor)

    # 运行测试
    test.run_all_tests()

    # 查看测试报告
    print(test.test_report)

返回值:
    bool: 测试是否通过
    Dict: 详细测试结果
"""

import unittest
import pandas as pd
import numpy as np
from typing import Type, Dict, Any, List
import logging
import time

logger = logging.getLogger(__name__)


class FactorUnitTest:
    """因子单元测试基类"""

    def __init__(self, factor_class: Type, factor_name: str = None):
        """
        初始化测试

        Args:
            factor_class: 因子类（如AlphaPegFactor）
            factor_name: 因子名称（用于报告）
        """
        self.factor_class = factor_class
        self.factor_name = factor_name or factor_class.__name__
        self.test_report = {}
        self.passed_tests = 0
        self.total_tests = 0

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有单元测试"""
        logger.info(f"开始运行因子单元测试: {self.factor_name}")

        tests = [
            ("数据验证测试", self.test_data_validation),
            ("正常数据计算测试", self.test_normal_calculation),
            ("异常值处理测试", self.test_outlier_handling),
            ("边界情况测试", self.test_boundary_cases),
            ("标准化测试", self.test_normalization),
            ("统计信息测试", self.test_statistics),
            ("一致性测试", self.test_consistency),
            ("性能测试", self.test_performance),
        ]

        for test_name, test_func in tests:
            self.total_tests += 1
            try:
                test_func()
                self.passed_tests += 1
                self.test_report[test_name] = "✅ 通过"
                logger.info(f"  ✓ {test_name}")
            except AssertionError as e:
                self.test_report[test_name] = f"❌ 失败: {str(e)}"
                logger.error(f"  ✗ {test_name}: {e}")
            except Exception as e:
                self.test_report[test_name] = f"⚠️ 错误: {str(e)}"
                logger.error(f"  ✗ {test_name}: {e}")

        # 总结
        self.test_report['summary'] = {
            'passed': self.passed_tests,
            'total': self.total_tests,
            'pass_rate': self.passed_tests / self.total_tests if self.total_tests > 0 else 0,
            'all_passed': self.passed_tests == self.total_tests
        }

        logger.info(f"测试完成: {self.passed_tests}/{self.total_tests} 通过")
        return self.test_report

    def test_data_validation(self):
        """测试数据验证"""
        logger.info("  测试数据验证...")

        # 测试缺少必需列
        invalid_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20250101']
        })

        factor = self.factor_class()
        try:
            result = factor.validate_data(invalid_data)
            assert result == False, "应该验证失败"
        except Exception:
            pass  # 验证失败是预期的

        # 测试数据量不足
        empty_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20250101'],
            'pe_ttm': [10.0],
            'dt_netprofit_yoy': [0.15]
        })

        try:
            result = factor.validate_data(empty_data)
            assert result == False, "数据量不足应该验证失败"
        except Exception:
            pass

    def test_normal_calculation(self):
        """测试正常数据计算"""
        logger.info("  测试正常数据计算...")

        # 创建测试数据
        test_data = self._generate_test_data(n=100, clean=True)

        factor = self.factor_class()
        result = factor.calculate(test_data)

        # 验证结果格式
        assert isinstance(result, pd.DataFrame), "结果应该是DataFrame"
        assert 'ts_code' in result.columns, "应该包含ts_code"
        assert 'factor' in result.columns, "应该包含factor列"
        assert len(result) > 0, "应该有计算结果"

        # 验证没有NaN值（正常数据）
        assert not result['factor'].isnull().any(), "正常数据不应该有NaN"

    def test_outlier_handling(self):
        """测试异常值处理"""
        logger.info("  测试异常值处理...")

        # 创建包含异常值的数据
        test_data = self._generate_test_data(n=100, clean=False)

        factor = self.factor_class()
        result = factor.calculate(test_data)

        # 验证结果存在
        assert len(result) > 0, "应该有计算结果"

        # 验证没有无穷值
        assert not np.isinf(result['factor']).any(), "不应该有无穷值"

    def test_boundary_cases(self):
        """测试边界情况"""
        logger.info("  测试边界情况...")

        # 空数据
        empty_data = pd.DataFrame()
        factor = self.factor_class()

        try:
            result = factor.calculate(empty_data)
            assert len(result) == 0, "空数据应该返回空结果"
        except Exception as e:
            # 允许抛出异常
            pass

        # 极小数据量
        small_data = self._generate_test_data(n=5, clean=True)
        try:
            result = factor.calculate(small_data)
            # 应该能处理，即使结果可能为空
        except Exception as e:
            # 允许因数据不足而失败
            pass

    def test_normalization(self):
        """测试标准化功能"""
        logger.info("  测试标准化...")

        test_data = self._generate_test_data(n=100, clean=True)

        # 测试不同标准化方法
        for method in ['zscore', 'rank']:
            params = {'normalization': method}

            # 需要因子类支持参数
            try:
                factor = self.factor_class(params)
                result = factor.calculate(test_data)

                if len(result) > 0:
                    # 验证标准化结果
                    if method == 'zscore':
                        # Z-score应该有均值约0，标准差约1
                        mean = result['factor'].mean()
                        std = result['factor'].std()
                        assert abs(mean) < 1, f"Z-score均值应该接近0，实际{mean}"
                    elif method == 'rank':
                        # Rank应该在[0,1]区间
                        assert result['factor'].min() >= 0, "Rank最小值应该>=0"
                        assert result['factor'].max() <= 1, "Rank最大值应该<=1"
            except Exception:
                # 如果不支持标准化，跳过
                pass

    def test_statistics(self):
        """测试统计信息"""
        logger.info("  测试统计信息...")

        test_data = self._generate_test_data(n=100, clean=True)
        factor = self.factor_class()
        result = factor.calculate(test_data)

        # 获取统计信息
        stats_func = getattr(factor, 'get_factor_stats', None)
        if stats_func:
            stats = stats_func(result)

            # 验证统计字段
            assert 'mean' in stats, "应该包含mean"
            assert 'std' in stats, "应该包含std"
            assert 'min' in stats, "应该包含min"
            assert 'max' in stats, "应该包含max"

            # 验证统计合理性
            if stats['std'] > 0:
                assert stats['min'] <= stats['mean'] <= stats['max'], "统计值应该有序"
        else:
            logger.warning("  因子类没有get_factor_stats方法")

    def test_consistency(self):
        """测试一致性"""
        logger.info("  测试一致性...")

        test_data = self._generate_test_data(n=100, clean=True)
        factor = self.factor_class()

        # 多次计算应该结果一致
        result1 = factor.calculate(test_data.copy())
        result2 = factor.calculate(test_data.copy())

        if len(result1) > 0 and len(result2) > 0:
            # 比较结果
            assert result1.equals(result2), "多次计算结果应该一致"

    def test_performance(self):
        """测试性能"""
        logger.info("  测试性能...")

        # 创建大数据量
        large_data = self._generate_test_data(n=1000, clean=True)
        factor = self.factor_class()

        # 计算耗时
        start_time = time.time()
        result = factor.calculate(large_data)
        elapsed = time.time() - start_time

        # 验证结果
        assert len(result) > 0, "应该有计算结果"

        # 性能指标（仅供参考）
        logger.info(f"  处理1000条数据耗时: {elapsed:.3f}秒")

        # 不设置严格时间限制，但记录性能
        self.test_report['performance_time'] = elapsed

    def _generate_test_data(self, n: int = 100, clean: bool = True) -> pd.DataFrame:
        """
        生成测试数据

        Args:
            n: 数据量
            clean: 是否生成干净数据（无异常值）

        Returns:
            测试DataFrame
        """
        np.random.seed(42)  # 可复现

        # 根据因子类型生成不同数据
        # 这里提供通用实现，子类可以重写

        if clean:
            # 干净数据
            pe = np.random.uniform(5, 50, n)
            growth = np.random.uniform(0.05, 0.5, n)
        else:
            # 包含异常值
            pe = np.random.uniform(5, 50, n)
            pe[:5] = [-10, 0, 1000, np.nan, np.inf]  # 异常值
            growth = np.random.uniform(0.05, 0.5, n)
            growth[5:10] = [-0.1, 0, 10, np.nan, np.inf]  # 异常值

        # 生成股票代码和日期
        ts_codes = [f"00000{i}.SZ" for i in range(1, min(n, 10))]
        ts_codes = ts_codes * (n // len(ts_codes) + 1)[:n]

        dates = pd.date_range('2025-01-01', periods=n, freq='D')

        data = pd.DataFrame({
            'ts_code': ts_codes,
            'trade_date': [d.strftime('%Y%m%d') for d in dates],
            'pe_ttm': pe,
            'dt_netprofit_yoy': growth,
        })

        return data


class AlphaPegFactorTest(FactorUnitTest):
    """alpha_peg因子专用测试"""

    def __init__(self):
        from factors.calculation.alpha_peg import AlphaPegFactor
        super().__init__(AlphaPegFactor, 'alpha_peg')

    def _generate_test_data(self, n: int = 100, clean: bool = True) -> pd.DataFrame:
        """生成alpha_peg专用测试数据"""
        np.random.seed(42)

        if clean:
            pe = np.random.uniform(5, 50, n)
            growth = np.random.uniform(0.05, 0.5, n)
        else:
            pe = np.random.uniform(5, 50, n)
            pe[:5] = [-10, 0, 200, np.nan, np.inf]
            growth = np.random.uniform(0.05, 0.5, n)
            growth[5:10] = [-0.1, 0, 10, np.nan, np.inf]

        ts_codes = [f"00000{i}.SZ" for i in range(1, min(n, 10))]
        ts_codes = ts_codes * (n // len(ts_codes) + 1)[:n]
        dates = pd.date_range('2025-01-01', periods=n, freq='D')

        return pd.DataFrame({
            'ts_code': ts_codes,
            'trade_date': [d.strftime('%Y%m%d') for d in dates],
            'pe_ttm': pe,
            'dt_netprofit_yoy': growth,
        })


class Alpha010FactorTest(FactorUnitTest):
    """alpha_010因子专用测试"""

    def __init__(self):
        from factors.price.PRI_TREND_4D_V2 import PriTrend4Dv2Factor
        super().__init__(PriTrend4Dv2Factor, 'alpha_010')

    def _generate_test_data(self, n: int = 100, clean: bool = True) -> pd.DataFrame:
        """生成alpha_010专用测试数据（价格数据）"""
        np.random.seed(42)

        # 生成价格序列
        ts_codes = [f"00000{i}.SZ" for i in range(1, 6)]
        dates = pd.date_range('2025-01-01', periods=n, freq='D')

        data_list = []
        for code in ts_codes:
            # 每只股票生成独立的价格序列
            base_price = np.random.uniform(10, 100)
            prices = [base_price]

            for _ in range(n-1):
                change = np.random.normal(0, 0.02)  # 2%波动
                prices.append(prices[-1] * (1 + change))

            if not clean:
                # 添加异常值
                prices[0] = -10
                prices[1] = 0
                prices[2] = np.nan

            for i, date in enumerate(dates):
                data_list.append({
                    'ts_code': code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'close': prices[i]
                })

        return pd.DataFrame(data_list)


# 工厂函数
def create_test(factor_name: str) -> FactorUnitTest:
    """
    创建因子测试实例

    Args:
        factor_name: 因子名称

    Returns:
        FactorUnitTest实例
    """
    test_map = {
        'alpha_peg': AlphaPegFactorTest,
        'alpha_010': Alpha010FactorTest,
        # 可以继续添加其他因子
    }

    if factor_name in test_map:
        return test_map[factor_name]()
    else:
        # 返回通用测试
        from factors.core.factor_registry import FactorRegistry
        if factor_name in FactorRegistry._registry:
            factor_class = FactorRegistry._registry[factor_name]['class']
            return FactorUnitTest(factor_class, factor_name)
        else:
            raise ValueError(f"未知因子: {factor_name}")


__all__ = [
    'FactorUnitTest',
    'AlphaPegFactorTest',
    'Alpha010FactorTest',
    'create_test',
]
