"""
回测引擎 - backtest/engine/backtest_engine.py

功能:
- T+20策略回测引擎
- 分行业排名选股
- 持仓管理
- 绩效指标计算

策略逻辑:
    1. 分行业计算alpha_peg因子
    2. 每行业选择排名前3个股
    3. T日等权重买入
    4. 持有20天后卖出
    5. 计算绩效指标
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from core.constants.config import (
    COMMISSION, STAMP_TAX, SLIPPAGE, TOTAL_COST,
    DEFAULT_INITIAL_CAPITAL, RISK_FREE_RATE
)


class T20BacktestEngine:
    """T+20回测引擎"""

    def __init__(self,
                 initial_capital: float = DEFAULT_INITIAL_CAPITAL,
                 holding_days: int = 20,
                 cost_rate: float = TOTAL_COST):
        """
        初始化回测引擎

        Args:
            initial_capital: 初始资金
            holding_days: 持有天数
            cost_rate: 交易成本率
        """
        self.initial_capital = initial_capital
        self.holding_days = holding_days
        self.cost_rate = cost_rate

    def run_backtest(self,
                     selected_df: pd.DataFrame,
                     price_df: pd.DataFrame,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        运行回测

        Args:
            selected_df: 选股结果 (ts_code, trade_date, l1_name, alpha_peg, industry_rank)
            price_df: 价格数据 (ts_code, trade_date, open, close)
            start_date: 回测开始日期
            end_date: 回测结束日期

        Returns:
            回测结果字典
        """
        print(f"\n{'='*80}")
        print(f"T+{self.holding_days}回测引擎启动")
        print(f"初始资金: {self.initial_capital:,.0f}")
        print(f"交易成本: {self.cost_rate:.4f}")
        print(f"{'='*80}")

        # 1. 准备数据
        selected_df = selected_df.copy()
        selected_df['trade_date'] = pd.to_datetime(selected_df['trade_date'], format='%Y%m%d')

        # 创建价格索引
        price_index = price_df.set_index(['ts_code', 'trade_date'])[['open', 'close']].to_dict('index')

        # 按日期排序
        trade_dates = sorted(selected_df['trade_date'].unique())

        # 2. 回测主循环
        portfolio_value = self.initial_capital
        daily_records = []
        trade_records = []
        daily_nav = []
        positions = {}  # 持仓管理

        print(f"\n开始回测，交易日期数: {len(trade_dates)}")

        for i, trade_date in enumerate(trade_dates):
            # 1. 卖出到期持仓
            sell_values = 0
            stocks_to_sell = []

            for ts_code, pos in list(positions.items()):
                if trade_date >= pos['sell_date']:
                    price_key = (ts_code, trade_date)
                    if price_key in price_index:
                        close_price = price_index[price_key]['close']
                        gross_value = pos['shares'] * close_price
                        net_value = gross_value * (1 - self.cost_rate)
                        sell_values += net_value

                        # 记录交易
                        gross_return = (close_price - pos['buy_price']) / pos['buy_price']
                        net_return = gross_return - self.cost_rate

                        trade_records.append({
                            'buy_date': pos['buy_date'],
                            'sell_date': trade_date,
                            'ts_code': ts_code,
                            'buy_price': pos['buy_price'],
                            'sell_price': close_price,
                            'return': net_return,
                            'holding_days': (trade_date - pos['buy_date']).days
                        })

                        stocks_to_sell.append(ts_code)

            # 清除已卖出的持仓
            for ts_code in stocks_to_sell:
                del positions[ts_code]

            # 更新资金
            if sell_values > 0:
                portfolio_value += sell_values

            # 2. 买入新股票
            today_stocks = selected_df[selected_df['trade_date'] == trade_date]['ts_code'].tolist()

            if len(today_stocks) > 0 and len(positions) == 0:
                capital_per_stock = portfolio_value / len(today_stocks)

                for ts_code in today_stocks:
                    price_key = (ts_code, trade_date)
                    if price_key in price_index:
                        open_price = price_index[price_key]['open']
                        buy_cost = capital_per_stock * (1 + COMMISSION + SLIPPAGE)
                        shares = buy_cost / open_price

                        positions[ts_code] = {
                            'buy_date': trade_date,
                            'buy_price': open_price,
                            'shares': shares,
                            'capital': capital_per_stock,
                            'sell_date': trade_date + timedelta(days=self.holding_days)
                        }

                portfolio_value -= len(today_stocks) * capital_per_stock

            # 3. 计算当前持仓市值
            current_positions_value = 0
            for ts_code, pos in positions.items():
                price_key = (ts_code, trade_date)
                if price_key in price_index:
                    current_positions_value += pos['shares'] * price_index[price_key]['close']

            # 4. 计算当日收益率
            total_value = portfolio_value + current_positions_value
            if i > 0:
                prev_value = daily_nav[-1]['portfolio_value']
                daily_return = (total_value - prev_value) / prev_value if prev_value > 0 else 0
                daily_nav[-1]['daily_return'] = daily_return

            # 5. 记录每日持仓
            daily_records.append({
                'trade_date': trade_date,
                'stock_count': len(positions),
                'portfolio_value': portfolio_value,
                'positions_value': current_positions_value,
                'total_value': total_value,
                'daily_return': 0
            })

            # 6. 记录净值
            daily_nav.append({
                'trade_date': trade_date,
                'portfolio_value': total_value,
                'daily_return': 0,
                'stock_count': len(positions)
            })

            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{len(trade_dates)} 日期，当前净值: {total_value:,.0f}")

        # 3. 清理剩余持仓
        if len(positions) > 0:
            last_date = trade_dates[-1]
            last_positions_value = 0

            for ts_code, pos in positions.items():
                price_key = (ts_code, last_date)
                if price_key in price_index:
                    close_price = price_index[price_key]['close']
                    last_positions_value += pos['shares'] * close_price

            if last_positions_value > 0:
                daily_nav[-1]['portfolio_value'] = portfolio_value + last_positions_value
                daily_nav[-1]['stock_count'] = len(positions)

            portfolio_value += last_positions_value

            for ts_code, pos in positions.items():
                price_key = (ts_code, last_date)
                if price_key in price_index:
                    close_price = price_index[price_key]['close']
                    gross_value = pos['shares'] * close_price
                    net_value = gross_value * (1 - self.cost_rate)

                    gross_return = (close_price - pos['buy_price']) / pos['buy_price']
                    net_return = gross_return - self.cost_rate

                    trade_records.append({
                        'buy_date': pos['buy_date'],
                        'sell_date': last_date,
                        'ts_code': ts_code,
                        'buy_price': pos['buy_price'],
                        'sell_price': close_price,
                        'return': net_return,
                        'holding_days': (last_date - pos['buy_date']).days
                    })

            portfolio_value = portfolio_value * (1 - self.cost_rate)
            daily_nav[-1]['portfolio_value'] = portfolio_value
            daily_nav[-1]['stock_count'] = 0

        # 4. 计算绩效指标
        print("\n计算绩效指标...")
        nav_df = pd.DataFrame(daily_nav)

        summary = self._calculate_performance_metrics(nav_df, trade_records, start_date, end_date)

        return {
            'daily_nav': nav_df,
            'daily_records': pd.DataFrame(daily_records),
            'trade_records': pd.DataFrame(trade_records) if trade_records else pd.DataFrame(),
            'summary': summary
        }

    def _calculate_performance_metrics(self,
                                       nav_df: pd.DataFrame,
                                       trade_records: List[Dict],
                                       start_date: Optional[str],
                                       end_date: Optional[str]) -> Dict[str, Any]:
        """
        计算绩效指标

        Args:
            nav_df: 每日净值DataFrame
            trade_records: 交易记录
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            绩效指标字典
        """
        if len(nav_df) == 0:
            return {}

        # 计算累计收益
        nav_df['cumulative_return'] = nav_df['portfolio_value'] / self.initial_capital - 1

        # 计算年化收益
        total_days = (nav_df['trade_date'].max() - nav_df['trade_date'].min()).days + 1
        annual_return = (1 + nav_df['cumulative_return'].iloc[-1]) ** (252 / total_days) - 1

        # 计算最大回撤
        nav_df['peak'] = nav_df['portfolio_value'].expanding().max()
        nav_df['drawdown'] = (nav_df['portfolio_value'] - nav_df['peak']) / nav_df['peak']
        max_drawdown = nav_df['drawdown'].min()

        # 计算波动率和夏普比率
        daily_returns = nav_df['daily_return'].dropna()
        volatility = daily_returns.std() * np.sqrt(252)

        excess_returns = daily_returns - RISK_FREE_RATE / 252
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() != 0 else 0

        # 胜率和盈亏比
        if trade_records:
            trade_df = pd.DataFrame(trade_records)
            positive_trades = trade_df[trade_df['return'] > 0]
            negative_trades = trade_df[trade_df['return'] < 0]

            win_rate = len(positive_trades) / len(trade_df) if len(trade_df) > 0 else 0
            avg_win = positive_trades['return'].mean() if len(positive_trades) > 0 else 0
            avg_loss = negative_trades['return'].mean() if len(negative_trades) > 0 else 0
            profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf
        else:
            win_rate = 0
            profit_loss_ratio = 0

        summary = {
            'period': f"{start_date}~{end_date}" if start_date and end_date else "Custom",
            'initial_capital': self.initial_capital,
            'final_value': nav_df['portfolio_value'].iloc[-1],
            'total_return': nav_df['cumulative_return'].iloc[-1],
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(trade_records) if trade_records else 0,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'avg_stocks_per_day': nav_df['stock_count'].mean(),
            'total_days': len(nav_df)
        }

        print(f"\n绩效指标:")
        print(f"  时间范围: {summary['period']}")
        print(f"  最终价值: {summary['final_value']:,.0f}")
        print(f"  总收益: {summary['total_return']:.4f} ({summary['total_return']*100:.2f}%)")
        print(f"  年化收益: {summary['annual_return']:.4f} ({summary['annual_return']*100:.2f}%)")
        print(f"  最大回撤: {summary['max_drawdown']:.4f} ({summary['max_drawdown']*100:.2f}%)")
        print(f"  夏普比率: {summary['sharpe_ratio']:.4f}")
        print(f"  胜率: {summary['win_rate']:.2%}")
        print(f"  盈亏比: {summary['profit_loss_ratio']:.2f}")
        print(f"  交易次数: {summary['total_trades']}")

        return summary


def calculate_benchmark_performance(index_df: pd.DataFrame,
                                   initial_capital: float = DEFAULT_INITIAL_CAPITAL) -> pd.DataFrame:
    """
    计算基准指数表现

    Args:
        index_df: 指数数据 (trade_date, close)
        initial_capital: 初始资金

    Returns:
        基准净值DataFrame
    """
    if len(index_df) == 0:
        return pd.DataFrame()

    index_df = index_df.sort_values('trade_date').reset_index(drop=True)
    index_df['close'] = index_df['close'].astype(float)

    # 计算基准净值
    index_df['benchmark_nav'] = initial_capital
    for i in range(1, len(index_df)):
        prev_close = index_df.loc[i-1, 'close']
        curr_close = index_df.loc[i, 'close']
        index_df.loc[i, 'benchmark_nav'] = index_df.loc[i-1, 'benchmark_nav'] * (curr_close / prev_close)

    # 计算收益
    index_df['benchmark_return'] = index_df['benchmark_nav'] / initial_capital - 1

    return index_df[['trade_date', 'benchmark_nav', 'benchmark_return']]


def compare_with_benchmark(portfolio_results: Dict[str, Any],
                          benchmark_df: pd.DataFrame) -> Dict[str, Any]:
    """
    策略与基准对比

    Args:
        portfolio_results: 回测结果
        benchmark_df: 基准数据

    Returns:
        对比结果字典
    """
    if len(benchmark_df) == 0 or len(portfolio_results['daily_nav']) == 0:
        return {}

    nav_df = portfolio_results['daily_nav'][['trade_date', 'portfolio_value', 'cumulative_return']].copy()
    nav_df['trade_date'] = pd.to_datetime(nav_df['trade_date'])
    benchmark_df['trade_date'] = pd.to_datetime(benchmark_df['trade_date'])

    merged = pd.merge(
        nav_df,
        benchmark_df[['trade_date', 'benchmark_return']],
        on='trade_date',
        how='inner'
    )

    if len(merged) == 0:
        return {}

    merged['excess_return'] = merged['cumulative_return'] - merged['benchmark_return']
    excess_total = merged['excess_return'].iloc[-1]
    excess_win_rate = (merged['excess_return'] > 0).mean()

    print(f"\n{'='*80}")
    print("vs 基准对比")
    print(f"{'='*80}")
    print(f"策略收益: {portfolio_results['summary']['total_return']:.2%}")
    print(f"基准收益: {merged['benchmark_return'].iloc[-1]:.2%}")
    print(f"超额收益: {excess_total:.2%}")
    print(f"超额胜率: {excess_win_rate:.2%}")

    return {
        'excess_return': excess_total,
        'excess_win_rate': excess_win_rate,
        'comparison_df': merged
    }
