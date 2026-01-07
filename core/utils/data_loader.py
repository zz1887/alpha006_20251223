"""
数据加载工具 - 增强版
版本: v2.0
更新日期: 2025-12-30

功能:
- 行业分类数据加载
- 价格数据获取
- 财务数据获取
- 基准指数数据获取
- 数据缓存管理
- 数据预处理和验证
"""

import pandas as pd
import numpy as np
import os
import pickle
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timedelta
import logging

# 导入配置和数据库连接
try:
    from core.config.settings import PATHS, TABLE_NAMES
    from core.utils.db_connection import db
except ImportError:
    # 回退配置
    PATHS = {
        'data_cache': '/home/zcy/alpha006_20251223/data/cache',
        'data_processed': '/home/zcy/alpha006_20251223/data/processed',
    }
    TABLE_NAMES = {
        'daily_kline': 'daily_kline',
        'daily_basic': 'daily_basic',
        'fina_indicator': 'fina_indicator',
        'stk_factor_pro': 'stk_factor_pro',
        'sw_industry': 'sw_industry',
        'stock_st': 'stock_st',
        'index_daily_zzsz': 'index_daily_zzsz',
    }

logger = logging.getLogger(__name__)


class DataLoader:
    """数据加载器类"""

    def __init__(self, use_cache: bool = True, cache_expiry: int = 3600):
        """
        初始化数据加载器

        Args:
            use_cache: 是否使用缓存
            cache_expiry: 缓存过期时间(秒)
        """
        self.use_cache = use_cache
        self.cache_expiry = cache_expiry
        self.cache_dir = PATHS['data_cache']
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")

    def _save_cache(self, data: Any, cache_key: str) -> bool:
        """保存到缓存"""
        if not self.use_cache:
            return False

        try:
            cache_path = self._get_cache_path(cache_key)
            with open(cache_path, 'wb') as f:
                pickle.dump({
                    'data': data,
                    'timestamp': datetime.now().timestamp(),
                    'version': '2.0'
                }, f)
            logger.debug(f"缓存已保存: {cache_key}")
            return True
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")
            return False

    def _load_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存加载"""
        if not self.use_cache:
            return None

        try:
            cache_path = self._get_cache_path(cache_key)
            if not os.path.exists(cache_path):
                return None

            # 检查缓存是否过期
            file_time = os.path.getmtime(cache_path)
            if datetime.now().timestamp() - file_time > self.cache_expiry:
                os.remove(cache_path)
                return None

            with open(cache_path, 'rb') as f:
                cached = pickle.load(f)

            # 检查版本
            if cached.get('version') != '2.0':
                return None

            logger.debug(f"从缓存加载: {cache_key}")
            return cached['data']

        except Exception as e:
            logger.warning(f"缓存加载失败: {e}")
            return None

    def get_tradable_stocks(self, target_date: str, filter_st: bool = True) -> List[str]:
        """
        获取可交易股票列表

        Args:
            target_date: 目标日期 (YYYYMMDD)
            filter_st: 是否过滤ST股票

        Returns:
            股票代码列表
        """
        cache_key = f"tradable_stocks_{target_date}_{filter_st}"

        # 尝试从缓存加载
        if self.use_cache:
            cached = self._load_cache(cache_key)
            if cached is not None:
                return cached

        # 从数据库获取
        sql = f"""
        SELECT DISTINCT ts_code
        FROM {TABLE_NAMES['daily_kline']}
        WHERE trade_date = %s
        """
        data = db.execute_query(sql, (target_date,))
        all_stocks = [row['ts_code'] for row in data]

        if not all_stocks:
            logger.warning(f"当日无交易数据: {target_date}")
            return []

        if filter_st:
            # 过滤ST股票
            sql_st = f"SELECT ts_code FROM {TABLE_NAMES['stock_st']} WHERE type = 'ST'"
            st_data = db.execute_query(sql_st, ())
            st_stocks = set([row['ts_code'] for row in st_data])

            valid_stocks = [s for s in all_stocks if s not in st_stocks]
            logger.info(f"过滤ST股票: {len(all_stocks)} -> {len(valid_stocks)}")
        else:
            valid_stocks = all_stocks

        # 保存到缓存
        self._save_cache(valid_stocks, cache_key)

        return valid_stocks

    def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """
        获取交易日列表

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            交易日列表
        """
        cache_key = f"trading_days_{start_date}_{end_date}"

        cached = self._load_cache(cache_key)
        if cached is not None:
            return cached

        sql = f"""
        SELECT DISTINCT trade_date
        FROM {TABLE_NAMES['daily_kline']}
        WHERE trade_date >= %s AND trade_date <= %s
        ORDER BY trade_date
        """
        data = db.execute_query(sql, (start_date, end_date))
        trading_days = [row['trade_date'] for row in data]

        self._save_cache(trading_days, cache_key)
        return trading_days

    def get_price_data(self, stocks: List[str], start_date: str, end_date: str,
                      columns: List[str] = None) -> pd.DataFrame:
        """
        获取价格数据

        Args:
            stocks: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            columns: 需要的列，None则返回所有列

        Returns:
            价格数据DataFrame
        """
        if not stocks:
            return pd.DataFrame()

        cache_key = f"price_{'_'.join(sorted(stocks)[:5])}_{start_date}_{end_date}"

        cached = self._load_cache(cache_key)
        if cached is not None:
            return cached

        if columns is None:
            columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']
        else:
            columns = ['ts_code', 'trade_date'] + [c for c in columns if c != 'ts_code' and c != 'trade_date']

        placeholders = ','.join(['%s'] * len(stocks))
        sql = f"""
        SELECT {', '.join(columns)}
        FROM {TABLE_NAMES['daily_kline']}
        WHERE trade_date >= %s AND trade_date <= %s
          AND ts_code IN ({placeholders})
        ORDER BY ts_code, trade_date
        """

        params = [start_date, end_date] + stocks
        data = db.execute_query(sql, params)
        df = pd.DataFrame(data)

        if len(df) == 0:
            logger.warning(f"未获取到价格数据: {len(stocks)}只股票, {start_date}~{end_date}")
            return df

        # 数据类型转换
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        for col in ['open', 'high', 'low', 'close', 'vol']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"获取价格数据: {len(df):,} 条记录, {df['ts_code'].nunique()} 只股票")

        # 保存缓存
        self._save_cache(df, cache_key)

        return df

    def get_fina_data(self, stocks: List[str], target_date: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        获取财务数据 (PE和净利润增长率)

        Args:
            stocks: 股票代码列表
            target_date: 目标日期 (YYYYMMDD)

        Returns:
            (PE数据, 财务数据) 两个DataFrame
        """
        if not stocks:
            return pd.DataFrame(), pd.DataFrame()

        # PE数据
        placeholders = ','.join(['%s'] * len(stocks))
        sql_pe = f"""
        SELECT ts_code, trade_date, pe_ttm
        FROM {TABLE_NAMES['daily_basic']}
        WHERE trade_date = %s
          AND ts_code IN ({placeholders})
          AND pe_ttm IS NOT NULL
          AND pe_ttm > 0
        """
        data_pe = db.execute_query(sql_pe, [target_date] + stocks)
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
        data_fina = db.execute_query(sql_fina, [target_date] + stocks)
        df_fina = pd.DataFrame(data_fina)

        logger.info(f"获取PE数据: {len(df_pe)} 条, 财务数据: {len(df_fina)} 条")

        return df_pe, df_fina

    def get_industry_data(self, stocks: List[str] = None) -> pd.DataFrame:
        """
        获取申万一级行业分类

        Args:
            stocks: 股票代码列表，None则返回所有

        Returns:
            行业数据DataFrame
        """
        cache_key = "sw_industry_all"

        cached = self._load_cache(cache_key)
        if cached is not None:
            if stocks is None:
                return cached
            else:
                return cached[cached['ts_code'].isin(stocks)]

        sql = f"""
        SELECT ts_code, l1_name
        FROM {TABLE_NAMES['sw_industry']}
        """
        if stocks:
            placeholders = ','.join(['%s'] * len(stocks))
            sql += f" WHERE ts_code IN ({placeholders})"

        data = db.execute_query(sql, stocks or ())
        df = pd.DataFrame(data)

        if len(df) == 0:
            logger.warning("未获取到行业数据")
            return df

        logger.info(f"获取行业数据: {len(df)} 条记录")

        # 保存缓存
        self._save_cache(df, cache_key)

        return df

    def get_cr_qfq_data(self, stocks: List[str], target_date: str) -> pd.DataFrame:
        """
        获取CR指标数据 (前复权)

        Args:
            stocks: 股票代码列表
            target_date: 目标日期 (YYYYMMDD)

        Returns:
            CR数据DataFrame
        """
        if not stocks:
            return pd.DataFrame()

        placeholders = ','.join(['%s'] * len(stocks))
        sql = f"""
        SELECT ts_code, trade_date, cr_qfq
        FROM {TABLE_NAMES['stk_factor_pro']}
        WHERE trade_date = %s
          AND ts_code IN ({placeholders})
        """

        data = db.execute_query(sql, [target_date] + stocks)
        df = pd.DataFrame(data)

        logger.info(f"获取CR数据: {len(df)} 条记录")

        return df

    def get_market_cap_and_amount(self, target_date: str) -> pd.DataFrame:
        """
        获取流通市值和成交额数据

        Args:
            target_date: 目标日期 (YYYYMMDD)

        Returns:
            DataFrame包含ts_code, circ_mv, amount
        """
        cache_key = f"market_cap_amount_{target_date}"

        # 尝试从缓存加载
        if self.use_cache:
            cached = self._load_cache(cache_key)
            if cached is not None:
                return cached

        # 获取流通市值数据 (circ_mv)
        sql_mv = f"""
        SELECT ts_code, circ_mv
        FROM {TABLE_NAMES['daily_basic']}
        WHERE trade_date = %s
          AND circ_mv IS NOT NULL
          AND circ_mv > 0
        """
        data_mv = db.execute_query(sql_mv, (target_date,))
        df_mv = pd.DataFrame(data_mv)

        # 获取成交额数据
        sql_amount = f"""
        SELECT ts_code, amount
        FROM {TABLE_NAMES['daily_kline']}
        WHERE trade_date = %s
          AND amount IS NOT NULL
          AND amount > 0
        """
        data_amount = db.execute_query(sql_amount, (target_date,))
        df_amount = pd.DataFrame(data_amount)

        # 合并数据
        if len(df_mv) == 0 or len(df_amount) == 0:
            logger.warning(f"未获取到市值或成交额数据: {target_date}")
            return pd.DataFrame()

        df_merged = df_mv.merge(df_amount, on='ts_code', how='inner')

        logger.info(f"获取流通市值/成交额数据: {len(df_merged)} 只股票")

        # 保存缓存
        self._save_cache(df_merged, cache_key)

        return df_merged

    def get_industry_data_from_csv(self, stocks: List[str] = None) -> pd.DataFrame:
        """
        从CSV文件获取申万一级行业分类

        Args:
            stocks: 股票代码列表，None则返回所有

        Returns:
            行业数据DataFrame (ts_code, l1_name)
        """
        cache_key = "sw_industry_csv_all"

        # 尝试从缓存加载
        if self.use_cache:
            cached = self._load_cache(cache_key)
            if cached is not None:
                if stocks is None:
                    return cached
                else:
                    return cached[cached['ts_code'].isin(stocks)]

        # 从CSV文件读取
        csv_path = '/home/zcy/alpha006_20251223/data/raw/industry_sw.csv'

        try:
            df = pd.read_csv(csv_path, encoding='utf-8')

            # 只保留需要的列
            df = df[['ts_code', 'l1_name']].drop_duplicates(subset=['ts_code'], keep='first')

            logger.info(f"从CSV获取行业数据: {len(df)} 条记录")

            # 保存缓存
            self._save_cache(df, cache_key)

            if stocks:
                return df[df['ts_code'].isin(stocks)]
            return df

        except Exception as e:
            logger.error(f"读取行业CSV失败: {e}")
            return pd.DataFrame()

    def get_price_data_for_period(self, stocks: List[str], target_date: str,
                                 lookback_days: int) -> pd.DataFrame:
        """
        获取指定股票在目标日期前N天的价格数据

        Args:
            stocks: 股票代码列表
            target_date: 目标日期 (YYYYMMDD)
            lookback_days: 回溯天数

        Returns:
            价格数据DataFrame
        """
        # 计算开始日期（需要额外缓冲）
        target_dt = datetime.strptime(target_date, '%Y%m%d')
        start_dt = target_dt - timedelta(days=lookback_days + 20)  # 20天缓冲
        start_date = start_dt.strftime('%Y%m%d')

        return self.get_price_data(stocks, start_date, target_date)

    def validate_data_quality(self, df: pd.DataFrame, name: str,
                            min_valid_ratio: float = 0.8) -> Dict[str, Any]:
        """
        验证数据质量

        Args:
            df: 待验证的DataFrame
            name: 数据名称
            min_valid_ratio: 最小有效数据比例

        Returns:
            质量检查结果字典
        """
        if df is None or len(df) == 0:
            return {
                'name': name,
                'valid': False,
                'reason': '数据为空',
                'stats': {}
            }

        stats = {
            'total_rows': len(df),
            'total_cols': len(df.columns),
            'missing_ratio': df.isna().sum().sum() / (len(df) * len(df.columns)),
            'duplicate_rows': df.duplicated().sum(),
        }

        # 检查关键列
        required_cols = ['ts_code', 'trade_date']
        missing_cols = [col for col in required_cols if col not in df.columns]

        valid = True
        reasons = []

        if missing_cols:
            valid = False
            reasons.append(f"缺少必要列: {missing_cols}")

        if stats['missing_ratio'] > 1 - min_valid_ratio:
            valid = False
            reasons.append(f"缺失率过高: {stats['missing_ratio']:.2%}")

        if stats['duplicate_rows'] > 0:
            reasons.append(f"存在重复行: {stats['duplicate_rows']}")

        result = {
            'name': name,
            'valid': valid,
            'stats': stats,
            'reasons': reasons if reasons else ['数据质量正常']
        }

        if valid:
            logger.info(f"✅ {name} 数据质量验证通过")
        else:
            logger.warning(f"❌ {name} 数据质量验证失败: {'; '.join(reasons)}")

        return result

    def export_data(self, df: pd.DataFrame, filename: str,
                   format: str = 'csv', output_dir: str = None) -> str:
        """
        导出数据到文件

        Args:
            df: 待导出的DataFrame
            filename: 文件名（不含扩展名）
            format: 导出格式 ('csv', 'excel', 'pickle')
            output_dir: 输出目录，None则使用processed目录

        Returns:
            文件路径
        """
        if output_dir is None:
            output_dir = PATHS['data_processed']

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename_with_time = f"{filename}_{timestamp}"

        if format == 'csv':
            filepath = os.path.join(output_dir, f"{filename_with_time}.csv")
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
        elif format == 'excel':
            filepath = os.path.join(output_dir, f"{filename_with_time}.xlsx")
            df.to_excel(filepath, index=False)
        elif format == 'pickle':
            filepath = os.path.join(output_dir, f"{filename_with_time}.pkl")
            with open(filepath, 'wb') as f:
                pickle.dump(df, f)
        else:
            raise ValueError(f"不支持的格式: {format}")

        logger.info(f"数据已导出: {filepath}")
        return filepath


# 全局实例
data_loader = DataLoader(use_cache=True)


# 兼容旧代码的函数接口
def load_industry_data(industry_path: Optional[str] = None) -> pd.DataFrame:
    """加载行业数据（兼容旧版）"""
    if industry_path:
        try:
            df = pd.read_csv(industry_path)
            return df[['ts_code', 'l1_name']].copy()
        except Exception as e:
            logger.error(f"加载行业数据失败: {e}")
            raise
    else:
        # 从数据库加载
        return data_loader.get_industry_data()


def get_price_data(start_date: str, end_date: str) -> pd.DataFrame:
    """获取价格数据（兼容旧版）"""
    # 获取所有股票
    stocks = data_loader.get_tradable_stocks(end_date)
    if not stocks:
        return pd.DataFrame()

    return data_loader.get_price_data(stocks, start_date, end_date)


def get_index_data(start_date: str, end_date: str, index_code: str = '000300.SH') -> pd.DataFrame:
    """获取指数数据（兼容旧版）"""
    sql = f"""
    SELECT trade_date, close
    FROM {TABLE_NAMES['index_daily_zzsz']}
    WHERE ts_code = %s
      AND trade_date >= %s AND trade_date <= %s
    ORDER BY trade_date
    """

    data = db.execute_query(sql, (index_code, start_date, end_date))
    df = pd.DataFrame(data)

    if len(df) > 0:
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df['close'] = df['close'].astype(float)

    return df


def validate_data(df: pd.DataFrame, name: str) -> bool:
    """验证数据（兼容旧版）"""
    result = data_loader.validate_data_quality(df, name)
    return result['valid']


def save_to_cache(df: pd.DataFrame, filename: str) -> str:
    """保存到缓存（兼容旧版）"""
    cache_path = os.path.join(PATHS['data_cache'], filename)
    df.to_csv(cache_path, index=False)
    return cache_path


def load_from_cache(filename: str) -> Optional[pd.DataFrame]:
    """从缓存加载（兼容旧版）"""
    cache_path = os.path.join(PATHS['data_cache'], filename)
    if os.path.exists(cache_path):
        return pd.read_csv(cache_path)
    return None


__all__ = [
    'DataLoader',
    'data_loader',
    'load_industry_data',
    'get_price_data',
    'get_index_data',
    'validate_data',
    'save_to_cache',
    'load_from_cache',
]