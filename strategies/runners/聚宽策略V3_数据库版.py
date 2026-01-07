# 聚宽策略V3 - 数据库适配版 (统一标准)
# 原策略: 聚宽平台
# 适配目标: MySQL数据库 (stock_database)
# 适配日期: 2026-01-04

# 修复内容：
# 1. 替换聚宽API为数据库查询 ✓
# 2. 适配数据库字段映射 ✓
# 3. 优化数据获取性能 ✓
# 4. 保持原有筛选逻辑不变 ✓
# 5. 统一标准: 创业板和主板使用相同筛选条件 ✓

# 统一标准说明：
# - 移除创业板特殊处理
# - 统一波动率阈值 (18%)
# - 统一CR20范围 (60-140)
# - 统一趋势要求 (3天上涨)
# - 统一放宽机制 (10只触发)

from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import talib as ta
import math
import time
import logging
from typing import Any, Dict, List
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 数据库适配层 ====================
# 导入项目核心模块
try:
    from core.config.settings import DATABASE_CONFIG, TABLE_NAMES
    from core.utils.db_connection import DBConnection
    from core.utils.data_loader import DataLoader
except ImportError:
    # 如果无法导入，使用相对路径
    import sys
    sys.path.append('/home/zcy/alpha006_20251223')
    from core.config.settings import DATABASE_CONFIG, TABLE_NAMES
    from core.utils.db_connection import DBConnection
    from core.utils.data_loader import DataLoader

# 初始化数据库连接和数据加载器
db = DBConnection(DATABASE_CONFIG)
data_loader = DataLoader(use_cache=True, cache_expiry=3600)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# 全局配置
MAX_WORKERS = 4  # 线程池最大线程数
CACHE_SIZE = 128  # 缓存大小

# 模拟聚宽的全局变量g
class GlobalVars:
    def __init__(self):
        self.params = {}
        self.max_hist_days = 120
        self.last_rebalance_day = None

g = GlobalVars()


# ==================== 工具函数模块（适配版） ====================
def to_datetime(input_date, field_name="未指定"):
    """日期转换工具函数，统一转换为datetime格式"""
    try:
        if input_date is None:
            raise ValueError(f"日期不能为空（{field_name}）")

        if isinstance(input_date, datetime):
            return input_date.replace(hour=0, minute=0, second=0, microsecond=0)
        if isinstance(input_date, date):
            return datetime.combine(input_date, datetime.min.time())
        if isinstance(input_date, str):
            # 确保字符串不为空
            if not input_date.strip():
                raise ValueError(f"日期字符串不能为空（{field_name}）")

            for fmt in ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']:
                try:
                    return datetime.strptime(input_date, fmt).replace(hour=0, minute=0, second=0, microsecond=0)
                except ValueError:
                    continue
            raise ValueError(f"无法解析字符串日期: {input_date}")
        raise TypeError(f"不支持的日期类型: {type(input_date)}")
    except Exception as e:
        raise type(e)(f"日期转换失败（{field_name}）: {str(e)}")


def to_date_str(input_date, field_name="未指定"):
    """将日期转换为字符串格式 'YYYYMMDD' (数据库格式)"""
    try:
        dt = to_datetime(input_date, field_name)
        return dt.strftime('%Y%m%d')
    except:
        # 作为最后的 fallback，返回一个默认日期字符串
        log.warning(f"无法转换日期 {input_date} 为字符串，使用默认日期")
        return '20200101'


def to_db_date(input_date, field_name="未指定"):
    """转换为数据库查询用的日期字符串"""
    try:
        dt = to_datetime(input_date, field_name)
        return dt.strftime('%Y%m%d')
    except:
        return '20200101'


def calc_ma_slope(ma_series, window=10):
    """计算均线斜率（角度制）"""
    if len(ma_series) < window:
        return 0.0
    try:
        x = np.arange(window)
        y = ma_series[-window:].values
        slope, _ = np.polyfit(x, y, 1)
        return np.degrees(np.arctan(slope / (ma_series[-1] + 1e-6) * 100))
    except:
        return 0.0


def get_common_stocks(list1, list2):
    """获取两个股票列表的交集，确保代码存在性"""
    return list(set(list1) & set(list2))


def calculate_valid_quantity(target_value, current_price, min_lot=100, min_commission=5, commission_rate=0.0015):
    """计算符合规则的下单数量（100的整数倍且大于0），考虑最低佣金"""
    if current_price <= 0 or target_value <= 0:
        return 0

    # 计算基础数量
    base_quantity = target_value / current_price
    lot_quantity = int(base_quantity / min_lot) * min_lot

    # 检查佣金：若佣金>交易金额1%，增加数量
    while lot_quantity > 0:
        trade_value = lot_quantity * current_price
        commission = max(trade_value * commission_rate, min_commission)
        if commission / trade_value <= 0.01:  # 佣金≤1%
            break
        lot_quantity += min_lot  # 增加1手，降低佣金占比

    # 确保数量至少为1手
    if lot_quantity < min_lot:
        required_value = min_lot * current_price
        required_commission = max(required_value * commission_rate, min_commission)
        if required_value + required_commission <= target_value * 1.05:  # 允许5%的价格波动
            return min_lot
        return 0

    return lot_quantity


@lru_cache(maxsize=CACHE_SIZE)
def get_industry_code(stock, date):
    """获取股票行业代码（从数据库）"""
    try:
        date_str = to_db_date(date, "行业代码查询日期")

        # 从sw_industry表查询
        sql = f"""
        SELECT l1_name
        FROM {TABLE_NAMES['sw_industry']}
        WHERE ts_code = %s
        """
        result = db.execute_query(sql, (stock,))

        if result:
            return result[0]['l1_name']
        else:
            return "其他"
    except Exception as e:
        log.warning(f"获取{stock}行业代码失败: {str(e)}")
        return "其他"


def get_market_state(index_code, price_data):
    """判断市场状态：上涨/下跌/震荡，高波动/低波动"""
    if price_data is None or len(price_data) < 60:
        return "neutral"  # 数据不足时默认中性

    # 指数均线趋势判断
    index_close = price_data['close']
    index_ma60 = ta.SMA(index_close.values, 60)
    index_ma20 = ta.SMA(index_close.values, 20)
    is_uptrend = index_ma20[-1] > index_ma60[-1] and index_close.iloc[-1] > index_ma20[-1]
    is_downtrend = index_ma20[-1] < index_ma60[-1] and index_close.iloc[-1] < index_ma20[-1]

    # 波动率判断（最近30天振幅）
    recent_30d = index_close.tail(30)
    volatility = (recent_30d.max() - recent_30d.min()) / recent_30d.min() * 100
    is_high_vol = volatility > 15  # 波动率>15%视为高波动

    if is_downtrend:
        return "downtrend_high_vol" if is_high_vol else "downtrend_low_vol"
    elif is_uptrend:
        return "uptrend_high_vol" if is_high_vol else "uptrend_low_vol"
    else:
        return "neutral"


def get_total_market_stocks(context):
    """获取全市场股票数量（从数据库）"""
    try:
        # 获取当前日期
        current_date = to_db_date(context.current_dt)

        # 查询当日有交易的股票数量
        sql = f"""
        SELECT COUNT(DISTINCT ts_code) as cnt
        FROM {TABLE_NAMES['daily_kline']}
        WHERE trade_date = %s
        """
        result = db.execute_query(sql, (current_date,))

        if result:
            return result[0]['cnt']
        else:
            log.warning(f"获取全市场股票数量失败，使用默认值3000")
            return 3000
    except Exception as e:
        log.warning(f"获取全市场股票数量失败: {e}，使用默认值3000")
        return 3000


def get_first_trading_day(year, month):
    """获取指定年月的第一个交易日（从数据库）"""
    # 构造当月第一天
    first_day = datetime(year, month, 1)

    # 循环查找第一个交易日
    current_day = first_day
    max_attempts = 10
    attempts = 0

    while attempts < max_attempts:
        # 跳过周末
        if current_day.weekday() >= 5:
            current_day += timedelta(days=1)
            attempts += 1
            continue

        # 查询当日是否有交易数据
        try:
            date_str = current_day.strftime('%Y%m%d')
            sql = f"""
            SELECT COUNT(*) as cnt
            FROM {TABLE_NAMES['daily_kline']}
            WHERE trade_date = %s
            """
            result = db.execute_query(sql, (date_str,))

            if result and result[0]['cnt'] > 0:
                return current_day
        except:
            pass

        current_day += timedelta(days=1)
        attempts += 1

    return first_day


# ==================== 数据获取模块（数据库版） ====================
def is_kcb_stock(stock_code):
    """判断是否为科创板股票（688开头的沪市股票）"""
    return stock_code.startswith('688') and stock_code.endswith('.SH')


def get_stock_pool(context, debug, is_mainboard=False, min_listed_days=365):
    """统一获取股票池（数据库版）"""
    try:
        # 1. 日期参数处理
        query_dt = context.current_dt
        query_date_str = to_db_date(query_dt, "股票池查询日期")

        pool_type = "主板" if is_mainboard else "创业板"
        if debug:
            log.debug(f"获取{pool_type}股票池：日期={query_date_str}")

        # 2. 获取当日所有股票
        sql = f"""
        SELECT DISTINCT ts_code
        FROM {TABLE_NAMES['daily_kline']}
        WHERE trade_date = %s
        """
        all_stocks_result = db.execute_query(sql, (query_date_str,))

        if not all_stocks_result:
            log.warning(f"{pool_type}当日无交易数据，尝试前一交易日")
            # 尝试前一交易日
            prev_date = (datetime.strptime(query_date_str, '%Y%m%d') - timedelta(days=1)).strftime('%Y%m%d')
            all_stocks_result = db.execute_query(sql, (prev_date,))
            if not all_stocks_result:
                log.error(f"{pool_type}股票数据获取失败")
                return []

        all_stocks = [row['ts_code'] for row in all_stocks_result]

        # 3. 筛选主板/创业板股票
        if is_mainboard:
            # 主板：排除创业板(300/301开头)和科创板(688开头)
            candidate_stocks = [
                s for s in all_stocks
                if not (s.startswith('300') or s.startswith('301'))
                and not s.startswith('688')
            ]
        else:
            # 创业板：包含300开头和301开头的深交所股票
            candidate_stocks = [
                s for s in all_stocks
                if (s.startswith('300') or s.startswith('301'))
                and s.endswith('.SZ')
            ]

        if not candidate_stocks:
            log.warning(f"{pool_type}初始筛选后无股票")
            return []

        # 4. 过滤ST股票和新股
        # 过滤ST股票
        sql_st = f"SELECT ts_code FROM {TABLE_NAMES['stock_st']} WHERE type = 'ST'"
        st_result = db.execute_query(sql_st, ())
        st_stocks = set([row['ts_code'] for row in st_result])

        # 过滤新股（上市不足min_listed_days天）
        qualified_stocks = []

        # 从CSV文件加载新股数据
        new_share_data = None
        try:
            new_share_csv = '/home/zcy/alpha006_20251223/data/new_share_increment_20251031221906.csv'
            new_share_df = pd.read_csv(new_share_csv)
            if 'ts_code' in new_share_df.columns and 'issue_date' in new_share_df.columns:
                new_share_data = {}
                for _, row in new_share_df.iterrows():
                    new_share_data[row['ts_code']] = row['issue_date']
                log.debug(f"从CSV加载新股数据: {len(new_share_data)}只")
        except Exception as e:
            log.warning(f"加载新股CSV失败: {e}")

        for stock in candidate_stocks:
            if stock in st_stocks:
                continue

            # 过滤新股
            if new_share_data and stock in new_share_data:
                issue_date_str = new_share_data[stock]
                try:
                    issue_date = datetime.strptime(str(issue_date_str), '%Y%m%d')
                    listed_days = (query_dt.date() - issue_date).days
                    if listed_days < min_listed_days:
                        continue
                except:
                    pass

            qualified_stocks.append(stock)

        log.info(f"{pool_type}股票池：原始{len(candidate_stocks)}只，筛选后{len(qualified_stocks)}只")
        return qualified_stocks

    except Exception as e:
        log.error(f"获取{pool_type}股票池失败: {str(e)}")
        return []


def batch_get_price_data(stocks, end_dt, max_days, debug, batch_size=200):
    """批量获取价格相关数据（数据库版）"""
    try:
        end_date_str = to_db_date(end_dt, "价格数据查询日期")

        if debug:
            log.debug(f"获取价格数据：日期={end_date_str}，股票数量={len(stocks)}")

        if not stocks:
            return None

        # 计算开始日期
        start_dt = datetime.strptime(end_date_str, '%Y%m%d') - timedelta(days=max_days + 20)
        start_date_str = start_dt.strftime('%Y%m%d')

        # 分批查询
        all_price_dfs = []
        total_batches = math.ceil(len(stocks) / batch_size)

        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i+batch_size]
            batch_num = i//batch_size + 1

            try:
                placeholders = ','.join(['%s'] * len(batch))
                sql = f"""
                SELECT ts_code, trade_date, close, high, low, vol
                FROM {TABLE_NAMES['daily_kline']}
                WHERE trade_date >= %s AND trade_date <= %s
                  AND ts_code IN ({placeholders})
                ORDER BY ts_code, trade_date
                """
                params = [start_date_str, end_date_str] + batch

                data = db.execute_query(sql, params)
                if data:
                    df = pd.DataFrame(data)
                    all_price_dfs.append(df)

                # 控制请求频率
                if total_batches > 5 and batch_num % 5 == 0:
                    time.sleep(1)
                else:
                    time.sleep(0.3)

            except Exception as e:
                log.warning(f"价格数据批次{batch_num}获取失败，重试: {str(e)}")
                # 失败重试
                for retry in range(2):
                    try:
                        time.sleep(1.5 * (retry + 1))
                        data = db.execute_query(sql, params)
                        if data:
                            df = pd.DataFrame(data)
                            all_price_dfs.append(df)
                        log.debug(f"价格数据批次{batch_num}重试{retry+1}次成功")
                        break
                    except Exception as e2:
                        log.warning(f"价格数据批次{batch_num}重试{retry+1}次失败: {str(e2)}")

        if not all_price_dfs:
            log.warning("价格数据返回为空")
            return None

        # 合并所有批次数据
        price_df = pd.concat(all_price_dfs, ignore_index=True)

        # 转换为透视表格式（日期×股票代码）
        price_df['trade_date'] = pd.to_datetime(price_df['trade_date'], format='%Y%m%d')
        price_data = {
            field: price_df.pivot(index='trade_date', columns='ts_code', values=field)
            for field in ['close', 'vol', 'high', 'low']
        }

        # 数据清洗 - 修复数据类型问题
        for field in price_data:
            # 确保数据为数值类型
            price_data[field] = price_data[field].astype(float)
            # 使用新的填充方法
            price_data[field] = price_data[field].ffill(limit=3).bfill(limit=3)

        # 排除近20天停牌≥5天的股票
        if price_data:
            close_data = price_data['close']
            recent_20d_close = close_data.tail(20)
            recent_20d_volume = price_data['vol'].tail(20)
            # 确保数据类型一致
            suspension_days = ((recent_20d_close.diff() == 0) & (recent_20d_volume == 0)).sum(axis=0)
            valid_stocks = suspension_days[suspension_days <= 5].index.tolist()

            for field in price_data:
                price_data[field] = price_data[field][valid_stocks]

            log.debug(f"排除长期停牌股后，剩余股票：{len(valid_stocks)}只")

        return price_data
    except Exception as e:
        log.error(f"价格数据获取失败: {str(e)}")
        return None


def get_turnover_data(stocks, end_dt, max_days, debug, batch_size=150):
    """获取换手率数据（数据库版）"""
    try:
        query_date_str = to_db_date(end_dt, "换手率查询日期")

        if debug:
            log.debug(f"获取换手率数据：日期={query_date_str}，股票数量={len(stocks)}")

        if not stocks:
            return pd.DataFrame()

        # 计算开始日期
        start_dt = datetime.strptime(query_date_str, '%Y%m%d') - timedelta(days=max_days)
        start_date_str = start_dt.strftime('%Y%m%d')

        # 分批查询
        all_dfs = []
        total_batches = math.ceil(len(stocks) / batch_size)

        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i+batch_size]
            batch_num = i//batch_size + 1

            try:
                placeholders = ','.join(['%s'] * len(batch))
                sql = f"""
                SELECT ts_code, trade_date, turnover_rate_f
                FROM {TABLE_NAMES['daily_basic']}
                WHERE trade_date >= %s AND trade_date <= %s
                  AND ts_code IN ({placeholders})
                ORDER BY ts_code, trade_date
                """
                params = [start_date_str, query_date_str] + batch

                data = db.execute_query(sql, params)
                if data:
                    df = pd.DataFrame(data)
                    all_dfs.append(df)

                # 控制请求频率
                if total_batches > 3 and batch_num % 3 == 0:
                    time.sleep(1)
                else:
                    time.sleep(0.5)

            except Exception as e:
                log.warning(f"换手率批次{batch_num}失败: {str(e)}")
                # 失败重试
                for retry in range(2):
                    try:
                        time.sleep(2 * (retry + 1))
                        data = db.execute_query(sql, params)
                        if data:
                            df = pd.DataFrame(data)
                            all_dfs.append(df)
                        log.debug(f"换手率批次{batch_num}重试{retry+1}次成功")
                        break
                    except Exception as e2:
                        log.warning(f"换手率批次{batch_num}重试{retry+1}次失败: {str(e2)}")

        if not all_dfs:
            log.warning("换手率数据返回为空")
            return pd.DataFrame()

        # 合并后转换为透视表
        turnover_df = pd.concat(all_dfs, ignore_index=True)
        turnover_df['trade_date'] = pd.to_datetime(turnover_df['trade_date'], format='%Y%m%d')
        return turnover_df.pivot(index='trade_date', columns='ts_code', values='turnover_rate_f')

    except Exception as e:
        log.warning(f"换手率数据获取失败: {str(e)}")
        return pd.DataFrame()


def get_factor_data_batch(stocks, start_dt, end_dt, factors, debug, batch_size=100):
    """批量获取因子数据（数据库版）"""
    try:
        if not stocks:
            return {factor: pd.DataFrame() for factor in factors}

        start_date_str = to_db_date(start_dt, "因子开始日期")
        end_date_str = to_db_date(end_dt, "因子结束日期")

        if debug:
            log.debug(f"批量获取因子数据 {factors}：{start_date_str}至{end_date_str}，股票数量={len(stocks)}")

        # 根据因子数量动态调整批次大小
        adjusted_batch = max(50, int(batch_size / len(factors))) if factors else batch_size

        result = {factor: [] for factor in factors}
        total_batches = math.ceil(len(stocks) / adjusted_batch)

        # 映射因子名到数据库字段
        factor_field_map = {
            'PEG': 'peg',  # 需要计算
            'CR20': 'cr_qfq',
            'alpha_038': 'alpha_038',
            'alpha_120cq': 'alpha_120cq',
            'alpha_pluse': 'alpha_pluse',
        }

        for i in range(0, len(stocks), adjusted_batch):
            batch = stocks[i:i+adjusted_batch]
            batch_num = i//adjusted_batch + 1

            if debug and batch_num % 5 == 0:
                log.debug(f"处理因子批次 {batch_num}/{total_batches}，股票数量: {len(batch)}")

            try:
                placeholders = ','.join(['%s'] * len(batch))

                # 从stk_factor_pro表获取因子数据
                # 注意：PEG需要单独计算，其他因子可以直接获取
                sql_fields = ['ts_code', 'trade_date']
                for factor in factors:
                    if factor in factor_field_map and factor_field_map[factor] != 'peg':
                        sql_fields.append(factor_field_map[factor])

                sql = f"""
                SELECT {', '.join(sql_fields)}
                FROM {TABLE_NAMES['stk_factor_pro']}
                WHERE trade_date >= %s AND trade_date <= %s
                  AND ts_code IN ({placeholders})
                ORDER BY ts_code, trade_date
                """
                params = [start_date_str, end_date_str] + batch

                data = db.execute_query(sql, params)
                if not data:
                    continue

                df = pd.DataFrame(data)
                df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')

                # 处理每个因子
                for factor in factors:
                    if factor == 'PEG':
                        # PEG需要从daily_basic和fina_indicator计算
                        peg_df = calculate_peg_data(batch, start_date_str, end_date_str)
                        if not peg_df.empty:
                            result[factor].append(peg_df)
                    elif factor in factor_field_map and factor_field_map[factor] in df.columns:
                        factor_df = df[['trade_date', 'ts_code', factor_field_map[factor]]].copy()
                        factor_df.columns = ['day', 'code', f'{factor}_value']
                        result[factor].append(factor_df)

                # 控制请求频率
                if total_batches > 5 and batch_num % 5 == 0:
                    time.sleep(1.5)
                else:
                    time.sleep(0.8)

            except Exception as e:
                log.warning(f"因子批次 {batch_num} 获取失败: {str(e)}")
                # 失败重试
                for retry in range(2):
                    try:
                        time.sleep(2 * (retry + 1))
                        data = db.execute_query(sql, params)
                        if data:
                            df = pd.DataFrame(data)
                            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')

                            for factor in factors:
                                if factor == 'PEG':
                                    peg_df = calculate_peg_data(batch, start_date_str, end_date_str)
                                    if not peg_df.empty:
                                        result[factor].append(peg_df)
                                elif factor in factor_field_map and factor_field_map[factor] in df.columns:
                                    factor_df = df[['trade_date', 'ts_code', factor_field_map[factor]]].copy()
                                    factor_df.columns = ['day', 'code', f'{factor}_value']
                                    result[factor].append(factor_df)

                            log.debug(f"因子批次 {batch_num} 重试{retry+1}次成功")
                            break
                    except Exception as e2:
                        log.warning(f"因子批次 {batch_num} 重试{retry+1}次失败: {str(e2)}")

        # 合并所有批次数据并转换为透视表
        final_result = {}
        for factor in factors:
            if result[factor]:
                combined_df = pd.concat(result[factor], ignore_index=True)
                final_result[factor] = combined_df.pivot(index='day', columns='code', values=f'{factor}_value')
            else:
                final_result[factor] = pd.DataFrame()

        # 如果包含 PEG 因子，移除 PEG 为空的记录，并同步更新其他因子
        if 'PEG' in final_result and not final_result['PEG'].empty:
            peg_notna = final_result['PEG'].notna()
            valid_index = peg_notna.stack().index

            for factor in final_result:
                if not final_result[factor].empty:
                    final_result[factor] = final_result[factor].stack().reindex(valid_index).unstack(level=-1)

        return final_result
    except Exception as e:
        log.error(f"因子数据获取失败: {str(e)}")
        return {factor: pd.DataFrame() for factor in factors}


def calculate_peg_data(stocks, start_date_str, end_date_str):
    """计算PEG数据（数据库版）"""
    try:
        if not stocks:
            return pd.DataFrame()

        placeholders = ','.join(['%s'] * len(stocks))

        # 获取PE数据
        sql_pe = f"""
        SELECT ts_code, trade_date, pe_ttm
        FROM {TABLE_NAMES['daily_basic']}
        WHERE trade_date >= %s AND trade_date <= %s
          AND ts_code IN ({placeholders})
          AND pe_ttm IS NOT NULL
          AND pe_ttm > 0
        """
        data_pe = db.execute_query(sql_pe, [start_date_str, end_date_str] + stocks)
        df_pe = pd.DataFrame(data_pe)

        if df_pe.empty:
            return pd.DataFrame()

        # 获取净利润增长率数据
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
        data_fina = db.execute_query(sql_fina, [end_date_str] + stocks)
        df_fina = pd.DataFrame(data_fina)

        if df_fina.empty:
            return pd.DataFrame()

        # 合并PE和财务数据
        # 将ann_date转换为trade_date，用于匹配
        df_fina['trade_date'] = df_fina['ann_date']

        # 合并
        df_merged = df_pe.merge(df_fina[['ts_code', 'trade_date', 'dt_netprofit_yoy']],
                               on=['ts_code', 'trade_date'], how='left')

        # 前向填充财务数据
        df_merged = df_merged.sort_values(['ts_code', 'trade_date'])
        df_merged['dt_netprofit_yoy'] = df_merged.groupby('ts_code')['dt_netprofit_yoy'].ffill()

        # 计算PEG
        df_merged['peg'] = df_merged['pe_ttm'] / df_merged['dt_netprofit_yoy']

        # 异常值处理
        df_merged['peg'] = df_merged['peg'].fillna(0)
        df_merged.loc[df_merged['peg'] <= 0, 'peg'] = 0
        df_merged.loc[df_merged['peg'] > 100, 'peg'] = 100  # 限制最大值

        # 转换为透视表格式
        df_merged['trade_date'] = pd.to_datetime(df_merged['trade_date'], format='%Y%m%d')
        result = df_merged[['trade_date', 'ts_code', 'peg']].copy()
        result.columns = ['day', 'code', 'PEG_value']

        return result

    except Exception as e:
        log.warning(f"计算PEG数据失败: {str(e)}")
        return pd.DataFrame()


# ==================== 主处理模块筛选（批量粗筛） ====================
def filter_turnover_first(turnover_data, params):
    """第一步：换手率批量筛选 - 使用市场分位数阈值"""
    if turnover_data.empty:
        return {'remaining_stocks': []}

    # 计算全市场换手率分位数
    market_turnover_series = turnover_data.mean()  # 每只股票的平均换手率
    turnover_threshold = market_turnover_series.quantile(params['turnover_quantile'])

    # 有效数据量检查
    valid_days = turnover_data.count()
    valid_mask = valid_days >= params['min_valid_days']

    # 平均换手率检查（使用市场分位数阈值）
    avg_turnover = turnover_data.mean()
    turnover_mask = avg_turnover >= turnover_threshold

    # 综合筛选
    pass_mask = valid_mask & turnover_mask
    remaining_stocks = pass_mask[pass_mask].index.tolist()

    log.info(f"[主处理] 换手率筛选：使用{params['turnover_quantile']*100}%分位数阈值({turnover_threshold:.2f})，保留 {len(remaining_stocks)} 只股票")
    return {
        'remaining_stocks': remaining_stocks,
        'stats': {
            'avg_turnover': avg_turnover,
            'turnover_threshold': turnover_threshold
        }
    }


def filter_price_liquidity(price_data, remaining_stocks, params):
    """第二步：价格与流动性批量筛选"""
    if not remaining_stocks or not price_data:
        return {'remaining_stocks': []}

    # 只保留价格数据中存在的股票
    close_columns = price_data['close'].columns.tolist()
    valid_stocks = get_common_stocks(remaining_stocks, close_columns)

    if len(valid_stocks) < len(remaining_stocks):
        log.warning(f"[主处理] 价格数据缺失 {len(remaining_stocks)-len(valid_stocks)} 只股票，已过滤")
    if not valid_stocks:
        return {'remaining_stocks': []}

    # 批量计算筛选指标 - 修复字段映射
    close = price_data['close'][valid_stocks]
    volume = price_data['vol'][valid_stocks] if 'vol' in price_data else price_data.get('volume', pd.DataFrame())[valid_stocks]
    high = price_data['high'][valid_stocks]

    valid_days = close.count()
    valid_mask = valid_days >= params['min_valid_days']

    avg_volume = volume.tail(params['price_period']).mean() / 100
    liquidity_mask = avg_volume >= params['min_avg_volume']

    recent_high = high.tail(params['price_period']).max()
    current_p = close.iloc[-1]
    max_drop = (current_p - recent_high) / recent_high * 100
    drop_mask = max_drop >= -params['max_recent_drop']

    # 先定义初始的pass_mask
    pass_mask = valid_mask & liquidity_mask & drop_mask

    # 现在可以安全地检查pass_mask了
    if sum(pass_mask) < 10:
        log.warning("价格流动性筛选结果过少，放宽条件")
        liquidity_mask = avg_volume >= params['min_avg_volume'] * 0.5  # 降低流动性要求
        drop_mask = max_drop >= -params['max_recent_drop'] * 1.5  # 放宽跌幅限制
        # 重新计算pass_mask
        pass_mask = valid_mask & liquidity_mask & drop_mask

    remaining_stocks = pass_mask[pass_mask].index.tolist()

    log.info(f"[主处理] 价格流动性筛选：保留 {len(remaining_stocks)} 只股票")
    return {
        'remaining_stocks': remaining_stocks,
        'stats': {
            'avg_volume': avg_volume,
            'max_drop': max_drop
        }
    }


def filter_peg(peg_data, remaining_stocks, params, context):
    """第三步：PEG因子批量筛选"""
    # 初始化默认返回结构
    default_stats = {'recent_peg': pd.Series()}

    if not remaining_stocks or peg_data.empty:
        log.warning("PEG筛选：无待筛选股票或PEG数据为空")
        return {
            'remaining_stocks': [],
            'stats': default_stats
        }

    # 只保留PEG数据中存在的股票
    peg_columns = peg_data.columns.tolist()
    valid_stocks = get_common_stocks(remaining_stocks, peg_columns)

    if not valid_stocks:
        log.warning("PEG筛选：无有效股票（数据缺失）")
        return {
            'remaining_stocks': [],
            'stats': default_stats
        }

    if len(valid_stocks) < len(remaining_stocks):
        log.warning(f"[主处理] PEG数据缺失 {len(remaining_stocks)-len(valid_stocks)} 只股票，已过滤")

    # 获取行业信息
    try:
        date_str = to_db_date(context.current_dt, "行业信息查询日期")
        # 使用DataLoader获取行业数据
        industry_info_df = data_loader.get_industry_data(valid_stocks)
        industry_info = {}
        for _, row in industry_info_df.iterrows():
            industry_info[row['ts_code']] = {'sw_l1': {'industry_name': row['l1_name']}}
    except Exception as e:
        log.warning(f"获取行业信息失败: {str(e)}，使用缓存数据")
        industry_info = {}

    # 按行业分组并计算行业PEG特性
    industry_peg_thresholds = {}
    industry_stocks = {}
    for stock in valid_stocks:
        industry_code = industry_info.get(stock, {}).get('sw_l1', {}).get('industry_name', '其他')

        if industry_code not in industry_stocks:
            industry_stocks[industry_code] = []
        industry_stocks[industry_code].append(stock)

    # 行业PEG阈值映射
    industry_peg_map = {
        '计算机': 3.0, '电子': 2.8, '国防军工': 2.8, '医药生物': 2.7, '传媒': 2.6,
        '电力设备': 2.5, '汽车': 2.3, '机械设备': 2.2, '通信': 2.2,
        '食品饮料': 2.0, '家用电器': 1.9, '美容护理': 2.0, '轻工制造': 1.8,
        '有色金属': 1.8, '化工': 1.7, '建筑材料': 1.6, '钢铁': 1.3, '采掘': 1.2,
        '银行': 1.1, '非银金融': 1.3, '房地产': 1.2, '公用事业': 1.1, '交通运输': 1.2,
        '其他': 2.1
    }

    # 计算各行业PEG阈值
    for industry_code, stocks in industry_stocks.items():
        if not stocks:
            continue
        industry_peg_values = []
        for stock in stocks:
            if stock in peg_data.columns:
                recent_peg = peg_data[stock].dropna().tail(30).mean()
                if not np.isnan(recent_peg) and recent_peg > 0:
                    industry_peg_values.append(recent_peg)

        if industry_peg_values:
            base_threshold = industry_peg_map.get(industry_code, industry_peg_map['其他'])
            industry_median = np.median(industry_peg_values)
            if industry_median > base_threshold * 1.5:
                industry_threshold = min(base_threshold * 1.2, 3.0)
            elif industry_median < base_threshold * 0.7:
                industry_threshold = max(base_threshold * 0.8, 0.5)
            else:
                industry_threshold = base_threshold
            industry_peg_thresholds[industry_code] = industry_threshold
            log.debug(f"行业 {industry_code} PEG阈值: {industry_threshold:.2f} (基准: {base_threshold:.2f}, 中位数: {industry_median:.2f})")

    # 批量计算筛选指标
    peg_subset = peg_data[valid_stocks]
    recent_peg = peg_subset.tail(30).mean()

    # 按行业应用阈值筛选
    pass_mask = pd.Series(False, index=valid_stocks)
    for stock in valid_stocks:
        industry_code = industry_info.get(stock, {}).get('sw_l1', {}).get('industry_name', '其他')
        threshold = industry_peg_thresholds.get(industry_code, params['default_peg_threshold'])
        if 0 < recent_peg[stock] <= threshold:
            pass_mask[stock] = True

    remaining_stocks = pass_mask[pass_mask].index.tolist()

    # 放宽条件（如果结果过少）
    if len(remaining_stocks) < 10:
        log.warning("PEG筛选结果过少，放宽条件")
        for stock in valid_stocks:
            if stock not in remaining_stocks and 0 < recent_peg[stock] <= threshold * 1.5:
                remaining_stocks.append(stock)

    log.info(f"[主处理] PEG因子筛选：保留 {len(remaining_stocks)} 只股票")
    return {
        'remaining_stocks': remaining_stocks,
        'stats': {'recent_peg': recent_peg}
    }


def filter_cr20(remaining_stocks, cr20_data, params, context, log):
    """第四步：CR20因子批量筛选 - 统一标准（创业板和主板一视同仁）"""
    # 边界条件处理
    if not remaining_stocks or cr20_data.empty:
        return {'remaining_stocks': []}

    # 过滤无CR20数据的股票
    cr20_columns = cr20_data.columns.tolist()
    valid_stocks = get_common_stocks(remaining_stocks, cr20_columns)

    if len(valid_stocks) < len(remaining_stocks):
        log.warning(f"[主处理] CR20数据缺失 {len(remaining_stocks)-len(valid_stocks)} 只股票，已过滤")
    if not valid_stocks:
        return {'remaining_stocks': []}

    # 获取行业信息
    try:
        date_str = to_db_date(context.current_dt, "行业信息查询日期")
        industry_info_df = data_loader.get_industry_data(valid_stocks)
        industry_info = {}
        for _, row in industry_info_df.iterrows():
            industry_info[row['ts_code']] = {'sw_l1': {'industry_name': row['l1_name']}}
    except Exception as e:
        log.warning(f"获取行业信息失败: {str(e)}，使用默认波动率阈值")
        industry_info = {}

    # 按行业分组
    industry_stocks = {}
    for stock in valid_stocks:
        industry_code = industry_info.get(stock, {}).get('sw_l1', {}).get('industry_name', '其他')
        if industry_code not in industry_stocks:
            industry_stocks[industry_code] = []
        industry_stocks[industry_code].append(stock)

    # 批量计算核心指标
    cr20_subset = cr20_data[valid_stocks]
    valid_days = cr20_subset.count()
    valid_mask = valid_days >= params['cr20_long_period']

    long_term = cr20_subset.tail(params['cr20_long_period']).mean()
    short_term = cr20_subset.tail(params['cr20_short_period']).mean()
    cr20_growth = (short_term - long_term) / long_term.replace(0, 1e-6) * 100

    # 波动率阈值 - 统一标准
    base_vol_threshold = {
        '有色金属': 25, '化工': 22, '钢铁': 20,
        '计算机': 18, '电子': 18, '传媒': 18,
        '食品饮料': 12, '家用电器': 12, '银行': 10,
        '其他': 18
    }

    recent_window = cr20_subset.tail(params['cr20_stable_days'])
    recent_mean = recent_window.mean()
    recent_volatility = recent_window.std() / recent_mean.replace(0, 1e-6) * 100

    # 生成波动率掩码 - 统一标准
    is_stable = pd.Series(False, index=valid_stocks)
    for stock in valid_stocks:
        industry_code = industry_info.get(stock, {}).get('sw_l1', {}).get('industry_name', '其他')
        threshold = base_vol_threshold.get(industry_code, 18)
        is_stable[stock] = recent_volatility[stock] < threshold

    # 趋势条件 - 统一标准
    trend_mask = pd.Series(False, index=valid_stocks)
    for stock in valid_stocks:
        recent_cr20 = cr20_subset[stock].dropna().tail(5)
        if len(recent_cr20) < 5:
            continue

        # 统一使用3天作为最小连续上涨天数
        min_increase_days = 3

        increase_days = sum(recent_cr20.iloc[i] > recent_cr20.iloc[i-1] for i in range(1, 5))
        overall_up = recent_cr20.iloc[-1] > recent_cr20.iloc[0]
        trend_mask[stock] = (increase_days >= min_increase_days) & overall_up

    # CR20范围 - 统一标准
    core_low = params['cr20_low_threshold']  # 60
    core_high = params['cr20_high_threshold']  # 140
    buffer_low = core_low * 0.9  # 54
    buffer_high = core_high * 1.1  # 154

    range_mask = pd.Series(False, index=valid_stocks)
    for stock in valid_stocks:
        core_mask = (short_term[stock] > core_low) & (short_term[stock] < core_high)
        buffer_mask = (short_term[stock] > buffer_low) & (short_term[stock] < buffer_high)

        # 统一的缓冲区逻辑
        buffer_growth_threshold = params['cr20_increase_threshold'] * 1.2  # 12%
        range_mask[stock] = core_mask | (buffer_mask & (cr20_growth[stock] > buffer_growth_threshold))

    # 增长条件 - 统一标准
    core_growth = params['cr20_increase_threshold']  # 10%
    buffer_growth = core_growth * 0.3  # 3%

    core_growth_mask = pd.Series(False, index=valid_stocks)
    buffer_growth_mask = pd.Series(False, index=valid_stocks)

    for stock in valid_stocks:
        core_growth_mask[stock] = cr20_growth[stock] >= core_growth
        buffer_growth_mask[stock] = cr20_growth[stock] >= buffer_growth

    # 初始筛选 - 统一标准
    pass_mask = valid_mask & range_mask & core_growth_mask & is_stable & trend_mask
    remaining_stocks = pass_mask[pass_mask].index.tolist()

    # 放宽机制 - 统一标准
    total_market_stocks = get_total_market_stocks(context)
    relax_trigger = 10 if total_market_stocks >= 3000 else 15

    # 统一放宽逻辑（不分创业板/主板）
    if len(remaining_stocks) < relax_trigger:
        log.warning(f"[放宽] 筛选结果过少（{len(remaining_stocks)}只），启动第一层放宽")

        # 降低增长要求
        pass_mask_relaxed = valid_mask & range_mask & buffer_growth_mask & is_stable & trend_mask
        remaining_stocks = pass_mask_relaxed[pass_mask_relaxed].index.tolist()

        if len(remaining_stocks) < relax_trigger // 2:
            log.warning(f"[放宽] 仍过少（{len(remaining_stocks)}只），启动第二层放宽（趋势再松）")

            # 进一步降低趋势要求
            trend_mask_relaxed = pd.Series(False, index=valid_stocks)
            for stock in valid_stocks:
                recent_cr20 = cr20_subset[stock].dropna().tail(5)
                if len(recent_cr20) < 5:
                    continue
                increase_days = sum(recent_cr20.iloc[i] > recent_cr20.iloc[i-1] for i in range(1, 5))
                overall_up = recent_cr20.iloc[-1] > recent_cr20.iloc[0]
                trend_mask_relaxed[stock] = (increase_days >= 2) & overall_up  # 从3降到2

            pass_mask_relaxed2 = valid_mask & range_mask & buffer_growth_mask & is_stable & trend_mask_relaxed
            remaining_stocks = pass_mask_relaxed2[pass_mask_relaxed2].index.tolist()

    log.info(f"[主处理] CR20因子筛选完成：共保留 {len(remaining_stocks)} 只")

    return {
        'remaining_stocks': remaining_stocks,
        'stats': {
            'cr20_short': short_term,
            'cr20_long': long_term,
            'cr20_growth': cr20_growth,
            'cr20_volatility': recent_volatility
        }
    }


# ==================== 单股票详细筛选（精筛） ====================
def filter_turnover_pulse(df, params):
    """优化后的换手率脉冲筛选"""
    # 1. 计算基础指标
    df['avg_turnover_30d'] = df['turnover'].rolling(params['turnover_period']).mean().fillna(0)
    df['avg_volume_30d'] = df['volume'].rolling(params['turnover_period']).mean().fillna(0)
    df['pct_change'] = df['close'].pct_change()
    df['stock_volatility'] = df['pct_change'].abs().rolling(120).mean().fillna(0.02)

    # 2. 基础脉冲信号识别
    df['base_pulse'] = (
        (df['avg_turnover_30d'] > params['min_turnover'] * 0.5) &
        (df['turnover'] >= params['min_turnover']) &
        (df['turnover'] >= df['avg_turnover_30d'] * 1.5) &
        (df['turnover'] <= df['avg_turnover_30d'] * 3.5) &
        (df['pct_change'].abs() <= df['stock_volatility'] * 1.2) &
        (df['volume'] >= df['avg_volume_30d'] * 1.3)
    )

    # 3. 脉冲有效性验证
    df['valid_pulse'] = False
    pulse_dates = df[df['base_pulse']].index.tolist()

    for pulse_date in pulse_dates:
        end_date = pulse_date + pd.Timedelta(days=3)
        post_pulse = df[(df.index > pulse_date) & (df.index <= end_date)]

        has_sustained = (post_pulse['turnover'] >= df.loc[pulse_date, 'avg_turnover_30d'] * 1.2).any() if not post_pulse.empty else False
        pulse_day_range = df.loc[pulse_date, 'high'] - df.loc[pulse_date, 'low']
        post_range = (post_pulse['high'].max() - post_pulse['low'].min()) if not post_pulse.empty else 0
        stable_after = (post_range <= pulse_day_range * 2)

        if has_sustained and stable_after:
            df.loc[pulse_date, 'valid_pulse'] = True

    # 4. 筛选40天内的有效脉冲
    end_date = df.index[-1]
    start_date = end_date - pd.Timedelta(days=params['pulse_days'])
    recent_df = df[(df.index >= start_date) & (df.index <= end_date)]
    valid_pulses = recent_df[recent_df['valid_pulse']].index.tolist()
    pulse_count = len(valid_pulses)

    if pulse_count < 2:
        return 0, pulse_count

    # 5. 验证脉冲分布合理性
    intervals = []
    for i in range(len(valid_pulses)-1):
        day_diff = (valid_pulses[i+1] - valid_pulses[i]).days
        intervals.append(day_diff)
    has_enough_interval = all(interval >= 5 for interval in intervals) if intervals else True

    recent_15d_start = end_date - pd.Timedelta(days=15)
    has_recent_pulse = any(p_date >= recent_15d_start for p_date in valid_pulses)

    # 6. 评分
    if has_enough_interval and has_recent_pulse:
        return 2, pulse_count
    else:
        return 1, pulse_count


def filter_price_position(df, params):
    """单股票：价格低位筛选"""
    price_period = params.get('price_period', 120)
    recent_prices = df['close'].tail(price_period).dropna()

    if len(recent_prices) < price_period * 0.7:
        return False, 0.0

    min_p = recent_prices.min()
    max_p = recent_prices.max()
    current_p = recent_prices.iloc[-1]
    price_range = max_p - min_p

    if price_range < 1e-6:
        price_quantile = 0.0
    else:
        price_quantile = (current_p - min_p) / price_range

    quantile_threshold = params.get('price_quantile_threshold', 0.3)
    is_low = price_quantile <= quantile_threshold

    consolidation_days = params.get('consolidation_days', 20)
    recent_consolidation = recent_prices.tail(consolidation_days)
    consolidation_range = (recent_consolidation.max() - recent_consolidation.min()) / recent_consolidation.min()
    in_consolidation = consolidation_range < 0.15

    # 估值验证（可选）
    is_low_valuation = True

    pass_filter = is_low and in_consolidation and is_low_valuation

    return pass_filter, round(price_quantile * 100, 2)


def filter_ma_trend(df, params):
    """单股票：均线趋势筛选"""
    ma_periods = params['ma_periods']
    ma_cols = [f'ma{p}' for p in ma_periods]
    valid_ma = True

    for p in ma_periods:
        if len(df) >= p * 0.9:
            df[f'ma{p}'] = ta.SMA(df['close'].values, timeperiod=p)
            df[f'ma{p}'] = df[f'ma{p}'].fillna(method='ffill')
        else:
            valid_ma = False

    if not (valid_ma and all(col in df.columns for col in ma_cols)):
        return False, 0, None

    mas = [df[col].iloc[-1] for col in ma_cols]
    ma_spread = (max(mas) - min(mas)) / (min(mas) + 1e-6) * 100

    ma_ascending = (df['ma10'].iloc[-1] >= df['ma20'].iloc[-1] * 0.98) and (df['ma60'].iloc[-1] > df['ma60'].iloc[-5])

    ma60_slope_current = calc_ma_slope(df['ma60'])
    ma60_available = len(df) > params['ma_trend_period']
    ma60_slope_past = calc_ma_slope(df['ma60'].iloc[:-params['ma_trend_period']]) if ma60_available else -10
    slope_condition = (ma60_slope_current >= 1 and ma60_slope_past < ma60_slope_current * 0.5)

    score = 0
    if ma_spread <= params['ma_spread_threshold'] and ma_ascending:
        score += 1
    if slope_condition:
        score += 1

    return True, score, {
        'ma_spread': round(ma_spread, 1),
        'ma60_slope': round(ma60_slope_current, 1)
    }


def filter_outperform_index(close, price_period, index_data, index_code='000300.SH'):
    """单股票：跑赢指数筛选"""
    try:
        if index_data is None or len(index_data) < 2 or len(close) < price_period:
            return False, 0

        stock_return = (close.iloc[-1] / close.iloc[-price_period] - 1) * (365 / price_period) * 100
        index_return = (index_data['close'].iloc[-1] / index_data['close'].iloc[0] - 1) * (365 / price_period) * 100
        outperform = round(stock_return - index_return, 1)

        return (stock_return > index_return), outperform
    except:
        return False, 0


def process_single_stock(args):
    """单股票处理函数，用于并行处理"""
    stock, price_data, turnover_data, main_stats, params, index_data, index_code, debug = args
    try:
        # 1. 基础信息与主处理统计数据
        stock_info = {
            'code': stock,
            'name': stock,  # 简化，实际可从数据库获取
            'avg_volume': round(main_stats['avg_volume'].get(stock, 0), 2),
            'max_drop': round(main_stats['max_drop'].get(stock, 0), 2),
            'avg_turnover': round(main_stats['avg_turnover'].get(stock, 0), 2),
            'recent_peg': round(main_stats['recent_peg'].get(stock, 0), 2),
            'cr20_short': round(main_stats['cr20_short'].get(stock, 0), 1),
            'cr20_long': round(main_stats['cr20_long'].get(stock, 0), 1),
            'cr20_growth': round(main_stats['cr20_growth'].get(stock, 0), 1),
            'cr20_volatility': round(main_stats['cr20_volatility'].get(stock, 0), 1)
        }

        score = 2

        # 2. 提取单股票数据
        close = price_data['close'][stock].dropna()
        volume = price_data['volume'][stock].dropna()
        high = price_data['high'][stock].dropna()
        low = price_data['low'][stock].dropna()
        turnover = turnover_data[stock].dropna() if stock in turnover_data.columns else pd.Series()

        # 数据合并
        close.index = pd.to_datetime(close.index)
        turnover.index = pd.to_datetime(turnover.index)
        start_date = min(close.index.min(), turnover.index.min()) if not turnover.empty else close.index.min()
        end_date = max(close.index.max(), turnover.index.max()) if not turnover.empty else close.index.max()
        full_index = pd.date_range(start=start_date, end=end_date)

        df = pd.DataFrame({
            'close': close.reindex(full_index),
            'high': high.reindex(full_index),
            'low': low.reindex(full_index),
            'turnover': turnover.reindex(full_index).fillna(0),
            'volume': volume.reindex(full_index)
        }).fillna(method='ffill', limit=3).fillna(method='bfill', limit=3).dropna(subset=['close'])

        required_days = max(params['price_period'], params['pulse_days'] + params['turnover_period'])
        if len(df) < int(required_days * params['merge_tolerance']):
            if debug:
                log.debug(f"[单股票] {stock} 数据量不足，淘汰")
            return None

        # 3. 详细筛选
        pulse_score, pulse_count = filter_turnover_pulse(df, params)
        stock_info['pulse_count'] = pulse_count
        score += pulse_score

        price_pass, price_quantile = filter_price_position(df, params)
        stock_info['price_quantile'] = price_quantile
        if price_pass:
            score += 1

        ma_pass, ma_score, ma_data = filter_ma_trend(df, params)
        if ma_pass:
            score += ma_score
        if ma_data:
            stock_info.update(ma_data)

        index_pass, outperform = filter_outperform_index(
            close, params['price_period'], index_data, index_code
        )
        stock_info['outperform_index'] = outperform
        if index_pass:
            score += 1

        stock_info['score'] = score
        if score >= params['pass_score']:
            return stock_info
        else:
            return None

    except Exception as e:
        log.error(f"[单股票] 处理 {stock} 出错: {str(e)}")
        return None


# ==================== 筛选流程控制器 ====================
def run_screening_pipeline(stock_pool, price_data, turnover_data, factor_data, params, index_data, index_code, debug, context):
    """筛选流程总控制器"""
    start_time = time.time()
    total_initial = len(stock_pool)
    log.info(f"\n===== 开始筛选流程（初始股票数：{total_initial}） =====")

    main_stats = {}

    # 1. 换手率筛选
    turnover_result = filter_turnover_first(turnover_data, params)
    main_stats['avg_turnover'] = turnover_result['stats']['avg_turnover']
    if not turnover_result['remaining_stocks']:
        log.info("主处理筛选：换手率筛选后无剩余股票，终止流程")
        return []

    # 2. 价格流动性筛选
    if not price_data:
        log.error("价格数据获取失败，无法进行价格流动性筛选")
        return []

    price_result = filter_price_liquidity(price_data, turnover_result['remaining_stocks'], params)
    if 'stats' not in price_result:
        log.warning("价格筛选结果格式异常，使用默认值")
        main_stats['avg_volume'] = pd.Series()
        main_stats['max_drop'] = pd.Series()
    else:
        main_stats['avg_volume'] = price_result['stats']['avg_volume']
        main_stats['max_drop'] = price_result['stats']['max_drop']

    if not price_result['remaining_stocks']:
        log.info("主处理筛选：价格流动性筛选后无剩余股票，终止流程")
        return []

    # 3. PEG因子筛选
    peg_result = filter_peg(factor_data.get('PEG', pd.DataFrame()), price_result['remaining_stocks'], params, context)
    if 'stats' not in peg_result or 'recent_peg' not in peg_result['stats']:
        log.warning("PEG筛选结果格式异常，使用默认空数据")
        main_stats['recent_peg'] = pd.Series()
    else:
        main_stats['recent_peg'] = peg_result['stats']['recent_peg']
    if not peg_result['remaining_stocks']:
        log.info("主处理筛选：PEG筛选后无剩余股票，终止流程")
        return []

    # 4. CR20因子筛选
    cr20_result = filter_cr20(
        remaining_stocks=peg_result['remaining_stocks'],
        cr20_data=factor_data.get('CR20', pd.DataFrame()),
        params=params,
        context=context,
        log=log
    )
    main_stats['cr20_short'] = cr20_result['stats']['cr20_short']
    main_stats['cr20_long'] = cr20_result['stats']['cr20_long']
    main_stats['cr20_growth'] = cr20_result['stats']['cr20_growth']
    main_stats['cr20_volatility'] = cr20_result['stats']['cr20_volatility']
    final_main_stocks = cr20_result['remaining_stocks']

    log.info(f"\n===== 主处理筛选完成（剩余股票数：{len(final_main_stocks)}） =====")
    if not final_main_stocks:
        return []

    # 第二阶段：单股票详细筛选
    qualified_stocks = []
    log.info(f"\n===== 开始单股票详细筛选（待筛选数：{len(final_main_stocks)}） =====")

    process_args = [
        (stock, price_data, turnover_data, main_stats, params, index_data, index_code, debug)
        for stock in final_main_stocks
    ]

    worker_count = min(MAX_WORKERS, len(process_args))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {executor.submit(process_single_stock, args): args[0] for args in process_args}

        for i, future in enumerate(as_completed(futures), 1):
            stock = futures[future]
            try:
                result = future.result()
                if result:
                    qualified_stocks.append(result)

                if i % 10 == 0 or i == len(process_args):
                    log.info(f"单股票筛选进度：{i}/{len(process_args)}，已合格：{len(qualified_stocks)}")

            except Exception as e:
                log.error(f"处理股票 {stock} 时发生异常: {str(e)}")

    # 降低合格分数线
    if len(qualified_stocks) < 3 and len(final_main_stocks) >= 10:
        log.warning("最终合格股票太少，降低合格分数线重新筛选")
        for stock_data in process_args:
            result = process_single_stock(stock_data)
            if result and result['score'] >= params['pass_score'] * 0.8:
                qualified_stocks.append(result)
        qualified_stocks = list({s['code']: s for s in qualified_stocks}.values())

    log.info(f"\n===== 筛选流程结束 =====")
    log.info(f"初始股票数：{total_initial} → 主处理后：{len(final_main_stocks)} → 最终合格：{len(qualified_stocks)}")
    log.info(f"总耗时：{time.time() - start_time:.2f}秒")

    return qualified_stocks


# ==================== 策略主函数 ====================
def initialize(context):
    """策略初始化"""
    g.params = {
        'price_period': 120,
        'turnover_period': 30,
        'cr20_long_period': 30,
        'turnover_quantile': 0.4,
        'pulse_days': 40,
        'min_turnover': 3,

        'stop_loss_ratio': 0.10,
        'take_profit_ratio': 0.60,
        'max_portfolio_drawdown': 15,

        'min_avg_volume': 5000,
        'min_valid_days': 15,

        'max_position': 5,
        'transaction_cost_rate': 0.0015,
        'min_commission': 5,

        'price_quantile_threshold': 0.3,
        'max_recent_drop': 30,

        'default_peg_threshold': 2.0,

        'cr20_short_period': 10,
        'cr20_low_threshold': 60,
        'cr20_high_threshold': 140,
        'cr20_increase_threshold': 10,
        'cr20_stable_days': 5,

        'ma_periods': [10, 20, 60, 120],
        'ma_spread_threshold': 10,
        'ma_trend_period': 40,

        'debug': True,
        'rebalance_monthday': 6,
        'merge_tolerance': 0.6,
        'pass_score': 5,
    }

    g.max_hist_days = max(
        g.params['price_period'],
        g.params['turnover_period'],
        g.params['cr20_long_period']
    )

    g.last_rebalance_day = None

    log.info(f"策略初始化完成：每月{g.params['rebalance_monthday']}日调仓，最大持仓{g.params['max_position']}只")
    log.info(f"止损比例: {g.params['stop_loss_ratio']*100}%，止盈比例: {g.params['take_profit_ratio']*100}%")


def check_stop_condition(stock, buy_price, current_price, params):
    """止损止盈判断"""
    change_ratio = (current_price - buy_price) / buy_price * 100
    stop_loss = current_price < buy_price * (1 - params['stop_loss_ratio'])
    take_profit = current_price > buy_price * (1 + params['take_profit_ratio'])

    if stop_loss:
        log.info(f"[止损触发] {stock} - 买入价:{buy_price:.2f}, 当前价:{current_price:.2f}, 跌幅:{change_ratio:.2f}%")
    elif take_profit:
        log.info(f"[止盈触发] {stock} - 买入价:{buy_price:.2f}, 当前价:{current_price:.2f}, 涨幅:{change_ratio:.2f}%")

    return stop_loss or take_profit


def select_and_adjust(context):
    """调仓主函数 - 统一处理所有股票"""
    current_dt = context.current_dt
    current_date = current_dt.date()
    date_str = current_date.strftime('%Y-%m-%d')
    params = g.params

    log.info("="*80)
    log.info(f"【{date_str}】开始月度调仓（与initialize配置的{params['rebalance_monthday']}日一致）")

    # 计算因子数据范围
    factor_start_date = (current_date - pd.Timedelta(days=params['cr20_long_period'] + 15)).strftime('%Y%m%d')
    factor_end_date = current_date.strftime('%Y%m%d')

    # 统一筛选所有股票（不分创业板/主板）
    qualified_stocks = process_stock_universe_all(
        context,
        start_date=factor_start_date,
        end_date=factor_end_date,
        index_code='000300.SH'
    )

    # 执行调仓
    if qualified_stocks:
        log.info(f"共筛选出{len(qualified_stocks)}只合格股票，执行调仓")
        execute_trade(context, qualified_stocks, current_dt, current_date)
    else:
        log.info("无合格股票，执行空仓操作")
        clear_all_positions(context)

    g.last_rebalance_day = current_date
    log.info(f"【{date_str}】月度调仓完成")
    log.info("="*80)


def process_stock_universe(context, is_mainboard, start_date, end_date, index_code):
    """筛选函数"""
    params = g.params
    debug = params['debug']

    # 1. 获取基础股票池
    stock_pool = get_stock_pool(
        context, debug,
        is_mainboard=is_mainboard,
        min_listed_days=365
    )
    if not stock_pool:
        log.info(f"{'主板' if is_mainboard else '创业板'}股票池为空，跳过筛选")
        return []

    # 2. 分步获取数据
    turnover_data = get_turnover_data(stock_pool, context.current_dt.date(), g.max_hist_days, debug)
    if turnover_data.empty:
        log.error(f"{'主板' if is_mainboard else '创业板'}换手率数据获取失败")
        return []

    # 3. 执行筛选
    stocks_after_turnover = filter_turnover_first(turnover_data, params)['remaining_stocks']
    if not stocks_after_turnover:
        return []

    # 4. 补充其他数据并完成最终筛选
    price_data = batch_get_price_data(stocks_after_turnover, context.current_dt, g.max_hist_days, debug)
    factor_data = get_factor_data_batch(
        stocks_after_turnover, start_date, end_date, ['PEG', 'CR20'], debug
    )

    # 获取指数数据
    index_start_date = (datetime.strptime(end_date, '%Y%m%d') - pd.Timedelta(days=params['price_period'])).strftime('%Y%m%d')
    sql = f"""
    SELECT trade_date, close
    FROM {TABLE_NAMES['index_daily_zzsz']}
    WHERE ts_code = %s AND trade_date >= %s AND trade_date <= %s
    ORDER BY trade_date
    """
    index_result = db.execute_query(sql, (index_code, index_start_date, end_date))
    index_data = pd.DataFrame(index_result)
    if not index_data.empty:
        index_data['trade_date'] = pd.to_datetime(index_data['trade_date'], format='%Y%m%d')
        index_data.set_index('trade_date', inplace=True)

    return run_screening_pipeline(
        stocks_after_turnover, price_data, turnover_data, factor_data,
        params, index_data, index_code, debug, context
    )


def process_stock_universe_all(context, start_date, end_date, index_code):
    """统一筛选函数 - 不分创业板/主板"""
    params = g.params
    debug = params['debug']

    # 1. 获取全市场股票池（包含所有股票）
    stock_pool = get_stock_pool(
        context, debug,
        is_mainboard=False,  # 这个参数现在只影响股票池获取，后续会统一处理
        min_listed_days=365
    )

    # 由于get_stock_pool函数内部会区分主板/创业板，我们需要修改它
    # 或者直接从全市场获取，这里我们修改get_stock_pool的调用方式
    # 为了简单起见，我们直接获取当日所有非ST股票

    query_dt = context.current_dt
    query_date_str = to_db_date(query_dt, "股票池查询日期")

    # 获取当日所有股票
    sql = f"""
    SELECT DISTINCT ts_code
    FROM {TABLE_NAMES['daily_kline']}
    WHERE trade_date = %s
    """
    all_stocks_result = db.execute_query(sql, (query_date_str,))

    if not all_stocks_result:
        log.warning("当日无交易数据，尝试前一交易日")
        prev_date = (datetime.strptime(query_date_str, '%Y%m%d') - timedelta(days=1)).strftime('%Y%m%d')
        all_stocks_result = db.execute_query(sql, (prev_date,))
        if not all_stocks_result:
            log.error("股票数据获取失败")
            return []

    all_stocks = [row['ts_code'] for row in all_stocks_result]

    # 过滤ST股票
    sql_st = f"SELECT ts_code FROM {TABLE_NAMES['stock_st']} WHERE type = 'ST'"
    st_result = db.execute_query(sql_st, ())
    st_stocks = set([row['ts_code'] for row in st_result])

    # 过滤科创板（688开头）- 策略暂不支持科创板
    all_stocks = [s for s in all_stocks if not s.startswith('688')]

    # 过滤ST
    stock_pool = [s for s in all_stocks if s not in st_stocks]

    # 过滤新股
    try:
        new_share_csv = '/home/zcy/alpha006_20251223/data/new_share_increment_20251031221906.csv'
        new_share_df = pd.read_csv(new_share_csv)
        if 'ts_code' in new_share_df.columns and 'issue_date' in new_share_df.columns:
            new_share_data = {}
            for _, row in new_share_df.iterrows():
                new_share_data[row['ts_code']] = row['issue_date']

            qualified_stocks = []
            for stock in stock_pool:
                if stock in new_share_data:
                    issue_date_str = new_share_data[stock]
                    try:
                        issue_date = datetime.strptime(str(issue_date_str), '%Y%m%d')
                        listed_days = (query_dt.date() - issue_date).days
                        if listed_days < 365:
                            continue
                    except:
                        pass
                qualified_stocks.append(stock)
            stock_pool = qualified_stocks
    except:
        pass

    log.info(f"全市场股票池：{len(stock_pool)}只")

    if not stock_pool:
        return []

    # 2. 分步获取数据
    turnover_data = get_turnover_data(stock_pool, context.current_dt.date(), g.max_hist_days, debug)
    if turnover_data.empty:
        log.error("换手率数据获取失败")
        return []

    # 3. 执行筛选
    stocks_after_turnover = filter_turnover_first(turnover_data, params)['remaining_stocks']
    if not stocks_after_turnover:
        return []

    # 4. 补充其他数据并完成最终筛选
    price_data = batch_get_price_data(stocks_after_turnover, context.current_dt, g.max_hist_days, debug)
    factor_data = get_factor_data_batch(
        stocks_after_turnover, start_date, end_date, ['PEG', 'CR20'], debug
    )

    # 获取指数数据
    index_start_date = (datetime.strptime(end_date, '%Y%m%d') - pd.Timedelta(days=params['price_period'])).strftime('%Y%m%d')
    sql = f"""
    SELECT trade_date, close
    FROM {TABLE_NAMES['index_daily_zzsz']}
    WHERE ts_code = %s AND trade_date >= %s AND trade_date <= %s
    ORDER BY trade_date
    """
    index_result = db.execute_query(sql, (index_code, index_start_date, end_date))
    index_data = pd.DataFrame(index_result)
    if not index_data.empty:
        index_data['trade_date'] = pd.to_datetime(index_data['trade_date'], format='%Y%m%d')
        index_data.set_index('trade_date', inplace=True)

    return run_screening_pipeline(
        stocks_after_turnover, price_data, turnover_data, factor_data,
        params, index_data, index_code, debug, context
    )


def execute_trade(context, qualified_stocks, current_dt, current_date):
    """交易执行函数"""
    params = g.params
    date_str = current_date.strftime('%Y-%m-%d')
    start_time = time.time()

    # 验证筛选结果格式
    if not all(isinstance(stock, dict) and 'code' in stock and 'score' in stock for stock in qualified_stocks):
        log.error("筛选结果格式错误，必须包含'code'和'score'字段")
        return

    # 止损止盈
    current_holdings = set(context.portfolio.positions.keys())
    for stock_code in current_holdings:
        position = context.portfolio.positions[stock_code]
        if position.total_amount <= 0:
            continue

        # 获取当前价格
        current_price = get_current_price(stock_code, current_dt)
        if check_stop_condition(stock_code, position.avg_cost, current_price, params):
            order_target_value(stock_code, 0)
            log.info(f"[止损/止盈执行] 卖出{stock_code}")

    # 全局回撤控制
    if check_portfolio_drawdown(context, params):
        log.info("触发全局回撤控制，调仓终止")
        return

    # 市场状态适配
    state_params = get_market_state_params(context, current_dt)
    log.info(f"当前市场状态：{state_params['state']}，最大持仓{state_params['max_position']}只")

    # 筛选最终标的
    final_selected = sorted(qualified_stocks, key=lambda x: x['score'], reverse=True)[:state_params['max_position']]
    target_holdings = {stock['code'] for stock in final_selected}

    # 执行买卖操作
    execute_sell_operations(context, current_holdings - target_holdings)
    execute_buy_operations(
        context, final_selected, target_holdings - current_holdings,
        state_params['max_cash_ratio'], params
    )

    log.info(f"【调仓总结】耗时{time.time()-start_time:.2f}秒，最终持仓{len(final_selected)}只")


def check_market_status(context):
    """监控函数"""
    current_dt = context.current_dt
    date_str = current_dt.strftime('%Y-%m-%d')

    log.info(f"\n【市场监控】{date_str}（上次调仓日：{g.last_rebalance_day or '未调仓'}）")

    # 指数监控
    monitor_indices = {
        '000300.SH': '沪深300',
        '000001.SH': '上证指数'
    }
    for code, name in monitor_indices.items():
        show_index_status(code, name, current_dt)

    # 持仓监控
    show_position_details(context, current_dt)

    # 资产概况
    total_asset = context.portfolio.total_value
    cash_ratio = context.portfolio.cash / total_asset * 100
    log.info(f"【资产概况】总资产: {total_asset:.2f}元, 现金占比: {cash_ratio:.2f}%")
    log.info("="*80)


# ==================== 辅助函数 ====================
def clear_all_positions(context):
    """空仓操作"""
    for stock in context.portfolio.positions:
        position = context.portfolio.positions[stock]
        if position.total_amount > 0:
            order_target_value(stock, 0)
            log.info(f"空仓操作：卖出{stock} {position.total_amount}股")


def check_portfolio_drawdown(context, params):
    """组合回撤检查"""
    portfolio = context.portfolio
    if not (hasattr(portfolio, 'max_total_value') and portfolio.max_total_value > 0):
        return False

    max_drawdown = (portfolio.max_total_value - portfolio.total_value) / portfolio.max_total_value * 100
    if max_drawdown > params['max_portfolio_drawdown']:
        log.warning(f"组合最大回撤{max_drawdown:.2f}%，超过阈值{params['max_portfolio_drawdown']}%")
        for stock in context.portfolio.positions:
            position = context.portfolio.positions[stock]
            if position.total_amount > 0:
                order_target_percent(stock, 0.3 / len(context.portfolio.positions))
        return True
    return False


def get_market_state_params(context, current_dt):
    """市场状态参数"""
    index_code = '000300.SH'

    # 获取指数数据
    end_date = current_dt.strftime('%Y%m%d')
    start_date = (datetime.strptime(end_date, '%Y%m%d') - pd.Timedelta(days=60)).strftime('%Y%m%d')

    sql = f"""
    SELECT trade_date, close
    FROM {TABLE_NAMES['index_daily_zzsz']}
    WHERE ts_code = %s AND trade_date >= %s AND trade_date <= %s
    ORDER BY trade_date
    """
    index_result = db.execute_query(sql, (index_code, start_date, end_date))
    index_data = pd.DataFrame(index_result)

    if not index_data.empty:
        index_data['trade_date'] = pd.to_datetime(index_data['trade_date'], format='%Y%m%d')
        index_data.set_index('trade_date', inplace=True)
        index_state = get_market_state(index_code, index_data)
    else:
        index_state = 'neutral'

    state_params = {
        "downtrend_high_vol": {"max_position": 3, "max_cash_ratio": 0.5, "state": "下跌高波动"},
        "downtrend_low_vol": {"max_position": 4, "max_cash_ratio": 0.3, "state": "下跌低波动"},
        "uptrend_high_vol": {"max_position": 6, "max_cash_ratio": 0.1, "state": "上涨高波动"},
        "uptrend_low_vol": {"max_position": 5, "max_cash_ratio": 0.2, "state": "上涨低波动"},
        "neutral": {"max_position": 5, "max_cash_ratio": 0.2, "state": "中性"}
    }
    return state_params.get(index_state, state_params["neutral"])


def execute_sell_operations(context, to_sell):
    """卖出操作"""
    log.info(f"[卖出操作] 共{len(to_sell)}只股票")
    for stock in to_sell:
        position = context.portfolio.positions[stock]
        if position.total_amount > 0:
            order_target_value(stock, 0)
            log.info(f"  卖出{stock}：{position.total_amount}股，市值{position.value:.2f}元")


def execute_buy_operations(context, final_selected, to_buy, max_cash_ratio, params):
    """买入操作"""
    total_cash = context.portfolio.total_value
    total_invest = total_cash * (1 - max_cash_ratio)
    target_value_per_stock = total_invest / len(final_selected) if final_selected else 0

    log.info(f"[买入操作] 共{len(to_buy)}只股票，单只目标市值{target_value_per_stock:.2f}元")
    for stock in final_selected:
        code = stock['code']
        if code not in to_buy:
            continue

        current_price = get_current_price(code, context.current_dt)
        valid_qty = calculate_valid_quantity(target_value_per_stock, current_price)
        actual_value = valid_qty * current_price
        commission = max(actual_value * params['transaction_cost_rate'], params['min_commission'])

        if actual_value + commission <= total_cash:
            order_target_value(code, actual_value)
            log.info(f"  买入{code}：{valid_qty}股，市值{actual_value:.2f}元，佣金{commission:.2f}元")
        else:
            log.warning(f"  资金不足，跳过买入{code}")


def show_index_status(code, name, current_dt):
    """指数状态展示"""
    try:
        end_date = current_dt.strftime('%Y%m%d')
        sql = f"""
        SELECT trade_date, close
        FROM {TABLE_NAMES['index_daily_zzsz']}
        WHERE ts_code = %s AND trade_date <= %s
        ORDER BY trade_date DESC
        LIMIT 2
        """
        data = db.execute_query(sql, (code, end_date))

        if len(data) >= 2:
            prev_close = data[1]['close']
            current_close = data[0]['close']
            change_ratio = (current_close - prev_close) / prev_close * 100
            log.info(f"  {name}({code})：{current_close:.2f}元，涨跌幅{change_ratio:.2f}%")
    except Exception as e:
        log.warning(f"  获取{name}数据失败：{str(e)}")


def show_position_details(context, current_dt):
    """持仓详情展示"""
    valid_holdings = {
        code: pos for code, pos in context.portfolio.positions.items()
        if pos.total_amount > 0
    }
    log.info(f"【持仓详情】共{len(valid_holdings)}只股票")

    if valid_holdings:
        log.info(f"  {'代码':<10} {'数量(股)':<10} {'成本价':<8} {'当前价':<8} {'盈亏(%)':<8}")
        for code, pos in valid_holdings.items():
            try:
                current_price = get_current_price(code, current_dt)
                profit_ratio = (current_price - pos.avg_cost) / pos.avg_cost * 100 if pos.avg_cost > 0 else 0
                log.info(
                    f"  {code:<10} {pos.total_amount:<10} "
                    f"{pos.avg_cost:.2f}    {current_price:.2f}    {profit_ratio:+.2f}%"
                )
            except Exception as e:
                log.warning(f"  获取{code}详情失败：{str(e)}")


def get_current_price(stock_code, current_dt):
    """获取当前价格"""
    date_str = current_dt.strftime('%Y%m%d')
    sql = f"""
    SELECT close
    FROM {TABLE_NAMES['daily_kline']}
    WHERE ts_code = %s AND trade_date = %s
    """
    result = db.execute_query(sql, (stock_code, date_str))
    if result:
        return result[0]['close']
    else:
        # 尝试获取最近一个交易日的价格
        sql = f"""
        SELECT close
        FROM {TABLE_NAMES['daily_kline']}
        WHERE ts_code = %s
        ORDER BY trade_date DESC
        LIMIT 1
        """
        result = db.execute_query(sql, (stock_code,))
        if result:
            return result[0]['close']
    return 0


# ==================== 兼容聚宽平台的订单函数（占位） ====================
def order_target_value(stock_code, value):
    """订单函数（占位，实际使用时需要对接交易系统）"""
    log.info(f"[订单] {stock_code} 目标市值: {value:.2f}元")


def order_target_percent(stock_code, percent):
    """订单函数（占位）"""
    log.info(f"[订单] {stock_code} 目标占比: {percent:.2%}")


# ==================== 上下文对象（模拟聚宽context） ====================
class Context:
    """模拟聚宽context对象"""
    def __init__(self, current_dt, portfolio=None):
        self.current_dt = current_dt
        self.portfolio = portfolio or Portfolio()


class Portfolio:
    """模拟聚宽portfolio对象"""
    def __init__(self):
        self.positions = {}
        self.total_value = 1000000
        self.cash = 1000000
        self.max_total_value = 1000000


class Position:
    """模拟聚宽position对象"""
    def __init__(self, code, amount, avg_cost):
        self.code = code
        self.total_amount = amount
        self.avg_cost = avg_cost
        self.value = amount * avg_cost


# ==================== 测试函数 ====================
def test_strategy():
    """测试策略"""
    print("="*80)
    print("聚宽策略V3 - 数据库版 - 测试")
    print("="*80)

    # 测试日期
    test_date = datetime(2025, 1, 3)
    context = Context(test_date)

    # 初始化
    g = type('obj', (object,), {})()
    g.params = {}
    g.max_hist_days = 120
    g.last_rebalance_day = None

    initialize(context)

    # 测试股票池获取
    print("\n1. 测试股票池获取...")
    stocks = get_stock_pool(context, debug=True, is_mainboard=False, min_listed_days=365)
    print(f"创业板股票池: {len(stocks)}只")
    if stocks:
        print(f"示例: {stocks[:5]}")

    # 测试价格数据获取
    if stocks:
        print("\n2. 测试价格数据获取...")
        price_data = batch_get_price_data(stocks[:10], test_date, 120, debug=True)
        if price_data:
            print(f"价格数据获取成功: {len(price_data['close'])}天")
            print(f"股票数量: {price_data['close'].shape[1]}")

    # 测试换手率数据获取
    if stocks:
        print("\n3. 测试换手率数据获取...")
        turnover_data = get_turnover_data(stocks[:10], test_date.date(), 120, debug=True)
        if not turnover_data.empty:
            print(f"换手率数据获取成功: {turnover_data.shape}")

    print("\n✅ 测试完成")


if __name__ == "__main__":
    # 运行测试
    test_strategy()
