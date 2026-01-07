"""
策略3综合得分计算脚本
版本: v2.0
更新日期: 2025-12-30

功能:
- 计算指定日期的策略3综合得分
- 支持多版本参数配置
- 输出Excel和统计报告
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import argparse
import logging

# 设置路径
sys.path.insert(0, '/home/zcy/alpha006_20251223')

# 导入核心模块
from core.config.params import get_factor_param, get_strategy_param
from core.config.settings import OUTPUT_CONFIG
from core.utils.db_connection import db
from core.utils.data_loader import data_loader
from factors import (
    create_alpha_peg,
    create_alpha_pluse,
    create_alpha_038,
    create_alpha_120cq,
    create_cr_qfq
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Strategy3Calculator:
    """策略3综合得分计算器"""

    def __init__(self, target_date: str, version: str = 'standard'):
        """
        初始化

        Args:
            target_date: 目标日期 (YYYYMMDD)
            version: 策略版本 ('standard', 'conservative', 'aggressive')
        """
        self.target_date = target_date
        self.target_date_dt = pd.to_datetime(target_date, format='%Y%m%d')
        self.version = version
        self.nan_reasons = {}

        # 加载策略配置
        self.strategy_config = get_strategy_param('strategy3', version)

        logger.info(f"初始化策略3计算器 - 日期: {target_date}, 版本: {version}")

    def get_tradable_stocks(self) -> list:
        """获取可交易股票"""
        logger.info("步骤1: 获取可交易股票")

        stocks = data_loader.get_tradable_stocks(self.target_date)
        if not stocks:
            raise ValueError("当日无有效股票")

        logger.info(f"有效股票: {len(stocks)}只")
        return stocks

    def get_trading_days_needed(self) -> list:
        """获取需要的交易日范围"""
        logger.info("步骤2: 获取交易日范围")

        # 根据各因子需求计算最大回溯天数
        max_lookback = 150  # alpha_120cq需要约120天 + 缓冲

        end_date = self.target_date_dt
        start_date = end_date - pd.Timedelta(days=max_lookback)

        trading_days = data_loader.get_trading_days(
            start_date.strftime('%Y%m%d'),
            self.target_date
        )

        logger.info(f"交易日范围: {len(trading_days)}天")
        return trading_days

    def calculate_all_factors(self, stocks: list, trading_days: list) -> pd.DataFrame:
        """计算所有因子"""
        logger.info("步骤3: 计算各因子")

        # 1. alpha_pluse - 量能因子
        logger.info("  计算alpha_pluse...")
        price_df = data_loader.get_price_data(stocks, trading_days[0], self.target_date)
        alpha_pluse_factor = create_alpha_pluse(self.version)
        df_pluse = alpha_pluse_factor.calculate_by_period(trading_days[0], self.target_date, self.target_date)

        # 2. alpha_peg - 估值因子
        logger.info("  计算alpha_peg...")
        alpha_peg_factor = create_alpha_peg(self.version)
        df_peg = alpha_peg_factor.calculate_by_period(trading_days[0], self.target_date, self.target_date)

        # 3. alpha_peg行业标准化
        logger.info("  计算alpha_peg行业标准化...")
        df_industry = data_loader.get_industry_data(stocks)
        df_peg_zscore = alpha_peg_factor.calculate_industry_zscore(df_peg, df_industry)

        # 4. alpha_038 - 价格强度因子
        logger.info("  计算alpha_038...")
        alpha_038_factor = create_alpha_038(self.version)
        df_alpha038 = alpha_038_factor.calculate_by_period(trading_days[0], self.target_date, self.target_date)

        # 5. alpha_120cq - 价格位置因子
        logger.info("  计算alpha_120cq...")
        alpha_120cq_factor = create_alpha_120cq(self.version)
        df_alpha120cq = alpha_120cq_factor.calculate_by_period(trading_days[0], self.target_date, self.target_date)

        # 6. cr_qfq - 动量因子
        logger.info("  获取cr_qfq...")
        cr_qfq_factor = create_cr_qfq(self.version)
        df_cr = cr_qfq_factor.calculate_by_period(self.target_date, stocks)

        return df_pluse, df_peg_zscore, df_alpha038, df_alpha120cq, df_cr

    def merge_factors(self, df_pluse, df_peg_zscore, df_alpha038, df_alpha120cq, df_cr) -> pd.DataFrame:
        """合并所有因子"""
        logger.info("步骤4: 合并因子")

        # 以alpha_peg_zscore为基础
        if len(df_peg_zscore) == 0:
            raise ValueError("无alpha_peg数据，无法合并")

        df_final = df_peg_zscore[['ts_code', 'l1_name', 'alpha_peg_raw', 'alpha_peg_zscore']].copy()

        # 合并各因子
        factor_dfs = {
            'alpha_pluse': df_pluse,
            'alpha_120cq': df_alpha120cq,
            'cr_qfq': df_cr,
            'alpha_038': df_alpha038,
        }

        for name, df in factor_dfs.items():
            if len(df) > 0:
                df_final = df_final.merge(df, on='ts_code', how='left')
                logger.info(f"  合并{name}: {len(df)}条")
            else:
                df_final[name] = np.nan
                logger.warning(f"  {name}为空")

        # 添加交易日
        df_final['trade_date'] = self.target_date

        return df_final

    def calculate_comprehensive_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算策略3综合得分"""
        logger.info("步骤5: 计算综合得分")

        df_result = df.copy()

        # 确保所有因子都是数值型
        for col in ['alpha_pluse', 'alpha_peg_zscore', 'alpha_120cq', 'cr_qfq', 'alpha_038']:
            if col in df_result.columns:
                df_result[col] = pd.to_numeric(df_result[col], errors='coerce')

        # 填充缺失值
        df_result['alpha_pluse'] = df_result['alpha_pluse'].fillna(0)
        df_result['alpha_peg_zscore'] = df_result['alpha_peg_zscore'].fillna(9999)
        df_result['alpha_120cq'] = df_result['alpha_120cq'].fillna(0)
        df_result['cr_qfq'] = df_result['cr_qfq'].fillna(-9999)
        df_result['alpha_038'] = df_result['alpha_038'].fillna(0)

        # 获取权重配置
        weights = self.strategy_config['weights']

        # 计算各因子标准化值
        # 1. alpha_pluse: 1 - alpha_pluse (反向)
        factor_1 = 1 - df_result['alpha_pluse']

        # 2. alpha_peg_zscore: -alpha_peg_zscore (负向)
        factor_2 = -df_result['alpha_peg_zscore']

        # 3. alpha_120cq: 直接使用 (正向)
        factor_3 = df_result['alpha_120cq']

        # 4. cr_qfq: 标准化 (除以最大值)
        cr_max = df_result['cr_qfq'].max()
        factor_4 = df_result['cr_qfq'] / cr_max if cr_max > 0 else 0

        # 5. alpha_038: 标准化 (负向，除以最小值)
        alpha_038_min = df_result['alpha_038'].min()
        factor_5 = -df_result['alpha_038'] / alpha_038_min if alpha_038_min < 0 else 0

        # 计算综合得分
        df_result['综合得分'] = (
            weights['alpha_pluse'] * factor_1 +
            weights['alpha_peg_zscore'] * factor_2 +
            weights['alpha_120cq'] * factor_3 +
            weights['cr_qfq'] * factor_4 +
            weights['alpha_038'] * factor_5
        )

        # 添加因子明细
        df_result['因子1_量能'] = factor_1
        df_result['因子2_估值'] = factor_2
        df_result['因子3_位置'] = factor_3
        df_result['因子4_动量'] = factor_4
        df_result['因子5_强度'] = factor_5

        # 添加备注
        df_result['备注'] = df_result['ts_code'].map(self.nan_reasons).fillna('')

        logger.info(f"综合得分计算完成，范围: {df_result['综合得分'].min():.4f} ~ {df_result['综合得分'].max():.4f}")

        return df_result

    def export_results(self, df_final: pd.DataFrame):
        """导出结果"""
        logger.info("步骤6: 导出结果")

        output_dir = '/home/zcy/alpha006_20251223/results/output'
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 选择输出列
        output_columns = [
            '股票代码', '交易日', '申万一级行业',
            'alpha_pluse', '行业标准化alpha_peg', 'alpha_120cq', 'cr_qfq', 'alpha_038',
            '综合得分',
            '因子1_量能', '因子2_估值', '因子3_位置', '因子4_动量', '因子5_强度',
            '备注'
        ]

        # 重命名列
        df_output = df_final.copy()
        df_output.rename(columns={
            'ts_code': '股票代码',
            'trade_date': '交易日',
            'l1_name': '申万一级行业',
            'alpha_peg_zscore': '行业标准化alpha_peg',
        }, inplace=True)

        # 确保所有列都存在
        for col in output_columns:
            if col not in df_output.columns:
                df_output[col] = ''

        df_export = df_output[output_columns].copy()

        # 格式化
        df_export['交易日'] = df_export['交易日'].astype(str)
        numeric_cols = ['alpha_pluse', '行业标准化alpha_peg', 'alpha_120cq', 'cr_qfq', 'alpha_038',
                       '综合得分', '因子1_量能', '因子2_估值', '因子3_位置', '因子4_动量', '因子5_强度']
        for col in numeric_cols:
            df_export[col] = pd.to_numeric(df_export[col], errors='coerce').round(4)

        # 排序
        df_export = df_export.sort_values('综合得分', ascending=False)

        # 保存完整文件
        full_path = os.path.join(output_dir, f'strategy3_comprehensive_scores_{timestamp}.xlsx')
        df_export.to_excel(full_path, index=False)
        logger.info(f"完整结果已保存: {full_path}")

        # 保存前100名
        top100_path = os.path.join(output_dir, f'strategy3_top100_{timestamp}.xlsx')
        df_export.head(100).to_excel(top100_path, index=False)
        logger.info(f"前100名已保存: {top100_path}")

        # 保存统计摘要
        summary_path = os.path.join(output_dir, f'strategy3_summary_{timestamp}.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"策略3综合得分计算 - {self.target_date}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"数据日期: {self.target_date}\n")
            f.write(f"策略版本: {self.version}\n")
            f.write(f"计算时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("数据统计:\n")
            f.write(f"  总股票数: {len(df_export)}\n")
            f.write(f"  有效数据: {df_export['综合得分'].notna().sum()}\n")
            f.write(f"  缺失数据: {df_export['综合得分'].isna().sum()}\n\n")

            f.write("综合得分统计:\n")
            stats = df_export['综合得分'].describe()
            for key, value in stats.items():
                f.write(f"  {key}: {value:.4f}\n")

            f.write("\n前10名股票:\n")
            top10 = df_export.head(10)[['股票代码', '申万一级行业', '综合得分', 'alpha_pluse', '行业标准化alpha_peg', 'alpha_120cq', 'cr_qfq', 'alpha_038']]
            f.write(top10.to_string())

        logger.info(f"统计摘要已保存: {summary_path}")

        return full_path, top100_path, summary_path

    def print_summary(self, df_final: pd.DataFrame):
        """打印执行总结"""
        print("\n" + "=" * 80)
        print("执行总结")
        print("=" * 80)

        print(f"\n📊 数据统计:")
        print(f"  目标日期: {self.target_date}")
        print(f"  策略版本: {self.version}")
        print(f"  总记录数: {len(df_final)}")
        print(f"  有效记录: {df_final['综合得分'].notna().sum()}")
        print(f"  缺失记录: {df_final['综合得分'].isna().sum()}")

        if df_final['综合得分'].notna().sum() > 0:
            print(f"\n📈 综合得分统计:")
            valid_data = df_final['综合得分'].dropna()
            print(f"  均值: {valid_data.mean():.4f}")
            print(f"  标准差: {valid_data.std():.4f}")
            print(f"  最小值: {valid_data.min():.4f}")
            print(f"  最大值: {valid_data.max():.4f}")
            print(f"  中位数: {valid_data.median():.4f}")

        print(f"\n📝 前10名优质个股:")
        top10 = df_final[df_final['综合得分'].notna()].nlargest(10, '综合得分')
        for _, row in top10.iterrows():
            print(f"  {row['ts_code']}  {row['l1_name']:<8} 得分={row['综合得分']:.4f}")

        if len(self.nan_reasons) > 0:
            from collections import Counter
            reason_counts = Counter(self.nan_reasons.values())
            print(f"\n⚠️  数据缺失原因:")
            for reason, count in reason_counts.most_common():
                print(f"  {reason}: {count}只")

    def run(self):
        """主执行流程"""
        print("\n" + "=" * 80)
        print("策略3综合得分计算")
        print("=" * 80)
        print(f"日期: {self.target_date}")
        print(f"版本: {self.version}")
        print(f"权重: {self.strategy_config['weights']}")
        print("=" * 80)

        start_time = datetime.now()

        try:
            # 1. 获取可交易股票
            stocks = self.get_tradable_stocks()
            if not stocks:
                return

            # 2. 获取交易日
            trading_days = self.get_trading_days_needed()

            # 3. 计算各因子
            df_pluse, df_peg_zscore, df_alpha038, df_alpha120cq, df_cr = self.calculate_all_factors(stocks, trading_days)

            # 4. 合并因子
            df_merged = self.merge_factors(df_pluse, df_peg_zscore, df_alpha038, df_alpha120cq, df_cr)

            # 5. 计算综合得分
            df_final = self.calculate_comprehensive_score(df_merged)

            # 6. 导出结果
            self.export_results(df_final)

            # 7. 打印总结
            self.print_summary(df_final)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print(f"\n⏱️  执行耗时: {duration:.2f} 秒")
            print("\n✅ 任务完成！")

        except Exception as e:
            logger.error(f"执行失败: {e}")
            raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='策略3综合得分计算')
    parser.add_argument('--date', type=str, required=True, help='目标日期 (YYYYMMDD)')
    parser.add_argument('--version', type=str, default='standard',
                       choices=['standard', 'conservative', 'aggressive'],
                       help='策略版本')

    args = parser.parse_args()

    calculator = Strategy3Calculator(args.date, args.version)
    calculator.run()


if __name__ == '__main__':
    main()