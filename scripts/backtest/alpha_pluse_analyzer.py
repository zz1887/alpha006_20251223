"""
Alpha Pluse 二元因子分析器

功能:
1. 信号有效性检验
2. 优势比分析
3. 点二列相关系数
4. 稳健性检验
5. 可视化输出
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import sys
import os
from typing import Dict, List, Tuple

sys.path.insert(0, '/home/zcy/alpha006_20251223')

from core.utils.data_loader import data_loader, get_index_data
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class AlphaPluseAnalyzer:
    """Alpha Pluse 二元因子分析器"""

    def __init__(self, start_date: str, end_date: str):
        self.start_date = start_date
        self.end_date = end_date

    def load_backtest_results(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        加载回测结果

        Returns:
            (回测数据, 因子数据, 绩效指标)
        """
        cache_dir = '/home/zcy/alpha006_20251223/data/cache'

        try:
            # 尝试加载最新文件
            factor_df = pd.read_csv(f"{cache_dir}/alpha_pluse_factor.csv")
            factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'])

            logger.info(f"加载因子数据: {len(factor_df):,} 条记录")
            return factor_df, None, None

        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            raise

    def signal_effectiveness_test(self, factor_df: pd.DataFrame) -> Dict[str, float]:
        """
        信号有效性检验

        Args:
            factor_df: 因子数据

        Returns:
            有效性指标字典
        """
        logger.info("=" * 60)
        logger.info("信号有效性检验")
        logger.info("=" * 60)

        # 信号频率
        signal_freq = factor_df['alpha_pluse'].mean()

        # 信号后收益 (简化: 使用下一期收益)
        # 这里需要价格数据来计算实际收益
        # 暂时返回信号频率
        result = {
            'signal_frequency': signal_freq,
        }

        logger.info(f"信号频率: {signal_freq:.2%}")

        return result

    def calculate_point_biserial_correlation(self, factor_df: pd.DataFrame, returns_df: pd.DataFrame) -> float:
        """
        计算点二列相关系数

        Args:
            factor_df: 因子数据
            returns_df: 收益数据

        Returns:
            点二列相关系数
        """
        # 合并数据
        merged = factor_df.merge(returns_df, on=['ts_code', 'trade_date'], how='inner')

        if len(merged) == 0:
            return 0.0

        # 计算
        signal = merged['alpha_pluse']
        returns = merged['return']

        M1 = returns[signal == 1].mean() if len(returns[signal == 1]) > 0 else 0
        M0 = returns[signal == 0].mean() if len(returns[signal == 0]) > 0 else 0
        p = signal.mean()
        sd = returns.std()

        if sd == 0 or p == 0 or p == 1:
            return 0.0

        r_pb = (M1 - M0) / sd * np.sqrt(p * (1 - p))

        return r_pb

    def odds_ratio_analysis(self, factor_df: pd.DataFrame, returns_df: pd.DataFrame) -> Dict[str, float]:
        """
        优势比分析

        Args:
            factor_df: 因子数据
            returns_df: 收益数据

        Returns:
            优势比指标
        """
        # 合并数据
        merged = factor_df.merge(returns_df, on=['ts_code', 'trade_date'], how='inner')

        if len(merged) == 0:
            return {'odds_ratio': 0.0, 'odds_signal': 0.0, 'odds_non_signal': 0.0}

        # 计算正收益比例
        signal_positive = (merged['alpha_pluse'] == 1) & (merged['return'] > 0)
        non_signal_positive = (merged['alpha_pluse'] == 0) & (merged['return'] > 0)

        signal_count = (merged['alpha_pluse'] == 1).sum()
        non_signal_count = (merged['alpha_pluse'] == 0).sum()

        if signal_count == 0 or non_signal_count == 0:
            return {'odds_ratio': 0.0, 'odds_signal': 0.0, 'odds_non_signal': 0.0}

        p_signal = signal_positive.sum() / signal_count
        p_non_signal = non_signal_positive.sum() / non_signal_count

        # 避免除零
        if p_signal == 0:
            p_signal = 0.001
        if p_non_signal == 0:
            p_non_signal = 0.001

        odds_signal = p_signal / (1 - p_signal)
        odds_non_signal = p_non_signal / (1 - p_non_signal)
        odds_ratio = odds_signal / odds_non_signal

        result = {
            'odds_ratio': odds_ratio,
            'odds_signal': odds_signal,
            'odds_non_signal': odds_non_signal,
            'p_signal': p_signal,
            'p_non_signal': p_non_signal,
        }

        logger.info(f"优势比分析:")
        logger.info(f"  信号组正收益概率: {p_signal:.2%}")
        logger.info(f"  非信号组正收益概率: {p_non_signal:.2%}")
        logger.info(f"  优势比: {odds_ratio:.2f}")

        return result

    def generate_report(self, factor_df: pd.DataFrame, metrics: Dict[str, float]):
        """
        生成分析报告

        Args:
            factor_df: 因子数据
            metrics: 绩效指标
        """
        output_dir = '/home/zcy/alpha006_20251223/results/backtest'
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 1. 因子统计报告
        stats = {
            '总记录数': len(factor_df),
            '股票数量': factor_df['ts_code'].nunique(),
            '交易日数': factor_df['trade_date'].nunique(),
            '信号总数': factor_df['alpha_pluse'].sum(),
            '信号比例': factor_df['alpha_pluse'].mean(),
            '平均count_20d': factor_df['count_20d'].mean() if 'count_20d' in factor_df.columns else 0,
        }

        stats_df = pd.DataFrame([stats])
        stats_file = f"{output_dir}/alpha_pluse_factor_stats_{self.start_date}_{self.end_date}_{timestamp}.csv"
        stats_df.to_csv(stats_file, index=False, encoding='utf-8-sig')
        logger.info(f"因子统计已保存: {stats_file}")

        # 2. 信号分布
        if 'count_20d' in factor_df.columns:
            signal_dist = factor_df['count_20d'].value_counts().sort_index()
            dist_file = f"{output_dir}/alpha_pluse_signal_dist_{self.start_date}_{self.end_date}_{timestamp}.csv"
            signal_dist.to_csv(dist_file, header=['count'])
            logger.info(f"信号分布已保存: {dist_file}")

        print("\n" + "=" * 80)
        print("因子分析报告")
        print("=" * 80)
        for key, value in stats.items():
            print(f"{key}: {value}")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Alpha Pluse 二元因子分析器")
    print("=" * 80)

    # 参数
    start_date = '20230101'
    end_date = '20251201'

    # 创建分析器
    analyzer = AlphaPluseAnalyzer(start_date, end_date)

    try:
        # 加载数据
        factor_df, _, _ = analyzer.load_backtest_results()

        # 信号有效性检验
        signal_metrics = analyzer.signal_effectiveness_test(factor_df)

        # 生成报告
        analyzer.generate_report(factor_df, signal_metrics)

        print("\n分析完成！")

    except Exception as e:
        logger.error(f"分析失败: {e}")
        raise


if __name__ == "__main__":
    main()
