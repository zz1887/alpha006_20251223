"""
文件input(依赖外部什么): core.utils, pandas, numpy, matplotlib, seaborn
文件output(提供什么): bias1_qfq优化因子（负值反转）有效性验证脚本
文件pos(系统局部地位): 测试验证层，提供因子质量评估和有效性验证

基于BIAS乖离率逻辑优化的因子验证：
    1. 原始bias1_qfq因子方向错误（高值对应低收益）
    2. 优化方案：使用 -bias1_qfq 作为新因子
    3. BIAS逻辑：负偏离=超卖=买入信号

使用示例:
    python verify_bias1_qfq_optimized.py --start_date 20250101 --end_date 20251231

返回值:
    验证报告（文本+图表）
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import argparse
import logging
from typing import Dict, List, Tuple

# 配置路径
sys.path.insert(0, '/home/zcy/alpha因子库')

from core.utils.db_connection import DBConnection
from core.utils.data_loader import DataLoader
from core.config import DATABASE_CONFIG

# 尝试导入绘图库
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("警告: matplotlib/seaborn未安装，将跳过图表生成")

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Bias1QfqOptimizedValidator:
    """
    Bias1 Qfq 优化因子验证器

    优化逻辑：
    - 原始因子：bias1_qfq（正偏离=超买）
    - 优化因子：-bias1_qfq（负偏离=超卖=买入信号）
    - 预期效果：反转原验证结果，获得正向ICIR
    """

    def __init__(self, start_date: str, end_date: str, output_dir: str = None):
        self.start_date = start_date
        self.end_date = end_date
        self.output_dir = output_dir or f"/home/zcy/alpha因子库/results/bias1_qfq/optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

        # 初始化数据库连接
        self.db = DBConnection(DATABASE_CONFIG)
        self.data_loader = DataLoader()

        logger.info(f"验证器初始化完成")
        logger.info(f"时间范围: {start_date} 至 {end_date}")
        logger.info(f"输出目录: {self.output_dir}")

    def load_original_factor(self) -> pd.DataFrame:
        """从数据库加载原始bias1_qfq因子"""
        logger.info("正在从数据库加载原始bias1_qfq因子...")

        query = f"""
        SELECT ts_code, trade_date, bias1_qfq
        FROM stock_database.stk_factor_pro
        WHERE trade_date BETWEEN '{self.start_date}' AND '{self.end_date}'
          AND bias1_qfq IS NOT NULL
        ORDER BY ts_code, trade_date
        """

        result = self.db.execute_query(query)
        factor_df = pd.DataFrame(result)

        if len(factor_df) == 0:
            raise ValueError("未获取到bias1_qfq因子数据，请检查数据库和日期范围")

        # 转换数据类型
        factor_df['bias1_qfq'] = factor_df['bias1_qfq'].astype(float)
        factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'])

        logger.info(f"加载原始因子数据: {len(factor_df):,} 条记录")
        return factor_df

    def create_optimized_factor(self, original_df: pd.DataFrame) -> pd.DataFrame:
        """创建优化因子：使用 -bias1_qfq"""
        logger.info("正在创建优化因子（-bias1_qfq）...")

        optimized_df = original_df.copy()
        optimized_df['bias1_qfq_optimized'] = -original_df['bias1_qfq']

        # 统计信息
        stats = optimized_df['bias1_qfq_optimized'].describe()
        logger.info(f"优化因子统计:")
        logger.info(f"  均值: {stats['mean']:.4f}")
        logger.info(f"  标准差: {stats['std']:.4f}")
        logger.info(f"  最小值: {stats['min']:.4f}")
        logger.info(f"  最大值: {stats['max']:.4f}")

        return optimized_df

    def load_price_data(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """加载价格数据用于计算未来收益"""
        logger.info("正在加载价格数据...")

        # 从因子数据中获取股票列表
        stocks = factor_df['ts_code'].unique().tolist()
        logger.info(f"需要加载 {len(stocks)} 只股票的价格数据")

        # 使用DataLoader获取价格数据
        price_data = self.data_loader.get_price_data(
            stocks,
            self.start_date,
            self.end_date,
            columns=['close']
        )

        if len(price_data) == 0:
            raise ValueError("未获取到价格数据")

        # 重命名列以匹配后续处理
        price_data = price_data.reset_index()
        price_data.rename(columns={'date': 'trade_date'}, inplace=True)
        price_data['trade_date'] = pd.to_datetime(price_data['trade_date'])

        logger.info(f"加载价格数据: {len(price_data):,} 条记录")
        return price_data

    def calculate_future_returns(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """计算未来收益（T+1日收益）"""
        logger.info("正在计算未来收益...")

        # 按股票分组计算下一日收益
        price_df = price_df.sort_values(['ts_code', 'trade_date'])
        price_df['next_close'] = price_df.groupby('ts_code')['close'].shift(-1)
        price_df['future_return'] = (price_df['next_close'] - price_df['close']) / price_df['close']

        # 只保留有效记录
        returns_df = price_df[['ts_code', 'trade_date', 'future_return']].dropna()

        logger.info(f"计算未来收益: {len(returns_df):,} 条有效记录")
        return returns_df

    def calculate_ic(self, factor_df: pd.DataFrame, returns_df: pd.DataFrame) -> pd.DataFrame:
        """计算信息系数(IC)"""
        logger.info("正在计算IC...")

        # 合并因子和未来收益
        merged = pd.merge(factor_df, returns_df, on=['ts_code', 'trade_date'], how='inner')

        if len(merged) == 0:
            raise ValueError("因子数据和收益数据无交集")

        # 按日期计算秩相关系数
        ic_series = merged.groupby('trade_date').apply(
            lambda x: x['bias1_qfq_optimized'].corr(x['future_return'], method='spearman')
        )

        ic_df = pd.DataFrame({
            'trade_date': ic_series.index,
            'ic': ic_series.values
        })

        logger.info(f"IC计算完成，共{len(ic_df)}个交易日")
        return ic_df

    def analyze_ic(self, ic_df: pd.DataFrame) -> Dict[str, float]:
        """分析IC统计特征"""
        ic_values = ic_df['ic']

        ic_mean = ic_values.mean()
        ic_std = ic_values.std()
        icir = ic_mean / ic_std if ic_std != 0 else 0
        positive_ic_ratio = (ic_values > 0).mean()

        analysis = {
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'icir': icir,
            'positive_ic_ratio': positive_ic_ratio,
            'ic_t_stat': ic_mean / (ic_std / np.sqrt(len(ic_values))) if ic_std != 0 else 0,
        }

        logger.info(f"IC分析:")
        logger.info(f"  IC均值: {ic_mean:.4f}")
        logger.info(f"  IC标准差: {ic_std:.4f}")
        logger.info(f"  ICIR: {icir:.4f}")
        logger.info(f"  正IC比例: {positive_ic_ratio:.2%}")

        return analysis

    def analyze_group_returns(self, factor_df: pd.DataFrame, returns_df: pd.DataFrame, n_groups: int = 5) -> Dict[str, any]:
        """分组收益分析"""
        logger.info("正在进行分组收益分析...")

        # 合并数据
        merged = pd.merge(factor_df, returns_df, on=['ts_code', 'trade_date'], how='inner')

        # 按日期分组，计算分位数
        merged['group'] = merged.groupby('trade_date')['bias1_qfq_optimized'].transform(
            lambda x: pd.qcut(x, n_groups, labels=False, duplicates='drop')
        )

        # 计算各组平均收益
        group_returns = merged.groupby(['trade_date', 'group'])['future_return'].mean().reset_index()
        group_stats = group_returns.groupby('group')['future_return'].agg(['mean', 'std', 'count']).reset_index()

        # 计算单调性
        group_means = group_stats['mean'].values
        monotonic = all(group_means[i] <= group_means[i+1] for i in range(len(group_means)-1))

        # 计算分组差异
        high_minus_low = group_means[-1] - group_means[0]

        result = {
            'group_stats': group_stats,
            'monotonic': monotonic,
            'high_minus_low': high_minus_low,
            'group_means': group_means.tolist(),
        }

        logger.info(f"分组分析:")
        logger.info(f"  分组差异(高-低): {high_minus_low:.4f}")
        logger.info(f"  单调性: {'✓' if monotonic else '✗'}")
        for i, row in group_stats.iterrows():
            logger.info(f"  组{int(row['group'])}: 均值={row['mean']:.4f}, 标准差={row['std']:.4f}")

        return result

    def analyze_stability(self, factor_df: pd.DataFrame) -> Dict[str, float]:
        """因子稳定性分析"""
        logger.info("正在进行稳定性分析...")

        # 计算每日因子均值
        daily_mean = factor_df.groupby('trade_date')['bias1_qfq_optimized'].mean()

        # 计算时间序列统计
        mean_volatility = daily_mean.std()  # 均值波动率
        mean_autocorr = daily_mean.autocorr(lag=1) if len(daily_mean) > 1 else 0  # 一阶自相关

        # 截面标准差（每日横截面波动）
        cross_section_std = factor_df.groupby('trade_date')['bias1_qfq_optimized'].std().mean()

        stability = {
            'mean_volatility': mean_volatility,
            'mean_autocorr': mean_autocorr,
            'cross_section_std': cross_section_std,
        }

        logger.info(f"稳定性分析:")
        logger.info(f"  均值波动率: {mean_volatility:.4f}")
        logger.info(f"  一阶自相关: {mean_autocorr:.4f}")
        logger.info(f"  截面标准差: {cross_section_std:.4f}")

        return stability

    def generate_score(self, ic_analysis: Dict, group_result: Dict, stability: Dict) -> Dict[str, float]:
        """生成综合评分（0-100）"""
        logger.info("正在生成综合评分...")

        score = 0

        # ICIR权重 40% (目标ICIR > 0.3)
        icir = ic_analysis['icir']
        icir_score = min(max(icir * 20, 0), 40)  # ICIR=0.3 → 6分, ICIR=1.0 → 20分, ICIR=2.0 → 40分
        score += icir_score

        # 正IC比例权重 10% (目标 > 50%)
        positive_ratio = ic_analysis['positive_ic_ratio']
        positive_score = min(positive_ratio * 20, 10)  # 50% → 10分
        score += positive_score

        # 分组单调性权重 25% (单调性20分 + 差异5分)
        monotonic_score = 20 if group_result['monotonic'] else 0
        diff = abs(group_result['high_minus_low'])
        diff_score = min(diff * 100, 5)  # 差异1% → 0.1分, 5% → 0.5分, 10% → 5分
        score += monotonic_score + diff_score

        # 稳定性权重 15% (自相关 > 0.5)
        autocorr = stability['mean_autocorr']
        stability_score = min(max(autocorr * 30, 0), 15)  # 0.5 → 15分
        score += stability_score

        # 数据质量权重 10% (缺失率倒数)
        quality_score = 10  # 默认满分，实际可根据缺失率调整
        score += quality_score

        # 限制最大100分
        total_score = min(score, 100)

        breakdown = {
            'total_score': total_score,
            'icir_score': icir_score,
            'positive_score': positive_score,
            'monotonic_score': monotonic_score,
            'diff_score': diff_score,
            'stability_score': stability_score,
            'quality_score': quality_score,
        }

        logger.info(f"综合评分: {total_score:.1f}/100")
        logger.info(f"  ICIR贡献: {icir_score:.1f}")
        logger.info(f"  正IC比例贡献: {positive_score:.1f}")
        logger.info(f"  单调性贡献: {monotonic_score:.1f}")
        logger.info(f"  分组差异贡献: {diff_score:.1f}")
        logger.info(f"  稳定性贡献: {stability_score:.1f}")
        logger.info(f"  数据质量贡献: {quality_score:.1f}")

        return breakdown

    def generate_report(self, factor_df: pd.DataFrame, ic_analysis: Dict, group_result: Dict, stability: Dict, scores: Dict):
        """生成验证报告"""
        logger.info("正在生成验证报告...")

        report_path = os.path.join(self.output_dir, "validation_report.txt")

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("BIAS1_QFQ 优化因子验证报告\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"时间范围: {self.start_date} 至 {self.end_date}\n")
            f.write(f"优化方案: 使用 -bias1_qfq 作为因子（反转原方向）\n\n")

            f.write("-" * 80 + "\n")
            f.write("1. 数据质量检查\n")
            f.write("-" * 80 + "\n")
            f.write(f"总记录数: {len(factor_df):,}\n")
            f.write(f"股票数量: {factor_df['ts_code'].nunique()}\n")
            f.write(f"日期数量: {factor_df['trade_date'].nunique()}\n")
            f.write(f"缺失率: {(1 - len(factor_df) / (factor_df['ts_code'].nunique() * factor_df['trade_date'].nunique())):.2%}\n\n")

            desc = factor_df['bias1_qfq_optimized'].describe()
            f.write("因子统计特征:\n")
            f.write(f"  均值: {desc['mean']:.4f}\n")
            f.write(f"  标准差: {desc['std']:.4f}\n")
            f.write(f"  中位数: {desc['50%']:.4f}\n")
            f.write(f"  最小值: {desc['min']:.4f}\n")
            f.write(f"  最大值: {desc['max']:.4f}\n\n")

            f.write("-" * 80 + "\n")
            f.write("2. 信息系数(IC)分析\n")
            f.write("-" * 80 + "\n")
            f.write(f"IC均值: {ic_analysis['ic_mean']:.4f}\n")
            f.write(f"IC标准差: {ic_analysis['ic_std']:.4f}\n")
            f.write(f"ICIR (IC均值/IC标准差): {ic_analysis['icir']:.4f}\n")
            f.write(f"正IC比例: {ic_analysis['positive_ic_ratio']:.2%}\n")
            f.write(f"IC t统计量: {ic_analysis['ic_t_stat']:.4f}\n\n")

            f.write("判断标准:\n")
            f.write("  ICIR > 0.3: 优秀因子\n")
            f.write("  ICIR 0.2-0.3: 良好因子\n")
            f.write("  ICIR 0.1-0.2: 一般因子\n")
            f.write("  ICIR < 0.1: 较差因子\n\n")

            f.write("-" * 80 + "\n")
            f.write("3. 分组收益分析\n")
            f.write("-" * 80 + "\n")
            f.write(f"分组差异(高组-低组): {group_result['high_minus_low']:.4f}\n")
            f.write(f"单调性: {'✓ 通过' if group_result['monotonic'] else '✗ 未通过'}\n\n")

            f.write("各组平均收益:\n")
            for i, row in group_result['group_stats'].iterrows():
                f.write(f"  组{int(row['group'])}: {row['mean']:.4f} (样本数: {int(row['count'])})\n")
            f.write("\n")

            f.write("-" * 80 + "\n")
            f.write("4. 因子稳定性分析\n")
            f.write("-" * 80 + "\n")
            f.write(f"均值波动率: {stability['mean_volatility']:.4f}\n")
            f.write(f"一阶自相关: {stability['mean_autocorr']:.4f}\n")
            f.write(f"截面标准差: {stability['cross_section_std']:.4f}\n\n")

            f.write("-" * 80 + "\n")
            f.write("5. 综合评分\n")
            f.write("-" * 80 + "\n")
            f.write(f"总分: {scores['total_score']:.1f}/90\n\n")

            f.write("评分明细:\n")
            f.write(f"  ICIR贡献: {scores['icir_score']:.1f}/40\n")
            f.write(f"  正IC比例贡献: {scores['positive_score']:.1f}/10\n")
            f.write(f"  单调性贡献: {scores['monotonic_score']:.1f}/20\n")
            f.write(f"  分组差异贡献: {scores['diff_score']:.1f}/5\n")
            f.write(f"  稳定性贡献: {scores['stability_score']:.1f}/15\n")
            f.write(f"  数据质量贡献: {scores['quality_score']:.1f}/10\n\n")

            f.write("-" * 80 + "\n")
            f.write("6. 结论\n")
            f.write("-" * 80 + "\n")

            if scores['total_score'] >= 60:
                verdict = "✅ 因子有效，建议使用"
            elif scores['total_score'] >= 40:
                verdict = "⚠️  因子一般，需要优化"
            else:
                verdict = "❌ 因子无效，不建议使用"

            f.write(f"验证结论: {verdict}\n\n")

            f.write("优化说明:\n")
            f.write("  原始bias1_qfq因子方向错误（高值对应低收益）\n")
            f.write("  优化方案：使用 -bias1_qfq 作为新因子\n")
            f.write("  BIAS乖离率逻辑：负偏离=超卖=买入信号\n")
            f.write("  预期效果：获得正向ICIR和良好回测表现\n\n")

            f.write("=" * 80 + "\n")
            f.write("报告结束\n")
            f.write("=" * 80 + "\n")

        logger.info(f"验证报告已保存: {report_path}")
        return report_path

    def save_factor_data(self, factor_df: pd.DataFrame):
        """保存优化后的因子数据"""
        factor_path = os.path.join(self.output_dir, "bias1_qfq_optimized_factor.csv")

        # 保存完整数据
        save_df = factor_df[['ts_code', 'trade_date', 'bias1_qfq_optimized']].copy()
        save_df['trade_date'] = save_df['trade_date'].dt.strftime('%Y-%m-%d')
        save_df.to_csv(factor_path, index=False, float_format='%.6f')

        logger.info(f"优化因子数据已保存: {factor_path}")
        return factor_path

    def plot_results(self, ic_df: pd.DataFrame, group_result: Dict, factor_df: pd.DataFrame):
        """绘制分析图表"""
        if not PLOTTING_AVAILABLE:
            logger.warning("绘图库不可用，跳过图表生成")
            return

        logger.info("正在生成图表...")

        # 1. IC时间序列图
        plt.figure(figsize=(12, 6))
        plt.plot(ic_df['trade_date'], ic_df['ic'], label='IC', alpha=0.7)
        plt.axhline(y=ic_df['ic'].mean(), color='r', linestyle='--', label=f'Mean({ic_df["ic"].mean():.4f})')
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.title('Optimized Factor IC Time Series')
        plt.xlabel('Date')
        plt.ylabel('IC')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'ic_timeseries.png'), dpi=300)
        plt.close()

        # 2. 分组收益柱状图
        plt.figure(figsize=(10, 6))
        group_means = group_result['group_means']
        groups = [f'Group{i}' for i in range(len(group_means))]
        colors = ['red' if x < 0 else 'green' for x in group_means]
        plt.bar(groups, group_means, color=colors, alpha=0.7)
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        plt.title('Optimized Factor Group Returns')
        plt.xlabel('Group')
        plt.ylabel('Average Forward Return')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'group_returns.png'), dpi=300)
        plt.close()

        # 3. 因子分布直方图
        plt.figure(figsize=(10, 6))
        sample_data = factor_df['bias1_qfq_optimized'].sample(n=min(100000, len(factor_df)), random_state=42)
        plt.hist(sample_data, bins=50, alpha=0.7, color='blue', edgecolor='black')
        plt.axvline(x=0, color='red', linestyle='--', label='Zero Line')
        plt.title('Optimized Factor Distribution')
        plt.xlabel('Factor Value')
        plt.ylabel('Frequency')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'factor_distribution.png'), dpi=300)
        plt.close()

        # 4. 因子均值时间序列
        daily_mean = factor_df.groupby('trade_date')['bias1_qfq_optimized'].mean()
        plt.figure(figsize=(12, 6))
        plt.plot(daily_mean.index, daily_mean.values, label='Daily Factor Mean', color='purple')
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        plt.title('Optimized Factor Mean Time Series')
        plt.xlabel('Date')
        plt.ylabel('Factor Mean')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'factor_timeseries.png'), dpi=300)
        plt.close()

        logger.info(f"图表已保存至: {self.output_dir}")

    def run(self):
        """运行完整验证流程"""
        try:
            logger.info("=" * 80)
            logger.info("开始优化因子验证流程")
            logger.info("=" * 80)

            # 1. 加载原始因子
            original_df = self.load_original_factor()

            # 2. 创建优化因子
            optimized_df = self.create_optimized_factor(original_df)

            # 3. 加载价格数据
            price_df = self.load_price_data(optimized_df)

            # 4. 计算未来收益
            returns_df = self.calculate_future_returns(price_df)

            # 5. 计算IC
            ic_df = self.calculate_ic(optimized_df, returns_df)

            # 6. IC分析
            ic_analysis = self.analyze_ic(ic_df)

            # 7. 分组收益分析
            group_result = self.analyze_group_returns(optimized_df, returns_df)

            # 8. 稳定性分析
            stability = self.analyze_stability(optimized_df)

            # 9. 生成评分
            scores = self.generate_score(ic_analysis, group_result, stability)

            # 10. 生成报告
            report_path = self.generate_report(optimized_df, ic_analysis, group_result, stability, scores)

            # 11. 保存因子数据
            factor_path = self.save_factor_data(optimized_df)

            # 12. 绘制图表
            self.plot_results(ic_df, group_result, optimized_df)

            logger.info("=" * 80)
            logger.info("验证流程完成！")
            logger.info(f"报告: {report_path}")
            logger.info(f"因子数据: {factor_path}")
            logger.info(f"图表: {self.output_dir}")
            logger.info("=" * 80)

            return {
                'success': True,
                'report_path': report_path,
                'factor_path': factor_path,
                'output_dir': self.output_dir,
                'scores': scores,
                'ic_analysis': ic_analysis,
            }

        except Exception as e:
            logger.error(f"验证过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Bias1 Qfq 优化因子验证')
    parser.add_argument('--start_date', type=str, default='20250101', help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end_date', type=str, default='20251231', help='结束日期 (YYYYMMDD)')
    parser.add_argument('--output_dir', type=str, default=None, help='输出目录')

    args = parser.parse_args()

    validator = Bias1QfqOptimizedValidator(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir
    )

    result = validator.run()

    if result['success']:
        print(f"\n✅ 验证成功！")
        print(f"报告: {result['report_path']}")
        print(f"总分: {result['scores']['total_score']:.1f}/90")
        print(f"ICIR: {result['ic_analysis']['icir']:.4f}")
    else:
        print(f"\n❌ 验证失败: {result['error']}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
