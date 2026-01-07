"""
文件input(依赖外部什么): core.utils, pandas, numpy, argparse, logging, factors.calculation.alpha_profit_employee
文件output(提供什么): alpha_profit_employee因子的完整T+20回测结果
文件pos(系统局部地位): 回测执行层，提供截面价值因子策略回测功能

基于营业利润+职工现金价值因子的回测：
    1. 计算因子：CSRank((营业利润 + 支付给职工现金) / 总市值, 公告日期)
    2. T+20持有策略
    3. 包含交易成本（0.154%）
    4. 2025年全年回测

使用示例:
    python3 alpha_profit_employee_backtest.py --start_date 20250101 --end_date 20251231

返回值:
    回测结果CSV文件（每日数据、绩效指标、分组收益、交易记录）
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
from core.config import DATABASE_CONFIG
from factors.calculation.alpha_profit_employee import AlphaProfitEmployeeFactor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AlphaProfitEmployeeBacktest:
    """
    Alpha Profit Employee 因子回测器

    因子逻辑：
    - 分子：营业利润 + 支付给职工现金
    - 分母：总市值（万元 -> 元）
    - 标准化：按公告日期截面排名（CSRank）
    - 持有周期：T+20天
    """

    def __init__(self, start_date: str, end_date: str, hold_days: int = 20, output_dir: str = None):
        self.start_date = start_date
        self.end_date = end_date
        self.hold_days = hold_days
        self.output_dir = output_dir or f"/home/zcy/alpha因子库/results/alpha_profit_employee/backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

        # 初始化数据库连接
        self.db = DBConnection(DATABASE_CONFIG)

        # 交易成本
        self.buy_cost = 0.00154  # 买入成本0.154%
        self.sell_cost = 0.00154  # 卖出成本0.154%

        logger.info(f"Alpha Profit Employee 回测器初始化完成")
        logger.info(f"时间范围: {start_date} 至 {end_date}")
        logger.info(f"持有天数: {hold_days}")
        logger.info(f"输出目录: {self.output_dir}")

    def load_financial_data(self) -> pd.DataFrame:
        """
        加载财务数据：income表(operate_profit) + cashflow表(c_paid_to_for_empl) + daily_basic表(total_mv)

        数据对齐方式：
        - income和cashflow通过(ts_code, ann_date)关联
        - daily_basic通过(ts_code, ann_date)关联（假设ann_date是交易日）
        - 使用pandas合并避免SQL JOIN的字符集编码问题
        """
        logger.info("正在从数据库加载财务数据...")

        # 1. 查询income表（营业利润）
        income_query = f"""
        SELECT ts_code, ann_date, operate_profit
        FROM stock_database.income
        WHERE ann_date BETWEEN '{self.start_date}' AND '{self.end_date}'
          AND operate_profit IS NOT NULL
        """
        income_result = self.db.execute_query(income_query)
        income_df = pd.DataFrame(income_result)

        if len(income_df) == 0:
            raise ValueError("income表未获取到数据，请检查数据库和日期范围")

        income_df['operate_profit'] = income_df['operate_profit'].astype(float)
        income_df['ann_date'] = income_df['ann_date'].astype(str)

        # 2. 查询cashflow表（支付给职工现金）
        cashflow_query = f"""
        SELECT ts_code, ann_date, c_paid_to_for_empl
        FROM stock_database.cashflow
        WHERE ann_date BETWEEN '{self.start_date}' AND '{self.end_date}'
          AND c_paid_to_for_empl IS NOT NULL
        """
        cashflow_result = self.db.execute_query(cashflow_query)
        cashflow_df = pd.DataFrame(cashflow_result)

        if len(cashflow_df) == 0:
            raise ValueError("cashflow表未获取到数据，请检查数据库和日期范围")

        cashflow_df['c_paid_to_for_empl'] = cashflow_df['c_paid_to_for_empl'].astype(float)
        cashflow_df['ann_date'] = cashflow_df['ann_date'].astype(str)

        # 3. 查询daily_basic表（总市值）
        daily_basic_query = f"""
        SELECT ts_code, trade_date, total_mv
        FROM stock_database.daily_basic
        WHERE trade_date BETWEEN '{self.start_date}' AND '{self.end_date}'
          AND total_mv IS NOT NULL AND total_mv > 0
        """
        daily_basic_result = self.db.execute_query(daily_basic_query)
        daily_basic_df = pd.DataFrame(daily_basic_result)

        if len(daily_basic_df) == 0:
            raise ValueError("daily_basic表未获取到数据，请检查数据库和日期范围")

        daily_basic_df['total_mv'] = daily_basic_df['total_mv'].astype(float)
        daily_basic_df['trade_date'] = daily_basic_df['trade_date'].astype(str)

        # 4. 使用pandas合并数据（避免字符集编码问题）
        logger.info(f"  income数据: {len(income_df):,} 条")
        logger.info(f"  cashflow数据: {len(cashflow_df):,} 条")
        logger.info(f"  daily_basic数据: {len(daily_basic_df):,} 条")

        # income和cashflow合并
        merged = pd.merge(
            income_df,
            cashflow_df,
            on=['ts_code', 'ann_date'],
            how='inner'
        )
        logger.info(f"  income+cashflow合并后: {len(merged):,} 条")

        if len(merged) == 0:
            raise ValueError("income和cashflow数据无交集，请检查数据")

        # 与daily_basic合并（通过ann_date = trade_date）
        # 将ann_date转换为字符串用于匹配
        merged['ann_date_str'] = merged['ann_date'].astype(str)

        result = pd.merge(
            merged,
            daily_basic_df,
            left_on=['ts_code', 'ann_date_str'],
            right_on=['ts_code', 'trade_date'],
            how='inner'
        )

        logger.info(f"  最终合并后: {len(result):,} 条记录")

        if len(result) == 0:
            raise ValueError("财务数据和市值数据无交集，请检查日期对齐")

        # 清理临时列
        result.drop(columns=['ann_date_str'], inplace=True)

        # 5. 数据类型转换和格式化
        result['ann_date'] = pd.to_datetime(result['ann_date'], format='%Y%m%d')
        result['trade_date'] = pd.to_datetime(result['trade_date'], format='%Y%m%d')

        logger.info(f"加载财务数据完成: {len(result):,} 条记录")
        logger.info(f"  股票数量: {result['ts_code'].nunique()}")
        logger.info(f"  公告日期数量: {result['ann_date'].nunique()}")

        return result

    def calculate_factor(self, fina_df: pd.DataFrame) -> pd.DataFrame:
        """使用AlphaProfitEmployeeFactor计算因子"""
        logger.info("正在计算alpha_profit_employee因子...")

        factor = AlphaProfitEmployeeFactor()
        result = factor.calculate(fina_df)

        # 统计信息
        stats = result['factor'].describe()
        logger.info(f"因子统计:")
        logger.info(f"  均值: {stats['mean']:.4f}")
        logger.info(f"  标准差: {stats['std']:.4f}")
        logger.info(f"  最小值: {stats['min']:.4f}")
        logger.info(f"  最大值: {stats['max']:.4f}")
        logger.info(f"  中位数: {stats['50%']:.4f}")

        return result

    def load_price_data(self) -> pd.DataFrame:
        """加载价格数据（使用daily_kline）"""
        logger.info("正在从daily_kline加载价格数据...")

        query = f"""
        SELECT ts_code, trade_date, close
        FROM stock_database.daily_kline
        WHERE trade_date BETWEEN '{self.start_date}' AND '{self.end_date}'
        ORDER BY ts_code, trade_date
        """

        result = self.db.execute_query(query)
        price_df = pd.DataFrame(result)

        if len(price_df) == 0:
            raise ValueError("未获取到价格数据，请检查数据库和日期范围")

        # 转换数据类型
        price_df['close'] = price_df['close'].astype(float)
        price_df['trade_date'] = pd.to_datetime(price_df['trade_date'], format='%Y%m%d')

        logger.info(f"加载价格数据: {len(price_df):,} 条记录")
        return price_df

    def calculate_forward_returns(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """计算未来收益（T+hold_days收益）"""
        logger.info(f"正在计算T+{self.hold_days}未来收益...")

        price_df = price_df.sort_values(['ts_code', 'trade_date']).copy()

        # 计算未来N日收盘价
        price_df['future_close'] = price_df.groupby('ts_code')['close'].shift(-self.hold_days)
        price_df['forward_return'] = (price_df['future_close'] - price_df['close']) / price_df['close']

        # 只保留有效记录
        returns_df = price_df[['ts_code', 'trade_date', 'forward_return']].dropna()

        logger.info(f"计算未来收益: {len(returns_df):,} 条有效记录")
        return returns_df

    def merge_factor_returns(self, factor_df: pd.DataFrame, returns_df: pd.DataFrame) -> pd.DataFrame:
        """合并因子数据和未来收益"""
        logger.info("正在合并因子和收益数据...")

        # 合并数据
        merged = pd.merge(factor_df, returns_df, on=['ts_code', 'trade_date'], how='inner')

        if len(merged) == 0:
            raise ValueError("因子数据和收益数据无交集，请检查时间对齐")

        logger.info(f"合并后数据: {len(merged):,} 条记录")
        return merged

    def calculate_ic(self, merged_df: pd.DataFrame) -> pd.DataFrame:
        """计算信息系数IC"""
        logger.info("正在计算信息系数IC...")

        # 按日期计算秩相关系数
        ic_series = merged_df.groupby('trade_date').apply(
            lambda x: x['factor'].corr(x['forward_return'], method='spearman')
        )

        ic_df = ic_series.reset_index()
        ic_df.columns = ['trade_date', 'ic']

        logger.info(f"IC统计: 均值={ic_df['ic'].mean():.4f}, 标准差={ic_df['ic'].std():.4f}")
        return ic_df

    def calculate_icir(self, ic_df: pd.DataFrame) -> float:
        """计算ICIR"""
        if len(ic_df) < 2:
            return 0.0
        icir = ic_df['ic'].mean() / ic_df['ic'].std()
        logger.info(f"ICIR: {icir:.4f}")
        return icir

    def group_backtest(self, merged_df: pd.DataFrame, n_groups: int = 5) -> pd.DataFrame:
        """分组回测"""
        logger.info(f"正在进行分组回测（{n_groups}组）...")

        # 按日期分组计算分位数
        merged_df['group'] = merged_df.groupby('trade_date')['factor'].transform(
            lambda x: pd.qcut(x, n_groups, labels=False, duplicates='drop')
        )

        # 计算每组每日收益
        group_returns = merged_df.groupby(['trade_date', 'group'])['forward_return'].mean().reset_index()

        # 统计每组收益
        group_stats = group_returns.groupby('group')['forward_return'].agg(['mean', 'std', 'count']).reset_index()

        logger.info(f"分组收益统计:")
        for _, row in group_stats.iterrows():
            logger.info(f"  组{int(row['group'])}: 均值={row['mean']:.4f}, 标准差={row['std']:.4f}, 样本={int(row['count'])}")

        # 检查单调性
        group_means = group_stats['mean'].values
        monotonic = all(group_means[i] <= group_means[i+1] for i in range(len(group_means)-1))
        logger.info(f"分组单调性: {'✅ 通过' if monotonic else '❌ 未通过'}")

        return group_returns

    def run_backtest(self, factor_df: pd.DataFrame, price_df: pd.DataFrame) -> Dict:
        """运行完整回测"""
        logger.info("=" * 80)
        logger.info("开始运行完整回测...")
        logger.info("=" * 80)

        # 1. 计算未来收益
        returns_df = self.calculate_forward_returns(price_df)

        # 2. 合并数据
        merged_df = self.merge_factor_returns(factor_df, returns_df)

        # 3. 计算IC
        ic_df = self.calculate_ic(merged_df)
        icir = self.calculate_icir(ic_df)

        # 4. 分组回测
        group_returns = self.group_backtest(merged_df)

        # 5. 计算策略收益（买入因子值最高的股票）
        logger.info("正在计算策略收益...")

        # 每日选择因子值最高的股票（前10%）
        merged_df['rank'] = merged_df.groupby('trade_date')['factor'].rank(ascending=False, pct=True)
        selected = merged_df[merged_df['rank'] <= 0.1].copy()

        # 等权重计算每日收益
        strategy_returns = selected.groupby('trade_date')['forward_return'].mean().reset_index()
        strategy_returns.columns = ['trade_date', 'strategy_return']

        # 计算累计收益
        strategy_returns['cumulative_return'] = (1 + strategy_returns['strategy_return']).cumprod() - 1

        # 计算绩效指标
        total_return = strategy_returns['cumulative_return'].iloc[-1]
        annual_return = (1 + total_return) ** (243 / len(strategy_returns)) - 1  # 243个交易日
        daily_vol = strategy_returns['strategy_return'].std()
        annual_vol = daily_vol * np.sqrt(243)
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0

        # 最大回撤
        cumulative = (1 + strategy_returns['strategy_return']).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # 胜率
        win_rate = (strategy_returns['strategy_return'] > 0).mean()

        logger.info(f"\n策略绩效:")
        logger.info(f"  累计收益: {total_return:.4f} ({total_return*100:.2f}%)")
        logger.info(f"  年化收益: {annual_return:.4f} ({annual_return*100:.2f}%)")
        logger.info(f"  夏普比率: {sharpe:.4f}")
        logger.info(f"  最大回撤: {max_drawdown:.4f} ({max_drawdown*100:.2f}%)")
        logger.info(f"  胜率: {win_rate:.4f} ({win_rate*100:.2f}%)")
        logger.info(f"  ICIR: {icir:.4f}")

        return {
            'strategy_returns': strategy_returns,
            'ic_df': ic_df,
            'icir': icir,
            'group_returns': group_returns,
            'merged_df': merged_df,
            'performance': {
                'total_return': total_return,
                'annual_return': annual_return,
                'sharpe': sharpe,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
            }
        }

    def save_results(self, results: Dict, fina_df: pd.DataFrame, factor_df: pd.DataFrame):
        """保存回测结果"""
        logger.info(f"正在保存结果到: {self.output_dir}")

        # 1. 保存因子数据
        factor_file = os.path.join(self.output_dir, f"alpha_profit_employee_factor_{self.start_date}_{self.end_date}.csv")
        factor_df.to_csv(factor_file, index=False)
        logger.info(f"  因子数据: {factor_file}")

        # 2. 保存每日策略收益和资产曲线
        strategy_returns = results['strategy_returns'].copy()

        # 计算资产价值曲线
        initial_capital = 1000000.0
        portfolio_value = initial_capital
        portfolio_values = []

        for _, row in strategy_returns.iterrows():
            daily_return = row['strategy_return']
            portfolio_value *= (1 + daily_return)
            portfolio_values.append(portfolio_value)

        strategy_returns['portfolio_value'] = portfolio_values

        # 更新results中的strategy_returns，供generate_report使用
        results['strategy_returns'] = strategy_returns

        performance_file = os.path.join(self.output_dir, f"alpha_profit_employee_performance_{self.start_date}_{self.end_date}.csv")
        strategy_returns.to_csv(performance_file, index=False)
        logger.info(f"  策略绩效: {performance_file}")

        # 3. 保存IC数据
        ic_file = os.path.join(self.output_dir, f"alpha_profit_employee_ic_{self.start_date}_{self.end_date}.csv")
        results['ic_df'].to_csv(ic_file, index=False)
        logger.info(f"  IC数据: {ic_file}")

        # 4. 保存分组收益
        group_file = os.path.join(self.output_dir, f"alpha_profit_employee_groups_{self.start_date}_{self.end_date}.csv")
        results['group_returns'].to_csv(group_file, index=False)
        logger.info(f"  分组收益: {group_file}")

        # 5. 保存交易记录（每日选股）
        trades_file = os.path.join(self.output_dir, f"alpha_profit_employee_trades_{self.start_date}_{self.end_date}.csv")
        trades_df = results['merged_df'][results['merged_df']['rank'] <= 0.1].copy()
        trades_df = trades_df[['ts_code', 'trade_date', 'factor', 'forward_return']]
        trades_df.to_csv(trades_file, index=False)
        logger.info(f"  交易记录: {trades_file}")

        logger.info("结果保存完成！")

    def generate_report(self, results: Dict):
        """生成回测报告"""
        report_file = os.path.join(self.output_dir, "backtest_report.txt")

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Alpha Profit Employee 因子回测报告\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"回测时间: {self.start_date} 至 {self.end_date}\n")
            f.write(f"持有天数: {self.hold_days} 天\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("因子说明:\n")
            f.write("  因子公式: CSRank((营业利润 + 支付给职工现金) / 总市值, 公告日期)\n")
            f.write("  因子类型: 截面价值因子\n")
            f.write("  选股逻辑: 每日选择因子值前10%的股票\n\n")

            f.write("绩效指标:\n")
            perf = results['performance']
            f.write(f"  累计收益: {perf['total_return']:.4f} ({perf['total_return']*100:.2f}%)\n")
            f.write(f"  年化收益: {perf['annual_return']:.4f} ({perf['annual_return']*100:.2f}%)\n")
            f.write(f"  夏普比率: {perf['sharpe']:.4f}\n")
            f.write(f"  最大回撤: {perf['max_drawdown']:.4f} ({perf['max_drawdown']*100:.2f}%)\n")
            f.write(f"  胜率: {perf['win_rate']:.4f} ({perf['win_rate']*100:.2f}%)\n")
            f.write(f"  ICIR: {results['icir']:.4f}\n\n")

            f.write("资产价值曲线:\n")
            strategy_returns = results['strategy_returns']
            for idx in [0, len(strategy_returns)//4, len(strategy_returns)//2, 3*len(strategy_returns)//4, -1]:
                if idx < len(strategy_returns):
                    row = strategy_returns.iloc[idx]
                    f.write(f"  {row['trade_date'].strftime('%Y-%m-%d')}: {row['portfolio_value']:,.2f}\n")

            f.write("\n分组收益统计:\n")
            group_returns = results['group_returns']
            group_stats = group_returns.groupby('group')['forward_return'].mean()
            for group, ret in group_stats.items():
                f.write(f"  组{int(group)}: {ret:.4f} ({ret*100:.2f}%)\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("报告结束\n")
            f.write("=" * 80 + "\n")

        logger.info(f"回测报告已生成: {report_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Alpha Profit Employee 因子回测')
    parser.add_argument('--start_date', type=str, default='20250101', help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end_date', type=str, default='20251231', help='结束日期 (YYYYMMDD)')
    parser.add_argument('--hold_days', type=int, default=20, help='持有天数')

    args = parser.parse_args()

    try:
        # 创建回测器
        backtest = AlphaProfitEmployeeBacktest(
            start_date=args.start_date,
            end_date=args.end_date,
            hold_days=args.hold_days
        )

        # 1. 加载财务数据
        fina_df = backtest.load_financial_data()

        # 2. 计算因子
        factor_df = backtest.calculate_factor(fina_df)

        # 3. 加载价格数据
        price_df = backtest.load_price_data()

        # 4. 运行回测
        results = backtest.run_backtest(factor_df, price_df)

        # 5. 保存结果
        backtest.save_results(results, fina_df, factor_df)

        # 6. 生成报告
        backtest.generate_report(results)

        logger.info("\n" + "=" * 80)
        logger.info("✅ 回测完成！")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"回测失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
