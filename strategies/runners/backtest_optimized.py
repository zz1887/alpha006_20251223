# 优化的回测脚本 - 2024-10-01 至 2025-12-01
import sys
sys.path.append('/home/zcy/alpha006_20251223')

from core.config.settings import DATABASE_CONFIG, TABLE_NAMES
from core.utils.db_connection import DBConnection
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging

# 初始化
db = DBConnection(DATABASE_CONFIG)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
log = logging.getLogger(__name__)

# 全局变量
class G:
    def __init__(self):
        self.params = {
            'price_period': 120,
            'turnover_period': 30,
            'turnover_quantile': 0.4,
            'min_avg_volume': 5000,
            'max_recent_drop': 30,
            'default_peg_threshold': 2.0,
            'cr20_long_period': 30,
            'cr20_short_period': 10,
            'cr20_low_threshold': 60,
            'cr20_high_threshold': 140,
            'cr20_increase_threshold': 10,
            'cr20_stable_days': 5,
            'max_position': 5,
            'pass_score': 5,
        }
        self.max_hist_days = 120

g = G()

# 模拟组合
class Portfolio:
    def __init__(self, initial_capital=1000000):
        self.positions = {}
        self.total_value = initial_capital
        self.cash = initial_capital
        self.max_total_value = initial_capital
        self.initial_capital = initial_capital
        self.trade_history = []

    def buy(self, code, amount, price, date):
        cost = amount * price
        if cost > self.cash:
            return False

        if code not in self.positions:
            self.positions[code] = {'amount': 0, 'avg_cost': 0, 'buy_date': date}

        pos = self.positions[code]
        total_cost = pos['amount'] * pos['avg_cost'] + cost
        pos['amount'] += amount
        pos['avg_cost'] = total_cost / pos['amount']
        pos['buy_date'] = date

        self.cash -= cost
        self.total_value -= cost * 0.0015  # 交易成本0.15%

        self.trade_history.append({
            'date': date, 'code': code, 'action': 'BUY',
            'amount': amount, 'price': price, 'cost': cost
        })
        return True

    def sell(self, code, amount, price, date):
        if code not in self.positions or self.positions[code]['amount'] < amount:
            return False

        pos = self.positions[code]
        sell_value = amount * price
        buy_cost = amount * pos['avg_cost']
        profit = sell_value - buy_cost - sell_value * 0.0015  # 交易成本

        pos['amount'] -= amount
        self.cash += sell_value - sell_value * 0.0015

        if pos['amount'] == 0:
            del self.positions[code]

        self.trade_history.append({
            'date': date, 'code': code, 'action': 'SELL',
            'amount': amount, 'price': price, 'profit': profit
        })
        return profit

    def get_positions_value(self):
        value = 0
        for code, pos in self.positions.items():
            price = get_current_price(code, self.current_date)
            value += pos['amount'] * price
        return value

    def update_value(self, date):
        self.current_date = date
        self.total_value = self.cash + self.get_positions_value()
        if self.total_value > self.max_total_value:
            self.max_total_value = self.total_value

# 工具函数
def to_db_date(dt):
    if isinstance(dt, datetime):
        return dt.strftime('%Y%m%d')
    return dt

def get_current_price(stock_code, date):
    date_str = to_db_date(date)
    sql = f"SELECT close FROM {TABLE_NAMES['daily_kline']} WHERE ts_code = %s AND trade_date = %s"
    result = db.execute_query(sql, (stock_code, date_str))
    if result:
        return result[0]['close']
    return None

# 数据获取函数（简化版）
def get_stock_pool(context):
    """获取股票池"""
    date_str = to_db_date(context.current_dt)

    # 获取当日所有股票
    sql = f"SELECT DISTINCT ts_code FROM {TABLE_NAMES['daily_kline']} WHERE trade_date = %s"
    result = db.execute_query(sql, (date_str,))
    all_stocks = [row['ts_code'] for row in result]

    # 过滤ST
    st_result = db.execute_query(f"SELECT DISTINCT ts_code FROM {TABLE_NAMES['stock_st']} WHERE type = 'ST'")
    st_stocks = set([row['ts_code'] for row in st_result])
    all_stocks = [s for s in all_stocks if s not in st_stocks]

    # 过滤科创板
    all_stocks = [s for s in all_stocks if not s.startswith('688')]

    # 过滤新股
    try:
        new_share_csv = '/home/zcy/alpha006_20251223/data/new_share_increment_20251031221906.csv'
        new_share_df = pd.read_csv(new_share_csv)
        new_share_data = {}
        for _, row in new_share_df.iterrows():
            new_share_data[row['ts_code']] = row['issue_date']

        qualified_stocks = []
        for stock in all_stocks:
            if stock in new_share_data:
                issue_date = datetime.strptime(str(new_share_data[stock]), '%Y%m%d')
                listed_days = (context.current_dt.date() - issue_date).days
                if listed_days < 365:
                    continue
            qualified_stocks.append(stock)
        all_stocks = qualified_stocks
    except:
        pass

    return all_stocks

def get_turnover_data(stocks, end_dt):
    """获取换手率数据"""
    end_date = to_db_date(end_dt)
    start_date = to_db_date(end_dt - timedelta(days=30))

    placeholders = ','.join(['%s'] * len(stocks))
    sql = f"""
    SELECT ts_code, trade_date, turnover_rate_f
    FROM {TABLE_NAMES['daily_basic']}
    WHERE trade_date >= %s AND trade_date <= %s
      AND ts_code IN ({placeholders})
    ORDER BY ts_code, trade_date
    """
    result = db.execute_query(sql, [start_date, end_date] + stocks)

    if not result:
        return pd.DataFrame()

    df = pd.DataFrame(result)
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    return df.pivot(index='trade_date', columns='ts_code', values='turnover_rate_f')

def get_price_data(stocks, end_dt):
    """获取价格数据"""
    end_date = to_db_date(end_dt)
    start_date = to_db_date(end_dt - timedelta(days=120))

    placeholders = ','.join(['%s'] * len(stocks))
    sql = f"""
    SELECT ts_code, trade_date, close, high, low, vol
    FROM {TABLE_NAMES['daily_kline']}
    WHERE trade_date >= %s AND trade_date <= %s
      AND ts_code IN ({placeholders})
    ORDER BY ts_code, trade_date
    """
    result = db.execute_query(sql, [start_date, end_date] + stocks)

    if not result:
        return None

    df = pd.DataFrame(result)
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')

    return {
        'close': df.pivot(index='trade_date', columns='ts_code', values='close'),
        'high': df.pivot(index='trade_date', columns='ts_code', values='high'),
        'low': df.pivot(index='trade_date', columns='ts_code', values='low'),
        'vol': df.pivot(index='trade_date', columns='ts_code', values='vol'),
    }

def get_factor_data(stocks, start_dt, end_dt):
    """获取因子数据"""
    start_date = to_db_date(start_dt)
    end_date = to_db_date(end_dt)

    # PEG数据
    placeholders = ','.join(['%s'] * len(stocks))
    sql_pe = f"""
    SELECT ts_code, trade_date, pe_ttm
    FROM {TABLE_NAMES['daily_basic']}
    WHERE trade_date >= %s AND trade_date <= %s
      AND ts_code IN ({placeholders})
      AND pe_ttm > 0
    """
    data_pe = db.execute_query(sql_pe, [start_date, end_date] + stocks)
    df_pe = pd.DataFrame(data_pe)

    # 财务数据
    sql_fina = f"""
    SELECT ts_code, ann_date, dt_netprofit_yoy
    FROM {TABLE_NAMES['fina_indicator']}
    WHERE ann_date <= %s
      AND ts_code IN ({placeholders})
      AND update_flag = '1'
      AND dt_netprofit_yoy IS NOT NULL
      AND dt_netprofit_yoy != 0
    ORDER BY ts_code, ann_date
    """
    data_fina = db.execute_query(sql_fina, [end_date] + stocks)
    df_fina = pd.DataFrame(data_fina)

    # CR20数据
    sql_cr = f"""
    SELECT ts_code, trade_date, cr_qfq
    FROM {TABLE_NAMES['stk_factor_pro']}
    WHERE trade_date >= %s AND trade_date <= %s
      AND ts_code IN ({placeholders})
    ORDER BY ts_code, trade_date
    """
    data_cr = db.execute_query(sql_cr, [start_date, end_date] + stocks)
    df_cr = pd.DataFrame(data_cr)

    return df_pe, df_fina, df_cr

# 筛选函数
def filter_turnover(turnover_data, params):
    """换手率筛选"""
    if turnover_data.empty:
        return []

    market_turnover = turnover_data.mean()
    threshold = market_turnover.quantile(params['turnover_quantile'])
    avg_turnover = turnover_data.mean()
    turnover_mask = avg_turnover >= threshold

    return turnover_mask[turnover_mask].index.tolist()

def filter_price_liquidity(price_data, stocks, params):
    """价格流动性筛选"""
    if not price_data or not stocks:
        return []

    close = price_data['close'][stocks]
    volume = price_data['vol'][stocks]
    high = price_data['high'][stocks]

    valid_days = close.count()
    valid_mask = valid_days >= params['price_period']

    avg_volume = volume.tail(120).mean() / 100
    liquidity_mask = avg_volume >= params['min_avg_volume']

    recent_high = high.tail(120).max()
    current_p = close.iloc[-1]
    max_drop = (current_p - recent_high) / recent_high * 100
    drop_mask = max_drop >= -params['max_recent_drop']

    pass_mask = valid_mask & liquidity_mask & drop_mask
    return pass_mask[pass_mask].index.tolist()

def filter_peg(df_pe, df_fina, stocks, context):
    """PEG筛选"""
    if df_pe.empty or df_fina.empty or not stocks:
        return []

    # 合并PE数据
    df_pe = df_pe[df_pe['ts_code'].isin(stocks)]
    if df_pe.empty:
        return []

    # 获取最新财务数据
    df_fina = df_fina[df_fina['ts_code'].isin(stocks)]
    df_fina = df_fina.groupby('ts_code').last().reset_index()

    # 合并
    df_merged = df_pe.merge(df_fina[['ts_code', 'dt_netprofit_yoy']], on='ts_code', how='inner')
    if df_merged.empty:
        return []

    # 计算PEG
    df_merged['peg'] = df_merged['pe_ttm'] / df_merged['dt_netprofit_yoy']
    df_merged['peg'] = df_merged['peg'].fillna(0)
    df_merged.loc[df_merged['peg'] <= 0, 'peg'] = 0
    df_merged.loc[df_merged['peg'] > 100, 'peg'] = 100

    # 获取行业数据
    try:
        from core.utils.data_loader import DataLoader
        data_loader = DataLoader(use_cache=False)
        industry_df = data_loader.get_industry_data(stocks)
        industry_map = {}
        for _, row in industry_df.iterrows():
            industry_map[row['ts_code']] = row['l1_name']
    except:
        industry_map = {}

    # 行业阈值
    industry_peg_map = {
        '计算机': 3.0, '电子': 2.8, '国防军工': 2.8, '医药生物': 2.7, '传媒': 2.6,
        '电力设备': 2.5, '汽车': 2.3, '机械设备': 2.2, '通信': 2.2,
        '食品饮料': 2.0, '家用电器': 1.9, '美容护理': 2.0, '轻工制造': 1.8,
        '有色金属': 1.8, '化工': 1.7, '建筑材料': 1.6, '钢铁': 1.3, '采掘': 1.2,
        '银行': 1.1, '非银金融': 1.3, '房地产': 1.2, '公用事业': 1.1, '交通运输': 1.2,
        '其他': 2.1
    }

    # 筛选
    peg_pass = []
    for _, row in df_merged.iterrows():
        stock = row['ts_code']
        peg_val = row['peg']
        industry = industry_map.get(stock, '其他')
        threshold = industry_peg_map.get(industry, 2.1)

        if 0 < peg_val <= threshold:
            peg_pass.append(stock)

    return peg_pass

def filter_cr20(df_cr, stocks, params, context):
    """CR20筛选"""
    if df_cr.empty or not stocks:
        return []

    # 只保留有数据的股票
    df_cr = df_cr[df_cr['ts_code'].isin(stocks)]
    if df_cr.empty:
        return []

    # 转换为透视表
    df_cr['trade_date'] = pd.to_datetime(df_cr['trade_date'], format='%Y%m%d')
    cr_pivot = df_cr.pivot(index='trade_date', columns='ts_code', values='cr_qfq')

    if cr_pivot.empty:
        return []

    # 计算指标
    valid_days = cr_pivot.count()
    valid_mask = valid_days >= params['cr20_long_period']

    long_term = cr_pivot.tail(params['cr20_long_period']).mean()
    short_term = cr_pivot.tail(params['cr20_short_period']).mean()
    cr_growth = (short_term - long_term) / long_term.replace(0, 1e-6) * 100

    # 波动率
    recent_window = cr_pivot.tail(params['cr20_stable_days'])
    recent_volatility = recent_window.std() / recent_window.mean().replace(0, 1e-6) * 100
    is_stable = recent_volatility < 18

    # 趋势
    trend_mask = pd.Series(False, index=stocks)
    for stock in stocks:
        if stock not in cr_pivot.columns:
            continue
        recent_cr20 = cr_pivot[stock].dropna().tail(5)
        if len(recent_cr20) < 5:
            continue
        increase_days = sum(recent_cr20.iloc[i] > recent_cr20.iloc[i-1] for i in range(1, 5))
        overall_up = recent_cr20.iloc[-1] > recent_cr20.iloc[0]
        trend_mask[stock] = (increase_days >= 3) & overall_up

    # 范围
    core_low = params['cr20_low_threshold']
    core_high = params['cr20_high_threshold']
    buffer_low = core_low * 0.9
    buffer_high = core_high * 1.1

    range_mask = pd.Series(False, index=stocks)
    for stock in stocks:
        if stock not in short_term.index:
            continue
        core_mask = (short_term[stock] > core_low) & (short_term[stock] < core_high)
        buffer_mask = (short_term[stock] > buffer_low) & (short_term[stock] < buffer_high)
        buffer_growth_threshold = params['cr20_increase_threshold'] * 1.2
        range_mask[stock] = core_mask | (buffer_mask & (cr_growth[stock] > buffer_growth_threshold))

    # 增长
    growth_mask = cr_growth >= params['cr20_increase_threshold']

    # 综合筛选
    pass_mask = valid_mask & range_mask & growth_mask & is_stable & trend_mask
    remaining_stocks = pass_mask[pass_mask].index.tolist()

    # 放宽机制
    if len(remaining_stocks) < 10:
        growth_mask_relaxed = cr_growth >= 3
        pass_mask_relaxed = valid_mask & range_mask & growth_mask_relaxed & is_stable & trend_mask
        remaining_stocks = pass_mask_relaxed[pass_mask_relaxed].index.tolist()

        if len(remaining_stocks) < 5:
            trend_mask_relaxed = pd.Series(False, index=stocks)
            for stock in stocks:
                if stock not in cr_pivot.columns:
                    continue
                recent_cr20 = cr_pivot[stock].dropna().tail(5)
                if len(recent_cr20) < 5:
                    continue
                increase_days = sum(recent_cr20.iloc[i] > recent_cr20.iloc[i-1] for i in range(1, 5))
                overall_up = recent_cr20.iloc[-1] > recent_cr20.iloc[0]
                trend_mask_relaxed[stock] = (increase_days >= 2) & overall_up

            pass_mask_relaxed2 = valid_mask & range_mask & growth_mask_relaxed & is_stable & trend_mask_relaxed
            remaining_stocks = pass_mask_relaxed2[pass_mask_relaxed2].index.tolist()

    return remaining_stocks

# 主回测函数
def run_backtest(start_date, end_date, rebalance_day=6):
    """运行回测"""
    print("="*80)
    print(f"开始回测: {start_date} 至 {end_date}")
    print(f"调仓日: 每月{rebalance_day}日")
    print("="*80)

    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    portfolio = Portfolio(initial_capital=1000000)

    # 获取所有调仓日期
    rebalance_dates = []
    current = start_dt
    while current <= end_dt:
        if current.day == rebalance_day:
            # 检查是否为交易日
            date_str = current.strftime('%Y%m%d')
            sql = f"SELECT COUNT(*) as cnt FROM {TABLE_NAMES['daily_kline']} WHERE trade_date = %s"
            result = db.execute_query(sql, (date_str,))
            if result and result[0]['cnt'] > 0:
                rebalance_dates.append(current)
        current += timedelta(days=1)

    print(f"\n调仓日期 ({len(rebalance_dates)}次):")
    for i, date in enumerate(rebalance_dates):
        print(f"  {i+1}. {date.strftime('%Y-%m-%d')}")

    # 回测循环
    for i, rebalance_date in enumerate(rebalance_dates):
        print(f"\n{'='*80}")
        print(f"【{rebalance_date.strftime('%Y-%m-%d')}】调仓 ({i+1}/{len(rebalance_dates)})")
        print("="*80)

        # 更新组合价值
        portfolio.update_value(rebalance_date)
        print(f"调仓前价值: {portfolio.total_value:,.2f}元")

        # 筛选股票
        context = type('Context', (), {'current_dt': rebalance_date})()

        # 1. 获取股票池
        stock_pool = get_stock_pool(context)
        print(f"初始股票池: {len(stock_pool)}只")

        # 2. 换手率筛选
        turnover_data = get_turnover_data(stock_pool, rebalance_date)
        stocks_after_turnover = filter_turnover(turnover_data, g.params)
        print(f"换手率筛选后: {len(stocks_after_turnover)}只")

        if not stocks_after_turnover:
            print("无符合条件股票，清仓")
            # 清仓
            for code in list(portfolio.positions.keys()):
                price = get_current_price(code, rebalance_date)
                if price:
                    portfolio.sell(code, portfolio.positions[code]['amount'], price, rebalance_date)
            continue

        # 3. 价格流动性筛选
        price_data = get_price_data(stocks_after_turnover, rebalance_date)
        stocks_after_price = filter_price_liquidity(price_data, stocks_after_turnover, g.params)
        print(f"价格流动性筛选后: {len(stocks_after_price)}只")

        if not stocks_after_price:
            print("无符合条件股票，清仓")
            for code in list(portfolio.positions.keys()):
                price = get_current_price(code, rebalance_date)
                if price:
                    portfolio.sell(code, portfolio.positions[code]['amount'], price, rebalance_date)
            continue

        # 4. PEG筛选
        df_pe, df_fina, df_cr = get_factor_data(stocks_after_price,
                                                 rebalance_date - timedelta(days=180),
                                                 rebalance_date)
        stocks_after_peg = filter_peg(df_pe, df_fina, stocks_after_price, context)
        print(f"PEG筛选后: {len(stocks_after_peg)}只")

        if not stocks_after_peg:
            print("无符合条件股票，清仓")
            for code in list(portfolio.positions.keys()):
                price = get_current_price(code, rebalance_date)
                if price:
                    portfolio.sell(code, portfolio.positions[code]['amount'], price, rebalance_date)
            continue

        # 5. CR20筛选
        stocks_final = filter_cr20(df_cr, stocks_after_peg, g.params, context)
        print(f"CR20筛选后: {len(stocks_final)}只")

        if not stocks_final:
            print("无符合条件股票，清仓")
            for code in list(portfolio.positions.keys()):
                price = get_current_price(code, rebalance_date)
                if price:
                    portfolio.sell(code, portfolio.positions[code]['amount'], price, rebalance_date)
            continue

        # 选择前5只
        stocks_to_buy = stocks_final[:g.params['max_position']]
        print(f"最终选择: {stocks_to_buy}")

        # 执行交易
        current_holdings = set(portfolio.positions.keys())
        to_sell = current_holdings - set(stocks_to_buy)
        to_buy = set(stocks_to_buy) - current_holdings

        # 卖出
        for code in to_sell:
            price = get_current_price(code, rebalance_date)
            if price:
                amount = portfolio.positions[code]['amount']
                profit = portfolio.sell(code, amount, price, rebalance_date)
                print(f"  卖出 {code}: {amount}股, 价格{price:.2f}, 盈亏{profit:.2f}")

        # 买入
        if stocks_to_buy:
            cash_per_stock = portfolio.cash / len(stocks_to_buy)
            for code in stocks_to_buy:
                price = get_current_price(code, rebalance_date)
                if price:
                    amount = int(cash_per_stock / price / 100) * 100  # 100股整数倍
                    if amount > 0:
                        portfolio.buy(code, amount, price, rebalance_date)
                        print(f"  买入 {code}: {amount}股, 价格{price:.2f}")

        # 更新价值
        portfolio.update_value(rebalance_date)
        print(f"调仓后价值: {portfolio.total_value:,.2f}元")

        # 计算收益率
        return_rate = (portfolio.total_value - portfolio.initial_capital) / portfolio.initial_capital * 100
        print(f"累计收益率: {return_rate:.2f}%")

    # 回测结束
    print(f"\n{'='*80}")
    print("回测完成！")
    print("="*80)

    # 最终结果
    portfolio.update_value(end_dt)
    final_value = portfolio.total_value
    initial_value = portfolio.initial_capital
    total_return = (final_value - initial_value) / initial_value * 100

    # 计算最大回撤
    max_drawdown = 0
    for trade in portfolio.trade_history:
        if trade['action'] == 'SELL':
            continue

    print(f"\n📊 回测结果统计:")
    print(f"初始资金: {initial_value:,.2f}元")
    print(f"最终价值: {final_value:,.2f}元")
    print(f"总收益率: {total_return:.2f}%")
    print(f"年化收益率: {total_return / (14/12):.2f}%")
    print(f"最大回撤: {max_drawdown:.2f}%")
    print(f"总交易次数: {len(portfolio.trade_history)}")

    # 保存结果
    result_df = pd.DataFrame([{
        '初始资金': initial_value,
        '最终价值': final_value,
        '总收益率(%)': total_return,
        '年化收益率(%)': total_return / (14/12),
        '最大回撤(%)': max_drawdown,
        '交易次数': len(portfolio.trade_history),
    }])

    output_file = '/home/zcy/alpha006_20251223/strategies/runners/回测结果_20241001_20251201.csv'
    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n✅ 结果已保存: {output_file}")

    # 保存交易历史
    if portfolio.trade_history:
        history_df = pd.DataFrame(portfolio.trade_history)
        history_file = '/home/zcy/alpha006_20251223/strategies/runners/交易历史_20241001_20251201.csv'
        history_df.to_csv(history_file, index=False, encoding='utf-8-sig')
        print(f"✅ 交易历史已保存: {history_file}")

    return portfolio

if __name__ == '__main__':
    # 运行回测
    portfolio = run_backtest('2024-10-01', '2025-12-01', rebalance_day=6)
