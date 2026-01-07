"""
文件input(依赖外部什么): pandas, numpy, typing, seaborn, matplotlib.pyplot
文件output(提供什么): FactorCorrelationAnalyzer类，提供因子相关性分析和冗余检测
文件pos(系统局部地位): 因子研究层，用于因子组合优化和冗余因子识别
文件功能:
    1. 计算因子间相关系数矩阵（支持多种方法）
    2. 识别高度相关因子对（冗余因子）
    3. 生成相关性热力图可视化
    4. 计算各因子冗余度分数
    5. 生成完整相关性分析报告

使用示例:
    from factors.research.correlation import FactorCorrelationAnalyzer

    # 创建相关性分析器
    analyzer = FactorCorrelationAnalyzer(factors_df)

    # 计算相关系数矩阵
    corr_matrix = analyzer.calculate_correlation(method='spearman')

    # 查找冗余因子
    redundant = analyzer.find_redundant_factors(threshold=0.8)

    # 生成热力图
    analyzer.generate_correlation_heatmap('correlation_heatmap.png')

    # 获取冗余度分数
    scores = analyzer.get_factor_redundancy_score()

    # 生成完整报告
    report = analyzer.generate_analysis_report()

参数说明:
    factors_df: 因子数据 [ts_code, trade_date, factor1, factor2, ...]
    method: 相关系数方法 ('pearson', 'spearman', 'kendall')
    threshold: 冗余阈值（默认0.8）
    output_path: 热力图保存路径

返回值:
    pd.DataFrame: 相关系数矩阵
    List[Tuple]: 冗余因子对 [(factor1, factor2, correlation), ...]
    Dict: 冗余度分数 {factor_name: redundancy_score}
    Dict: 完整分析报告
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import seaborn as sns
import matplotlib.pyplot as plt


class FactorCorrelationAnalyzer:
    """
    因子相关性分析器

    功能：
    1. 计算因子间相关系数矩阵
    2. 识别高度相关因子对
    3. 生成相关性热力图
    4. 因子冗余度分析
    """

    def __init__(self, factors_df: pd.DataFrame):
        """
        初始化

        Args:
            factors_df: 因子数据 [ts_code, trade_date, factor1, factor2, ...]
        """
        self.factors_df = factors_df.copy()
        self.correlation_matrix = None
        self.redundant_pairs = None

    def calculate_correlation(self, method: str = 'spearman') -> pd.DataFrame:
        """
        计算因子相关系数矩阵

        Args:
            method: 相关系数方法 ('pearson', 'spearman', 'kendall')

        Returns:
            pd.DataFrame: 相关系数矩阵
        """
        # 提取因子列
        factor_cols = [col for col in self.factors_df.columns
                      if col not in ['ts_code', 'trade_date']]

        if len(factor_cols) < 2:
            raise ValueError("至少需要2个因子才能计算相关性")

        # 按日期计算平均因子值
        daily_means = self.factors_df.groupby('trade_date')[factor_cols].mean()

        # 计算相关系数矩阵
        self.correlation_matrix = daily_means.corr(method=method)

        return self.correlation_matrix

    def find_redundant_factors(self, threshold: float = 0.8) -> List[Tuple[str, str, float]]:
        """
        查找高度相关的因子对（冗余因子）

        Args:
            threshold: 相关系数阈值

        Returns:
            List[Tuple]: [(factor1, factor2, correlation), ...]
        """
        if self.correlation_matrix is None:
            self.calculate_correlation()

        redundant = []
        factor_cols = self.correlation_matrix.columns.tolist()

        for i, f1 in enumerate(factor_cols):
            for j, f2 in enumerate(factor_cols):
                if i < j:  # 避免重复和对角线
                    corr = self.correlation_matrix.loc[f1, f2]
                    if abs(corr) >= threshold:
                        redundant.append((f1, f2, corr))

        # 按相关系数绝对值降序排序
        redundant.sort(key=lambda x: abs(x[2]), reverse=True)
        self.redundant_pairs = redundant

        return redundant

    def generate_correlation_heatmap(self, output_path: Optional[str] = None):
        """
        生成相关性热力图

        Args:
            output_path: 保存路径，None则显示
        """
        if self.correlation_matrix is None:
            self.calculate_correlation()

        plt.figure(figsize=(10, 8))
        sns.heatmap(
            self.correlation_matrix,
            annot=True,
            cmap='coolwarm',
            center=0,
            vmin=-1,
            vmax=1,
            square=True,
            fmt='.3f'
        )
        plt.title('因子相关性热力图')
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"热力图已保存: {output_path}")
        else:
            plt.show()

        plt.close()

    def get_factor_redundancy_score(self) -> Dict[str, float]:
        """
        计算各因子的冗余度分数

        Returns:
            Dict: {factor_name: redundancy_score}
        """
        if self.correlation_matrix is None:
            self.calculate_correlation()

        factor_cols = self.correlation_matrix.columns.tolist()
        redundancy_scores = {}

        for factor in factor_cols:
            # 计算该因子与其他因子的平均绝对相关系数
            other_factors = [f for f in factor_cols if f != factor]
            if other_factors:
                avg_corr = self.correlation_matrix.loc[factor, other_factors].abs().mean()
            else:
                avg_corr = 0
            redundancy_scores[factor] = avg_corr

        return redundancy_scores

    def generate_analysis_report(self) -> Dict:
        """
        生成相关性分析报告

        Returns:
            Dict: 完整分析报告
        """
        # 计算相关系数矩阵
        corr_matrix = self.calculate_correlation()

        # 查找冗余因子
        redundant_pairs = self.find_redundant_factors(threshold=0.8)

        # 计算冗余度分数
        redundancy_scores = self.get_factor_redundancy_score()

        # 统计信息
        avg_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean()
        max_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].max()

        report = {
            'summary': {
                'total_factors': len(corr_matrix.columns),
                'redundant_pairs_count': len(redundant_pairs),
                'average_correlation': avg_corr,
                'max_correlation': max_corr,
            },
            'redundant_pairs': redundant_pairs,
            'redundancy_scores': redundancy_scores,
            'correlation_matrix': corr_matrix.to_dict(),
        }

        return report
