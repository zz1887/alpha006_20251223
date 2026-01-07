"""
vectorbt回测引擎 - backtest/engine/vbt_backtest_engine.py

功能:
- 基于vectorbt库实现多持仓天数回测
- 支持10-45天持仓天数测试
- 计算核心绩效指标
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from core.constants.config import COMMISSION, STAMP_TAX, SLIPPAGE


class VBTBacktestEngine:
    """vectorbt回测引擎"""

    def __init__(self, price_df: pd.DataFrame, signal_matrix: pd.DataFrame):
        """
        初始化回测引擎

        Args:
            price_df: 价格数据 (ts_code, trade_date, close)
            signal_matrix: 信号矩阵 (trade_date x ts_code)
        """
        self.price_df = price_df
        self.signal_matrix = signal_matrix

        # 准备vectorbt所需格式
        self._prepare_data()

    def _prepare_data(self):
        """准备vectorbt所需格式的数据"""
        # 1. 创建价格矩阵 (trade_date x ts_code)
        price_pivot = self.price_df.pivot_table(
            index='trade_date',
            columns='ts_code',
            values='close',
            aggfunc='first'
        )

        # 转换为datetime索引（先转换再对齐）
        price_pivot.index = pd.to_datetime(price_pivot.index, format='%Y%m%d')
        self.signal_matrix.index = pd.to_datetime(self.signal_matrix.index, format='%Y%m%d')

        # 确保信号矩阵和价格矩阵的日期、股票对齐
        common_dates = self.signal_matrix.index.intersection(price_pivot.index)
        common_stocks = self.signal_matrix.columns.intersection(price_pivot.columns)

        if len(common_dates) == 0:
            print(f"⚠️ 警告: 信号矩阵和价格矩阵无共同日期")
            print(f"  信号矩阵日期范围: {self.signal_matrix.index.min()} ~ {self.signal_matrix.index.max()}")
            print(f"  价格矩阵日期范围: {price_pivot.index.min()} ~ {price_pivot.index.max()}")
            # 使用信号矩阵的日期作为基准
            common_dates = self.signal_matrix.index

        self.price_matrix = price_pivot.loc[common_dates, common_stocks]
        self.signal_matrix = self.signal_matrix.loc[common_dates, common_stocks]

        # 填充缺失的价格数据
        self.price_matrix = self.price_matrix.ffill().bfill()

        print(f"✓ 对齐后数据: {len(self.price_matrix)}个交易日, {len(self.price_matrix.columns)}只股票")

    def run_backtest(self, holding_days: int, initial_capital: float = 1000000.0) -> Dict[str, Any]:
        """
        运行单次回测

        Args:
            holding_days: 持有天数
            initial_capital: 初始资金

        Returns:
            回测结果字典
        """
        print(f"\n{'='*80}")
        print(f"运行回测: 持有天数 = {holding_days}")
        print(f"{'='*80}")

        # 检查数据是否有效
        if len(self.price_matrix) == 0 or len(self.signal_matrix) == 0:
            print("❌ 无有效数据")
            return {}

        # 1. 生成实际持仓信号（考虑持有天数）
        # 使用rolling_sum来实现N天持有
        rolling_signals = self.signal_matrix.rolling(window=holding_days, min_periods=1).sum()

        # 转换为实际持仓信号（只要在窗口期内有信号就持有）
        actual_signals = (rolling_signals > 0).astype(int)

        # 2. 计算交易成本
        total_cost = COMMISSION + STAMP_TAX + SLIPPAGE

        # 3. 运行vectorbt回测 - 使用单列方式避免多列现金分配问题
        try:
            # 将多列信号合并为单列：只要有任意股票被选中，就标记为1
            # 这样我们跟踪的是一个虚拟的"选股组合"，而不是单独的股票
            combined_signal = (actual_signals.sum(axis=1) > 0).astype(int)

            # 使用平均价格作为虚拟组合的价格 - 向量化计算
            # 计算每天被选中股票的平均价格
            # actual_signals > 0 会生成布尔矩阵，乘以价格矩阵后只保留被选中股票的价格
            price_masked = self.price_matrix.where(actual_signals > 0)
            avg_price = price_masked.mean(axis=1)

            # 对于没有选中股票的日期，使用所有股票的平均价格
            no_selection = (actual_signals.sum(axis=1) == 0)
            if no_selection.any():
                avg_price[no_selection] = self.price_matrix.mean(axis=1)[no_selection]

            single_price = avg_price.rename('portfolio')

            # 创建单列信号
            entries = (combined_signal == 1).astype(bool).to_frame(name='portfolio')
            exits = (combined_signal == 0).astype(bool).to_frame(name='portfolio')

            portfolio = vbt.Portfolio.from_signals(
                close=single_price.to_frame(),
                entries=entries,
                exits=exits,
                freq='D',
                init_cash=initial_capital,
                fees=total_cost,
                size=1.0,
                size_type='percent',
                log=False
            )

            # 4. 计算绩效指标
            summary = self._calculate_metrics(portfolio, holding_days)

            # 5. 返回结果
            result = {
                'holding_days': holding_days,
                'summary': summary,
                'portfolio': portfolio,
                'signals': actual_signals,
                'daily_nav': portfolio.value(),
                'daily_returns': portfolio.returns(),
                'trades': portfolio.trades.records_readable if portfolio.trades else None
            }

            print(f"✓ 回测完成: 最终价值 {summary['final_value']:.0f}, 年化收益 {summary['annual_return']:.2%}")

            return result

        except Exception as e:
            print(f"❌ 回测失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _calculate_metrics(self, portfolio, holding_days: int) -> Dict[str, Any]:
        """
        计算绩效指标

        Args:
            portfolio: vectorbt投资组合对象
            holding_days: 持有天数

        Returns:
            绩效指标字典
        """
        try:
            # 获取净值序列 - 处理多列情况
            nav = portfolio.value()
            returns = portfolio.returns()

            # 如果是多列，取总和
            if isinstance(nav, pd.DataFrame) and len(nav.columns) > 1:
                nav = nav.sum(axis=1)
            if isinstance(returns, pd.DataFrame) and len(returns.columns) > 1:
                returns = returns.sum(axis=1)

            if len(nav) == 0 or len(returns) == 0:
                return {}

            # 累计收益
            nav_first = float(nav.iloc[0])
            nav_last = float(nav.iloc[-1])
            total_return = nav_last / nav_first - 1

            # 年化收益
            total_days = (nav.index[-1] - nav.index[0]).days + 1
            annual_return = (1 + total_return) ** (252 / total_days) - 1

            # 最大回撤
            peak = nav.expanding().max()
            drawdown = (nav - peak) / peak
            max_drawdown = float(drawdown.min())

            # 夏普比率
            risk_free_rate = 0.02 / 252
            excess_returns = returns - risk_free_rate
            std = float(excess_returns.std())
            sharpe_ratio = float(excess_returns.mean() / std * np.sqrt(252)) if std != 0 else 0

            # 波动率
            volatility = float(returns.std() * np.sqrt(252))

            # 换手率（简单估算）
            turnover = 0.0  # 简化处理

            # 交易次数
            try:
                trades = portfolio.trades.records_readable
                total_trades = len(trades) if trades is not None else 0
            except:
                total_trades = 0

            # 胜率和盈亏比
            win_rate = 0.0
            profit_loss_ratio = 0.0
            if total_trades > 0:
                try:
                    if trades is not None and len(trades) > 0:
                        positive_trades = trades[trades['ReturnPct'] > 0]
                        negative_trades = trades[trades['ReturnPct'] < 0]

                        win_rate = len(positive_trades) / total_trades
                        avg_win = positive_trades['ReturnPct'].mean() if len(positive_trades) > 0 else 0
                        avg_loss = negative_trades['ReturnPct'].mean() if len(negative_trades) > 0 else 0
                        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                except:
                    pass

            summary = {
                'holding_days': holding_days,
                'initial_capital': nav_first,
                'final_value': nav_last,
                'total_return': total_return,
                'annual_return': annual_return,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'turnover': turnover,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'profit_loss_ratio': profit_loss_ratio,
                'avg_stocks': self.signal_matrix.sum(axis=1).mean(),
                'total_days': len(nav),
                'ic_mean': 0,
                'ic_std': 0,
                'ic_ir': 0
            }

            return summary

        except Exception as e:
            print(f"  计算指标时出错: {e}")
            return {}

    def _calculate_turnover(self, portfolio) -> float:
        """
        计算换手率

        Args:
            portfolio: vectorbt投资组合对象

        Returns:
            日均换手率
        """
        try:
            # 获取每日持仓变化
            positions = portfolio.positions()
            if positions is None or len(positions) == 0:
                return 0

            # 计算持仓变化的绝对值总和
            position_changes = positions.diff().abs().sum(axis=1)
            avg_position = positions.mean().sum()

            if avg_position == 0:
                return 0

            # 换手率 = 日均变化 / 平均持仓
            turnover = position_changes.sum() / (avg_position * len(positions))
            return turnover
        except:
            return 0

    def _calculate_ic(self, portfolio) -> Optional[Dict[str, float]]:
        """
        计算信息系数 (IC)

        Args:
            portfolio: vectorbt投资组合对象

        Returns:
            IC统计信息
        """
        try:
            # 获取每日收益
            returns = portfolio.returns()

            # 获取因子值（这里使用信号强度作为代理）
            factor_values = self.signal_matrix.sum(axis=1)  # 每日持有股票数

            # 对齐数据
            aligned = pd.DataFrame({
                'returns': returns,
                'factor': factor_values
            }).dropna()

            if len(aligned) < 2:
                return None

            # 计算IC（相关系数）
            ic_series = []
            for i in range(1, len(aligned)):
                if i < len(aligned):
                    # 当期因子 vs 下一期收益
                    corr = np.corrcoef([aligned['factor'].iloc[i-1]], [aligned['returns'].iloc[i]])[0, 1]
                    if not np.isnan(corr):
                        ic_series.append(corr)

            if len(ic_series) == 0:
                return None

            return {
                'mean': np.mean(ic_series),
                'std': np.std(ic_series),
                'ir': np.mean(ic_series) / np.std(ic_series) if np.std(ic_series) != 0 else 0
            }
        except:
            return None

    def run_multiple_hold_days(self,
                               hold_days_range: List[int],
                               initial_capital: float = 1000000.0) -> pd.DataFrame:
        """
        运行多个持仓天数的回测

        Args:
            hold_days_range: 持有天数范围列表
            initial_capital: 初始资金

        Returns:
            包含所有结果的DataFrame
        """
        print(f"\n{'='*80}")
        print(f"开始多持仓天数回测: {len(hold_days_range)}个测试")
        print(f"测试范围: {min(hold_days_range)}-{max(hold_days_range)}天")
        print(f"{'='*80}")

        results = []

        for hold_days in hold_days_range:
            try:
                result = self.run_backtest(hold_days, initial_capital)
                results.append(result['summary'])

                # 显示进度
                if len(results) % 5 == 0:
                    print(f"  进度: {len(results)}/{len(hold_days_range)}")

            except Exception as e:
                print(f"❌ 持有{hold_days}天回测失败: {e}")
                continue

        return pd.DataFrame(results)


def compare_hold_days_results(results_df: pd.DataFrame) -> Dict[str, Any]:
    """
    对比不同持仓天数的结果

    Args:
        results_df: 包含多个持仓天数结果的DataFrame

    Returns:
        对比分析结果
    """
    print(f"\n{'='*80}")
    print("持仓天数对比分析")
    print(f"{'='*80}")

    if len(results_df) == 0:
        print("❌ 无有效结果数据")
        return {}

    # 检查必需的列是否存在
    required_cols = ['holding_days', 'sharpe_ratio', 'total_return', 'max_drawdown', 'turnover']
    missing_cols = [col for col in required_cols if col not in results_df.columns]
    if missing_cols:
        print(f"❌ 缺少必需列: {missing_cols}")
        return {}

    # 先过滤掉包含NaN的行（在所有计算之前）
    results_df = results_df.dropna(subset=['sharpe_ratio', 'total_return', 'max_drawdown', 'turnover'])

    if len(results_df) == 0:
        print("❌ 所有测试结果都包含NaN值，无法进行分析")
        return {}

    # 按夏普比率排序
    results_df = results_df.sort_values('sharpe_ratio', ascending=False)

    # 最优天数（夏普最高）
    best_by_sharpe = results_df.iloc[0]
    best_days = int(best_by_sharpe['holding_days'])

    # 其他维度的最优
    best_by_return = results_df.loc[results_df['total_return'].idxmax()]
    best_by_drawdown = results_df.loc[results_df['max_drawdown'].idxmax()]  # 最小回撤
    best_by_turnover = results_df.loc[results_df['turnover'].idxmin()]  # 最小换手

    # 生成对比表
    comparison_table = results_df[[
        'holding_days', 'total_return', 'annual_return', 'sharpe_ratio',
        'max_drawdown', 'turnover', 'total_trades', 'ic_mean'
    ]].copy()

    # 标记特殊天数
    comparison_table['备注'] = ''
    for idx, row in comparison_table.iterrows():
        notes = []
        if row['holding_days'] == best_by_return['holding_days']:
            notes.append('收益最高')
        if row['holding_days'] == best_by_drawdown['holding_days']:
            notes.append('回撤最小')
        if row['holding_days'] == best_by_turnover['holding_days']:
            notes.append('换手最低')
        if row['turnover'] > 1.0:
            notes.append('换手过高')
        if row['max_drawdown'] < -0.2:
            notes.append('回撤较大')

        comparison_table.loc[idx, '备注'] = ', '.join(notes) if notes else '-'

    # 计算综合评分（夏普60%，收益20%，回撤10%，换手10%）

    # 归一化处理（带零除保护）
    sharpe_max = results_df['sharpe_ratio'].max()
    return_min = results_df['total_return'].min()
    return_max = results_df['total_return'].max()
    drawdown_min = results_df['max_drawdown'].min()
    drawdown_max = results_df['max_drawdown'].max()
    turnover_max = results_df['turnover'].max()
    turnover_min = results_df['turnover'].min()

    # 夏普比率（直接除以最大值）
    if sharpe_max > 0:
        results_df['sharpe_score'] = results_df['sharpe_ratio'] / sharpe_max
    else:
        results_df['sharpe_score'] = 0.0

    # 收益评分（范围归一化）
    return_range = return_max - return_min
    if return_range > 0:
        results_df['return_score'] = (results_df['total_return'] - return_min) / return_range
    else:
        results_df['return_score'] = 0.5  # 所有值相同，给中间分

    # 回撤评分（反向，回撤越小分越高）
    drawdown_range = drawdown_max - drawdown_min
    if drawdown_range > 0:
        results_df['drawdown_score'] = (results_df['max_drawdown'] - drawdown_min) / drawdown_range
    else:
        results_df['drawdown_score'] = 0.5

    # 换手评分（反向，换手越低分越高）
    turnover_range = turnover_max - turnover_min
    if turnover_range > 0:
        results_df['turnover_score'] = (turnover_max - results_df['turnover']) / turnover_range
    else:
        results_df['turnover_score'] = 0.5

    # 计算综合评分
    results_df['composite_score'] = (
        0.6 * results_df['sharpe_score'] +
        0.2 * results_df['return_score'] +
        0.1 * results_df['drawdown_score'] +
        0.1 * results_df['turnover_score']
    )

    # 找出综合最优
    best_by_composite_idx = results_df['composite_score'].idxmax()
    best_by_composite = results_df.loc[best_by_composite_idx]

    print(f"\n最优持仓天数分析:")
    print(f"  综合最优 (评分): {int(best_by_composite['holding_days'])}天")
    print(f"  夏普最优: {best_days}天 (夏普={best_by_sharpe['sharpe_ratio']:.3f})")
    print(f"  收益最优: {int(best_by_return['holding_days'])}天 (收益={best_by_return['total_return']:.2%})")
    print(f"  回撤最优: {int(best_by_drawdown['holding_days'])}天 (回撤={best_by_drawdown['max_drawdown']:.2%})")
    print(f"  换手最优: {int(best_by_turnover['holding_days'])}天 (换手={best_by_turnover['turnover']:.2f})")

    return {
        'comparison_table': comparison_table,
        'best_by_sharpe': best_by_sharpe,
        'best_by_composite': best_by_composite,
        'best_by_return': best_by_return,
        'best_by_drawdown': best_by_drawdown,
        'best_by_turnover': best_by_turnover,
        'results_df': results_df
    }
