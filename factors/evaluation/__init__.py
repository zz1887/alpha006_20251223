"""
文件input(依赖外部什么): factors.evaluation.metrics, report, backtest, analysis
文件output(提供什么): 因子评估完整工具集统一导入接口
文件pos(系统局部地位): 因子评估层入口，提供因子质量评估和回测功能
文件功能:
    1. 评价指标计算（IC/ICIR/分组回测/换手率/稳定性）
    2. 因子回测引擎（单期/多期）
    3. 因子分析工具（相关性/IC分析/优化/冗余检测）
    4. 评估报告生成（综合评分/可视化）

使用示例:
    from factors.evaluation import FactorEvaluationReport, FactorMetrics

    # 创建评估报告
    report = FactorEvaluationReport('alpha_peg')

    # 运行完整评估
    metrics = report.run_full_evaluation(
        factor_df=factor_df,
        price_df=price_df,
        hold_days=20,
        n_groups=5
    )

    # 生成报告
    report_text = report.generate_report('results/alpha_peg_report.txt')

    # 单独计算IC
    ic_series = FactorMetrics.calculate_ic(factor_df, forward_returns)
    icir = FactorMetrics.calculate_icir(ic_series)

返回值:
    FactorMetrics: 指标计算工具类
    FactorEvaluationReport: 评估报告生成器
    FactorBacktestEngine: 单期回测引擎
    MultiPeriodBacktest: 多期回测引擎
    FactorCorrelationAnalyzer: 相关性分析器
    ICAnalyzer: IC分析器
    FactorOptimizer: 因子优化器
    FactorRedundancyDetector: 冗余检测器
"""

from .metrics import FactorMetrics
from .report import FactorEvaluationReport
from .backtest import FactorBacktestEngine, MultiPeriodBacktest
from .analysis import (
    FactorCorrelationAnalyzer,
    ICAnalyzer,
    FactorOptimizer,
    FactorRedundancyDetector
)

__all__ = [
    'FactorMetrics',
    'FactorEvaluationReport',
    'FactorBacktestEngine',
    'MultiPeriodBacktest',
    'FactorCorrelationAnalyzer',
    'ICAnalyzer',
    'FactorOptimizer',
    'FactorRedundancyDetector',
]