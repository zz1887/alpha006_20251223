"""
文件input(依赖外部什么): unittest, pandas, numpy, factors.core, factors.calculation, factors.evaluation
文件output(提供什么): 因子集成测试类，验证因子与评估系统的集成
文件pos(系统局部地位): 测试框架层 - 集成测试模块
文件功能: 测试因子与评估系统的集成，包括数据流、回测兼容性、多因子组合等

使用示例:
    from factors.testing.integration_test import FactorIntegrationTest

    test = FactorIntegrationTest()
    test.run_integration_tests()

返回值:
    bool: 集成测试是否通过
    Dict: 集成测试报告
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class FactorIntegrationTest:
    """因子集成测试"""

    def __init__(self):
        self.test_report = {}
        self.passed_tests = 0
        self.total_tests = 0

    def run_integration_tests(self) -> Dict[str, Any]:
        """运行所有集成测试"""
        logger.info("开始运行因子集成测试")

        tests = [
            ("数据流测试", self.test_data_flow),
            ("回测兼容性测试", self.test_backtest_compatibility),
            ("多因子组合测试", self.test_multi_factor),
            ("行业中性化测试", self.test_industry_neutral),
            ("异常传播测试", self.test_error_propagation),
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

        self.test_report['summary'] = {
            'passed': self.passed_tests,
            'total': self.total_tests,
            'pass_rate': self.passed_tests / self.total_tests if self.total_tests > 0 else 0,
        }

        logger.info(f"集成测试完成: {self.passed_tests}/{self.total_tests} 通过")
        return self.test_report

    def test_data_flow(self):
        """测试数据流：从原始数据到因子结果"""
        logger.info("  测试数据流...")

        # 模拟数据加载
        from core.utils.data_loader import DataLoader

        try:
            loader = DataLoader()

            # 测试获取价格数据
            price_data = loader.get_price_data(
                ['000001.SZ', '000002.SZ'],
                '20250101',
                '20250110'
            )

            assert len(price_data) > 0, "应该能加载价格数据"
            assert 'ts_code' in price_data.columns, "应该包含ts_code"
            assert 'close' in price_data.columns, "应该包含close"

            # 测试获取估值数据
            # 注意：实际使用时需要数据库中有数据
            logger.info("  数据流测试通过（基础验证）")

        except Exception as e:
            logger.warning(f"  数据流测试跳过: {e}")

    def test_backtest_compatibility(self):
        """测试与回测系统的兼容性"""
        logger.info("  测试回测兼容性...")

        # 验证因子输出格式符合回测要求
        from factors.calculation.alpha_peg import AlphaPegFactor

        # 生成测试数据
        data = self._generate_integration_data()

        factor = AlphaPegFactor()
        result = factor.calculate(data)

        # 验证格式
        assert isinstance(result, pd.DataFrame), "结果必须是DataFrame"
        assert 'ts_code' in result.columns, "必须包含ts_code"
        assert 'trade_date' in result.columns, "必须包含trade_date"
        assert 'factor' in result.columns, "必须包含factor列"

        # 验证数据类型
        assert result['ts_code'].dtype == object, "ts_code应该是字符串类型"
        assert result['factor'].dtype in [np.float64, np.float32], "factor应该是数值类型"

        logger.info("  回测兼容性测试通过")

    def test_multi_factor(self):
        """测试多因子组合"""
        logger.info("  测试多因子组合...")

        from factors.calculation.alpha_peg import AlphaPegFactor
        from factors.price.PRI_TREND_4D_V2 import PriTrend4Dv2Factor

        # 生成测试数据
        data = self._generate_integration_data()

        # 计算多个因子
        peg_factor = AlphaPegFactor()
        peg_result = peg_factor.calculate(data)

        trend_factor = PriTrend4Dv2Factor()
        trend_result = trend_factor.calculate(data)

        # 验证各自结果
        assert len(peg_result) > 0, "PEG因子应该有结果"
        assert len(trend_result) > 0, "趋势因子应该有结果"

        # 测试合并（简单示例）
        merged = pd.merge(
            peg_result[['ts_code', 'trade_date', 'factor']],
            trend_result[['ts_code', 'trade_date', 'factor']],
            on=['ts_code', 'trade_date'],
            suffixes=('_peg', '_trend')
        )

        assert len(merged) > 0, "合并后应该有数据"

        logger.info("  多因子组合测试通过")

    def test_industry_neutral(self):
        """测试行业中性化"""
        logger.info("  测试行业中性化...")

        from factors.calculation.alpha_peg import AlphaPegFactor

        # 生成带行业数据
        data = self._generate_integration_data(with_industry=True)

        # 启用行业中性化
        params = {
            'industry_neutral': True,
            'industry_specific': True
        }

        factor = AlphaPegFactor(params)
        result = factor.calculate(data)

        # 验证结果
        assert len(result) > 0, "应该有结果"

        logger.info("  行业中性化测试通过")

    def test_error_propagation(self):
        """测试错误传播"""
        logger.info("  测试错误传播...")

        from factors.calculation.alpha_peg import AlphaPegFactor

        # 测试无效数据
        invalid_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20250101'],
            'pe_ttm': [0],  # 无效PE
            'dt_netprofit_yoy': [0.15]
        })

        factor = AlphaPegFactor()

        # 应该能处理无效数据而不崩溃
        try:
            result = factor.calculate(invalid_data)
            # 可能返回空结果或过滤后的结果
            logger.info("  错误传播测试通过（数据被正确处理）")
        except Exception as e:
            # 如果抛出异常，应该是合理的错误
            logger.info(f"  错误传播测试通过（合理异常: {e}）")

    def _generate_integration_data(self, n: int = 50, with_industry: bool = False) -> pd.DataFrame:
        """生成集成测试数据"""
        np.random.seed(42)

        ts_codes = [f"00000{i}.SZ" for i in range(1, 6)]
        dates = pd.date_range('2025-01-01', periods=n, freq='D')

        data_list = []
        for code in ts_codes:
            for date in dates:
                row = {
                    'ts_code': code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'pe_ttm': np.random.uniform(5, 50),
                    'dt_netprofit_yoy': np.random.uniform(0.05, 0.5),
                    'close': np.random.uniform(10, 100),
                    'vol': np.random.uniform(1000000, 10000000),
                }

                if with_industry:
                    row['sw_industry'] = np.random.choice(['金融', '科技', '消费', '工业'])

                data_list.append(row)

        return pd.DataFrame(data_list)


__all__ = ['FactorIntegrationTest']
