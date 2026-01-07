"""
文件input(依赖外部什么): pandas, numpy, time, memory_profiler, factors.core, factors.calculation
文件output(提供什么): 因子性能测试类，评估因子计算效率和资源消耗
文件pos(系统局部地位): 测试框架层 - 性能测试模块
文件功能: 测试因子在不同数据规模下的计算性能、内存占用、处理速度等

使用示例:
    from factors.testing.performance_test import PerformanceTest

    test = PerformanceTest()
    test.run_performance_tests()

返回值:
    Dict: 性能测试报告（耗时、内存、吞吐量等）
"""

import pandas as pd
import numpy as np
import time
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceTest:
    """因子性能测试"""

    def __init__(self, factor_class, factor_name: str = None):
        self.factor_class = factor_class
        self.factor_name = factor_name or factor_class.__name__
        self.performance_report = {}

    def run_performance_tests(self) -> Dict[str, Any]:
        """运行所有性能测试"""
        logger.info(f"开始运行性能测试: {self.factor_name}")

        test_scales = [
            (100, "小规模（100条）"),
            (1000, "中规模（1000条）"),
            (5000, "大规模（5000条）"),
        ]

        results = {}

        for scale, description in test_scales:
            logger.info(f"  测试 {description}...")
            result = self.test_scale(scale)
            results[f"scale_{scale}"] = result
            logger.info(f"    耗时: {result['elapsed']:.3f}s, 内存: {result.get('memory_mb', 'N/A')}MB")

        # 综合分析
        self.performance_report = {
            'factor_name': self.factor_name,
            'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'scale_tests': results,
            'summary': self._generate_summary(results),
        }

        logger.info("性能测试完成")
        return self.performance_report

    def test_scale(self, n: int) -> Dict[str, Any]:
        """测试特定数据规模"""
        # 生成测试数据
        data = self._generate_large_data(n)

        # 测试计算性能
        factor = self.factor_class()

        # 内存使用估算（简化版）
        start_memory = self._estimate_memory_usage(data)

        # 计时
        start_time = time.time()
        result = factor.calculate(data)
        elapsed = time.time() - start_time

        end_memory = self._estimate_memory_usage(result)

        # 计算指标
        memory_used = max(0, end_memory - start_memory)

        return {
            'data_size': n,
            'elapsed': elapsed,
            'memory_mb': round(memory_used, 2),
            'throughput': n / elapsed if elapsed > 0 else 0,  # 条/秒
            'result_size': len(result),
            'efficiency': len(result) / n if n > 0 else 0,  # 输出率
        }

    def test_stress(self, max_scale: int = 10000) -> Dict[str, Any]:
        """压力测试 - 逐步增加数据量直到性能下降"""
        logger.info("  运行压力测试...")

        scales = [1000, 2000, 5000, 10000]
        results = []

        for scale in scales:
            if scale > max_scale:
                break

            try:
                result = self.test_scale(scale)
                results.append(result)
                logger.info(f"    {scale}条: {result['elapsed']:.3f}s")
            except Exception as e:
                logger.error(f"    {scale}条失败: {e}")
                break

        # 分析性能拐点
        if len(results) >= 2:
            times = [r['elapsed'] for r in results]
            scales = [r['data_size'] for r in results]

            # 计算性能增长率
            growth_rates = []
            for i in range(1, len(times)):
                if times[i-1] > 0:
                    rate = (times[i] - times[i-1]) / times[i-1]
                    growth_rates.append(rate)

            avg_growth = np.mean(growth_rates) if growth_rates else 0

            return {
                'stress_results': results,
                'avg_growth_rate': avg_growth,
                'performance_trend': '线性' if avg_growth < 1.5 else '非线性',
                'max_scale': scales[-1],
            }

        return {'stress_results': results}

    def test_concurrency(self, n: int = 1000) -> Dict[str, Any]:
        """测试并发处理能力（模拟）"""
        logger.info("  测试并发处理...")

        # 生成多组独立数据
        data = self._generate_large_data(n)

        # 测试单次处理
        factor = self.factor_class()
        start = time.time()
        result1 = factor.calculate(data)
        time1 = time.time() - start

        # 测试重复处理（模拟并发）
        start = time.time()
        for _ in range(3):
            factor.calculate(data.copy())
        time3 = time.time() - start

        avg_time = time3 / 3

        return {
            'single_time': time1,
            'avg_concurrent_time': avg_time,
            'overhead': (avg_time - time1) / time1 if time1 > 0 else 0,
            'concurrency_score': 1 / avg_time if avg_time > 0 else 0,
        }

    def test_memory_efficiency(self, n: int = 5000) -> Dict[str, Any]:
        """测试内存效率"""
        logger.info("  测试内存效率...")

        data = self._generate_large_data(n)

        # 估算输入内存
        input_memory = self._estimate_memory_usage(data)

        factor = self.factor_class()
        result = factor.calculate(data)

        # 估算输出内存
        output_memory = self._estimate_memory_usage(result)

        # 计算内存效率
        memory_ratio = output_memory / input_memory if input_memory > 0 else 0

        return {
            'input_memory_mb': round(input_memory, 2),
            'output_memory_mb': round(output_memory, 2),
            'memory_ratio': round(memory_ratio, 2),
            'efficiency': '高' if memory_ratio < 0.5 else '中' if memory_ratio < 1 else '低',
        }

    def _generate_large_data(self, n: int) -> pd.DataFrame:
        """生成大规模测试数据"""
        np.random.seed(42)

        # 根据因子类型生成数据
        if 'peg' in self.factor_name.lower():
            return self._generate_peg_data(n)
        elif '010' in self.factor_name.lower():
            return self._generate_price_data(n)
        elif 'pluse' in self.factor_name.lower():
            return self._generate_volume_data(n)
        else:
            return self._generate_generic_data(n)

    def _generate_peg_data(self, n: int) -> pd.DataFrame:
        """生成PEG测试数据"""
        ts_codes = [f"00000{i}.SZ" for i in range(1, 10)]
        dates = pd.date_range('2025-01-01', periods=n//10 + 1, freq='D')

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
        """生成价格测试数据"""
        ts_codes = [f"00000{i}.SZ" for i in range(1, 10)]
        dates = pd.date_range('2025-01-01', periods=n//10 + 1, freq='D')

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
        """生成成交量测试数据"""
        ts_codes = [f"00000{i}.SZ" for i in range(1, 10)]
        dates = pd.date_range('2025-01-01', periods=n//10 + 1, freq='D')

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
        """生成通用测试数据"""
        ts_codes = [f"00000{i}.SZ" for i in range(1, 10)]
        dates = pd.date_range('2025-01-01', periods=n//10 + 1, freq='D')

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

    def _estimate_memory_usage(self, df: pd.DataFrame) -> float:
        """估算DataFrame内存使用（MB）"""
        if df is None or len(df) == 0:
            return 0

        # 简化估算：每条记录约100字节
        approx_bytes = len(df) * len(df.columns) * 100
        return approx_bytes / (1024 * 1024)

    def _generate_summary(self, results: Dict) -> Dict[str, Any]:
        """生成性能总结"""
        if not results:
            return {}

        # 提取关键指标
        elapsed_times = [r['elapsed'] for r in results.values()]
        throughputs = [r['throughput'] for r in results.values()]
        memories = [r['memory_mb'] for r in results.values()]

        # 计算性能等级
        avg_throughput = np.mean(throughputs)
        if avg_throughput > 1000:
            performance_level = "优秀"
        elif avg_throughput > 500:
            performance_level = "良好"
        elif avg_throughput > 100:
            performance_level = "中等"
        else:
            performance_level = "较低"

        # 线性度分析（理想情况下，时间应随数据量线性增长）
        scales = [r['data_size'] for r in results.values()]
        if len(scales) >= 2:
            time_growth = elapsed_times[-1] / elapsed_times[0]
            scale_growth = scales[-1] / scales[0]
            linearity = time_growth / scale_growth if scale_growth > 0 else 0
            linearity_score = "良好" if 0.8 <= linearity <= 1.2 else "一般"
        else:
            linearity_score = "未知"

        return {
            'avg_throughput': round(avg_throughput, 2),
            'avg_elapsed': round(np.mean(elapsed_times), 3),
            'avg_memory': round(np.mean(memories), 2),
            'performance_level': performance_level,
            'linearity': linearity_score,
            'recommendation': self._generate_recommendation(performance_level, linearity_score),
        }

    def _generate_recommendation(self, performance: str, linearity: str) -> str:
        """生成优化建议"""
        recs = []

        if performance == "较低":
            recs.append("考虑优化计算逻辑或使用向量化操作")
        elif performance == "中等":
            recs.append("可以接受，但大数据量时需监控性能")

        if linearity == "一般":
            recs.append("存在非线性开销，建议检查循环或分组操作")

        if not recs:
            return "性能良好，无需优化"

        return "; ".join(recs)


__all__ = ['PerformanceTest']
