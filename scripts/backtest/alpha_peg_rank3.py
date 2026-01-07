"""
alpha_peg因子 - 分行业排名前3回测（20250101-20250630）

策略逻辑:
1. 分行业对alpha_peg排名（值越小越靠前）
2. 每行业选前3名个股
3. T日买入，T+1日卖出（持有1天）
4. 等权重分配资金

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

# 重点行业（可选）
FOCUS_INDUSTRIES = ['食品饮料', '家用电器', '电子', '电力设备', '计算机', '机械设备', '基础化工', '有色金属']


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
    """
    分行业计算alpha_peg因子并排名

    返回:
        DataFrame: ts_code, trade_date, l1_name, alpha_peg, industry_rank
    """
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
    """
    每行业选择alpha_peg排名前3的个股

    返回:
        DataFrame: ts_code, trade_date, l1_name, alpha_peg, industry_rank
    """
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


def run_rank3_backtest(selected_df: pd.DataFrame,
                       price_df: pd.DataFrame,
                       index_df: pd.DataFrame,
                       initial_capital: float = 1000000.0,
                       holding_days: int = 1) -> dict:
    """
    运行T+N回测（每行业选前3，持有N天）

    参数:
        selected_df: 选股结果
        price_df: 价格数据
        index_df: 基准数据
        initial_capital: 初始资金
        holding_days: 持有天数（默认1天）

    返回:
        dict: 包含每日持仓、交易记录、绩效指标
    """
    print(f"\n{'='*80}")
    print(f"运行T+{holding_days}回测（每行业前3，持有{holding_days}天）")
    print(f"{'='*80}")

    # 1. 准备数据
    # 确保日期格式一致
    selected_df = selected_df.copy()
    selected_df['trade_date'] = pd.to_datetime(selected_df['trade_date'], format='%Y%m%d')

    # 创建价格索引
    price_index = price_df.set_index(['ts_code', 'trade_date'])[['open', 'close']].to_dict('index')

    # 按日期排序
    trade_dates = sorted(selected_df['trade_date'].unique())

    # 2. 回测主循环
    portfolio_value = initial_capital
    daily_records = []  # 每日持仓明细
    trade_records = []  # 交易记录
    daily_nav = []      # 每日净值

    print(f"\n开始回测，交易日期数: {len(trade_dates)}")

    for i, trade_date in enumerate(trade_dates):
        # 获取当日选中股票
        today_stocks = selected_df[selected_df['trade_date'] == trade_date]['ts_code'].tolist()
        stock_count = len(today_stocks)

        if stock_count == 0:
            # 无持仓，净值不变
            daily_nav.append({
                'trade_date': trade_date,
                'portfolio_value': portfolio_value,
                'daily_return': 0,
                'stock_count': 0
            })
            continue

        # T日：买入（按开盘价）
        buy_prices = []
        valid_stocks = []

        for ts_code in today_stocks:
            price_key = (ts_code, trade_date)
            if price_key in price_index:
                open_price = price_index[price_key]['open']
                buy_prices.append(open_price)
                valid_stocks.append(ts_code)

        if len(valid_stocks) == 0:
            continue

        # 等权重分配资金（扣除买入成本）
        capital_per_stock = portfolio_value / len(valid_stocks)
        buy_cost_total = 0

        for buy_price in buy_prices:
            # 买入成本: 佣金0.05% + 滑点0.1%
            buy_cost = capital_per_stock * (1 + COMMISSION + SLIPPAGE)
            buy_cost_total += buy_cost

        # 记录每日持仓（T日买入后）
        daily_records.append({
            'trade_date': trade_date,
            'stock_count': len(valid_stocks),
            'portfolio_value': portfolio_value,
            'daily_return': (portfolio_value - initial_capital) / initial_capital if i == 0 else 0
        })

        # 记录净值（T日收盘时，持仓未卖出）
        # 计算当前持仓市值
        current_positions_value = 0
        for ts_code in valid_stocks:
            price_key = (ts_code, trade_date)
            if price_key in price_index:
                current_positions_value += capital_per_stock / price_index[price_key]['open'] * price_index[price_key]['close']

        daily_nav.append({
            'trade_date': trade_date,
            'portfolio_value': portfolio_value,  # 现金（已扣除买入成本）
            'positions_value': current_positions_value,  # 持仓市值
            'total_value': portfolio_value + current_positions_value,  # 总价值
            'daily_return': 0,  # 将在下一日计算
            'stock_count': len(valid_stocks)
        })

        # 计算当日实际收益率（基于总价值）
        if i > 0:
            prev_value = daily_nav[-2]['total_value']
            current_value = portfolio_value + current_positions_value
            daily_return = (current_value - prev_value) / prev_value if prev_value > 0 else 0
            daily_nav[-2]['daily_return'] = daily_return

        if (i + 1) % 10 == 0:
            print(f"  进度: {i+1}/{len(trade_dates)} 日期，当前净值: {portfolio_value:,.0f}")

    # 3. 计算绩效指标
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
        volatility = daily_returns.std() * np.sqrt(252)  # 年化波动率

        risk_free_rate = 0.02  # 假设无风险利率2%
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

        print(f"\n绩效指标:")
        print(f"  初始资金: {initial_capital:,.0f}")
        print(f"  最终价值: {summary['final_value']:,.0f}")
        print(f"  总收益: {summary['total_return']:.4f} ({summary['total_return']*100:.2f}%)")
        print(f"  年化收益: {summary['annual_return']:.4f} ({summary['annual_return']*100:.2f}%)")
        print(f"  最大回撤: {summary['max_drawdown']:.4f} ({summary['max_drawdown']*100:.2f}%)")
        print(f"  年化波动率: {summary['volatility']:.4f} ({summary['volatility']*100:.2f}%)")
        print(f"  夏普比率: {summary['sharpe_ratio']:.4f}")
        print(f"  总交易次数: {summary['total_trades']}")
        print(f"  胜率: {summary['win_rate']:.2%}")
        print(f"  盈亏比: {summary['profit_loss_ratio']:.2f}")
        print(f"  平均每日持仓: {summary['avg_stocks_per_day']:.1f} 只")

    return {
        'daily_nav': nav_df,
        'daily_records': pd.DataFrame(daily_records),
        'trade_records': pd.DataFrame(trade_records) if trade_records else pd.DataFrame(),
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


def compare_with_benchmark(portfolio_results: dict, benchmark_df: pd.DataFrame):
    """对比策略与基准"""
    print(f"\n{'='*80}")
    print("策略 vs 基准对比")
    print(f"{'='*80}")

    if len(benchmark_df) == 0 or len(portfolio_results['daily_nav']) == 0:
        print("❌ 数据不足，无法对比")
        return

    # 合并数据
    nav_df = portfolio_results['daily_nav'][['trade_date', 'portfolio_value', 'cumulative_return']].copy()
    nav_df['trade_date'] = pd.to_datetime(nav_df['trade_date'])

    benchmark_df = benchmark_df.copy()
    benchmark_df['trade_date'] = pd.to_datetime(benchmark_df['trade_date'])

    # 对齐日期
    merged = pd.merge(
        nav_df,
        benchmark_df[['trade_date', 'benchmark_return']],
        on='trade_date',
        how='inner'
    )

    if len(merged) == 0:
        print("❌ 日期无法对齐")
        return

    # 计算超额收益
    merged['excess_return'] = merged['cumulative_return'] - merged['benchmark_return']

    # 统计
    print(f"策略总收益: {merged['cumulative_return'].iloc[-1]:.4f} ({merged['cumulative_return'].iloc[-1]*100:.2f}%)")
    print(f"基准总收益: {merged['benchmark_return'].iloc[-1]:.4f} ({merged['benchmark_return'].iloc[-1]*100:.2f}%)")
    print(f"超额收益: {merged['excess_return'].iloc[-1]:.4f} ({merged['excess_return'].iloc[-1]*100:.2f}%)")

    # 胜率
    positive_excess = (merged['excess_return'] > 0).sum()
    excess_win_rate = positive_excess / len(merged)
    print(f"超额胜率: {excess_win_rate:.2%}")

    return merged


def save_results(results: dict, selected_df: pd.DataFrame, output_dir: str = '/home/zcy/alpha006_20251223/results/'):
    """保存回测结果"""
    import os

    # 创建目录
    os.makedirs(output_dir + 'factor/', exist_ok=True)
    os.makedirs(output_dir + 'backtest/', exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 1. 保存选股明细
    if len(selected_df) > 0:
        selection_file = f"{output_dir}backtest/selection_rank3_{timestamp}.csv"
        selected_df.to_csv(selection_file, index=False)
        print(f"\n✓ 选股明细已保存: {selection_file}")

    # 2. 保存每日持仓
    if len(results['daily_records']) > 0:
        daily_file = f"{output_dir}backtest/daily_holdings_rank3_{timestamp}.csv"
        results['daily_records'].to_csv(daily_file, index=False)
        print(f"✓ 每日持仓已保存: {daily_file}")

    # 3. 保存交易记录
    if len(results['trade_records']) > 0:
        trade_file = f"{output_dir}backtest/trades_rank3_{timestamp}.csv"
        results['trade_records'].to_csv(trade_file, index=False)
        print(f"✓ 交易记录已保存: {trade_file}")

    # 4. 保存每日净值
    if len(results['daily_nav']) > 0:
        nav_file = f"{output_dir}backtest/nav_rank3_{timestamp}.csv"
        results['daily_nav'].to_csv(nav_file, index=False)
        print(f"✓ 每日净值已保存: {nav_file}")

    # 5. 保存绩效汇总
    summary_file = f"{output_dir}backtest/performance_summary_rank3_{timestamp}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("alpha_peg因子 - 分行业排名前3回测绩效汇总\n")
        f.write("="*60 + "\n\n")
        f.write(f"回测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"时间范围: 20250101 ~ 20250630\n")
        f.write(f"策略: 分行业选alpha_peg前3，T+1平仓\n\n")

        f.write("绩效指标:\n")
        for key, value in results['summary'].items():
            if isinstance(value, float):
                f.write(f"  {key}: {value:.6f}\n")
            else:
                f.write(f"  {key}: {value}\n")

        f.write("\n策略说明:\n")
        f.write("  1. 分行业对alpha_peg排名（值越小越靠前）\n")
        f.write("  2. 每行业选择前3名个股\n")
        f.write("  3. T日买入，T+1日卖出（持有1天）\n")
        f.write("  4. 等权重分配资金\n")
        f.write("  5. 交易成本: 佣金0.05% + 印花税0.2% + 滑点0.1%\n")

    print(f"✓ 绩效汇总已保存: {summary_file}")

    print(f"\n所有结果已保存至: {output_dir}backtest/")


def run_backtest(start_date: str = '20250101',
                 end_date: str = '20250630',
                 outlier_sigma: float = 3.0,
                 initial_capital: float = 1000000.0) -> dict:
    """
    主回测函数

    参数:
        start_date: 开始日期
        end_date: 结束日期
        outlier_sigma: 异常值阈值
        initial_capital: 初始资金

    返回:
        dict: 回测结果
    """
    print("\n" + "="*80)
    print("alpha_peg因子 - 分行业排名前3回测")
    print("="*80)
    print(f"时间范围: {start_date} ~ {end_date}")
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

    # 6. 运行回测
    print("\n【步骤6】运行回测...")
    results = run_rank3_backtest(selected_df, price_df, index_df, initial_capital)

    # 7. 对比基准
    if len(index_df) > 0:
        benchmark_nav = calculate_benchmark_performance(index_df, initial_capital)
        results['benchmark'] = benchmark_nav
        compare_with_benchmark(results, benchmark_nav)

    # 8. 保存结果
    print("\n【步骤7】保存结果...")
    save_results(results, selected_df)

    return results


if __name__ == "__main__":
    # 运行回测
    results = run_backtest(
        start_date='20250101',
        end_date='20250630',
        outlier_sigma=3.0,
        initial_capital=1000000.0
    )

    if results:
        print("\n" + "="*80)
        print("✅ 回测完成！")
        print("="*80)
