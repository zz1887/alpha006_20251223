"""
文件input(依赖外部什么): pandas, numpy, logging
文件output(提供什么): 因子分析工具类集合，包括相关性分析、IC分析、组合优化、冗余检测
文件pos(系统局部地位): 因子评估分析层，提供高级分析功能，支持因子研究和优化
文件功能:
    1. 因子相关性分析 - 检测因子间冗余
    2. IC时序分析 - 评估因子稳定性
    3. 因子组合优化 - 权重分配策略
    4. 因子冗余检测 - 识别需要剔除的因子

使用示例:
    from factors.evaluation import FactorCorrelationAnalyzer, ICAnalyzer

    # 相关性分析
    analyzer = FactorCorrelationAnalyzer(factor_df)
    corr_matrix = analyzer.calculate_correlation()
    report = analyzer.generate_analysis_report()

    # IC分析
    ic_analyzer = ICAnalyzer(ic_series)
    analysis = ic_analyzer.generate_ic_analysis_report()

参数说明:
    factor_df: 因子数据 [ts_code, trade_date, factor1, factor2, ...]
    ic_series: IC时间序列
    forward_returns: 前瞻收益率
    threshold: 高相关性阈值 (默认0.7)

返回值:
    pd.DataFrame: 相关系数矩阵
    Dict[str, any]: 分析报告
    Dict[str, float]: 因子权重
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging


class FactorCorrelationAnalyzer:
    """因子相关性分析器"""

    def __init__(self, factor_df: pd.DataFrame):
        """
        初始化

        Args:
            factor_df: 因子数据，格式为 [ts_code, trade_date, factor1, factor2, ...]
        """
        self.factor_df = factor_df.copy()
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_correlation(self, method: str = 'pearson') -> pd.DataFrame:
        """
        计算因子间相关系数矩阵

        Args:
            method: 相关系数方法 ('pearson', 'spearman', 'kendall')

        Returns:
            pd.DataFrame: 相关系数矩阵
        """
        # 提取因子列（排除ts_code和trade_date）
        factor_cols = [col for col in self.factor_df.columns
                      if col not in ['ts_code', 'trade_date']]

        if len(factor_cols) < 2:
            self.logger.warning("至少需要2个因子才能计算相关性")
            return pd.DataFrame()

        # 按日期计算平均相关性
        daily_corrs = []

        for date in self.factor_df['trade_date'].unique():
            daily_data = self.factor_df[self.factor_df['trade_date'] == date][factor_cols]
            if len(daily_data) > 10:  # 确保有足够数据
                corr = daily_data.corr(method=method)
                daily_corrs.append(corr)

        if not daily_corrs:
            return pd.DataFrame()

        # 计算平均相关性
        avg_corr = pd.concat(daily_corrs).groupby(level=0).mean()

        return avg_corr

    def generate_analysis_report(self, threshold: float = 0.7) -> Dict[str, any]:
        """
        生成相关性分析报告

        Args:
            threshold: 高相关性阈值

        Returns:
            Dict: 分析报告
        """
        corr_matrix = self.calculate_correlation()

        if corr_matrix.empty:
            return {'error': '无法计算相关性'}

        # 识别高相关性因子对
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) >= threshold:
                    high_corr_pairs.append({
                        'factor1': corr_matrix.columns[i],
                        'factor2': corr_matrix.columns[j],
                        'correlation': corr_value
                    })

        # 计算每个因子的平均相关性
        avg_corr_per_factor = corr_matrix.mean()

        return {
            'correlation_matrix': corr_matrix,
            'high_correlation_pairs': high_corr_pairs,
            'avg_correlation_per_factor': avg_corr_per_factor,
            'redundancy_score': len(high_corr_pairs) / (len(corr_matrix) * (len(corr_matrix) - 1) / 2),
            'recommendation': self._generate_recommendations(corr_matrix, high_corr_pairs)
        }

    def _generate_recommendations(self, corr_matrix: pd.DataFrame, high_corr_pairs: List) -> List[str]:
        """生成优化建议"""
        recommendations = []

        if len(high_corr_pairs) == 0:
            recommendations.append("因子间相关性较低，适合组合使用")
        else:
            recommendations.append(f"发现{len(high_corr_pairs)}对高相关性因子，建议选择其中一个")
            for pair in high_corr_pairs:
                recommendations.append(f"- {pair['factor1']} 与 {pair['factor2']} 相关性: {pair['correlation']:.3f}")

        # 检查是否存在完全冗余（相关性>0.95）
        highly_redundant = [p for p in high_corr_pairs if abs(p['correlation']) > 0.95]
        if highly_redundant:
            recommendations.append("⚠️  存在高度冗余因子，强烈建议剔除")

        return recommendations


class ICAnalyzer:
    """IC（信息系数）分析器"""

    def __init__(self, ic_series: pd.Series):
        """
        初始化

        Args:
            ic_series: IC时间序列，索引为日期
        """
        self.ic_series = ic_series.dropna()
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_ic_metrics(self) -> Dict[str, float]:
        """计算IC相关指标"""
        if len(self.ic_series) < 2:
            return {'error': 'IC数据不足'}

        ic_mean = self.ic_series.mean()
        ic_std = self.ic_series.std()
        icir = ic_mean / ic_std if ic_std != 0 else 0

        # 计算IC显著性（t统计量）
        t_stat = ic_mean / (ic_std / np.sqrt(len(self.ic_series)))

        # 计算IC正负比例
        positive_ratio = (self.ic_series > 0).mean()
        negative_ratio = (self.ic_series < 0).mean()

        # 计算IC稳定性（变异系数的倒数）
        stability = 1 / (ic_std / abs(ic_mean)) if ic_mean != 0 else 0

        return {
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'icir': icir,
            't_stat': t_stat,
            'positive_ratio': positive_ratio,
            'negative_ratio': negative_ratio,
            'stability': stability,
            'valid_periods': len(self.ic_series)
        }

    def generate_ic_analysis_report(self) -> Dict[str, any]:
        """生成IC分析报告"""
        metrics = self.calculate_ic_metrics()

        if 'error' in metrics:
            return metrics

        # 评估标准
        evaluation = []

        if abs(metrics['icir']) > 0.15:
            evaluation.append("优秀：ICIR > 0.15")
        elif abs(metrics['icir']) > 0.10:
            evaluation.append("良好：ICIR > 0.10")
        elif abs(metrics['icir']) > 0.05:
            evaluation.append("一般：ICIR > 0.05")
        else:
            evaluation.append("较弱：ICIR <= 0.05")

        if metrics['t_stat'] > 2.0:
            evaluation.append("统计显著：t > 2.0")
        elif metrics['t_stat'] > 1.65:
            evaluation.append("边缘显著：t > 1.65")
        else:
            evaluation.append("不显著：t <= 1.65")

        if metrics['stability'] > 2.0:
            evaluation.append("稳定性高")
        elif metrics['stability'] > 1.0:
            evaluation.append("稳定性中等")
        else:
            evaluation.append("稳定性低")

        return {
            'metrics': metrics,
            'evaluation': evaluation,
            'summary': self._generate_summary(metrics)
        }

    def _generate_summary(self, metrics: Dict[str, float]) -> str:
        """生成总结"""
        icir = metrics['icir']
        stability = metrics['stability']
        positive_ratio = metrics['positive_ratio']

        summary = f"IC均值: {metrics['ic_mean']:.4f}, ICIR: {icir:.4f}, "
        summary += f"稳定性: {stability:.2f}, 正IC比例: {positive_ratio:.1%}"

        return summary


class FactorOptimizer:
    """因子组合优化器"""

    def __init__(self, factor_df: pd.DataFrame, forward_returns: pd.Series):
        """
        初始化

        Args:
            factor_df: 因子数据 [ts_code, trade_date, factor1, factor2, ...]
            forward_returns: 前瞻收益率，MultiIndex: (ts_code, trade_date)
        """
        self.factor_df = factor_df.copy()
        self.forward_returns = forward_returns.copy()
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_factor_ic(self, factor_name: str) -> pd.Series:
        """计算单因子IC"""
        # 合并因子和收益率
        # 修复：Series.reset_index()不支持name参数，需要先reset再重命名
        returns_df = self.forward_returns.reset_index()
        if len(returns_df.columns) == 3:  # MultiIndex: ts_code, trade_date, value
            returns_df.columns = ['ts_code', 'trade_date', 'forward_return']

        merged = pd.merge(
            self.factor_df[['ts_code', 'trade_date', factor_name]],
            returns_df,
            on=['ts_code', 'trade_date'],
            how='inner'
        )

        if len(merged) == 0:
            return pd.Series()

        # 计算每日IC（秩相关系数）
        def calc_daily_ic(group):
            if len(group) < 5:
                return np.nan
            return group[factor_name].corr(group['forward_return'], method='spearman')

        ic_series = merged.groupby('trade_date').apply(calc_daily_ic)
        return ic_series.dropna()

    def optimize_weights(self, method: str = 'icir') -> Dict[str, float]:
        """
        优化因子权重

        Args:
            method: 优化方法 ('icir', 'max_sharpe', 'equal')

        Returns:
            Dict: 因子权重
        """
        factor_cols = [col for col in self.factor_df.columns
                      if col not in ['ts_code', 'trade_date']]

        if len(factor_cols) == 0:
            return {}

        if method == 'equal':
            weight = 1.0 / len(factor_cols)
            return {col: weight for col in factor_cols}

        # 计算每个因子的ICIR
        icir_dict = {}
        for factor in factor_cols:
            ic_series = self.calculate_factor_ic(factor)
            if len(ic_series) > 0:
                icir = ic_series.mean() / ic_series.std() if ic_series.std() != 0 else 0
                icir_dict[factor] = icir

        if not icir_dict:
            return {col: 1.0 / len(factor_cols) for col in factor_cols}

        if method == 'icir':
            # 按ICIR绝对值分配权重
            total_icir = sum(abs(v) for v in icir_dict.values())
            if total_icir == 0:
                return {col: 1.0 / len(factor_cols) for col in factor_cols}
            return {col: abs(icir) / total_icir for col, icir in icir_dict.items()}

        elif method == 'max_sharpe':
            # 简化版：按ICIR正负分配
            positive_icir = {k: v for k, v in icir_dict.items() if v > 0}
            if not positive_icir:
                return {col: 1.0 / len(factor_cols) for col in factor_cols}
            total = sum(positive_icir.values())
            return {k: v / total for k, v in positive_icir.items()}

        return {col: 1.0 / len(factor_cols) for col in factor_cols}

    def evaluate_combination(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        评估组合效果

        Args:
            weights: 因子权重

        Returns:
            Dict: 评估指标
        """
        # 计算加权因子
        weighted_factor = None
        for factor, weight in weights.items():
            if factor not in self.factor_df.columns:
                continue
            if weighted_factor is None:
                weighted_factor = self.factor_df[factor] * weight
            else:
                weighted_factor += self.factor_df[factor] * weight

        if weighted_factor is None:
            return {'error': '无法计算加权因子'}

        # 创建加权因子DataFrame
        weighted_df = self.factor_df[['ts_code', 'trade_date']].copy()
        weighted_df['factor'] = weighted_factor

        # 计算IC
        # 修复：Series.reset_index()不支持name参数
        returns_df = self.forward_returns.reset_index()
        if len(returns_df.columns) == 3:
            returns_df.columns = ['ts_code', 'trade_date', 'forward_return']

        merged = pd.merge(
            weighted_df,
            returns_df,
            on=['ts_code', 'trade_date'],
            how='inner'
        )

        if len(merged) == 0:
            return {'error': '无匹配数据'}

        ic_series = merged.groupby('trade_date').apply(
            lambda g: g['factor'].corr(g['forward_return'], method='spearman')
        ).dropna()

        if len(ic_series) < 2:
            return {'error': 'IC数据不足'}

        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        icir = ic_mean / ic_std if ic_std != 0 else 0

        return {
            'ic_mean': float(ic_mean),
            'ic_std': float(ic_std),
            'icir': float(icir),
            'sharpe_ratio': icir * np.sqrt(252) if icir > 0 else 0,
            'weights': weights
        }


class FactorRedundancyDetector:
    """因子冗余检测器"""

    def __init__(self, factor_df: pd.DataFrame):
        self.factor_df = factor_df.copy()
        self.logger = logging.getLogger(self.__class__.__name__)

    def detect_redundancy(self, threshold: float = 0.85) -> Dict[str, any]:
        """
        检测冗余因子

        Args:
            threshold: 冗余阈值

        Returns:
            Dict: 冗余分析结果
        """
        analyzer = FactorCorrelationAnalyzer(self.factor_df)
        corr_matrix = analyzer.calculate_correlation()

        if corr_matrix.empty:
            return {'error': '无法计算相关性'}

        # 找出高度相关的因子对
        redundant_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) >= threshold:
                    redundant_pairs.append({
                        'factor1': corr_matrix.columns[i],
                        'factor2': corr_matrix.columns[j],
                        'correlation': corr_value
                    })

        # 识别需要剔除的因子
        to_remove = self._identify_factors_to_remove(redundant_pairs, corr_matrix)

        return {
            'redundant_pairs': redundant_pairs,
            'factors_to_remove': to_remove,
            'redundancy_score': len(redundant_pairs) / (len(corr_matrix) * (len(corr_matrix) - 1) / 2),
            'recommendation': self._generate_redundancy_recommendations(redundant_pairs, to_remove)
        }

    def _identify_factors_to_remove(self, redundant_pairs: List[Dict], corr_matrix: pd.DataFrame) -> List[str]:
        """识别需要剔除的因子"""
        if not redundant_pairs:
            return []

        # 构建因子关系图
        from collections import defaultdict
        graph = defaultdict(list)
        for pair in redundant_pairs:
            graph[pair['factor1']].append(pair['factor2'])
            graph[pair['factor2']].append(pair['factor1'])

        # 优先剔除与其他因子相关性最高的
        factor_scores = {}
        for factor in corr_matrix.columns:
            if factor in graph:
                # 计算平均相关性
                avg_corr = np.mean([abs(corr_matrix.loc[factor, other]) for other in graph[factor]])
                factor_scores[factor] = avg_corr

        # 排序并选择要剔除的因子
        sorted_factors = sorted(factor_scores.items(), key=lambda x: x[1], reverse=True)
        to_remove = [f[0] for f in sorted_factors[:len(sorted_factors)//2 + 1]]

        return list(set(to_remove))

    def _generate_redundancy_recommendations(self, redundant_pairs: List[Dict], to_remove: List[str]) -> List[str]:
        """生成冗余检测建议"""
        recommendations = []

        if not redundant_pairs:
            recommendations.append("✅ 未发现冗余因子")
            return recommendations

        recommendations.append(f"⚠️  发现{len(redundant_pairs)}对冗余因子")
        recommendations.append(f"建议剔除以下因子: {', '.join(to_remove)}")
        recommendations.append("理由：这些因子与其他因子高度相关，保留会增加计算复杂度但不增加信息量")

        return recommendations


__all__ = [
    'FactorCorrelationAnalyzer',
    'ICAnalyzer',
    'FactorOptimizer',
    'FactorRedundancyDetector',
]