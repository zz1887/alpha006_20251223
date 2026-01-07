"""
alpha_peg因子 - 多持有期对比回测（T+5, T+10, T+20, T+30）

策略逻辑:
1. 分行业对alpha_peg排名（值越小越靠前）
2. 每行业选前3名个股
3. T日买入，不同持有期卖出（T+5, T+10, T+20, T+30）
4. 等权重分配资金
5. 对比不同持有期的表现

交易成本:
- 佣金: 0.05% (0.0005)
- 印花税: 0.2% (0.002)
- 滑点: 0.1% (0.001)
- 单边总成本: 0.35% (0.0035)

基准: 沪深300指数 (000300.SH)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from db_connection import db

# 交易成本配置
COMMISSION = 0.0005
STAMP_TAX = 0.002
SLIPPAGE = 0.001
TOTAL_COST = COMMISSION + STAMP_TAX + SLIPPAGE  # 0.35%


def load_industry_data(industry_path: str = None) -> pd.DataFrame:
    """加载行业分类数据"""
    if industry_path is None:
        industry_path = '/mnt/c/Users/mm/PyCharmMiscProject/获取数据代码/industry_cache.csv'

    try:
        df = pd.read_csv(industry_path)
        industry_map = df[['ts_code', 'l1_name']].copy()
        print(f"✓ 加载行业数据: {len(industry_map)} 只股票，{industry_map['l1_name'].nunique()} 个行业")
        return industry_map
    except Exception as e:
        print(f"✗ 加载行业数据失败: {e}")
        return pd.DataFrame()


def get_data_by_period(start_date: str, end_date: str) -> tuple:
    """提取指定时间段数据"""
    print(f"\n{'='*80}")
    print(f"数据提取: {start_date} ~ {end_date}")
    print(f"{'='*80}")

    # 1. 获取PE数据
    sql_pe = """
    SELECT ts_code, trade_date, pe_ttm
    FROM daily_basic
    WHERE trade_date >= %s AND trade_date <= %s
      AND pe_ttm IS NOT NULL AND pe_ttm > 0
    ORDER BY ts_code, trade_date
    """
    data_pe = db.execute_query(sql_pe, (start_date, end_date))
    df_pe = pd.DataFrame(data_pe)

    if len(df_pe) == 0:
        print("⚠️  未获取到daily_basic数据")
    else:
        print(f"✓ daily_basic: {len(df_pe):,} 条，{df_pe['ts_code'].nunique()} 只股票")

    # 2. 获取财务数据
    sql_fina = """
    SELECT ts_code, ann_date, dt_netprofit_yoy
    FROM fina_indicator
    WHERE ann_date >= %s AND ann_date <= %s
      AND update_flag = '1'
      AND dt_netprofit_yoy IS NOT NULL
      AND dt_netprofit_yoy != 0
    ORDER BY ts_code, ann_date
    """
    data_fina = db.execute_query(sql_fina, (start_date, end_date))
    df_fina = pd.DataFrame(data_fina)

    if len(df_fina) == 0:
        print("⚠️  未获取到fina_indicator数据")
    else:
        print(f"✓ fina_indicator: {len(df_fina):,} 条，{df_fina['ts_code'].nunique()} 只股票")

    # 3. 加载行业数据
    df_industry = load_industry_data()

    return df_pe, df_fina, df_industry


def calc_alpha_peg_industry_rank(df_pe: pd.DataFrame,
                                 df_fina: pd.DataFrame,
                                 df_industry: pd.DataFrame,
                                 outlier_sigma: float = 3.0) -> pd.DataFrame:
    """分行业计算alpha_peg因子并排名"""
    print(f"\n{'='*80}")
    print("分行业计算alpha_peg因子并排名")
    print(f"{'='*80}")

    # 1. 关联数据
    print("\n步骤1: 关联数据...")
    df_merged = pd.merge(
        df_pe,
        df_fina[['ts_code', 'ann_date', 'dt_netprofit_yoy']],
        left_on=['ts_code', 'trade_date'],
        right_on=['ts_code', 'ann_date'],
        how='left'
    )

    # 转换为float类型
    if len(df_merged) > 0:
        df_merged['pe_ttm'] = df_merged['pe_ttm'].astype(float)
        if 'dt_netprofit_yoy' in df_merged.columns:
            df_merged['dt_netprofit_yoy'] = df_merged['dt_netprofit_yoy'].astype(float)

    # 2. 前向填充
    df_merged['dt_netprofit_yoy_ffill'] = df_merged.groupby('ts_code')['dt_netprofit_yoy'].ffill()

    # 3. 过滤有效数据
    valid_mask = (
        df_merged['pe_ttm'].notna() &
        (df_merged['pe_ttm'] > 0) &
        df_merged['dt_netprofit_yoy_ffill'].notna() &
        (df_merged['dt_netprofit_yoy_ffill'] != 0)
    )

    df_valid = df_merged[valid_mask].copy()
    df_valid['dt_netprofit_yoy'] = df_valid['dt_netprofit_yoy_ffill'].astype(float)

    print(f"  有效数据: {len(df_valid):,} 条")

    if len(df_valid) == 0:
        print("❌ 无有效数据")
        return pd.DataFrame()

    # 4. 合并行业
    df_with_industry = df_valid.merge(df_industry, on='ts_code', how='left')
    df_with_industry['l1_name'] = df_with_industry['l1_name'].fillna('其他')

    # 5. 分行业计算alpha_peg
    print("\n步骤2: 分行业计算并排名...")
    results = []

    for industry, group in df_with_industry.groupby('l1_name'):
        industry_data = group.copy()

        # 基础计算
        industry_data['alpha_peg_raw'] = industry_data['pe_ttm'] / industry_data['dt_netprofit_yoy']

        # 异常值处理
        if outlier_sigma > 0:
            threshold = outlier_sigma

            # 行业特定阈值
            if industry in ['银行', '公用事业', '交通运输']:
                threshold = 2.5
            elif industry in ['电子', '电力设备', '医药生物', '计算机']:
                threshold = 3.5

            mean_val = industry_data['alpha_peg_raw'].mean()
            std_val = industry_data['alpha_peg_raw'].std()

            if std_val > 0:
                lower_bound = mean_val - threshold * std_val
                upper_bound = mean_val + threshold * std_val
                industry_data['alpha_peg_raw'] = industry_data['alpha_peg_raw'].clip(lower_bound, upper_bound)

        # 最终因子值
        industry_data['alpha_peg'] = industry_data['alpha_peg_raw']

        # 分行业排名（值越小排名越前）
        industry_data['industry_rank'] = industry_data['alpha_peg'].rank(ascending=True, method='first')

        results.append(industry_data)

    # 6. 合并结果
    df_result = pd.concat(results, ignore_index=True)

    # 7. 保留关键字段
    df_result = df_result[[
        'ts_code',
        'trade_date',
        'l1_name',
        'pe_ttm',
        'dt_netprofit_yoy',
        'alpha_peg',
        'industry_rank'
    ]]

    print(f"\n✓ 因子计算完成")
    print(f"  记录数: {len(df_result):,}")
    print(f"  股票数: {df_result['ts_code'].nunique()}")
    print(f"  行业数: {df_result['l1_name'].nunique()}")

    return df_result


def select_top3_by_industry(factor_df: pd.DataFrame) -> pd.DataFrame:
    """每行业选择alpha_peg排名前3的个股"""
    print(f"\n{'='*80}")
    print("每行业选择前3名个股")
    print(f"{'='*80}")

    # 按日期和行业分组，选择排名前3
    selected = []

    for (trade_date, industry), group in factor_df.groupby(['trade_date', 'l1_name']):
        # 排序并取前3
        top3 = group.nsmallest(3, 'alpha_peg')[['ts_code', 'trade_date', 'l1_name', 'alpha_peg', 'industry_rank']]
        selected.append(top3)

    df_selected = pd.concat(selected, ignore_index=True)

    print(f"  选中记录数: {len(df_selected):,}")
    print(f"  平均每日选股: {len(df_selected) / factor_df['trade_date'].nunique():.1f} 只")

    return df_selected


def get_price_data(start_date: str, end_date: str) -> pd.DataFrame:
    """获取价格数据"""
    sql = """
    SELECT ts_code, trade_date, open, high, low, close, vol
    FROM daily_kline
    WHERE trade_date >= %s AND trade_date <= %s
    ORDER BY ts_code, trade_date
    """

    data = db.execute_query(sql, (start_date, end_date))
    df = pd.DataFrame(data)

    if len(df) == 0:
        print("⚠️  未获取到价格数据")
        return df

    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    for col in ['open', 'high', 'low', 'close', 'vol']:
        df[col] = df[col].astype(float)

    print(f"✓ 价格数据: {len(df):,} 条")
    return df


def get_index_data(start_date: str, end_date: str) -> pd.DataFrame:
    """获取基准指数数据"""
    sql = """
    SELECT trade_date, close
    FROM index_daily_zzsz
    WHERE ts_code = '000300.SH'
      AND trade_date >= %s AND trade_date <= %s
    ORDER BY trade_date
    """

    data = db.execute_query(sql, (start_date, end_date))
    df = pd.DataFrame(data)

    if len(df) == 0:
        print("⚠️  未获取到基准数据")
        return df

    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    df['close'] = df['close'].astype(float)

    print(f"✓ 基准指数: {len(df):,} 条")
    return df


def run_backtest_with_holding_period(selected_df: pd.DataFrame,
                                     price_df: pd.DataFrame,
                                     holding_days: int,
                                     initial_capital: float = 1000000.0) -> dict:
    """
    运行指定持有期的回测（修正版）

    参数:
        selected_df: 选股结果
        price_df: 价格数据
        holding_days: 持有天数 (5, 10, 20, 30)
        initial_capital: 初始资金

    返回:
        dict: 包含每日持仓、交易记录、绩效指标
    """
    print(f"\n{'='*80}")
    print(f"运行T+{holding_days}回测（每行业前3，持有{holding_days}天）")
    print(f"{'='*80}")

    # 1. 准备数据
    selected_df = selected_df.copy()
    selected_df['trade_date'] = pd.to_datetime(selected_df['trade_date'], format='%Y%m%d')

    # 创建价格索引
    price_index = price_df.set_index(['ts_code', 'trade_date'])[['open', 'close']].to_dict('index')

    # 按日期排序
    trade_dates = sorted(selected_df['trade_date'].unique())

    # 2. 回测主循环
    portfolio_value = initial_capital
    daily_records = []
    trade_records = []
    daily_nav = []

    # 持仓管理: {ts_code: {'buy_date': date, 'buy_price': price, 'shares': shares, 'capital': capital}}
    positions = {}

    print(f"\n开始回测，交易日期数: {len(trade_dates)}")

    for i, trade_date in enumerate(trade_dates):
        # 1. 卖出到期持仓
        sell_values = 0
        stocks_to_sell = []

        for ts_code, pos in list(positions.items()):
            # 检查是否到期
            if trade_date >= pos['sell_date']:
                price_key = (ts_code, trade_date)
                if price_key in price_index:
                    close_price = price_index[price_key]['close']
                    # 计算卖出价值（扣除成本）
                    gross_value = pos['shares'] * close_price
                    net_value = gross_value * (1 - TOTAL_COST)
                    sell_values += net_value

                    # 记录交易
                    gross_return = (close_price - pos['buy_price']) / pos['buy_price']
                    net_return = gross_return - TOTAL_COST

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

        # 更新资金（卖出所得）
        if sell_values > 0:
            portfolio_value += sell_values

        # 2. 买入新股票（今日选中的）- 只使用可用资金，不重复使用
        today_stocks = selected_df[selected_df['trade_date'] == trade_date]['ts_code'].tolist()

        if len(today_stocks) > 0 and len(positions) == 0:  # 无持仓时才买入
            # 等权重分配资金（使用当前可用资金）
            capital_per_stock = portfolio_value / len(today_stocks)

            for ts_code in today_stocks:
                price_key = (ts_code, trade_date)
                if price_key in price_index:
                    open_price = price_index[price_key]['open']
                    # 计算买入价值（扣除买入成本）
                    buy_cost = capital_per_stock * (1 + COMMISSION + SLIPPAGE)
                    shares = buy_cost / open_price

                    positions[ts_code] = {
                        'buy_date': trade_date,
                        'buy_price': open_price,
                        'shares': shares,
                        'capital': capital_per_stock,  # 记录占用的资金
                        'sell_date': trade_date + timedelta(days=holding_days)
                    }

            # 扣除买入占用的资金
            portfolio_value -= len(today_stocks) * capital_per_stock

        # 3. 计算当前持仓市值
        current_positions_value = 0
        for ts_code, pos in positions.items():
            price_key = (ts_code, trade_date)
            if price_key in price_index:
                current_positions_value += pos['shares'] * price_index[price_key]['close']

        # 4. 计算当日实际收益率（基于总市值）
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
            'daily_return': 0  # 将在下一日计算
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

    # 3. 清理剩余持仓（最后一天全部卖出，使用最后一天的收盘价）
    if len(positions) > 0:
        last_date = trade_dates[-1]

        # 先计算当前持仓在最后一天的市值
        last_positions_value = 0
        for ts_code, pos in positions.items():
            price_key = (ts_code, last_date)
            if price_key in price_index:
                close_price = price_index[price_key]['close']
                last_positions_value += pos['shares'] * close_price

        # 更新最后一天的总价值（现金+持仓市值）
        if last_positions_value > 0:
            daily_nav[-1]['portfolio_value'] = portfolio_value + last_positions_value
            daily_nav[-1]['stock_count'] = len(positions)

        # 记录最后一天的持仓市值
        portfolio_value += last_positions_value

        # 然后在最后一天卖出所有持仓（计算最终价值）
        for ts_code, pos in positions.items():
            price_key = (ts_code, last_date)
            if price_key in price_index:
                close_price = price_index[price_key]['close']
                gross_value = pos['shares'] * close_price
                net_value = gross_value * (1 - TOTAL_COST)

                gross_return = (close_price - pos['buy_price']) / pos['buy_price']
                net_return = gross_return - TOTAL_COST

                trade_records.append({
                    'buy_date': pos['buy_date'],
                    'sell_date': last_date,
                    'ts_code': ts_code,
                    'buy_price': pos['buy_price'],
                    'sell_price': close_price,
                    'return': net_return,
                    'holding_days': (last_date - pos['buy_date']).days
                })

        # 最终价值（卖出后）
        portfolio_value = portfolio_value * (1 - TOTAL_COST)  # 扣除卖出成本

        # 更新最后一天净值为最终价值
        daily_nav[-1]['portfolio_value'] = portfolio_value
        daily_nav[-1]['stock_count'] = 0

    # 4. 计算绩效指标
    print("\n计算绩效指标...")

    nav_df = pd.DataFrame(daily_nav)
    if len(nav_df) > 0:
        # 计算累计收益
        nav_df['cumulative_return'] = nav_df['portfolio_value'] / initial_capital - 1

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

        risk_free_rate = 0.02
        excess_returns = daily_returns - risk_free_rate / 252
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
            'holding_days': holding_days,
            'initial_capital': initial_capital,
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

        print(f"\nT+{holding_days} 绩效指标:")
        print(f"  最终价值: {summary['final_value']:,.0f}")
        print(f"  总收益: {summary['total_return']:.4f} ({summary['total_return']*100:.2f}%)")
        print(f"  年化收益: {summary['annual_return']:.4f} ({summary['annual_return']*100:.2f}%)")
        print(f"  最大回撤: {summary['max_drawdown']:.4f} ({summary['max_drawdown']*100:.2f}%)")
        print(f"  夏普比率: {summary['sharpe_ratio']:.4f}")
        print(f"  胜率: {summary['win_rate']:.2%}")
        print(f"  盈亏比: {summary['profit_loss_ratio']:.2f}")

    return {
        'daily_nav': nav_df,
        'daily_records': pd.DataFrame(daily_records),
        'trade_records': pd.DataFrame(trade_records),
        'summary': summary
    }


def calculate_benchmark_performance(index_df: pd.DataFrame, initial_capital: float = 1000000.0) -> pd.DataFrame:
    """计算基准指数表现"""
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


def run_multi_period_backtest(start_date: str = '20250101',
                              end_date: str = '20250630',
                              holding_periods: list = [5, 10, 20, 30],
                              outlier_sigma: float = 3.0,
                              initial_capital: float = 1000000.0) -> dict:
    """
    主回测函数 - 多持有期对比

    参数:
        start_date: 开始日期
        end_date: 结束日期
        holding_periods: 持有期列表 [5, 10, 20, 30]
        outlier_sigma: 异常值阈值
        initial_capital: 初始资金

    返回:
        dict: 各持有期的回测结果
    """
    print("\n" + "="*80)
    print("alpha_peg因子 - 多持有期对比回测")
    print("="*80)
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"持有期测试: {holding_periods}")
    print(f"异常值处理: {outlier_sigma}σ")
    print(f"初始资金: {initial_capital:,.0f}")
    print(f"交易成本: {TOTAL_COST:.4f} (佣金{COMMISSION:.4f} + 印花税{STAMP_TAX:.4f} + 滑点{SLIPPAGE:.4f})")
    print("="*80)

    # 1. 数据提取
    print("\n【步骤1】数据提取...")
    df_pe, df_fina, df_industry = get_data_by_period(start_date, end_date)

    if len(df_pe) == 0 or len(df_fina) == 0 or len(df_industry) == 0:
        print("❌ 数据不完整，回测失败")
        return {}

    # 2. 因子计算与排名
    print("\n【步骤2】因子计算与排名...")
    factor_df = calc_alpha_peg_industry_rank(df_pe, df_fina, df_industry, outlier_sigma)

    if len(factor_df) == 0:
        print("❌ 因子计算失败")
        return {}

    # 3. 选股（每行业前3）
    print("\n【步骤3】选股（每行业前3）...")
    selected_df = select_top3_by_industry(factor_df)

    if len(selected_df) == 0:
        print("❌ 选股失败")
        return {}

    # 4. 获取价格数据
    print("\n【步骤4】获取价格数据...")
    price_df = get_price_data(start_date, end_date)

    if len(price_df) == 0:
        print("❌ 价格数据获取失败")
        return {}

    # 5. 获取基准数据
    print("\n【步骤5】获取基准数据...")
    index_df = get_index_data(start_date, end_date)

    # 6. 运行多持有期回测
    results = {}

    for holding_days in holding_periods:
        print(f"\n【步骤6.{holding_days}】运行T+{holding_days}回测...")
        result = run_backtest_with_holding_period(selected_df, price_df, holding_days, initial_capital)
        results[f'T+{holding_days}'] = result

    # 7. 对比基准
    if len(index_df) > 0:
        benchmark_nav = calculate_benchmark_performance(index_df, initial_capital)
        results['benchmark'] = benchmark_nav

    # 8. 对比分析
    print(f"\n{'='*80}")
    print("多持有期对比分析")
    print(f"{'='*80}")

    comparison = []
    for period_name, result in results.items():
        if period_name != 'benchmark':
            summary = result['summary']
            comparison.append({
                '持有期': period_name,
                '总收益': summary['total_return'],
                '年化收益': summary['annual_return'],
                '夏普比率': summary['sharpe_ratio'],
                '最大回撤': summary['max_drawdown'],
                '胜率': summary['win_rate'],
                '盈亏比': summary['profit_loss_ratio'],
                '交易次数': summary['total_trades']
            })

    if comparison:
        comp_df = pd.DataFrame(comparison)
        print("\n各持有期绩效对比:")
        print(comp_df.to_string(index=False, formatters={
            '总收益': '{:.2%}'.format,
            '年化收益': '{:.2%}'.format,
            '夏普比率': '{:.3f}'.format,
            '最大回撤': '{:.2%}'.format,
            '胜率': '{:.2%}'.format,
            '盈亏比': '{:.2f}'.format
        }))

        # 找出最优持有期
        if len(comp_df) > 0:
            best_by_sharpe = comp_df.loc[comp_df['夏普比率'].idxmax()]
            best_by_return = comp_df.loc[comp_df['总收益'].idxmax()]

            print(f"\n💡 最优持有期分析:")
            print(f"  按夏普比率: {best_by_sharpe['持有期']} (夏普={best_by_sharpe['夏普比率']:.3f})")
            print(f"  按总收益: {best_by_return['持有期']} (收益={best_by_return['总收益']:.2%})")

            # 综合推荐
            comp_df['综合评分'] = comp_df['夏普比率'] - comp_df['最大回撤'].abs() * 2
            best_overall = comp_df.loc[comp_df['综合评分'].idxmax()]
            print(f"  综合推荐: {best_overall['持有期']} (夏普={best_overall['夏普比率']:.3f}, 回撤={best_overall['最大回撤']:.2%})")

    # 9. 保存结果
    print(f"\n【步骤7】保存结果...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = '/home/zcy/alpha006_20251223/results/backtest/'

    # 保存对比结果
    if comparison:
        comp_df.to_csv(f"{output_dir}multi_period_comparison_{timestamp}.csv", index=False)
        print(f"✓ 对比结果已保存: {output_dir}multi_period_comparison_{timestamp}.csv")

    # 保存各持有期详细结果
    for period_name, result in results.items():
        if period_name != 'benchmark' and len(result['daily_nav']) > 0:
            nav_file = f"{output_dir}nav_{period_name.replace('+', '')}_{timestamp}.csv"
            result['daily_nav'].to_csv(nav_file, index=False)
            print(f"✓ {period_name}净值已保存: {nav_file}")

    print(f"\n所有结果已保存至: {output_dir}")
    return results


if __name__ == "__main__":
    # 运行多持有期回测
    results = run_multi_period_backtest(
        start_date='20250101',
        end_date='20250630',
        holding_periods=[5, 10, 20, 30],
        outlier_sigma=3.0,
        initial_capital=1000000.0
    )

    if results:
        print("\n" + "="*80)
        print("✅ 多持有期回测完成！")
        print("="*80)
