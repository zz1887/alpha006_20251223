"""
文件input(依赖外部什么): pandas, numpy, factors.evaluation, factors.core.factor_registry
文件output(提供什么): FactorEvaluation类，提供因子完整评估流程和多版本对比
文件pos(系统局部地位): 评估层，用于因子质量评估和版本优化
文件功能:
    1. 单版本因子评估（IC/ICIR/分组回测/稳定性）
    2. 多版本对比分析
    3. 参数敏感性分析
    4. 评估报告生成
    5. 结果可视化和保存

使用示例:
    from factors.templates.evaluation_template import FactorEvaluation

    # 创建评估器
    evaluator = FactorEvaluation('alpha_peg', version='standard')

    # 单版本评估
    result = evaluator.run_evaluation(
        start_date='20240101',
        end_date='20240331',
        hold_days=20,
        n_groups=5
    )

    # 多版本对比
    comparison = evaluator.compare_versions(
        versions=['standard', 'conservative', 'aggressive'],
        start_date='20240101',
        end_date='20240331'
    )

    # 敏感性分析
    sensitivity = evaluator.sensitivity_analysis(
        param_name='outlier_sigma',
        param_values=[2.0, 2.5, 3.0, 3.5, 4.0],
        start_date='20240101',
        end_date='20240331'
    )

参数说明:
    factor_name: 因子名称
    version: 因子版本（standard/conservative/aggressive）
    start_date: 评估开始日期
    end_date: 评估结束日期
    hold_days: 持有天数（默认20）
    n_groups: 分组数量（默认5）
    output_path: 报告输出路径

返回值:
    Dict: 评估结果（包含metrics, summary, report_text）
    pd.DataFrame: 版本对比结果
    pd.DataFrame: 敏感性分析结果

评估指标:
    1. ICIR（信息比率）: >0.3为优秀
    2. 分组差异: >5%为有效
    3. 换手率: <30%为佳
    4. 稳定性: >70分为稳定
    5. 综合评分: 0-100分

开发步骤:
    1. 复制此文件并重命名为因子名_evaluation.py
    2. 修改FACTOR_NAME为实际因子名
    3. 修改load_data方法加载真实数据
    4. 运行main函数执行评估
    5. 根据结果调整参数或版本
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from factors.evaluation import FactorEvaluationReport
from factors.core.factor_registry import FactorRegistry


class FactorEvaluation:
    """因子评估器"""

    def __init__(self, factor_name: str, version: str = 'standard'):
        """
        初始化

        Args:
            factor_name: 因子名称
            version: 因子版本
        """
        self.factor_name = factor_name
        self.version = version
        self.report = None

    def load_data(self,
                  start_date: str,
                  end_date: str,
                  data_source: str = 'database') -> tuple:
        """
        加载数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            data_source: 数据源

        Returns:
            Tuple: (因子数据, 价格数据)
        """
        # 1. 获取因子实例
        factor = FactorRegistry.get_factor(self.factor_name, version=self.version)

        # 2. 加载原始数据（根据因子需求）
        # 示例：
        # from factors.utils.data_loader import DataLoader
        # loader = DataLoader(data_source=data_source)

        # factor_data = loader.load_finance_data(
        #     ts_codes=None,
        #     start_date=start_date,
        #     end_date=end_date,
        #     fields=['pe_ttm', 'dt_netprofit_yoy']
        # )

        # 3. 计算因子
        # factor_df = factor.calculate(factor_data)

        # 4. 加载价格数据
        # price_df = loader.load_price_data(
        #     ts_codes=None,
        #     start_date=start_date,
        #     end_date=end_date
        # )

        # 返回示例数据（实际使用时替换为真实数据）
        return self._generate_sample_data(start_date, end_date)

    def _generate_sample_data(self, start_date: str, end_date: str):
        """生成示例数据用于演示"""
        dates = pd.date_range(start_date, end_date, freq='D')
        stocks = ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ']

        # 因子数据
        factor_data = []
        price_data = []

        for date in dates:
            for stock in stocks:
                # 模拟因子值（带一定IC）
                base_factor = np.random.normal(0, 1)
                # 与未来收益相关
                future_return = base_factor * 0.1 + np.random.normal(0, 0.5)

                factor_data.append({
                    'ts_code': stock,
                    'trade_date': date,
                    'factor': base_factor
                })

                price_data.append({
                    'ts_code': stock,
                    'trade_date': date,
                    'close': 100 + np.random.uniform(-10, 10)
                })

        factor_df = pd.DataFrame(factor_data)
        price_df = pd.DataFrame(price_data)

        return factor_df, price_df

    def run_evaluation(self,
                      start_date: str,
                      end_date: str,
                      hold_days: int = 20,
                      n_groups: int = 5,
                      output_path: Optional[str] = None) -> Dict:
        """
        运行完整评估

        Args:
            start_date: 开始日期
            end_date: 结束日期
            hold_days: 持有天数
            n_groups: 分组数量
            output_path: 报告输出路径

        Returns:
            Dict: 评估结果
        """
        print(f"开始评估因子: {self.factor_name} (版本: {self.version})")
        print(f"时间范围: {start_date} 至 {end_date}")
        print(f"持有天数: {hold_days}, 分组数: {n_groups}")

        # 1. 加载数据
        factor_df, price_df = self.load_data(start_date, end_date)

        print(f"因子数据: {len(factor_df)} 条记录")
        print(f"价格数据: {len(price_df)} 条记录")

        # 2. 创建评估报告
        self.report = FactorEvaluationReport(self.factor_name)

        # 3. 运行评估
        metrics = self.report.run_full_evaluation(
            factor_df=factor_df,
            price_df=price_df,
            hold_days=hold_days,
            n_groups=n_groups
        )

        # 4. 生成文本报告
        report_text = self.report.generate_report(output_path)

        # 5. 获取摘要
        summary = self.report.get_summary()

        print("\n" + "="*60)
        print("评估完成！")
        print("="*60)

        return {
            'metrics': metrics,
            'summary': summary,
            'report_text': report_text
        }

    def compare_versions(self,
                        versions: List[str],
                        start_date: str,
                        end_date: str,
                        hold_days: int = 20) -> pd.DataFrame:
        """
        比较不同版本

        Args:
            versions: 版本列表
            start_date: 开始日期
            end_date: 结束日期
            hold_days: 持有天数

        Returns:
            pd.DataFrame: 版本对比结果
        """
        results = []

        for version in versions:
            print(f"\n评估版本: {version}")

            try:
                # 临时修改版本
                old_version = self.version
                self.version = version

                # 运行评估
                eval_result = self.run_evaluation(start_date, end_date, hold_days)

                # 提取关键指标
                summary = eval_result['summary']
                results.append({
                    '版本': version,
                    '综合评分': summary['score'],
                    'ICIR': summary['icir'],
                    '换手率': summary['turnover'],
                    '稳定性': summary['stability'],
                    '状态': summary['status'],
                })

                # 恢复版本
                self.version = old_version

            except Exception as e:
                print(f"版本{version}评估失败: {e}")
                results.append({
                    '版本': version,
                    '综合评分': 0,
                    'ICIR': 0,
                    '换手率': 0,
                    '稳定性': 0,
                    '状态': '失败',
                })

        return pd.DataFrame(results)

    def sensitivity_analysis(self,
                           param_name: str,
                           param_values: List,
                           start_date: str,
                           end_date: str) -> pd.DataFrame:
        """
        参数敏感性分析

        Args:
            param_name: 参数名
            param_values: 参数值列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 敏感性分析结果
        """
        from factors.core.factor_registry import FactorRegistry

        results = []

        for value in param_values:
            print(f"\n测试 {param_name}={value}")

            try:
                # 获取因子并设置参数
                factor = FactorRegistry.get_factor(self.factor_name, version=self.version)
                factor.params[param_name] = value

                # 计算因子
                factor_df, price_df = self.load_data(start_date, end_date)
                factor_df = factor.calculate(factor_df)

                # 评估
                report = FactorEvaluationReport(self.factor_name)
                metrics = report.run_full_evaluation(factor_df, price_df)

                results.append({
                    param_name: value,
                    'ICIR': metrics.get('ic_analysis', {}).get('icir', 0),
                    '综合评分': metrics.get('comprehensive_score', 0),
                    '分组差': metrics.get('group_analysis', {}).get('group_1_vs_5', 0),
                })

            except Exception as e:
                print(f"测试失败: {e}")

        return pd.DataFrame(results)


def main():
    """主函数：运行完整评估流程"""

    # 配置
    FACTOR_NAME = 'alpha_peg'  # 修改为你的因子名
    VERSIONS = ['standard', 'conservative', 'aggressive']
    START_DATE = '20240101'
    END_DATE = '20240331'

    # 创建评估器
    evaluator = FactorEvaluation(FACTOR_NAME, version='standard')

    # 1. 单版本评估
    print("="*60)
    print("1. 单版本评估")
    print("="*60)

    result = evaluator.run_evaluation(
        start_date=START_DATE,
        end_date=END_DATE,
        hold_days=20,
        n_groups=5,
        output_path=f'results/{FACTOR_NAME}_evaluation.txt'
    )

    # 2. 多版本对比
    print("\n" + "="*60)
    print("2. 多版本对比")
    print("="*60)

    comparison = evaluator.compare_versions(
        versions=VERSIONS,
        start_date=START_DATE,
        end_date=END_DATE
    )
    print(comparison)

    # 保存对比结果
    comparison.to_csv(f'results/{FACTOR_NAME}_version_comparison.csv', index=False)

    # 3. 敏感性分析（可选）
    print("\n" + "="*60)
    print("3. 敏感性分析")
    print("="*60)

    sensitivity = evaluator.sensitivity_analysis(
        param_name='outlier_sigma',
        param_values=[2.0, 2.5, 3.0, 3.5, 4.0],
        start_date=START_DATE,
        end_date=END_DATE
    )

    if len(sensitivity) > 0:
        print(sensitivity)
        sensitivity.to_csv(f'results/{FACTOR_NAME}_sensitivity.csv', index=False)

    print("\n" + "="*60)
    print("所有评估完成！")
    print("="*60)


if __name__ == '__main__':
    main()
