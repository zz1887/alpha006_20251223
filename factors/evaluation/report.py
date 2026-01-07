"""
文件input(依赖外部什么): pandas, numpy, FactorMetrics, datetime
文件output(提供什么): FactorEvaluationReport类，提供完整因子评估和报告生成
文件pos(系统局部地位): 因子评估输出层，整合所有评估指标，生成标准化报告和综合评分
文件功能:
    1. 运行完整因子评估流程
    2. 整合IC/ICIR/分组回测/换手率等指标
    3. 计算因子综合评分 (0-100)
    4. 生成结构化评估报告
    5. 支持多版本对比

使用示例:
    from factors.evaluation import FactorEvaluationReport

    # 创建评估报告
    report = FactorEvaluationReport('alpha_peg')

    # 运行完整评估
    metrics = report.run_full_evaluation(
        factor_df=factor_df,
        price_df=price_df,
        hold_days=20,
        n_groups=5
    )

    # 生成报告文本
    report_text = report.generate_report()

    # 获取摘要
    summary = report.get_summary()

参数说明:
    factor_name: 因子名称
    factor_df: 因子数据 [ts_code, trade_date, factor]
    price_df: 价格数据 [ts_code, trade_date, close]
    hold_days: 持有天数 (默认20)
    n_groups: 分组数量 (默认5)
    output_path: 报告输出路径 (可选)

返回值:
    Dict[str, Any]: 评估指标字典
    str: 格式化报告文本
    Dict[str, float]: 评估摘要
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from .metrics import FactorMetrics


class FactorEvaluationReport:
    """
    因子评估报告生成器

    功能：
    1. 运行完整因子评估
    2. 生成标准化报告
    3. 计算综合评分
    4. 输出可视化数据
    """

    def __init__(self, factor_name: str):
        """
        初始化

        Args:
            factor_name: 因子名称
        """
        self.factor_name = factor_name
        self.metrics = {}
        self.timestamp = datetime.now()

    def run_full_evaluation(self,
                           factor_df: pd.DataFrame,
                           price_df: pd.DataFrame,
                           hold_days: int = 20,
                           n_groups: int = 5) -> Dict[str, Any]:
        """
        运行完整因子评估

        Args:
            factor_df: 因子数据 [ts_code, trade_date, factor]
            price_df: 价格数据 [ts_code, trade_date, close]
            hold_days: 持有天数
            n_groups: 分组数量

        Returns:
            Dict[str, Any]: 完整评估结果
        """
        if len(factor_df) == 0 or len(price_df) == 0:
            return {'error': '数据为空'}

        # 1. 基础统计
        self._calculate_basic_stats(factor_df)

        # 2. 准备前瞻收益率
        forward_returns = self._prepare_forward_returns(price_df, hold_days)

        if forward_returns is None or len(forward_returns) == 0:
            return {'error': '无法计算前瞻收益率'}

        # 3. IC分析
        self._calculate_ic_analysis(factor_df, forward_returns)

        # 4. 分组回测
        self._calculate_group_analysis(factor_df, forward_returns, n_groups)

        # 5. 换手率
        self._calculate_turnover(factor_df)

        # 6. 稳定性
        self._calculate_stability()

        # 7. 综合评分
        self._calculate_comprehensive_score()

        return self.metrics

    def _calculate_basic_stats(self, factor_df: pd.DataFrame):
        """计算基础统计"""
        if 'factor' not in factor_df.columns:
            factor_col = [c for c in factor_df.columns if c not in ['ts_code', 'trade_date']][0]
            factor_df = factor_df.rename(columns={factor_col: 'factor'})

        valid_data = factor_df['factor'].dropna()

        self.metrics['basic_stats'] = {
            'total_records': len(factor_df),
            'valid_records': len(valid_data),
            'missing_ratio': 1 - len(valid_data) / len(factor_df),
            'stock_count': factor_df['ts_code'].nunique(),
            'date_count': factor_df['trade_date'].nunique(),
            'mean': float(valid_data.mean()),
            'std': float(valid_data.std()),
            'min': float(valid_data.min()),
            'max': float(valid_data.max()),
            'median': float(valid_data.median()),
        }

    def _prepare_forward_returns(self,
                                 price_df: pd.DataFrame,
                                 hold_days: int) -> Optional[pd.DataFrame]:
        """
        准备前瞻收益率

        Args:
            price_df: 价格数据
            hold_days: 持有天数

        Returns:
            前瞻收益率DataFrame
        """
        df = price_df.sort_values(['ts_code', 'trade_date']).copy()

        # 计算未来收益率
        df['future_price'] = df.groupby('ts_code')['close'].shift(-hold_days)
        df['forward_return'] = (df['future_price'] / df['close'] - 1)

        # 保留有效数据
        result = df[['ts_code', 'trade_date', 'forward_return']].dropna()

        if len(result) == 0:
            return None

        return result

    def _calculate_ic_analysis(self,
                              factor_df: pd.DataFrame,
                              forward_returns: pd.DataFrame):
        """IC分析"""
        if 'factor' not in factor_df.columns:
            factor_col = [c for c in factor_df.columns if c not in ['ts_code', 'trade_date']][0]
            factor_df = factor_df.rename(columns={factor_col: 'factor'})

        ic_series = FactorMetrics.calculate_ic(factor_df, forward_returns)
        icir_stats = FactorMetrics.calculate_icir(ic_series)

        self.metrics['ic_analysis'] = {
            'ic_series': ic_series.to_dict(),
            **icir_stats,
        }

    def _calculate_group_analysis(self,
                                 factor_df: pd.DataFrame,
                                 forward_returns: pd.DataFrame,
                                 n_groups: int):
        """分组分析"""
        if 'factor' not in factor_df.columns:
            factor_col = [c for c in factor_df.columns if c not in ['ts_code', 'trade_date']][0]
            factor_df = factor_df.rename(columns={factor_col: 'factor'})

        group_stats = FactorMetrics.calculate_group_returns(
            factor_df, forward_returns, n_groups
        )

        self.metrics['group_analysis'] = group_stats

    def _calculate_turnover(self, factor_df: pd.DataFrame):
        """换手率"""
        if 'factor' not in factor_df.columns:
            factor_col = [c for c in factor_df.columns if c not in ['ts_code', 'trade_date']][0]
            factor_df = factor_df.rename(columns={factor_col: 'factor'})

        turnover = FactorMetrics.calculate_turnover(factor_df)
        self.metrics['turnover'] = turnover

    def _calculate_stability(self):
        """稳定性分析"""
        if 'ic_analysis' in self.metrics and 'ic_series' in self.metrics['ic_analysis']:
            ic_series = pd.Series(self.metrics['ic_analysis']['ic_series'])
            stability = FactorMetrics.calculate_stability(ic_series)
            self.metrics['stability'] = stability

    def _calculate_comprehensive_score(self):
        """综合评分"""
        score = FactorMetrics.calculate_comprehensive_score(self.metrics)
        self.metrics['comprehensive_score'] = score

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """
        生成文本报告

        Args:
            output_path: 输出路径，None则返回字符串

        Returns:
            str: 报告文本
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"因子评估报告: {self.factor_name}")
        lines.append(f"生成时间: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")

        # 基础统计
        if 'basic_stats' in self.metrics:
            lines.append("📊 基础统计")
            bs = self.metrics['basic_stats']
            lines.append(f"  总记录数: {bs['total_records']:,}")
            lines.append(f"  有效记录: {bs['valid_records']:,} ({bs['missing_ratio']:.2%}缺失)")
            lines.append(f"  股票数量: {bs['stock_count']:,}")
            lines.append(f"  日期数量: {bs['date_count']:,}")
            lines.append(f"  均值: {bs['mean']:.4f}")
            lines.append(f"  标准差: {bs['std']:.4f}")
            lines.append(f"  范围: [{bs['min']:.4f}, {bs['max']:.4f}]")
            lines.append("")

        # IC分析
        if 'ic_analysis' in self.metrics:
            lines.append("📈 IC分析")
            ic = self.metrics['ic_analysis']
            lines.append(f"  IC均值: {ic['ic_mean']:.4f}")
            lines.append(f"  IC标准差: {ic['ic_std']:.4f}")
            lines.append(f"  ICIR: {ic['icir']:.4f}")
            lines.append(f"  正IC比例: {ic['ic_positive_ratio']:.2%}")
            lines.append(f"  |IC|均值: {ic['ic_abs_mean']:.4f}")
            lines.append("")

        # 分组分析
        if 'group_analysis' in self.metrics:
            lines.append("🎯 分组回测")
            ga = self.metrics['group_analysis']
            for i in range(1, 6):
                key = f'group_{i}'
                if key in ga:
                    lines.append(f"  组{i}: {ga[key]:.4%}")
            if 'group_1_vs_5' in ga:
                lines.append(f"  组1-组5差: {ga['group_1_vs_5']:.4%}")
            lines.append("")

        # 换手率和稳定性
        if 'turnover' in self.metrics:
            lines.append(f"🔄 换手率: {self.metrics['turnover']:.2%}")

        if 'stability' in self.metrics:
            st = self.metrics['stability']
            lines.append(f"📊 稳定性得分: {st['stability_score']:.1f}/100")

        # 综合评分
        if 'comprehensive_score' in self.metrics:
            lines.append("")
            lines.append("=" * 60)
            lines.append(f"🏆 综合评分: {self.metrics['comprehensive_score']:.1f}/100")
            lines.append("=" * 60)

        report_text = "\n".join(lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"报告已保存: {output_path}")
        else:
            print(report_text)

        return report_text

    def get_summary(self) -> Dict[str, Any]:
        """
        获取评估摘要

        Returns:
            Dict[str, Any]: 摘要信息
        """
        summary = {
            'factor_name': self.factor_name,
            'timestamp': self.timestamp.isoformat(),
            'score': self.metrics.get('comprehensive_score', 0),
            'icir': self.metrics.get('ic_analysis', {}).get('icir', 0),
            'turnover': self.metrics.get('turnover', 0),
            'stability': self.metrics.get('stability', {}).get('stability_score', 0),
            'status': 'valid' if self.metrics.get('comprehensive_score', 0) > 50 else 'needs_review',
        }

        return summary