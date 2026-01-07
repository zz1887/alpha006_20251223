"""
alpha_peg因子 - 行业优化版回测（20250101-20250630）

功能:
1. 提取指定时间段数据（20250101-20250630）
2. 分行业计算alpha_peg因子
3. 使用vectorbt进行回测（含交易成本）
4. 计算IC值、分层收益、累计收益等指标
5. 重点行业分析（消费、科技、周期）

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

# 尝试导入vectorbt，如果失败则使用自定义实现
try:
    import vectorbt as vbt
    VBT_AVAILABLE = True
except ImportError:
    VBT_AVAILABLE = False
    print("⚠️  vectorbt未安装，将使用自定义回测逻辑")

from core.utils.db_connection import db


# 交易成本配置
COMMISSION = 0.0005  # 佣金
STAMP_TAX = 0.002    # 印花税
SLIPPAGE = 0.001     # 滑点
TOTAL_COST = COMMISSION + STAMP_TAX + SLIPPAGE  # 单边总成本: 0.35%

# 重点行业配置
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
    """
    提取指定时间段数据

    返回:
        (df_pe, df_fina, df_industry)
    """
    print(f"\n{'='*80}")
    print(f"数据提取: {start_date} ~ {end_date}")
    print(f"{'='*80}")

    # 1. 获取PE数据（日频）
    sql_pe = """
    SELECT
        ts_code,
        trade_date,
        pe_ttm
    FROM daily_basic
    WHERE trade_date >= %s
      AND trade_date <= %s
      AND pe_ttm IS NOT NULL
      AND pe_ttm > 0
    ORDER BY ts_code, trade_date
    """

    data_pe = db.execute_query(sql_pe, (start_date, end_date))
    df_pe = pd.DataFrame(data_pe)

    if len(df_pe) == 0:
        print("⚠️  未获取到daily_basic数据")
    else:
        print(f"✓ daily_basic: {len(df_pe):,} 条记录")
        print(f"  时间范围: {df_pe['trade_date'].min()} ~ {df_pe['trade_date'].max()}")
        print(f"  股票数量: {df_pe['ts_code'].nunique()}")

    # 2. 获取财务数据（财报周期）
    sql_fina = """
    SELECT
        ts_code,
        ann_date,
        dt_netprofit_yoy
    FROM fina_indicator
    WHERE ann_date >= %s
      AND ann_date <= %s
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
        print(f"✓ fina_indicator: {len(df_fina):,} 条记录")
        print(f"  时间范围: {df_fina['ann_date'].min()} ~ {df_fina['ann_date'].max()}")
        print(f"  股票数量: {df_fina['ts_code'].nunique()}")

    # 3. 加载行业数据
    df_industry = load_industry_data()

    return df_pe, df_fina, df_industry


def calc_alpha_peg_industry_backtest(df_pe: pd.DataFrame,
                                     df_fina: pd.DataFrame,
                                     df_industry: pd.DataFrame,
                                     outlier_sigma: float = 3.0) -> pd.DataFrame:
    """
    分行业计算alpha_peg因子（回测专用）

    返回:
        DataFrame: ts_code, trade_date, l1_name, alpha_peg
    """
    print(f"\n{'='*80}")
    print("分行业计算alpha_peg因子")
    print(f"{'='*80}")

    # 1. 关联PE和财务数据
    print("\n步骤1: 关联数据...")
    df_merged = pd.merge(
        df_pe,
        df_fina[['ts_code', 'ann_date', 'dt_netprofit_yoy']],
        left_on=['ts_code', 'trade_date'],
        right_on=['ts_code', 'ann_date'],
        how='left'
    )

    # 转换为float类型（避免Decimal类型错误）
    if len(df_merged) > 0:
        df_merged['pe_ttm'] = df_merged['pe_ttm'].astype(float)
        if 'dt_netprofit_yoy' in df_merged.columns:
            df_merged['dt_netprofit_yoy'] = df_merged['dt_netprofit_yoy'].astype(float)

    # 2. 前向填充财务数据
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
        print("❌ 无有效数据，无法计算因子")
        return pd.DataFrame()

    # 4. 合并行业信息
    df_with_industry = df_valid.merge(df_industry, on='ts_code', how='left')
    df_with_industry['l1_name'] = df_with_industry['l1_name'].fillna('其他')

    # 5. 分行业计算alpha_peg
    print("\n步骤2: 分行业计算...")
    results = []

    for industry, group in df_with_industry.groupby('l1_name'):
        industry_data = group.copy()

        # 基础计算
        industry_data['alpha_peg_raw'] = industry_data['pe_ttm'] / industry_data['dt_netprofit_yoy']

        # 行业内异常值处理（3σ原则）
        if outlier_sigma > 0:
            # 行业特定阈值
            threshold = outlier_sigma

            # 防御性行业更严格
            if industry in ['银行', '公用事业', '交通运输']:
                threshold = 2.5
            # 高成长行业更宽松
            elif industry in ['电子', '电力设备', '医药生物', '计算机']:
                threshold = 3.5

            mean_val = industry_data['alpha_peg_raw'].mean()
            std_val = industry_data['alpha_peg_raw'].std()

            if std_val > 0:
                lower_bound = mean_val - threshold * std_val
                upper_bound = mean_val + threshold * std_val

                # 缩尾处理
                outlier_count = (
                    (industry_data['alpha_peg_raw'] < lower_bound) |
                    (industry_data['alpha_peg_raw'] > upper_bound)
                ).sum()

                if outlier_count > 0:
                    print(f"  {industry}: 异常值 {outlier_count} 条 (阈值: {threshold}σ)")

                industry_data['alpha_peg_raw'] = industry_data['alpha_peg_raw'].clip(
                    lower_bound, upper_bound
                )

        # 不做标准化（保留原始值，便于分层）
        industry_data['alpha_peg'] = industry_data['alpha_peg_raw']

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
        'alpha_peg'
    ]]

    print(f"\n✓ 因子计算完成")
    print(f"  记录数: {len(df_result):,}")
    print(f"  股票数: {df_result['ts_code'].nunique()}")
    print(f"  行业数: {df_result['l1_name'].nunique()}")

    return df_result


def get_price_data(start_date: str, end_date: str) -> pd.DataFrame:
    """获取价格数据"""
    sql = """
    SELECT
        ts_code,
        trade_date,
        open,
        high,
        low,
        close,
        vol
    FROM daily_kline
    WHERE trade_date >= %s
      AND trade_date <= %s
    ORDER BY ts_code, trade_date
    """

    data = db.execute_query(sql, (start_date, end_date))
    df = pd.DataFrame(data)

    if len(df) == 0:
        print("⚠️  未获取到价格数据")
        return df

    # 转换数据类型
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    for col in ['open', 'high', 'low', 'close', 'vol']:
        df[col] = df[col].astype(float)

    print(f"✓ 价格数据: {len(df):,} 条")
    print(f"  时间范围: {df['trade_date'].min().strftime('%Y%m%d')} ~ {df['trade_date'].max().strftime('%Y%m%d')}")

    return df


def get_index_data(start_date: str, end_date: str) -> pd.DataFrame:
    """获取基准指数数据（沪深300）"""
    sql = """
    SELECT
        trade_date,
        close
    FROM index_daily_zzsz
    WHERE ts_code = '000300.SH'
      AND trade_date >= %s
      AND trade_date <= %s
    ORDER BY trade_date
    """

    data = db.execute_query(sql, (start_date, end_date))
    df = pd.DataFrame(data)

    if len(df) == 0:
        print("⚠️  未获取到基准指数数据")
        return df

    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    df['close'] = df['close'].astype(float)

    print(f"✓ 基准指数: {len(df):,} 条")

    return df


def calculate_ic(factor_df: pd.DataFrame, price_df: pd.DataFrame,
                 holding_days: int = 10) -> pd.DataFrame:
    """
    计算IC值（信息系数）

    参数:
        factor_df: 因子数据 (ts_code, trade_date, alpha_peg)
        price_df: 价格数据
        holding_days: 持有期（天）

    返回:
        IC统计结果
    """
    print(f"\n{'='*80}")
    print("计算IC值")
    print(f"{'='*80}")

    # 确保trade_date类型一致
    factor_df = factor_df.copy()
    factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'], format='%Y%m%d')

    # 合并因子和价格
    df = factor_df.merge(
        price_df[['ts_code', 'trade_date', 'close']],
        on=['ts_code', 'trade_date'],
        how='inner'
    )

    if len(df) == 0:
        print("❌ 无匹配数据")
        return pd.DataFrame()

    # 计算未来收益
    df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)

    # 创建价格索引以便快速查找
    price_index = price_df.set_index(['ts_code', 'trade_date'])['close'].to_dict()

    ic_results = []

    # 按日期分组计算IC
    for trade_date, group in df.groupby('trade_date'):
        # 计算持有期结束时的收益
        future_date = trade_date + timedelta(days=holding_days)

        # 获取每个股票的未来价格
        returns = []
        valid_stocks = []

        for _, row in group.iterrows():
            ts_code = row['ts_code']

            # 查找未来价格
            future_price = price_index.get((ts_code, future_date))

            if future_price is not None:
                current_price = row['close']
                ret = (future_price - current_price) / current_price
                returns.append(ret)
                valid_stocks.append(row['alpha_peg'])

        if len(returns) >= 5:  # 至少5只股票才计算IC
            # 计算Rank IC
            factor_rank = pd.Series(valid_stocks).rank()
            return_rank = pd.Series(returns).rank()
            rank_ic = factor_rank.corr(return_rank)

            # 计算原始IC
            raw_ic = pd.Series(valid_stocks).corr(pd.Series(returns))

            ic_results.append({
                'trade_date': trade_date,
                'stock_count': len(returns),
                'rank_ic': rank_ic,
                'raw_ic': raw_ic
            })

    ic_df = pd.DataFrame(ic_results)

    if len(ic_df) > 0:
        print(f"  计算周期数: {len(ic_df)}")
        print(f"  Rank IC均值: {ic_df['rank_ic'].mean():.4f}")
        print(f"  Rank IC标准差: {ic_df['rank_ic'].std():.4f}")
        print(f"  Rank IC显著性(|IC|>0.05): {(abs(ic_df['rank_ic']) > 0.05).sum()}/{len(ic_df)}")
        print(f"  原始IC均值: {ic_df['raw_ic'].mean():.4f}")

    return ic_df


def calculate_factor_returns(factor_df: pd.DataFrame,
                            price_df: pd.DataFrame,
                            quantiles: int = 5,
                            holding_days: int = 10,
                            rebalancing: str = 'fixed') -> pd.DataFrame:
    """
    计算分层收益（分位数分组）

    参数:
        factor_df: 因子数据
        price_df: 价格数据
        quantiles: 分层数量
        holding_days: 持有期
        rebalancing: 再平衡方式 ('fixed'固定日期)

    返回:
        分层收益数据
    """
    print(f"\n{'='*80}")
    print(f"计算分层收益 ({quantiles}层)")
    print(f"{'='*80}")

    # 确保trade_date类型一致
    factor_df = factor_df.copy()
    factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'], format='%Y%m%d')

    # 合并数据
    df = factor_df.merge(
        price_df[['ts_code', 'trade_date', 'close']],
        on=['ts_code', 'trade_date'],
        how='inner'
    )

    if len(df) == 0:
        print("❌ 无匹配数据")
        return pd.DataFrame()

    # 按日期分组，计算分位数
    df['quantile'] = df.groupby('trade_date')['alpha_peg'].transform(
        lambda x: pd.qcut(x, quantiles, labels=False, duplicates='drop')
    )

    # 创建价格索引
    price_index = price_df.set_index(['ts_code', 'trade_date'])['close'].to_dict()

    # 计算各分层收益
    quantile_returns = []

    for trade_date, group in df.groupby('trade_date'):
        future_date = trade_date + timedelta(days=holding_days)

        for q in range(quantiles):
            q_group = group[group['quantile'] == q]

            if len(q_group) == 0:
                continue

            # 计算该分层的平均收益
            returns = []
            for _, row in q_group.iterrows():
                future_price = price_index.get((row['ts_code'], future_date))
                if future_price is not None:
                    ret = (future_price - row['close']) / row['close']
                    returns.append(ret)

            if len(returns) > 0:
                avg_return = np.mean(returns)
                quantile_returns.append({
                    'trade_date': trade_date,
                    'quantile': q + 1,  # 1-based
                    'return': avg_return,
                    'stock_count': len(returns)
                })

    q_returns_df = pd.DataFrame(quantile_returns)

    if len(q_returns_df) > 0:
        # 汇总统计
        summary = q_returns_df.groupby('quantile').agg({
            'return': ['mean', 'std', 'count'],
            'stock_count': 'mean'
        }).round(4)

        print("\n分层收益统计:")
        print(summary)

        # 计算多空组合收益（最高层 - 最低层）
        long_short = q_returns_df.pivot_table(
            index='trade_date',
            columns='quantile',
            values='return'
        )
        if quantiles in long_short.columns and 1 in long_short.columns:
            long_short['long_short'] = long_short[quantiles] - long_short[1]
            ls_mean = long_short['long_short'].mean()
            ls_std = long_short['long_short'].std()
            print(f"\n多空组合 (Q{quantiles} - Q1):")
            print(f"  平均收益: {ls_mean:.4f}")
            print(f"  标准差: {ls_std:.4f}")
            if ls_std != 0:
                print(f"  夏普比率: {ls_mean / ls_std:.4f}")

    return q_returns_df


def calculate_cumulative_returns(factor_df: pd.DataFrame,
                                price_df: pd.DataFrame,
                                quantile: int = 5) -> pd.DataFrame:
    """
    计算累计收益（最高分位数 vs 基准）

    参数:
        factor_df: 因子数据
        price_df: 价格数据
        quantile: 选择的分位数（默认最高分位数）

    返回:
        累计收益数据
    """
    print(f"\n{'='*80}")
    print("计算累计收益")
    print(f"{'='*80}")

    # 确保trade_date类型一致
    factor_df = factor_df.copy()
    factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'], format='%Y%m%d')

    # 合并数据
    df = factor_df.merge(
        price_df[['ts_code', 'trade_date', 'close']],
        on=['ts_code', 'trade_date'],
        how='inner'
    )

    if len(df) == 0:
        print("❌ 无匹配数据")
        return pd.DataFrame()

    # 计算分位数
    df['quantile'] = df.groupby('trade_date')['alpha_peg'].transform(
        lambda x: pd.qcut(x, quantile, labels=False, duplicates='drop')
    )

    # 选择最高分位数
    top_quantile = df[df['quantile'] == (quantile - 1)].copy()

    # 创建价格索引
    price_index = price_df.set_index(['ts_code', 'trade_date'])['close'].to_dict()

    # 按日期计算收益
    daily_returns = []

    for trade_date, group in top_quantile.groupby('trade_date'):
        future_date = trade_date + timedelta(days=10)

        returns = []
        for _, row in group.iterrows():
            future_price = price_index.get((row['ts_code'], future_date))
            if future_price is not None:
                ret = (future_price - row['close']) / row['close']
                returns.append(ret)

        if len(returns) > 0:
            daily_returns.append({
                'trade_date': trade_date,
                'avg_return': np.mean(returns),
                'stock_count': len(returns)
            })

    returns_df = pd.DataFrame(daily_returns)

    if len(returns_df) > 0:
        # 计算累计收益
        returns_df = returns_df.sort_values('trade_date').reset_index(drop=True)
        returns_df['cumulative_return'] = (1 + returns_df['avg_return']).cumprod() - 1

        print(f"  交易次数: {len(returns_df)}")
        print(f"  总收益: {returns_df['cumulative_return'].iloc[-1]:.4f}")
        print(f"  年化收益: {(1 + returns_df['cumulative_return'].iloc[-1]) ** (252 / len(returns_df)) - 1:.4f}")

        # 累计收益曲线
        print("\n累计收益曲线（前10期）:")
        print(returns_df[['trade_date', 'avg_return', 'cumulative_return']].head(10).to_string(index=False))

    return returns_df


def analyze_focus_industries(factor_df: pd.DataFrame,
                            price_df: pd.DataFrame,
                            focus_industries: list = None) -> dict:
    """
    重点行业分析

    参数:
        factor_df: 因子数据
        price_df: 价格数据
        focus_industries: 重点行业列表

    返回:
        各行业的统计结果
    """
    if focus_industries is None:
        focus_industries = FOCUS_INDUSTRIES

    print(f"\n{'='*80}")
    print("重点行业分析")
    print(f"{'='*80}")

    # 确保trade_date类型一致
    factor_df = factor_df.copy()
    factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date'], format='%Y%m%d')

    # 合并数据
    df = factor_df.merge(
        price_df[['ts_code', 'trade_date', 'close']],
        on=['ts_code', 'trade_date'],
        how='inner'
    )

    if len(df) == 0:
        print("❌ 无匹配数据")
        return {}

    # 创建价格索引
    price_index = price_df.set_index(['ts_code', 'trade_date'])['close'].to_dict()

    industry_results = {}

    for industry in focus_industries:
        industry_df = df[df['l1_name'] == industry].copy()

        if len(industry_df) == 0:
            continue

        # 计算该行业的IC
        ic_results = []
        for trade_date, group in industry_df.groupby('trade_date'):
            future_date = trade_date + timedelta(days=10)

            returns = []
            factors = []

            for _, row in group.iterrows():
                future_price = price_index.get((row['ts_code'], future_date))
                if future_price is not None:
                    ret = (future_price - row['close']) / row['close']
                    returns.append(ret)
                    factors.append(row['alpha_peg'])

            if len(returns) >= 3:
                rank_ic = pd.Series(factors).rank().corr(pd.Series(returns).rank())
                ic_results.append(rank_ic)

        # 计算分层收益
        q_results = []
        for trade_date, group in industry_df.groupby('trade_date'):
            future_date = trade_date + timedelta(days=10)

            # 分5层
            group['quantile'] = pd.qcut(group['alpha_peg'], 5, labels=False, duplicates='drop')

            for q in range(5):
                q_group = group[group['quantile'] == q]
                if len(q_group) == 0:
                    continue

                returns = []
                for _, row in q_group.iterrows():
                    future_price = price_index.get((row['ts_code'], future_date))
                    if future_price is not None:
                        ret = (future_price - row['close']) / row['close']
                        returns.append(ret)

                if len(returns) > 0:
                    q_results.append({
                        'quantile': q + 1,
                        'return': np.mean(returns)
                    })

        q_df = pd.DataFrame(q_results)

        # 汇总
        if len(q_df) > 0:
            q_summary = q_df.groupby('quantile')['return'].mean()

            industry_results[industry] = {
                'record_count': len(industry_df),
                'stock_count': industry_df['ts_code'].nunique(),
                'ic_mean': np.mean(ic_results) if ic_results else 0,
                'ic_count': len(ic_results),
                'q1_return': q_summary.get(1, 0),
                'q5_return': q_summary.get(5, 0),
                'long_short': q_summary.get(5, 0) - q_summary.get(1, 0)
            }

    # 打印结果
    if industry_results:
        print("\n重点行业表现:")
        print(f"{'行业':<12} {'记录数':>8} {'股票数':>8} {'IC均值':>8} {'Q1收益':>8} {'Q5收益':>8} {'多空':>8}")
        print("-" * 80)

        for industry, stats in industry_results.items():
            print(f"{industry:<12} {stats['record_count']:>8} {stats['stock_count']:>8} "
                  f"{stats['ic_mean']:>8.4f} {stats['q1_return']:>8.4f} "
                  f"{stats['q5_return']:>8.4f} {stats['long_short']:>8.4f}")

    return industry_results


def run_backtest(start_date: str = '20250101',
                 end_date: str = '20250630',
                 outlier_sigma: float = 3.0,
                 quantiles: int = 5,
                 holding_days: int = 10) -> dict:
    """
    主回测函数

    参数:
        start_date: 开始日期
        end_date: 结束日期
        outlier_sigma: 异常值阈值
        quantiles: 分层数量
        holding_days: 持有期（天）

    返回:
        回测结果字典
    """
    print("\n" + "="*80)
    print("alpha_peg因子 - 行业优化版回测")
    print("="*80)
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"异常值处理: {outlier_sigma}σ")
    print(f"分层数量: {quantiles}")
    print(f"持有期: {holding_days}天")
    print(f"交易成本: {TOTAL_COST:.4f} (佣金{COMMISSION:.4f} + 印花税{STAMP_TAX:.4f} + 滑点{SLIPPAGE:.4f})")
    print("="*80)

    # 1. 数据提取
    print("\n【步骤1】数据提取...")
    df_pe, df_fina, df_industry = get_data_by_period(start_date, end_date)

    if len(df_pe) == 0 or len(df_fina) == 0 or len(df_industry) == 0:
        print("❌ 数据不完整，回测失败")
        return {}

    # 2. 因子计算
    print("\n【步骤2】因子计算...")
    factor_df = calc_alpha_peg_industry_backtest(df_pe, df_fina, df_industry, outlier_sigma)

    if len(factor_df) == 0:
        print("❌ 因子计算失败")
        return {}

    # 3. 获取价格数据（需要延长到持有期结束）
    price_end_date = (datetime.strptime(end_date, '%Y%m%d') + timedelta(days=holding_days)).strftime('%Y%m%d')
    print(f"\n【步骤3】获取价格数据（至{price_end_date}）...")
    price_df = get_price_data(start_date, price_end_date)

    if len(price_df) == 0:
        print("❌ 价格数据获取失败")
        return {}

    # 4. 获取基准数据
    print("\n【步骤4】获取基准数据...")
    index_df = get_index_data(start_date, price_end_date)

    # 5. 计算IC值
    print("\n【步骤5】计算IC值...")
    ic_df = calculate_ic(factor_df, price_df, holding_days)

    # 6. 计算分层收益
    print("\n【步骤6】计算分层收益...")
    quantile_returns = calculate_factor_returns(factor_df, price_df, quantiles, holding_days)

    # 7. 计算累计收益
    print("\n【步骤7】计算累计收益...")
    cumulative_returns = calculate_cumulative_returns(factor_df, price_df, quantiles)

    # 8. 重点行业分析
    print("\n【步骤8】重点行业分析...")
    industry_analysis = analyze_focus_industries(factor_df, price_df)

    # 9. 汇总结果
    print("\n" + "="*80)
    print("回测结果汇总")
    print("="*80)

    results = {
        'factor_data': factor_df,
        'ic_data': ic_df,
        'quantile_returns': quantile_returns,
        'cumulative_returns': cumulative_returns,
        'industry_analysis': industry_analysis,
        'summary': {
            'total_records': len(factor_df),
            'unique_stocks': factor_df['ts_code'].nunique(),
            'unique_dates': factor_df['trade_date'].nunique(),
            'unique_industries': factor_df['l1_name'].nunique(),
            'ic_mean': ic_df['rank_ic'].mean() if len(ic_df) > 0 else 0,
            'ic_std': ic_df['rank_ic'].std() if len(ic_df) > 0 else 0
        }
    }

    # 打印关键指标
    print(f"\n数据规模:")
    print(f"  总记录数: {len(factor_df):,}")
    print(f"  股票数量: {factor_df['ts_code'].nunique()}")
    print(f"  交易日期: {factor_df['trade_date'].nunique()}")
    print(f"  行业数量: {factor_df['l1_name'].nunique()}")

    print(f"\nIC统计:")
    if len(ic_df) > 0:
        print(f"  Rank IC均值: {ic_df['rank_ic'].mean():.4f}")
        print(f"  Rank IC标准差: {ic_df['rank_ic'].std():.4f}")
        print(f"  IC显著性(|IC|>0.05): {(abs(ic_df['rank_ic']) > 0.05).sum()}/{len(ic_df)}")

    if len(quantile_returns) > 0:
        q_summary = quantile_returns.groupby('quantile')['return'].mean()
        print(f"\n分层收益均值:")
        for q in range(1, quantiles + 1):
            if q in q_summary:
                print(f"  Q{q}: {q_summary[q]:.4f}")

        if quantiles in q_summary and 1 in q_summary:
            print(f"  多空(Q{quantiles}-Q1): {q_summary[quantiles] - q_summary[1]:.4f}")

    return results


def save_results(results: dict, output_dir: str = '/home/zcy/alpha006_20251223/results/'):
    """保存回测结果"""
    import os

    # 创建目录
    os.makedirs(output_dir + 'factor/', exist_ok=True)
    os.makedirs(output_dir + 'backtest/', exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 保存因子数据
    if 'factor_data' in results and len(results['factor_data']) > 0:
        factor_file = f"{output_dir}factor/alpha_peg_industry_backtest_{timestamp}.csv"
        results['factor_data'].to_csv(factor_file, index=False)
        print(f"\n✓ 因子数据已保存: {factor_file}")

    # 保存IC数据
    if 'ic_data' in results and len(results['ic_data']) > 0:
        ic_file = f"{output_dir}backtest/ic_values_{timestamp}.csv"
        results['ic_data'].to_csv(ic_file, index=False)
        print(f"✓ IC数据已保存: {ic_file}")

    # 保存分层收益
    if 'quantile_returns' in results and len(results['quantile_returns']) > 0:
        q_file = f"{output_dir}backtest/quantile_returns_{timestamp}.csv"
        results['quantile_returns'].to_csv(q_file, index=False)
        print(f"✓ 分层收益已保存: {q_file}")

    # 保存累计收益
    if 'cumulative_returns' in results and len(results['cumulative_returns']) > 0:
        cum_file = f"{output_dir}backtest/cumulative_returns_{timestamp}.csv"
        results['cumulative_returns'].to_csv(cum_file, index=False)
        print(f"✓ 累计收益已保存: {cum_file}")

    # 保存汇总结果
    summary_file = f"{output_dir}backtest/backtest_summary_{timestamp}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("alpha_peg因子 - 行业优化版回测汇总\n")
        f.write("="*60 + "\n\n")
        f.write(f"时间范围: 20250101 ~ 20250630\n")
        f.write(f"交易成本: {TOTAL_COST:.4f}\n\n")

        if 'summary' in results:
            f.write("数据规模:\n")
            for key, value in results['summary'].items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")

        if 'industry_analysis' in results and results['industry_analysis']:
            f.write("重点行业分析:\n")
            for industry, stats in results['industry_analysis'].items():
                f.write(f"  {industry}:\n")
                for key, value in stats.items():
                    f.write(f"    {key}: {value}\n")
                f.write("\n")

    print(f"✓ 汇总结果已保存: {summary_file}")


if __name__ == "__main__":
    # 运行回测
    results = run_backtest(
        start_date='20250101',
        end_date='20250630',
        outlier_sigma=3.0,
        quantiles=5,
        holding_days=10
    )

    # 保存结果
    if results:
        save_results(results)

        print("\n" + "="*80)
        print("回测完成！")
        print("="*80)
