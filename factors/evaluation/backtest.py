"""
文件input(依赖外部什么): pandas, numpy, logging, datetime
文件output(提供什么): FactorBacktestEngine类，提供因子回测引擎；MultiPeriodBacktest类，提供多周期回测
文件pos(系统局部地位): 因子评估回测层，负责因子绩效验证和交易成本分析
文件功能:
    1. 前瞻收益率计算
    2. 分组回测引擎
    3. 交易成本建模
    4. 绩效指标计算
    5. 多周期回测支持

使用示例:
    from factors.evaluation import FactorBacktestEngine

    # 创建回测引擎
    engine = FactorBacktestEngine(transaction_cost=0.0035)

    # 运行完整回测
    result = engine.run_backtest(
        factor_df=factor_df,
        price_df=price_df,
        hold_days=20,
        n_groups=5
    )

参数说明:
    factor_df: 因子数据 [ts_code, trade_date, factor]
    price_df: 价格数据 [ts_code, trade_date, close]
    hold_days: 持有天数 (默认20)
    n_groups: 分组数量 (默认5)
    transaction_cost: 单边交易成本 (默认0.0035)

返回值:
    Dict[str, any]: 完整回测结果，包含分组收益、绩效指标等
    pd.DataFrame: 多周期回测结果
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import timedelta


class FactorBacktestEngine:
    """因子回测引擎"""

    def __init__(self, transaction_cost: float = 0.0035):
        """
        初始化

        Args:
            transaction_cost: 单边交易成本（默认0.35%）
        """
        self.transaction_cost = transaction_cost
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_forward_returns(self,
                                  price_df: pd.DataFrame,
                                  hold_days: int = 20,
                                  price_col: str = 'close') -> pd.DataFrame:
        """
        计算前瞻收益率

        Args:
            price_df: 价格数据 [ts_code, trade_date, close]
            hold_days: 持有天数
            price_col: 价格列名

        Returns:
            pd.DataFrame: 前瞻收益率 [ts_code, trade_date, forward_return]
        """
        df = price_df.copy()
        df = df.sort_values(['ts_code', 'trade_date'])

        # 计算未来价格
        df['future_price'] = df.groupby('ts_code')[price_col].shift(-hold_days)

        # 计算收益率
        df['forward_return'] = (df['future_price'] - df[price_col]) / df[price_col]

        # 返回结果
        result = df[['ts_code', 'trade_date', 'forward_return']].dropna()
        result = result.set_index(['ts_code', 'trade_date'])

        self.logger.info(f"计算前瞻收益率完成，持有期: {hold_days}天")
        return result

    def group_backtest(self,
                       factor_df: pd.DataFrame,
                       forward_returns: pd.DataFrame,
                       n_groups: int = 5,
                       hold_days: int = 20) -> Dict[str, any]:
        """
        分组回测

        Args:
            factor_df: 因子数据 [ts_code, trade_date, factor]
            forward_returns: 前瞻收益率
            n_groups: 分组数量
            hold_days: 持有天数

        Returns:
            Dict: 回测结果
        """
        # 合并因子和收益率
        merged = pd.merge(
            factor_df,
            forward_returns.reset_index(),
            on=['ts_code', 'trade_date'],
            how='inner'
        )

        if len(merged) == 0:
            return {'error': '无匹配数据'}

        # 按日期分组，计算分位数
        merged['group'] = merged.groupby('trade_date')['factor'].transform(
            lambda x: pd.qcut(x, n_groups, labels=False, duplicates='drop')
        )

        # 计算各组收益率
        group_returns = merged.groupby(['trade_date', 'group'])['forward_return'].mean().unstack()

        # 计算累计收益率
        cumulative_returns = (1 + group_returns).cumprod()

        # 计算各组总收益
        total_returns = cumulative_returns.iloc[-1] - 1

        # 计算多空组合（最高组 - 最低组）
        if n_groups >= 2:
            long_short_return = total_returns.iloc[-1] - total_returns.iloc[0]
        else:
            long_short_return = 0

        # 计算换手率
        turnover = self._calculate_turnover(factor_df, n_groups)

        # 计算最大回撤
        max_drawdowns = self._calculate_max_drawdown(cumulative_returns)

        # 计算年化收益
        annual_returns = self._calculate_annual_returns(total_returns, hold_days)

        return {
            'group_returns': group_returns,
            'cumulative_returns': cumulative_returns,
            'total_returns': total_returns,
            'annual_returns': annual_returns,
            'long_short_return': long_short_return,
            'turnover': turnover,
            'max_drawdowns': max_drawdowns,
            'n_groups': n_groups,
            'hold_days': hold_days
        }

    def _calculate_turnover(self, factor_df: pd.DataFrame, n_groups: int) -> float:
        """计算换手率"""
        # 按日期分组，计算每日分组变化
        df = factor_df.copy()
        df = df.sort_values(['ts_code', 'trade_date'])

        # 计算每日分组
        df['group'] = df.groupby('trade_date')['factor'].transform(
            lambda x: pd.qcut(x, n_groups, labels=False, duplicates='drop')
        )

        # 计算换手率：每日更换的股票比例
        turnover_list = []
        dates = df['trade_date'].unique()

        for i in range(1, len(dates)):
            prev_date = dates[i-1]
            curr_date = dates[i]

            prev_data = df[df['trade_date'] == prev_date][['ts_code', 'group']]
            curr_data = df[df['trade_date'] == curr_date][['ts_code', 'group']]

            merged = pd.merge(prev_data, curr_data, on='ts_code', how='inner', suffixes=('_prev', '_curr'))

            if len(merged) > 0:
                turnover_rate = (merged['group_prev'] != merged['group_curr']).mean()
                turnover_list.append(turnover_rate)

        return np.mean(turnover_list) if turnover_list else 0

    def _calculate_max_drawdown(self, cumulative_returns: pd.DataFrame) -> pd.Series:
        """计算最大回撤"""
        max_drawdowns = {}

        for group in cumulative_returns.columns:
            cum_ret = cumulative_returns[group]
            running_max = cum_ret.expanding().max()
            drawdown = (cum_ret - running_max) / running_max
            max_drawdowns[group] = drawdown.min()

        return pd.Series(max_drawdowns)

    def _calculate_annual_returns(self, total_returns: pd.Series, hold_days: int) -> pd.Series:
        """计算年化收益率"""
        # 假设一年约252个交易日
        n_periods_per_year = 252 // hold_days
        annual_returns = (1 + total_returns) ** n_periods_per_year - 1
        return annual_returns

    def calculate_performance_metrics(self,
                                     group_returns: pd.DataFrame,
                                     turnover: float,
                                     long_short_return: float) -> Dict[str, float]:
        """
        计算绩效指标

        Args:
            group_returns: 分组收益率
            turnover: 换手率
            long_short_return: 多空收益

        Returns:
            Dict: 绩效指标
        """
        # 计算各组夏普比率
        sharpe_ratios = {}
        for group in group_returns.columns:
            mean_ret = group_returns[group].mean()
            std_ret = group_returns[group].std()
            if std_ret > 0:
                sharpe_ratios[f'group_{group}'] = (mean_ret / std_ret) * np.sqrt(252)
            else:
                sharpe_ratios[f'group_{group}'] = 0

        # 计算信息比率（相对于市场均值）
        market_return = group_returns.mean(axis=1)
        excess_returns = group_returns.sub(market_return, axis=0)

        ir_ratios = {}
        for group in group_returns.columns:
            excess_mean = excess_returns[group].mean()
            excess_std = excess_returns[group].std()
            if excess_std > 0:
                ir_ratios[f'group_{group}'] = excess_mean / excess_std
            else:
                ir_ratios[f'group_{group}'] = 0

        # 计算分组区分度
        if len(group_returns.columns) >= 2:
            group_1_vs_5 = group_returns.iloc[:, -1].mean() - group_returns.iloc[:, 0].mean()
        else:
            group_1_vs_5 = 0

        # 综合评分（简化版）
        # 考虑：多空收益、换手率（越低越好）、稳定性
        stability = group_returns.std().mean()  # 收益率波动率的倒数
        score = 0

        if long_short_return > 0:
            score += min(long_short_return * 50, 50)  # 多空收益权重50%

        if turnover > 0:
            turnover_score = max(0, (1 - turnover) * 30)
            score += turnover_score  # 换手率权重30%

        if stability > 0:
            stability_score = min(20, 20 / stability)
            score += stability_score  # 稳定性权重20%

        return {
            'sharpe_ratios': sharpe_ratios,
            'information_ratios': ir_ratios,
            'group_1_vs_5': float(group_1_vs_5),
            'turnover': float(turnover),
            'long_short_return': float(long_short_return),
            'stability': float(1 / stability if stability > 0 else 0),
            'comprehensive_score': float(min(score, 100))
        }

    def run_backtest(self,
                     factor_df: pd.DataFrame,
                     price_df: pd.DataFrame,
                     hold_days: int = 20,
                     n_groups: int = 5) -> Dict[str, any]:
        """
        运行完整回测

        Args:
            factor_df: 因子数据
            price_df: 价格数据
            hold_days: 持有天数
            n_groups: 分组数量

        Returns:
            Dict: 完整回测结果
        """
        # 1. 计算前瞻收益率
        forward_returns = self.calculate_forward_returns(price_df, hold_days)

        # 2. 运行分组回测
        backtest_result = self.group_backtest(factor_df, forward_returns, n_groups, hold_days)

        if 'error' in backtest_result:
            return backtest_result

        # 3. 计算绩效指标
        metrics = self.calculate_performance_metrics(
            backtest_result['group_returns'],
            backtest_result['turnover'],
            backtest_result['long_short_return']
        )

        # 4. 合并结果
        result = {
            **backtest_result,
            'performance_metrics': metrics
        }

        return result


class MultiPeriodBacktest:
    """多周期回测"""

    def __init__(self, backtest_engine: Optional[FactorBacktestEngine] = None):
        self.backtest_engine = backtest_engine or FactorBacktestEngine()
        self.logger = logging.getLogger(self.__class__.__name__)

    def run_rolling_backtest(self,
                            factor_df: pd.DataFrame,
                            price_df: pd.DataFrame,
                            train_period: int = 60,
                            test_period: int = 20,
                            n_groups: int = 5) -> pd.DataFrame:
        """
        滚动回测

        Args:
            factor_df: 因子数据
            price_df: 价格数据
            train_period: 训练期（天）
            test_period: 测试期（天）
            n_groups: 分组数量

        Returns:
            pd.DataFrame: 滚动回测结果
        """
        dates = sorted(factor_df['trade_date'].unique())
        results = []

        for i in range(train_period, len(dates) - test_period, test_period):
            train_start = dates[i - train_period]
            train_end = dates[i - 1]
            test_start = dates[i]
            test_end = dates[i + test_period - 1] if i + test_period < len(dates) else dates[-1]

            # 训练期数据
            train_factor = factor_df[
                (factor_df['trade_date'] >= train_start) &
                (factor_df['trade_date'] <= train_end)
            ]

            # 测试期数据
            test_factor = factor_df[
                (factor_df['trade_date'] >= test_start) &
                (factor_df['trade_date'] <= test_end)
            ]

            test_price = price_df[
                (price_df['trade_date'] >= test_start) &
                (price_df['trade_date'] <= test_end)
            ]

            if len(test_factor) == 0 or len(test_price) == 0:
                continue

            # 运行回测
            result = self.backtest_engine.run_backtest(
                test_factor, test_price, hold_days=20, n_groups=n_groups
            )

            if 'error' not in result:
                results.append({
                    'period': f"{test_start} to {test_end}",
                    'long_short_return': result['performance_metrics']['long_short_return'],
                    'turnover': result['performance_metrics']['turnover'],
                    'comprehensive_score': result['performance_metrics']['comprehensive_score']
                })

        return pd.DataFrame(results)

    def run_period_backtest(self,
                           factor_df: pd.DataFrame,
                           price_df: pd.DataFrame,
                           periods: List[Tuple[str, str]],
                           n_groups: int = 5) -> pd.DataFrame:
        """
        指定周期回测

        Args:
            factor_df: 因子数据
            price_df: 价格数据
            periods: 周期列表 [(start1, end1), (start2, end2), ...]
            n_groups: 分组数量

        Returns:
            pd.DataFrame: 各周期回测结果
        """
        results = []

        for start_date, end_date in periods:
            period_factor = factor_df[
                (factor_df['trade_date'] >= start_date) &
                (factor_df['trade_date'] <= end_date)
            ]

            period_price = price_df[
                (price_df['trade_date'] >= start_date) &
                (price_df['trade_date'] <= end_date)
            ]

            if len(period_factor) == 0 or len(period_price) == 0:
                continue

            result = self.backtest_engine.run_backtest(
                period_factor, period_price, hold_days=20, n_groups=n_groups
            )

            if 'error' not in result:
                metrics = result['performance_metrics']
                results.append({
                    'period': f"{start_date} to {end_date}",
                    'long_short_return': metrics['long_short_return'],
                    'turnover': metrics['turnover'],
                    'comprehensive_score': metrics['comprehensive_score'],
                    'group_1_vs_5': metrics['group_1_vs_5']
                })

        return pd.DataFrame(results)


__all__ = [
    'FactorBacktestEngine',
    'MultiPeriodBacktest',
]