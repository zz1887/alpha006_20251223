"""
文件input(依赖外部什么): core.utils, pandas, numpy, matplotlib, seaborn
文件output(提供什么): bias1_qfq因子有效性验证脚本
文件pos(系统局部地位): 测试验证层，提供因子质量评估和有效性验证
文件功能:
    1. 因子数据质量检查（完整性、异常值、分布）
    2. 分组收益分析（验证因子单调性）
    3. IC/ICIR计算（信息系数和信息比率）
    4. 因子稳定性分析（时间序列稳定性）
    5. 相关性分析（与其他因子对比）
    6. 可视化图表生成

使用示例:
    python verify_bias1_qfq.py --start_date 20240101 --end_date 20241231

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


class Bias1QfqValidator:
    """Bias1 Qfq 因子验证器"""

    def __init__(self, start_date: str, end_date: str, output_dir: str = None):
        """
        初始化验证器

        Args:
            start_date: 开始日期
            end_date: 结束日期
            output_dir: 输出目录
        """
        self.start_date = start_date
        self.end_date = end_date
        self.output_dir = output_dir or f"/home/zcy/alpha因子库/results/bias1_qfq/validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.db = DBConnection(DATABASE_CONFIG)
        self.data_loader = DataLoader()

        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(f"初始化验证器: {start_date} ~ {end_date}")
        logger.info(f"输出目录: {self.output_dir}")

    def extract_factor_data(self) -> pd.DataFrame:
        """提取因子数据"""
        logger.info("\n" + "=" * 60)
        logger.info("步骤1: 提取bias1_qfq因子数据")
        logger.info("=" * 60)

        query = f"""
        SELECT
            ts_code,
            trade_date,
            bias1_qfq
        FROM stock_database.stk_factor_pro
        WHERE bias1_qfq IS NOT NULL
            AND trade_date >= '{self.start_date}'
            AND trade_date <= '{self.end_date}'
        ORDER BY trade_date, ts_code
        """

        result = self.db.execute_query(query)
        factor_df = pd.DataFrame(result)
        if len(factor_df) > 0:
            factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'], format='%Y%m%d')

        logger.info(f"获取数据: {len(factor_df):,} 条记录")
        logger.info(f"股票数量: {factor_df['ts_code'].nunique()}")
        logger.info(f"日期数量: {factor_df['trade_date'].nunique()}")

        return factor_df

    def extract_price_data(self, stocks: List[str]) -> pd.DataFrame:
        """提取价格数据"""
        logger.info("\n提取价格数据...")

        price_df = self.data_loader.get_price_data(
            stocks,
            self.start_date,
            self.end_date,
            columns=['close']
        )

        logger.info(f"价格数据: {len(price_df):,} 条记录")

        return price_df

    def check_data_quality(self, factor_df: pd.DataFrame) -> Dict:
        """
        检查数据质量

        Returns:
            质量检查结果字典
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤2: 数据质量检查")
        logger.info("=" * 60)

        results = {}

        # 1. 完整性检查
        total_records = len(factor_df)
        missing_count = factor_df['bias1_qfq'].isnull().sum()
        valid_count = total_records - missing_count

        results['total_records'] = total_records
        results['valid_records'] = valid_count
        results['missing_ratio'] = missing_count / total_records if total_records > 0 else 0

        logger.info(f"总记录数: {total_records:,}")
        logger.info(f"有效记录数: {valid_count:,}")
        logger.info(f"缺失率: {results['missing_ratio']:.2%}")

        # 2. 异常值检查
        factor_values = factor_df['bias1_qfq'].dropna()

        results['mean'] = factor_values.mean()
        results['std'] = factor_values.std()
        results['min'] = factor_values.min()
        results['max'] = factor_values.max()
        results['median'] = factor_values.median()

        # 检查无穷值
        inf_count = np.isinf(factor_values).sum()
        results['inf_count'] = inf_count

        # 检查极端值（超过均值±5倍标准差）
        extreme_threshold = 5
        extreme_count = ((factor_values - results['mean']).abs() > extreme_threshold * results['std']).sum()
        results['extreme_ratio'] = extreme_count / len(factor_values)

        logger.info(f"\n统计特征:")
        logger.info(f"  均值: {results['mean']:.4f}")
        logger.info(f"  标准差: {results['std']:.4f}")
        logger.info(f"  中位数: {results['median']:.4f}")
        logger.info(f"  最小值: {results['min']:.4f}")
        logger.info(f"  最大值: {results['max']:.4f}")
        logger.info(f"\n异常检查:")
        logger.info(f"  无穷值: {inf_count}")
        logger.info(f"  极端值比例(>5σ): {results['extreme_ratio']:.2%}")

        # 3. 时间序列完整性
        daily_count = factor_df.groupby('trade_date').size()
        results['avg_daily_stocks'] = daily_count.mean()
        results['min_daily_stocks'] = daily_count.min()
        results['max_daily_stocks'] = daily_count.max()

        logger.info(f"\n时间序列:")
        logger.info(f"  日均股票数: {results['avg_daily_stocks']:.0f}")
        logger.info(f"  最少股票数: {results['min_daily_stocks']:.0f}")
        logger.info(f"  最多股票数: {results['max_daily_stocks']:.0f}")

        return results

    def calculate_ic_icir(self, factor_df: pd.DataFrame, price_df: pd.DataFrame) -> Dict:
        """
        计算IC和ICIR

        Args:
            factor_df: 因子数据
            price_df: 价格数据

        Returns:
            IC/ICIR结果字典
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤3: 计算IC和ICIR")
        logger.info("=" * 60)

        # 准备数据
        factor_df = factor_df.copy()
        price_df = price_df.copy()

        factor_df['trade_date_str'] = factor_df['trade_date'].astype(str)
        price_df['trade_date_str'] = price_df['trade_date'].astype(str)

        # 计算未来收益（T+1到T+20）
        trading_days = sorted(factor_df['trade_date'].unique())
        ic_records = []

        for i, trade_date in enumerate(trading_days):
            if i >= len(trading_days) - 20:  # 最后20天无法计算未来收益
                continue

            # 当日因子数据
            factor_today = factor_df[factor_df['trade_date'] == trade_date].copy()

            # 未来20天收益
            next_date = trading_days[i + 20]
            price_today = price_df[price_df['trade_date'] == trade_date][['ts_code', 'close']].set_index('ts_code')['close'].to_dict()
            price_next = price_df[price_df['trade_date'] == next_date][['ts_code', 'close']].set_index('ts_code')['close'].to_dict()

            # 计算每只股票的未来收益
            returns = []
            factors = []

            for _, row in factor_today.iterrows():
                ts_code = row['ts_code']
                if ts_code in price_today and ts_code in price_next:
                    price_t = price_today[ts_code]
                    price_n = price_next[ts_code]
                    if price_t > 0:
                        ret = (price_n - price_t) / price_t
                        returns.append(ret)
                        factors.append(row['bias1_qfq'])

            # 计算秩相关系数（IC）
            if len(factors) >= 10:  # 至少10只股票
                ic = np.corrcoef(factors, returns)[0, 1] if len(factors) > 1 else np.nan

                ic_records.append({
                    'trade_date': trade_date,
                    'ic': ic,
                    'n_stocks': len(factors)
                })

        if not ic_records:
            logger.warning("无法计算IC，数据不足")
            return {}

        ic_df = pd.DataFrame(ic_records)

        # 计算统计量
        ic_mean = ic_df['ic'].mean()
        ic_std = ic_df['ic'].std()
        icir = ic_mean / ic_std if ic_std > 0 else 0

        # 正IC比例
        positive_ic_ratio = (ic_df['ic'] > 0).mean()

        # IC稳定性（滚动标准差）
        if len(ic_df) >= 20:
            rolling_std = ic_df['ic'].rolling(20).std()
            ic_stability = rolling_std.mean()
        else:
            ic_stability = np.nan

        results = {
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'icir': icir,
            'positive_ic_ratio': positive_ic_ratio,
            'ic_stability': ic_stability,
            'ic_series': ic_df,
            'total_months': len(ic_df)
        }

        logger.info(f"\nIC统计:")
        logger.info(f"  IC均值: {ic_mean:.4f}")
        logger.info(f"  IC标准差: {ic_std:.4f}")
        logger.info(f"  ICIR: {icir:.4f}")
        logger.info(f"  正IC比例: {positive_ic_ratio:.2%}")
        logger.info(f"  IC稳定性: {ic_stability:.4f}")
        logger.info(f"  样本数: {len(ic_df)}")

        return results

    def analyze_group_returns(self, factor_df: pd.DataFrame, price_df: pd.DataFrame, n_groups: int = 5) -> Dict:
        """
        分组收益分析

        Args:
            factor_df: 因子数据
            price_df: 价格数据
            n_groups: 分组数量

        Returns:
            分组分析结果
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤4: 分组收益分析")
        logger.info("=" * 60)

        # 准备数据
        factor_df = factor_df.copy()
        price_df = price_df.copy()

        price_index = price_df.set_index(['ts_code', 'trade_date'])['close'].to_dict()

        trading_days = sorted(factor_df['trade_date'].unique())
        group_records = []

        for i, trade_date in enumerate(trading_days):
            if i >= len(trading_days) - 20:
                continue

            # 当日因子数据
            factor_today = factor_df[factor_df['trade_date'] == trade_date].copy()

            if len(factor_today) < 20:  # 股票数太少
                continue

            # 分组（按因子值等分）
            try:
                factor_today['group'] = pd.qcut(factor_today['bias1_qfq'], n_groups, labels=False, duplicates='drop')
            except:
                continue

            # 计算下一期收益（T+20）
            next_date = trading_days[i + 20]

            for group in range(n_groups):
                group_stocks = factor_today[factor_today['group'] == group]['ts_code'].tolist()

                if len(group_stocks) == 0:
                    continue

                # 计算组内平均收益
                group_returns = []
                for ts_code in group_stocks:
                    price_key_current = (ts_code, trade_date)
                    price_key_next = (ts_code, next_date)

                    if price_key_current in price_index and price_key_next in price_index:
                        price_current = price_index[price_key_current]
                        price_next = price_index[price_key_next]

                        if price_current > 0:
                            ret = (price_next - price_current) / price_current
                            group_returns.append(ret)

                if group_returns:
                    avg_return = np.mean(group_returns)
                    group_records.append({
                        'date': trade_date,
                        'group': group,
                        'return': avg_return,
                        'n_stocks': len(group_returns)
                    })

        if not group_records:
            logger.warning("无法进行分组分析，数据不足")
            return {}

        group_df = pd.DataFrame(group_records)

        # 分组统计
        group_summary = group_df.groupby('group').agg({
            'return': ['mean', 'std', 'count'],
            'n_stocks': 'mean'
        }).round(4)

        group_summary.columns = ['平均收益', '收益标准差', '样本数', '平均股票数']
        group_summary.index.name = '分组'

        logger.info(f"\n分组收益统计:")
        logger.info(group_summary.to_string())

        # 计算分组差异（高分组 - 低分组）
        high_group = group_df[group_df['group'] == n_groups - 1]['return'].mean()
        low_group = group_df[group_df['group'] == 0]['return'].mean()
        group_spread = high_group - low_group

        logger.info(f"\n分组差异:")
        logger.info(f"  高分组({n_groups-1})平均收益: {high_group:.4f}")
        logger.info(f"  低分组(0)平均收益: {low_group:.4f}")
        logger.info(f"  分组差异: {group_spread:.4f}")

        # 检查单调性
        group_means = group_df.groupby('group')['return'].mean().values
        is_monotonic = all(group_means[i] <= group_means[i+1] for i in range(len(group_means)-1))

        logger.info(f"  单调性: {'✅ 通过' if is_monotonic else '❌ 未通过'}")

        return {
            'group_df': group_df,
            'group_summary': group_summary,
            'group_spread': group_spread,
            'is_monotonic': is_monotonic,
            'high_group_return': high_group,
            'low_group_return': low_group
        }

    def analyze_factor_stability(self, factor_df: pd.DataFrame) -> Dict:
        """
        因子稳定性分析

        Args:
            factor_df: 因子数据

        Returns:
            稳定性分析结果
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤5: 因子稳定性分析")
        logger.info("=" * 60)

        # 按日期计算因子统计
        daily_stats = factor_df.groupby('trade_date')['bias1_qfq'].agg(['mean', 'std', 'median']).reset_index()

        # 计算时间序列统计
        mean_volatility = daily_stats['mean'].std()
        median_volatility = daily_stats['median'].std()

        # 计算因子值的截面稳定性（每日因子值的标准差）
        cross_sectional_std = factor_df.groupby('trade_date')['bias1_qfq'].std().mean()

        # 计算自相关性（相邻日期因子值的相关性）
        # 这里简化处理，计算每日均值的自相关
        if len(daily_stats) >= 2:
            autocorr = daily_stats['mean'].autocorr(lag=1)
        else:
            autocorr = np.nan

        logger.info(f"\n稳定性指标:")
        logger.info(f"  均值波动率: {mean_volatility:.4f}")
        logger.info(f"  中位数波动率: {median_volatility:.4f}")
        logger.info(f"  截面标准差: {cross_sectional_std:.4f}")
        logger.info(f"  一阶自相关: {autocorr:.4f}")

        results = {
            'mean_volatility': mean_volatility,
            'median_volatility': median_volatility,
            'cross_sectional_std': cross_sectional_std,
            'autocorr': autocorr,
            'daily_stats': daily_stats
        }

        return results

    def generate_visualizations(self, factor_df: pd.DataFrame, ic_results: Dict, group_results: Dict, stability_results: Dict):
        """
        生成可视化图表

        Args:
            factor_df: 因子数据
            ic_results: IC结果
            group_results: 分组结果
            stability_results: 稳定性结果
        """
        if not PLOTTING_AVAILABLE:
            logger.warning("绘图库不可用，跳过图表生成")
            return

        logger.info("\n" + "=" * 60)
        logger.info("步骤6: 生成可视化图表")
        logger.info("=" * 60)

        plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

        # 1. 因子值分布图
        plt.figure(figsize=(12, 5))

        plt.subplot(1, 2, 1)
        factor_values = factor_df['bias1_qfq'].dropna()
        plt.hist(factor_values, bins=50, alpha=0.7, edgecolor='black')
        plt.title('Bias1 Qfq 因子值分布')
        plt.xlabel('因子值')
        plt.ylabel('频数')
        plt.grid(True, alpha=0.3)

        plt.subplot(1, 2, 2)
        factor_values.plot.box(vert=False)
        plt.title('因子值箱线图')
        plt.xlabel('因子值')
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/factor_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()

        # 2. IC时间序列图
        if 'ic_series' in ic_results:
            plt.figure(figsize=(14, 6))
            ic_df = ic_results['ic_series']

            plt.plot(ic_df['trade_date'], ic_df['ic'], alpha=0.7, linewidth=1)
            plt.axhline(y=0, color='red', linestyle='--', alpha=0.5)
            plt.axhline(y=ic_results['ic_mean'], color='green', linestyle='--', alpha=0.7, label=f'均值={ic_results["ic_mean"]:.4f}')

            plt.title('IC时间序列')
            plt.xlabel('日期')
            plt.ylabel('IC')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)

            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/ic_timeseries.png", dpi=300, bbox_inches='tight')
            plt.close()

        # 3. 分组收益图
        if 'group_df' in group_results:
            plt.figure(figsize=(12, 6))

            group_means = group_results['group_df'].groupby('group')['return'].mean()
            plt.bar(range(len(group_means)), group_means.values, color='steelblue', alpha=0.8)
            plt.axhline(y=0, color='red', linestyle='--', alpha=0.5)

            plt.title('分组平均收益')
            plt.xlabel('分组（0=低因子值，4=高因子值）')
            plt.ylabel('平均收益')
            plt.grid(True, alpha=0.3, axis='y')

            for i, v in enumerate(group_means.values):
                plt.text(i, v + 0.001 if v >= 0 else v - 0.002, f'{v:.4f}', ha='center', va='bottom' if v >= 0 else 'top')

            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/group_returns.png", dpi=300, bbox_inches='tight')
            plt.close()

        # 4. 因子均值时间序列
        if 'daily_stats' in stability_results:
            plt.figure(figsize=(14, 6))

            daily_stats = stability_results['daily_stats']
            plt.plot(daily_stats['trade_date'], daily_stats['mean'], label='均值', linewidth=2)
            plt.plot(daily_stats['trade_date'], daily_stats['median'], label='中位数', linewidth=1, alpha=0.7)
            plt.fill_between(daily_stats['trade_date'],
                           daily_stats['mean'] - daily_stats['std'],
                           daily_stats['mean'] + daily_stats['std'],
                           alpha=0.3, label='均值±标准差')

            plt.title('因子均值时间序列')
            plt.xlabel('日期')
            plt.ylabel('因子值')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)

            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/factor_timeseries.png", dpi=300, bbox_inches='tight')
            plt.close()

        logger.info(f"图表已保存到: {self.output_dir}")

    def generate_report(self, quality_results: Dict, ic_results: Dict, group_results: Dict, stability_results: Dict):
        """
        生成验证报告

        Args:
            quality_results: 质量检查结果
            ic_results: IC结果
            group_results: 分组结果
            stability_results: 稳定性结果
        """
        logger.info("\n" + "=" * 60)
        logger.info("生成验证报告")
        logger.info("=" * 60)

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("Bias1 Qfq 因子有效性验证报告")
        report_lines.append("=" * 80)
        report_lines.append(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"时间范围: {self.start_date} ~ {self.end_date}")
        report_lines.append("")

        # 1. 数据质量
        report_lines.append("一、数据质量检查")
        report_lines.append("-" * 40)
        report_lines.append(f"总记录数: {quality_results['total_records']:,}")
        report_lines.append(f"有效记录数: {quality_results['valid_records']:,}")
        report_lines.append(f"缺失率: {quality_results['missing_ratio']:.2%}")
        report_lines.append(f"无穷值: {quality_results['inf_count']}")
        report_lines.append(f"极端值比例: {quality_results['extreme_ratio']:.2%}")
        report_lines.append(f"日均股票数: {quality_results['avg_daily_stocks']:.0f}")
        report_lines.append("")

        # 2. IC/ICIR
        report_lines.append("二、信息系数(IC)分析")
        report_lines.append("-" * 40)
        if ic_results:
            report_lines.append(f"IC均值: {ic_results['ic_mean']:.4f}")
            report_lines.append(f"IC标准差: {ic_results['ic_std']:.4f}")
            report_lines.append(f"ICIR: {ic_results['icir']:.4f}")
            report_lines.append(f"正IC比例: {ic_results['positive_ic_ratio']:.2%}")
            report_lines.append(f"IC稳定性: {ic_results['ic_stability']:.4f}")
            report_lines.append(f"样本数: {ic_results['total_months']}")
            report_lines.append("")
            report_lines.append("有效性判断:")
            if ic_results['icir'] > 0.3:
                report_lines.append("  ✅ ICIR > 0.3，因子优秀")
            elif ic_results['icir'] > 0.2:
                report_lines.append("  ⚠️  ICIR > 0.2，因子良好")
            elif ic_results['icir'] > 0.1:
                report_lines.append("  ⚠️  ICIR > 0.1，因子一般")
            else:
                report_lines.append("  ❌ ICIR <= 0.1，因子无效")
        else:
            report_lines.append("  ❌ 无法计算IC")
        report_lines.append("")

        # 3. 分组收益
        report_lines.append("三、分组收益分析")
        report_lines.append("-" * 40)
        if group_results:
            report_lines.append(f"分组差异(高-低): {group_results['group_spread']:.4f}")
            report_lines.append(f"单调性: {'✅ 通过' if group_results['is_monotonic'] else '❌ 未通过'}")
            report_lines.append(f"高分组收益: {group_results['high_group_return']:.4f}")
            report_lines.append(f"低分组收益: {group_results['low_group_return']:.4f}")
            report_lines.append("")
            report_lines.append("有效性判断:")
            if group_results['is_monotonic'] and group_results['group_spread'] > 0.01:
                report_lines.append("  ✅ 因子具有良好的单调性和区分度")
            elif group_results['group_spread'] > 0.005:
                report_lines.append("  ⚠️  因子有一定区分度，但单调性不足")
            else:
                report_lines.append("  ❌ 因子区分度不足")
        else:
            report_lines.append("  ❌ 无法进行分组分析")
        report_lines.append("")

        # 4. 稳定性
        report_lines.append("四、因子稳定性")
        report_lines.append("-" * 40)
        if stability_results:
            report_lines.append(f"均值波动率: {stability_results['mean_volatility']:.4f}")
            report_lines.append(f"截面标准差: {stability_results['cross_sectional_std']:.4f}")
            report_lines.append(f"一阶自相关: {stability_results['autocorr']:.4f}")
            report_lines.append("")
            report_lines.append("稳定性判断:")
            if stability_results['autocorr'] > 0.5:
                report_lines.append("  ✅ 自相关性高，因子稳定")
            elif stability_results['autocorr'] > 0.3:
                report_lines.append("  ⚠️  自相关性中等")
            else:
                report_lines.append("  ⚠️  自相关性低，因子可能不稳定")
        else:
            report_lines.append("  ❌ 无法进行稳定性分析")
        report_lines.append("")

        # 5. 综合评价
        report_lines.append("五、综合评价")
        report_lines.append("-" * 40)

        score = 0
        if ic_results and ic_results['icir'] > 0.3:
            score += 40
        elif ic_results and ic_results['icir'] > 0.2:
            score += 30
        elif ic_results and ic_results['icir'] > 0.1:
            score += 20

        if group_results and group_results['is_monotonic'] and group_results['group_spread'] > 0.01:
            score += 30
        elif group_results and group_results['group_spread'] > 0.005:
            score += 20

        if stability_results and stability_results['autocorr'] > 0.5:
            score += 20
        elif stability_results and stability_results['autocorr'] > 0.3:
            score += 15

        report_lines.append(f"综合评分: {score}/90")

        if score >= 70:
            report_lines.append("结论: ✅ 优秀因子，建议使用")
        elif score >= 50:
            report_lines.append("结论: ⚠️  良好因子，可优化后使用")
        elif score >= 30:
            report_lines.append("结论: ⚠️  一般因子，需进一步验证")
        else:
            report_lines.append("结论: ❌ 因子无效，不建议使用")

        report_lines.append("")
        report_lines.append("=" * 80)

        # 保存报告
        report_text = "\n".join(report_lines)
        report_file = f"{self.output_dir}/validation_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)

        logger.info(f"\n验证报告已保存: {report_file}")
        logger.info("\n" + report_text)

        return report_text

    def run(self):
        """运行完整验证流程"""
        try:
            # 1. 提取数据
            factor_df = self.extract_factor_data()
            if len(factor_df) == 0:
                raise ValueError("未获取到因子数据")

            # 2. 数据质量检查
            quality_results = self.check_data_quality(factor_df)

            # 3. 获取价格数据
            stocks = factor_df['ts_code'].unique().tolist()
            price_df = self.extract_price_data(stocks)

            # 4. IC/ICIR计算
            ic_results = self.calculate_ic_icir(factor_df, price_df)

            # 5. 分组收益分析
            group_results = self.analyze_group_returns(factor_df, price_df)

            # 6. 稳定性分析
            stability_results = self.analyze_factor_stability(factor_df)

            # 7. 生成图表
            self.generate_visualizations(factor_df, ic_results, group_results, stability_results)

            # 8. 生成报告
            report = self.generate_report(quality_results, ic_results, group_results, stability_results)

            logger.info("\n" + "=" * 80)
            logger.info("验证完成！")
            logger.info("=" * 80)
            logger.info(f"结果保存在: {self.output_dir}")

            return {
                'quality': quality_results,
                'ic': ic_results,
                'group': group_results,
                'stability': stability_results,
                'report': report
            }

        except Exception as e:
            logger.error(f"验证失败: {e}")
            raise


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Bias1 Qfq 因子有效性验证")
    print("=" * 80)

    parser = argparse.ArgumentParser(description='Bias1 Qfq 因子验证')
    parser.add_argument('--start_date', type=str, default='20240101', help='开始日期')
    parser.add_argument('--end_date', type=str, default='20241231', help='结束日期')
    parser.add_argument('--output_dir', type=str, default=None, help='输出目录')

    args = parser.parse_args()

    # 创建验证器
    validator = Bias1QfqValidator(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir
    )

    # 运行验证
    results = validator.run()

    print("\n" + "=" * 80)
    print("验证完成！")
    print("=" * 80)
    print(f"结果保存在: {validator.output_dir}")


if __name__ == "__main__":
    main()
