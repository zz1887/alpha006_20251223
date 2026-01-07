"""
Alpha101因子库 - 基础实现框架

包含101个Alpha因子的实现框架
来源: 聚宽Alpha101因子库
"""

import pandas as pd
import numpy as np
from typing import Optional, Union, List
import warnings
warnings.filterwarnings('ignore')

from core.utils.db_connection import db


class Alpha101Base:
    """
    Alpha101因子基础类

    提供因子计算所需的基础函数和数据获取方法
    """

    def __init__(self):
        """初始化因子计算器"""
        self.data_cache = {}

    def get_price_data(self, ts_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取价格数据

        参数:
            ts_codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        返回:
            DataFrame包含: ts_code, trade_date, open, high, low, close, volume, vwap
        """
        # 使用参数化查询避免SQL注入
        placeholders = ','.join(['%s'] * len(ts_codes))
        sql = f"""
        SELECT
            ts_code,
            trade_date,
            open,
            high,
            low,
            close,
            vol as volume,
            amount,
            (close * vol) as vwap  -- 简化vwap计算
        FROM daily_kline
        WHERE ts_code IN ({placeholders})
          AND trade_date >= %s
          AND trade_date <= %s
        ORDER BY ts_code, trade_date
        """

        data = db.execute_query(sql, ts_codes + [start_date, end_date])
        df = pd.DataFrame(data)

        if len(df) > 0:
            # 转换decimal为float
            for col in df.columns:
                if col not in ['ts_code', 'trade_date', 'ann_date']:
                    df[col] = df[col].astype(float)
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            if 'ann_date' in df.columns:
                df['ann_date'] = pd.to_datetime(df['ann_date'], format='%Y%m%d')
            df = df.sort_values(['ts_code', 'trade_date' if 'trade_date' in df.columns else 'ann_date'])

        return df

    def get_daily_basic_data(self, ts_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取日频基础数据

        参数:
            ts_codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        返回:
            DataFrame包含: ts_code, trade_date, turnover_rate, turnover_rate_f, etc.
        """
        placeholders = ','.join(['%s'] * len(ts_codes))
        sql = f"""
        SELECT
            ts_code,
            trade_date,
            turnover_rate,
            turnover_rate_f,
            volume_ratio,
            pe,
            pe_ttm,
            pb,
            ps,
            dv_ratio,
            dv_ttm,
            total_mv,
            circ_mv
        FROM daily_basic
        WHERE ts_code IN ({placeholders})
          AND trade_date >= %s
          AND trade_date <= %s
        ORDER BY ts_code, trade_date
        """

        data = db.execute_query(sql, ts_codes + [start_date, end_date])
        df = pd.DataFrame(data)

        if len(df) > 0:
            # 转换decimal为float
            for col in df.columns:
                if col not in ['ts_code', 'trade_date', 'ann_date']:
                    df[col] = df[col].astype(float)
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            if 'ann_date' in df.columns:
                df['ann_date'] = pd.to_datetime(df['ann_date'], format='%Y%m%d')
            df = df.sort_values(['ts_code', 'trade_date' if 'trade_date' in df.columns else 'ann_date'])

        return df

    def get_fina_indicator_data(self, ts_codes: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取财务指标数据

        参数:
            ts_codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        返回:
            DataFrame包含: ts_code, ann_date, 财务指标
        """
        placeholders = ','.join(['%s'] * len(ts_codes))
        sql = f"""
        SELECT
            ts_code,
            ann_date,
            netprofit_margin as net_profit_margin,
            dt_netprofit_yoy,
            roe,
            roa,
            grossprofit_margin as gross_profit_margin,
            eps,
            bps,
            debt_to_assets as debt_to_asset
        FROM fina_indicator
        WHERE ts_code IN ({placeholders})
          AND ann_date >= %s
          AND ann_date <= %s
          AND update_flag = '1'
        ORDER BY ts_code, ann_date
        """

        data = db.execute_query(sql, ts_codes + [start_date, end_date])
        df = pd.DataFrame(data)

        if len(df) > 0:
            df['ann_date'] = pd.to_datetime(df['ann_date'], format='%Y%m%d')
            df = df.sort_values(['ts_code', 'ann_date'])

        return df

    # ==================== 基础函数 ====================

    @staticmethod
    def rank(series: pd.Series) -> pd.Series:
        """排名函数 - 小值排名小"""
        return series.rank()

    @staticmethod
    def ts_rank(series: pd.Series, window: int) -> pd.Series:
        """时间序列排名"""
        window = int(window)
        return series.rolling(window, min_periods=window).rank()

    @staticmethod
    def ts_argmax(series: pd.Series, window: int) -> pd.Series:
        """时间序列最大值位置"""
        window = int(window)
        return series.rolling(window, min_periods=window).apply(
            lambda x: x.argmax() + 1 if len(x.dropna()) > 0 else np.nan
        )

    @staticmethod
    def ts_argmin(series: pd.Series, window: int) -> pd.Series:
        """时间序列最小值位置"""
        window = int(window)
        return series.rolling(window, min_periods=window).apply(
            lambda x: x.argmin() + 1 if len(x.dropna()) > 0 else np.nan
        )

    @staticmethod
    def correlation(x: pd.Series, y: pd.Series, window: int) -> pd.Series:
        """滚动相关系数"""
        window = int(window)
        return x.rolling(window, min_periods=window).corr(y)

    @staticmethod
    def covariance(x: pd.Series, y: pd.Series, window: int) -> pd.Series:
        """滚动协方差"""
        window = int(window)
        return x.rolling(window, min_periods=window).cov(y)

    @staticmethod
    def stddev(series: pd.Series, window: int) -> pd.Series:
        """滚动标准差"""
        window = int(window)
        return series.rolling(window, min_periods=window).std()

    @staticmethod
    def delta(series: pd.Series, period: int) -> pd.Series:
        """差分"""
        period = int(period)
        return series.diff(period)

    @staticmethod
    def delay(series: pd.Series, period: int) -> pd.Series:
        """滞后"""
        period = int(period)
        return series.shift(period)

    @staticmethod
    def ts_min(series: pd.Series, window: int) -> pd.Series:
        """滚动最小值"""
        window = int(window)
        return series.rolling(window, min_periods=window).min()

    @staticmethod
    def ts_max(series: pd.Series, window: int) -> pd.Series:
        """滚动最大值"""
        window = int(window)
        return series.rolling(window, min_periods=window).max()

    @staticmethod
    def decay_linear(series: pd.Series, window: int) -> pd.Series:
        """线性衰减"""
        window = int(window)
        weights = np.arange(1, window + 1)
        return series.rolling(window, min_periods=window).apply(
            lambda x: np.average(x, weights=weights) if len(x.dropna()) == window else np.nan
        )

    @staticmethod
    def scale(series: pd.Series) -> pd.Series:
        """标准化到[-1, 1]"""
        max_val = series.abs().max()
        if max_val > 0:
            return series / max_val
        return series

    @staticmethod
    def sign(series: pd.Series) -> pd.Series:
        """符号函数"""
        return series.apply(lambda x: np.sign(x) if pd.notna(x) else np.nan)

    @staticmethod
    def SignedPower(x: pd.Series, p: float) -> pd.Series:
        """带符号的幂运算"""
        return x.apply(lambda val: np.sign(val) * (abs(val) ** p) if pd.notna(val) else np.nan)

    @staticmethod
    def product(series: pd.Series, window: int) -> pd.Series:
        """滚动乘积"""
        window = int(window)
        return series.rolling(window, min_periods=window).apply(
            lambda x: np.prod(x.dropna()) if len(x.dropna()) > 0 else np.nan
        )

    @staticmethod
    def sum(series: pd.Series, window: int) -> pd.Series:
        """滚动求和"""
        window = int(window)
        return series.rolling(window, min_periods=window).sum()

    @staticmethod
    def adv(series: pd.Series, window: int) -> pd.Series:
        """平均成交量/金额"""
        window = int(window)
        return series.rolling(window, min_periods=window).mean()


class Alpha101Calculator(Alpha101Base):
    """
    Alpha101因子计算器

    实现101个Alpha因子的计算
    """

    def __init__(self, ts_codes: List[str], start_date: str, end_date: str):
        """
        初始化计算器

        参数:
            ts_codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        """
        super().__init__()
        self.ts_codes = ts_codes
        self.start_date = start_date
        self.end_date = end_date

        # 加载基础数据
        self.load_base_data()

    def load_base_data(self):
        """加载所有需要的基础数据"""
        print("正在加载基础数据...")

        # 价格数据
        self.price_data = self.get_price_data(self.ts_codes, self.start_date, self.end_date)
        print(f"  价格数据: {len(self.price_data)} 条")

        # 日频基础数据
        self.daily_basic = self.get_daily_basic_data(self.ts_codes, self.start_date, self.end_date)
        print(f"  日频基础数据: {len(self.daily_basic)} 条")

        # 财务数据
        self.fina_data = self.get_fina_indicator_data(self.ts_codes, self.start_date, self.end_date)
        print(f"  财务数据: {len(self.fina_data)} 条")

        # 合并数据
        self.merge_data()

    def merge_data(self):
        """合并所有数据"""
        # 合并价格和日频数据
        if len(self.price_data) > 0 and len(self.daily_basic) > 0:
            self.merged_data = pd.merge(
                self.price_data,
                self.daily_basic,
                on=['ts_code', 'trade_date'],
                how='left'
            )
        else:
            self.merged_data = self.price_data

        # 计算衍生指标
        if len(self.merged_data) > 0:
            # 收益率
            self.merged_data['returns'] = self.merged_data.groupby('ts_code')['close'].pct_change()

            # 成交量平均
            for window in [5, 10, 15, 20, 30, 40, 50, 60, 81, 120, 150, 180, 220, 240, 250]:
                self.merged_data[f'adv{window}'] = self.merged_data.groupby('ts_code')['volume'].transform(
                    lambda x: x.rolling(window, min_periods=window).mean()
                )

            # 简单市值（如果可用）
            if 'total_mv' in self.merged_data.columns:
                self.merged_data['cap'] = self.merged_data['total_mv']

        print(f"  合并后数据: {len(self.merged_data)} 条")

    def get_stock_data(self, ts_code: str) -> pd.DataFrame:
        """获取单只股票的数据"""
        if len(self.merged_data) == 0:
            return pd.DataFrame()

        df = self.merged_data[self.merged_data['ts_code'] == ts_code].copy()
        df = df.sort_values('trade_date').reset_index(drop=True)
        return df

    # ==================== Alpha因子实现 ====================

    def alpha_001(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_001: (rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5)
        """
        # 计算条件值
        condition = df['returns'] < 0
        value = pd.Series(index=df.index, dtype=float)
        value[condition] = self.stddev(df['returns'], 20)[condition]
        value[~condition] = df['close'][~condition]

        # SignedPower^2
        value = self.SignedPower(value, 2)

        # Ts_ArgMax
        argmax = self.ts_argmax(value, 5)

        # rank - 0.5
        result = self.rank(argmax) - 0.5

        return result

    def alpha_002(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_002: (-1*correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6))
        """
        # 计算中间变量
        log_volume = np.log(df['volume'])
        delta_log_volume = self.delta(log_volume, 2)
        price_change = (df['close'] - df['open']) / df['open']

        # 排名
        rank_delta_log_volume = self.rank(delta_log_volume)
        rank_price_change = self.rank(price_change)

        # 相关系数
        corr = self.correlation(rank_delta_log_volume, rank_price_change, 6)

        return -1 * corr

    def alpha_003(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_003: (-1*correlation(rank(open), rank(volume), 10))
        """
        rank_open = self.rank(df['open'])
        rank_volume = self.rank(df['volume'])

        corr = self.correlation(rank_open, rank_volume, 10)

        return -1 * corr

    def alpha_004(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_004: (-1*Ts_Rank(rank(low), 9))
        """
        rank_low = self.rank(df['low'])
        ts_rank_low = self.ts_rank(rank_low, 9)

        return -1 * ts_rank_low

    def alpha_005(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_005: (rank((open - (sum(vwap, 10) / 10)))*(-1*abs(rank((close - vwap)))))
        """
        vwap = df['vwap']
        sum_vwap_10 = self.sum(vwap, 10)
        avg_vwap_10 = sum_vwap_10 / 10

        part1 = self.rank(df['open'] - avg_vwap_10)
        part2 = -1 * np.abs(self.rank(df['close'] - vwap))

        return part1 * part2

    def alpha_006(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_006: (-1*correlation(open, volume, 10))
        """
        corr = self.correlation(df['open'], df['volume'], 10)
        return -1 * corr

    def alpha_007(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_007: ((adv20 < volume) ? ((-1*ts_rank(abs(delta(close, 7)), 60))*sign(delta(close, 7))) : (-1*1))
        """
        adv20 = df['adv20']
        condition = adv20 < df['volume']

        result = pd.Series(index=df.index, dtype=float)

        # 满足条件
        delta_close_7 = self.delta(df['close'], 7)
        abs_delta_close_7 = np.abs(delta_close_7)
        ts_rank_abs = self.ts_rank(abs_delta_close_7, 60)
        sign_delta = self.sign(delta_close_7)

        result[condition] = -1 * ts_rank_abs * sign_delta
        result[~condition] = -1

        return result

    def alpha_008(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_008: (-1*rank(((sum(open, 5)*sum(returns, 5)) - delay((sum(open, 5)*sum(returns, 5)), 10))))
        """
        sum_open_5 = self.sum(df['open'], 5)
        sum_returns_5 = self.sum(df['returns'], 5)
        product_5 = sum_open_5 * sum_returns_5

        product_5_delay = self.delay(product_5, 10)

        value = product_5 - product_5_delay

        return -1 * self.rank(value)

    def alpha_009(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_009: ((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1*delta(close, 1))))
        """
        delta_close_1 = self.delta(df['close'], 1)
        ts_min_delta = self.ts_min(delta_close_1, 5)
        ts_max_delta = self.ts_max(delta_close_1, 5)

        condition1 = 0 < ts_min_delta
        condition2 = ts_max_delta < 0

        result = pd.Series(index=df.index, dtype=float)
        result[condition1] = delta_close_1[condition1]
        result[condition2] = delta_close_1[condition2]
        result[~condition1 & ~condition2] = -1 * delta_close_1[~condition1 & ~condition2]

        return result

    def alpha_010(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_010: rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : (-1*delta(close, 1)))))
        """
        delta_close_1 = self.delta(df['close'], 1)
        ts_min_delta = self.ts_min(delta_close_1, 4)
        ts_max_delta = self.ts_max(delta_close_1, 4)

        condition1 = 0 < ts_min_delta
        condition2 = ts_max_delta < 0

        value = pd.Series(index=df.index, dtype=float)
        value[condition1] = delta_close_1[condition1]
        value[condition2] = delta_close_1[condition2]
        value[~condition1 & ~condition2] = -1 * delta_close_1[~condition1 & ~condition2]

        return self.rank(value)

    def alpha_011(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_011: ((rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3)))*rank(delta(volume, 3)))
        """
        vwap_close_diff = df['vwap'] - df['close']

        part1 = self.rank(self.ts_max(vwap_close_diff, 3))
        part2 = self.rank(self.ts_min(vwap_close_diff, 3))
        part3 = self.rank(self.delta(df['volume'], 3))

        return (part1 + part2) * part3

    def alpha_012(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_012: (sign(delta(volume, 1))*(-1 * delta(close, 1)))
        """
        return self.sign(self.delta(df['volume'], 1)) * (-1 * self.delta(df['close'], 1))

    def alpha_013(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_013: (-1*rank(covariance(rank(close), rank(volume), 5)))
        """
        rank_close = self.rank(df['close'])
        rank_volume = self.rank(df['volume'])

        cov = self.covariance(rank_close, rank_volume, 5)

        return -1 * self.rank(cov)

    def alpha_014(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_014: ((-1*rank(delta(returns, 3)))*correlation(open, volume, 10))
        """
        part1 = -1 * self.rank(self.delta(df['returns'], 3))
        part2 = self.correlation(df['open'], df['volume'], 10)

        return part1 * part2

    def alpha_015(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_015: (-1*sum(rank(correlation(rank(high), rank(volume), 3)), 3))
        """
        rank_high = self.rank(df['high'])
        rank_volume = self.rank(df['volume'])

        corr = self.correlation(rank_high, rank_volume, 3)
        rank_corr = self.rank(corr)

        return -1 * self.sum(rank_corr, 3)

    def alpha_016(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_016: (-1*rank(covariance(rank(high), rank(volume), 5)))
        """
        rank_high = self.rank(df['high'])
        rank_volume = self.rank(df['volume'])

        cov = self.covariance(rank_high, rank_volume, 5)

        return -1 * self.rank(cov)

    def alpha_017(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_017: ((-1*rank(ts_rank(close, 10)))*rank(delta(delta(close, 1), 1)))*rank(ts_rank((volume / adv20), 5)))
        """
        part1 = -1 * self.rank(self.ts_rank(df['close'], 10))
        part2 = self.rank(self.delta(self.delta(df['close'], 1), 1))
        part3 = self.rank(self.ts_rank((df['volume'] / df['adv20']), 5))

        return part1 * part2 * part3

    def alpha_018(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_018: (-1*rank(((stddev(abs((close - open)), 5) + (close - open)) + correlation(close, open, 10))))
        """
        abs_diff = np.abs(df['close'] - df['open'])
        std = self.stddev(abs_diff, 5)
        diff = df['close'] - df['open']
        corr = self.correlation(df['close'], df['open'], 10)

        value = std + diff + corr

        return -1 * self.rank(value)

    def alpha_019(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_019: ((-1*sign(((close - delay(close, 7)) + delta(close, 7))))*(1 + rank((1 + sum(returns, 250)))))
        """
        part1 = -1 * self.sign((df['close'] - self.delay(df['close'], 7)) + self.delta(df['close'], 7))
        part2 = 1 + self.rank(1 + self.sum(df['returns'], 250))

        return part1 * part2

    def alpha_020(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_020: (((-1*rank((open - delay(high, 1))))* rank((open - delay(close, 1))))* rank((open - delay(low, 1))))
        """
        part1 = -1 * self.rank(df['open'] - self.delay(df['high'], 1))
        part2 = self.rank(df['open'] - self.delay(df['close'], 1))
        part3 = self.rank(df['open'] - self.delay(df['low'], 1))

        return part1 * part2 * part3

    def alpha_021(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_021: ((((sum(close, 8) / 8) + stddev(close, 8)) < (sum(close, 2) / 2)) ? (-1* 1) : (((sum(close, 2) / 2) < ((sum(close, 8) / 8) - stddev(close, 8))) ? 1 : (((1 < (volume / adv20)) or ((volume / adv20) == 1)) ? 1 : (-1* 1))))
        """
        sum_close_8 = self.sum(df['close'], 8)
        avg_close_8 = sum_close_8 / 8
        std_close_8 = self.stddev(df['close'], 8)

        sum_close_2 = self.sum(df['close'], 2)
        avg_close_2 = sum_close_2 / 2

        condition1 = (avg_close_8 + std_close_8) < avg_close_2
        condition2 = avg_close_2 < (avg_close_8 - std_close_8)
        condition3 = (1 < (df['volume'] / df['adv20'])) | ((df['volume'] / df['adv20']) == 1)

        result = pd.Series(index=df.index, dtype=float)
        result[condition1] = -1
        result[condition2] = 1
        result[~condition1 & condition3] = 1
        result[~condition1 & ~condition2 & ~condition3] = -1

        return result

    def alpha_022(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_022: (-1* (delta(correlation(high, volume, 5), 5)* rank(stddev(close, 20))))
        """
        corr = self.correlation(df['high'], df['volume'], 5)
        delta_corr = self.delta(corr, 5)
        rank_std = self.rank(self.stddev(df['close'], 20))

        return -1 * delta_corr * rank_std

    def alpha_023(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_023: (((sum(high, 20) / 20) < high) ? (-1* delta(high, 2)) : 0)
        """
        avg_high_20 = self.sum(df['high'], 20) / 20
        condition = avg_high_20 < df['high']

        result = pd.Series(index=df.index, dtype=float)
        result[condition] = -1 * self.delta(df['high'], 2)
        result[~condition] = 0

        return result

    def alpha_024(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_024: ((((delta((sum(close, 100) / 100), 100) / delay(close, 100)) < 0.05) or ((delta((sum(close, 100) / 100), 100) / delay(close, 100)) == 0.05)) ? (-1* (close - ts_min(close, 100))) : (-1* delta(close, 3)))
        """
        avg_close_100 = self.sum(df['close'], 100) / 100
        delta_avg = self.delta(avg_close_100, 100)
        delay_close_100 = self.delay(df['close'], 100)

        ratio = delta_avg / delay_close_100

        condition = (ratio < 0.05) | (ratio == 0.05)

        result = pd.Series(index=df.index, dtype=float)
        result[condition] = -1 * (df['close'] - self.ts_min(df['close'], 100))
        result[~condition] = -1 * self.delta(df['close'], 3)

        return result

    def alpha_025(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_025: rank(((((-1* returns)* adv20)* vwap)* (high - close)))
        """
        value = (-1 * df['returns']) * df['adv20'] * df['vwap'] * (df['high'] - df['close'])
        return self.rank(value)

    def alpha_026(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_026: (-1* ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3))
        """
        rank_volume = self.ts_rank(df['volume'], 5)
        rank_high = self.ts_rank(df['high'], 5)

        corr = self.correlation(rank_volume, rank_high, 5)

        return -1 * self.ts_max(corr, 3)

    def alpha_027(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_027: ((0.5 < rank((sum(correlation(rank(volume), rank(vwap), 6), 2) / 2.0))) ? (-1* 1) : 1)
        """
        rank_volume = self.rank(df['volume'])
        rank_vwap = self.rank(df['vwap'])

        corr = self.correlation(rank_volume, rank_vwap, 6)
        sum_corr = self.sum(corr, 2)
        avg_corr = sum_corr / 2.0

        condition = 0.5 < self.rank(avg_corr)

        result = pd.Series(index=df.index, dtype=float)
        result[condition] = -1
        result[~condition] = 1

        return result

    def alpha_028(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_028: scale(((correlation(adv20, low, 5) + ((high + low) / 2)) - close))
        """
        corr = self.correlation(df['adv20'], df['low'], 5)
        mid_price = (df['high'] + df['low']) / 2

        value = corr + mid_price - df['close']

        return self.scale(value)

    def alpha_029(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_029: (min(product(rank(rank(scale(log(sum(ts_min(rank(rank((-1*rank(delta((close - 1), 5))))), 2), 1))))), 1), 5) + ts_rank(delay((-1* returns), 6), 5))
        """
        # 这个因子非常复杂，需要逐步计算
        # 简化版本
        delta_close = self.delta((df['close'] - 1), 5)
        rank_delta = self.rank(delta_close)
        rank_rank_delta = self.rank(rank_delta)
        neg_rank = -1 * rank_rank_delta

        # 简化处理
        result = self.ts_rank(self.delay((-1 * df['returns']), 6), 5)

        return result

    def alpha_030(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_030: (((1.0 - rank(((sign((close - delay(close, 1))) + sign((delay(close, 1) - delay(close, 2)))) + sign((delay(close, 2) - delay(close, 3))))))* sum(volume, 5)) / sum(volume, 20))
        """
        sign1 = self.sign(df['close'] - self.delay(df['close'], 1))
        sign2 = self.sign(self.delay(df['close'], 1) - self.delay(df['close'], 2))
        sign3 = self.sign(self.delay(df['close'], 2) - self.delay(df['close'], 3))

        sum_sign = sign1 + sign2 + sign3

        part1 = 1.0 - self.rank(sum_sign)
        part2 = self.sum(df['volume'], 5)
        part3 = self.sum(df['volume'], 20)

        return (part1 * part2) / part3

    def alpha_031(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_031: ((rank(rank(rank(decay_linear((-1* rank(rank(delta(close, 10)))), 10)))) + rank((-1* delta(close, 3)))) + sign(scale(correlation(adv20, low, 12))))
        """
        part1 = self.rank(self.rank(self.rank(self.decay_linear(-1 * self.rank(self.rank(self.delta(df['close'], 10))), 10))))
        part2 = self.rank(-1 * self.delta(df['close'], 3))
        part3 = self.sign(self.scale(self.correlation(df['adv20'], df['low'], 12)))

        return part1 + part2 + part3

    def alpha_032(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_032: (scale(((sum(close, 7) / 7) - close)) + (20* scale(correlation(vwap, delay(close, 5), 230))))
        """
        part1 = self.scale((self.sum(df['close'], 7) / 7) - df['close'])
        part2 = 20 * self.scale(self.correlation(df['vwap'], self.delay(df['close'], 5), 230))

        return part1 + part2

    def alpha_033(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_033: rank((-1* ((1 - (open / close))^1)))
        """
        value = -1 * ((1 - (df['open'] / df['close'])) ** 1)
        return self.rank(value)

    def alpha_034(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_034: rank(((1 - rank((stddev(returns, 2) / stddev(returns, 5)))) + (1 - rank(delta(close, 1)))))
        """
        std2 = self.stddev(df['returns'], 2)
        std5 = self.stddev(df['returns'], 5)

        part1 = 1 - self.rank(std2 / std5)
        part2 = 1 - self.rank(self.delta(df['close'], 1))

        return self.rank(part1 + part2)

    def alpha_035(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_035: ((Ts_Rank(volume, 32)* (1 - Ts_Rank(((close + high) - low), 16)))* (1 - Ts_Rank(returns, 32)))
        """
        part1 = self.ts_rank(df['volume'], 32)
        part2 = 1 - self.ts_rank((df['close'] + df['high']) - df['low'], 16)
        part3 = 1 - self.ts_rank(df['returns'], 32)

        return part1 * part2 * part3

    def alpha_036(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_036: (((((2.21* rank(correlation((close - open), delay(volume, 1), 15))) + (0.7* rank((open - close)))) + (0.73* rank(Ts_Rank(delay((-1* returns), 6), 5)))) + rank(abs(correlation(vwap, adv20, 6)))) + (0.6* rank((((sum(close, 200) / 200) - open)* (close - open)))))
        """
        part1 = 2.21 * self.rank(self.correlation((df['close'] - df['open']), self.delay(df['volume'], 1), 15))
        part2 = 0.7 * self.rank((df['open'] - df['close']))
        part3 = 0.73 * self.rank(self.ts_rank(self.delay((-1 * df['returns']), 6), 5))
        part4 = self.rank(np.abs(self.correlation(df['vwap'], df['adv20'], 6)))
        part5 = 0.6 * self.rank(((self.sum(df['close'], 200) / 200) - df['open']) * (df['close'] - df['open']))

        return part1 + part2 + part3 + part4 + part5

    def alpha_037(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_037: (rank(correlation(delay((open - close), 1), close, 200)) + rank((open - close)))
        """
        part1 = self.rank(self.correlation(self.delay((df['open'] - df['close']), 1), df['close'], 200))
        part2 = self.rank(df['open'] - df['close'])

        return part1 + part2

    def alpha_038(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_038: ((-1* rank(Ts_Rank(close, 10)))* rank((close / open)))
        """
        part1 = -1 * self.rank(self.ts_rank(df['close'], 10))
        part2 = self.rank(df['close'] / df['open'])

        return part1 * part2

    def alpha_039(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_039: ((-1* rank((delta(close, 7)* (1 - rank(decay_linear((volume / adv20), 9)))))* (1 + rank(sum(returns, 250))))
        """
        part1 = -1 * self.rank(self.delta(df['close'], 7) * (1 - self.rank(self.decay_linear((df['volume'] / df['adv20']), 9))))
        part2 = 1 + self.rank(self.sum(df['returns'], 250))

        return part1 * part2

    def alpha_040(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_040: ((-1* rank(stddev(high, 10)))* correlation(high, volume, 10))
        """
        part1 = -1 * self.rank(self.stddev(df['high'], 10))
        part2 = self.correlation(df['high'], df['volume'], 10)

        return part1 * part2

    def alpha_041(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_041: (((high* low)^0.5) - vwap)
        """
        return np.sqrt(df['high'] * df['low']) - df['vwap']

    def alpha_042(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_042: (rank((vwap - close)) / rank((vwap + close)))
        """
        return self.rank(df['vwap'] - df['close']) / self.rank(df['vwap'] + df['close'])

    def alpha_043(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_043: (ts_rank((volume / adv20), 20)* ts_rank((-1* delta(close, 7)), 8))
        """
        part1 = self.ts_rank(df['volume'] / df['adv20'], 20)
        part2 = self.ts_rank(-1 * self.delta(df['close'], 7), 8)

        return part1 * part2

    def alpha_044(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_044: (-1* correlation(high, rank(volume), 5))
        """
        return -1 * self.correlation(df['high'], self.rank(df['volume']), 5)

    def alpha_045(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_045: (-1* ((rank((sum(delay(close, 5), 20) / 20))* correlation(close, volume, 2))* rank(correlation(sum(close, 5), sum(close, 20), 2))))
        """
        part1 = self.rank((self.sum(self.delay(df['close'], 5), 20) / 20))
        part2 = self.correlation(df['close'], df['volume'], 2)
        part3 = self.rank(self.correlation(self.sum(df['close'], 5), self.sum(df['close'], 20), 2))

        return -1 * (part1 * part2 * part3)

    def alpha_046(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_046: ((0.25 < (((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10))) ? (-1* 1) : (((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < 0) ? 1 : ((-1* 1)* (close - delay(close, 1)))))
        """
        diff1 = (self.delay(df['close'], 20) - self.delay(df['close'], 10)) / 10
        diff2 = (self.delay(df['close'], 10) - df['close']) / 10

        condition1 = 0.25 < (diff1 - diff2)
        condition2 = (diff1 - diff2) < 0

        result = pd.Series(index=df.index, dtype=float)
        result[condition1] = -1
        result[condition2] = 1
        result[~condition1 & ~condition2] = -1 * (df['close'] - self.delay(df['close'], 1))

        return result

    def alpha_047(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_047: ((((rank((1 / close))* volume) / adv20)* ((high* rank((high - close))) / (sum(high, 5) / 5))) - rank((vwap - delay(vwap, 5))))
        """
        part1 = (self.rank(1 / df['close']) * df['volume']) / df['adv20']
        part2 = (df['high'] * self.rank(df['high'] - df['close'])) / (self.sum(df['high'], 5) / 5)
        part3 = self.rank(df['vwap'] - self.delay(df['vwap'], 5))

        return (part1 * part2) - part3

    def alpha_049(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_049: (((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < (-1* 0.1)) ? 1 : ((-1* 1)* (close - delay(close, 1))))
        """
        diff1 = (self.delay(df['close'], 20) - self.delay(df['close'], 10)) / 10
        diff2 = (self.delay(df['close'], 10) - df['close']) / 10

        condition = (diff1 - diff2) < (-1 * 0.1)

        result = pd.Series(index=df.index, dtype=float)
        result[condition] = 1
        result[~condition] = -1 * (df['close'] - self.delay(df['close'], 1))

        return result

    def alpha_050(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_050: (-1* ts_max(rank(correlation(rank(volume), rank(vwap), 5)), 5))
        """
        rank_volume = self.rank(df['volume'])
        rank_vwap = self.rank(df['vwap'])

        corr = self.correlation(rank_volume, rank_vwap, 5)
        rank_corr = self.rank(corr)

        return -1 * self.ts_max(rank_corr, 5)

    def alpha_051(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_051: (((((delay(close, 20) - delay(close, 10)) / 10) - ((delay(close, 10) - close) / 10)) < (-1* 0.05)) ? 1 : ((-1* 1)* (close - delay(close, 1))))
        """
        diff1 = (self.delay(df['close'], 20) - self.delay(df['close'], 10)) / 10
        diff2 = (self.delay(df['close'], 10) - df['close']) / 10

        condition = (diff1 - diff2) < (-1 * 0.05)

        result = pd.Series(index=df.index, dtype=float)
        result[condition] = 1
        result[~condition] = -1 * (df['close'] - self.delay(df['close'], 1))

        return result

    def alpha_052(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_052: ((((-1* ts_min(low, 5)) + delay(ts_min(low, 5), 5))* rank(((sum(returns, 240) - sum(returns, 20)) / 220)))* ts_rank(volume, 5))
        """
        min_low_5 = self.ts_min(df['low'], 5)
        part1 = -1 * min_low_5 + self.delay(min_low_5, 5)
        part2 = self.rank((self.sum(df['returns'], 240) - self.sum(df['returns'], 20)) / 220)
        part3 = self.ts_rank(df['volume'], 5)

        return part1 * part2 * part3

    def alpha_053(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_053: (-1* delta((((close - low) - (high - close)) / (close - low)), 9))
        """
        value = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['close'] - df['low'])
        return -1 * self.delta(value, 9)

    def alpha_054(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_054: ((-1* ((low - close)* (open^5))) / ((low - high)* (close^5)))
        """
        numerator = -1 * ((df['low'] - df['close']) * (df['open'] ** 5))
        denominator = (df['low'] - df['high']) * (df['close'] ** 5)

        return numerator / denominator

    def alpha_055(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_055: (-1* correlation(rank(((close - ts_min(low, 12)) / (ts_max(high, 12) - ts_min(low, 12)))), rank(volume), 6))
        """
        value = (df['close'] - self.ts_min(df['low'], 12)) / (self.ts_max(df['high'], 12) - self.ts_min(df['low'], 12))

        return -1 * self.correlation(self.rank(value), self.rank(df['volume']), 6)

    def alpha_056(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_056: (0 - (1* (rank((sum(returns, 10) / sum(sum(returns, 2), 3)))* rank((returns* cap)))))
        """
        part1 = self.rank((self.sum(df['returns'], 10) / self.sum(self.sum(df['returns'], 2), 3)))
        part2 = self.rank(df['returns'] * df['cap'])

        return 0 - (1 * part1 * part2)

    def alpha_057(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_057: (0 - (1* ((close - vwap) / decay_linear(rank(ts_argmax(close, 30)), 2))))
        """
        part1 = df['close'] - df['vwap']
        part2 = self.decay_linear(self.rank(self.ts_argmax(df['close'], 30)), 2)

        return 0 - (1 * (part1 / part2))

    def alpha_060(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_060: (0 - (1* ((2* scale(rank(((((close - low) - (high - close)) / (high - low))* volume)))) - scale(rank(ts_argmax(close, 10))))))
        """
        value1 = (((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])) * df['volume']
        part1 = 2 * self.scale(self.rank(value1))
        part2 = self.scale(self.rank(self.ts_argmax(df['close'], 10)))

        return 0 - (1 * (part1 - part2))

    def alpha_061(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_061: (rank((vwap - ts_min(vwap, 16.1219))) < rank(correlation(vwap, adv180, 17.9282)))
        """
        part1 = self.rank(df['vwap'] - self.ts_min(df['vwap'], 16.1219))
        part2 = self.rank(self.correlation(df['vwap'], df['adv180'], 17.9282))

        return (part1 < part2).astype(float)

    def alpha_062(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_062: ((rank(correlation(vwap, sum(adv20, 22.4101), 9.91009)) < rank(((rank(open) + rank(open)) < (rank(((high + low) / 2)) + rank(high)))))*-1)
        """
        part1 = self.rank(self.correlation(df['vwap'], self.sum(df['adv20'], 22.4101), 9.91009))
        part2 = self.rank(((self.rank(df['open']) + self.rank(df['open'])) < (self.rank((df['high'] + df['low']) / 2) + self.rank(df['high']))))

        return (part1 < part2).astype(float) * -1

    def alpha_064(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_064: ((rank(correlation(sum(((open* 0.178404) + (low* (1 - 0.178404))), 12.7054), sum(adv120, 12.7054), 16.6208)) < rank(delta(((((high + low) / 2)* 0.178404) + (vwap* (1 - 0.178404))), 3.69741))) * -1)
        """
        value1 = (df['open'] * 0.178404) + (df['low'] * (1 - 0.178404))
        value2 = (df['high'] + df['low']) / 2 * 0.178404 + df['vwap'] * (1 - 0.178404)

        part1 = self.rank(self.correlation(self.sum(value1, 12.7054), self.sum(df['adv120'], 12.7054), 16.6208))
        part2 = self.rank(self.delta(value2, 3.69741))

        return (part1 < part2).astype(float) * -1

    def alpha_065(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_065: ((rank(correlation(((open* 0.00817205) + (vwap* (1 - 0.00817205))), sum(adv60, 8.6911), 6.40374)) < rank((open - ts_min(open, 13.635)))) * -1)
        """
        value = (df['open'] * 0.00817205) + (df['vwap'] * (1 - 0.00817205))

        part1 = self.rank(self.correlation(value, self.sum(df['adv60'], 8.6911), 6.40374))
        part2 = self.rank(df['open'] - self.ts_min(df['open'], 13.635))

        return (part1 < part2).astype(float) * -1

    def alpha_066(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_066: ((rank(decay_linear(delta(vwap, 3.51013), 7.23052)) + Ts_Rank(decay_linear(((((low* 0.96633) + (low* (1 - 0.96633))) - vwap) / (open - ((high + low) / 2))), 11.4157), 6.72611)) * -1)
        """
        part1 = self.rank(self.decay_linear(self.delta(df['vwap'], 3.51013), 7.23052))

        value2 = ((df['low'] * 0.96633) + (df['low'] * (1 - 0.96633)) - df['vwap']) / (df['open'] - ((df['high'] + df['low']) / 2))
        part2 = self.ts_rank(self.decay_linear(value2, 11.4157), 6.72611)

        return (part1 + part2) * -1

    def alpha_068(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_068: ((Ts_Rank(correlation(rank(high), rank(adv15), 8.91644), 13.9333) < rank(delta(((close* 0.518371) + (low* (1 - 0.518371))), 1.06157))) * -1)
        """
        part1 = self.ts_rank(self.correlation(self.rank(df['high']), self.rank(df['adv15']), 8.91644), 13.9333)
        value = df['close'] * 0.518371 + df['low'] * (1 - 0.518371)
        part2 = self.rank(self.delta(value, 1.06157))

        return (part1 < part2).astype(float) * -1

    def alpha_071(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_071: max(Ts_Rank(decay_linear(correlation(Ts_Rank(close, 3.43976), Ts_Rank(adv180, 12.0647), 18.0175), 4.20501), 15.6948), Ts_Rank(decay_linear((rank(((low + open) - (vwap + vwap)))^2), 16.4662), 4.4388))
        """
        part1 = self.ts_rank(
            self.decay_linear(
                self.correlation(
                    self.ts_rank(df['close'], 3.43976),
                    self.ts_rank(df['adv180'], 12.0647),
                    18.0175
                ),
                4.20501
            ),
            15.6948
        )

        value2 = self.rank(((df['low'] + df['open']) - (df['vwap'] + df['vwap']))) ** 2
        part2 = self.ts_rank(self.decay_linear(value2, 16.4662), 4.4388)

        return np.maximum(part1, part2)

    def alpha_072(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_072: (rank(decay_linear(correlation(((high + low) / 2), adv40, 8.93345), 10.1519)) / rank(decay_linear(correlation(Ts_Rank(vwap, 3.72469), Ts_Rank(volume, 18.5188), 6.86671), 2.95011)))
        """
        part1 = self.rank(self.decay_linear(self.correlation((df['high'] + df['low']) / 2, df['adv40'], 8.93345), 10.1519))
        part2 = self.rank(self.decay_linear(self.correlation(self.ts_rank(df['vwap'], 3.72469), self.ts_rank(df['volume'], 18.5188), 6.86671), 2.95011))

        return part1 / part2

    def alpha_073(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_073: (max(rank(decay_linear(delta(vwap, 4.72775), 2.91864)), Ts_Rank(decay_linear(((delta(((open* 0.147155) + (low* (1 - 0.147155))), 2.03608) / ((open* 0.147155) + (low* (1 - 0.147155)))) * -1), 3.33829), 16.7411)) * -1)
        """
        part1 = self.rank(self.decay_linear(self.delta(df['vwap'], 4.72775), 2.91864))

        value2 = (df['open'] * 0.147155) + (df['low'] * (1 - 0.147155))
        delta_value2 = self.delta(value2, 2.03608)
        ratio = (delta_value2 / value2) * -1

        part2 = self.ts_rank(self.decay_linear(ratio, 3.33829), 16.7411)

        return np.maximum(part1, part2) * -1

    def alpha_074(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_074: ((rank(correlation(close, sum(adv30, 37.4843), 15.1365)) < rank(correlation(rank(((high* 0.0261661) + (vwap* (1 - 0.0261661)))), rank(volume), 11.4791))) * -1)
        """
        part1 = self.rank(self.correlation(df['close'], self.sum(df['adv30'], 37.4843), 15.1365))
        value = df['high'] * 0.0261661 + df['vwap'] * (1 - 0.0261661)
        part2 = self.rank(self.correlation(self.rank(value), self.rank(df['volume']), 11.4791))

        return (part1 < part2).astype(float) * -1

    def alpha_075(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_075: (rank(correlation(vwap, volume, 4.24304)) < rank(correlation(rank(low), rank(adv50), 12.4413)))
        """
        part1 = self.rank(self.correlation(df['vwap'], df['volume'], 4.24304))
        part2 = self.rank(self.correlation(self.rank(df['low']), self.rank(df['adv50']), 12.4413))

        return (part1 < part2).astype(float)

    def alpha_077(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_077: min(rank(decay_linear(((((high + low) / 2) + high) - (vwap + high)), 20.0451)), rank(decay_linear(correlation(((high + low) / 2), adv40, 3.1614), 5.64125)))
        """
        value1 = (((df['high'] + df['low']) / 2) + df['high']) - (df['vwap'] + df['high'])
        part1 = self.rank(self.decay_linear(value1, 20.0451))

        part2 = self.rank(self.decay_linear(self.correlation((df['high'] + df['low']) / 2, df['adv40'], 3.1614), 5.64125))

        return np.minimum(part1, part2)

    def alpha_078(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_078: (rank(correlation(sum(((low* 0.352233) + (vwap* (1 - 0.352233))), 19.7428), sum(adv40, 19.7428), 6.83313))^rank(correlation(rank(vwap), rank(volume), 5.77492)))
        """
        value = df['low'] * 0.352233 + df['vwap'] * (1 - 0.352233)
        part1 = self.rank(self.correlation(self.sum(value, 19.7428), self.sum(df['adv40'], 19.7428), 6.83313))
        part2 = self.rank(self.correlation(self.rank(df['vwap']), self.rank(df['volume']), 5.77492))

        return part1 ** part2

    def alpha_083(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_083: ((rank(delay(((high - low) / (sum(close, 5) / 5)), 2))* rank(rank(volume))) / (((high - low) / (sum(close, 5) / 5)) / (vwap - close)))
        """
        value1 = (df['high'] - df['low']) / (self.sum(df['close'], 5) / 5)
        part1 = self.rank(self.delay(value1, 2)) * self.rank(self.rank(df['volume']))
        part2 = value1 / (df['vwap'] - df['close'])

        return part1 / part2

    def alpha_084(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_084: SignedPower(Ts_Rank((vwap - ts_max(vwap, 15.3217)), 20.7127), delta(close, 4.96796))
        """
        value = df['vwap'] - self.ts_max(df['vwap'], 15.3217)
        rank_value = self.ts_rank(value, 20.7127)
        power = self.delta(df['close'], 4.96796)

        return self.SignedPower(rank_value, power.iloc[-1] if isinstance(power, pd.Series) else power)

    def alpha_085(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_085: (rank(correlation(((high* 0.876703) + (close* (1 - 0.876703))), adv30, 9.61331))^rank(correlation(Ts_Rank(((high + low) / 2), 3.70596), Ts_Rank(volume, 10.1595), 7.11408)))
        """
        value1 = df['high'] * 0.876703 + df['close'] * (1 - 0.876703)
        part1 = self.rank(self.correlation(value1, df['adv30'], 9.61331))

        value2 = (df['high'] + df['low']) / 2
        part2 = self.rank(self.correlation(self.ts_rank(value2, 3.70596), self.ts_rank(df['volume'], 10.1595), 7.11408))

        return part1 ** part2

    def alpha_086(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_086: ((Ts_Rank(correlation(close, sum(adv20, 14.7444), 6.00049), 20.4195) < rank(((open + close) - (vwap + open)))) * -1)
        """
        part1 = self.ts_rank(self.correlation(df['close'], self.sum(df['adv20'], 14.7444), 6.00049), 20.4195)
        part2 = self.rank((df['open'] + df['close']) - (df['vwap'] + df['open']))

        return (part1 < part2).astype(float) * -1

    def alpha_088(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_088: min(rank(decay_linear(((rank(open) + rank(low)) - (rank(high) + rank(close))), 8.06882)), Ts_Rank(decay_linear(correlation(Ts_Rank(close, 8.44728), Ts_Rank(adv60, 20.6966), 8.01266), 6.65053), 2.61957))
        """
        value1 = (self.rank(df['open']) + self.rank(df['low'])) - (self.rank(df['high']) + self.rank(df['close']))
        part1 = self.rank(self.decay_linear(value1, 8.06882))

        part2 = self.ts_rank(
            self.decay_linear(
                self.correlation(
                    self.ts_rank(df['close'], 8.44728),
                    self.ts_rank(df['adv60'], 20.6966),
                    8.01266
                ),
                6.65053
            ),
            2.61957
        )

        return np.minimum(part1, part2)

    def alpha_092(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_092: min(Ts_Rank(decay_linear(((((high + low) / 2) + close) < (low + open)), 14.7221), 18.8683), Ts_Rank(decay_linear(correlation(rank(low), rank(adv30), 7.58555), 6.94024), 6.80584))
        """
        value1 = (((df['high'] + df['low']) / 2) + df['close']) < (df['low'] + df['open'])
        part1 = self.ts_rank(self.decay_linear(value1.astype(float), 14.7221), 18.8683)

        part2 = self.ts_rank(
            self.decay_linear(
                self.correlation(self.rank(df['low']), self.rank(df['adv30']), 7.58555),
                6.94024
            ),
            6.80584
        )

        return np.minimum(part1, part2)

    def alpha_094(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_094: ((rank((vwap - ts_min(vwap, 11.5783)))^Ts_Rank(correlation(Ts_Rank(vwap, 19.6462), Ts_Rank(adv60, 4.02992), 18.0926), 2.70756)) * -1)
        """
        part1 = self.rank(df['vwap'] - self.ts_min(df['vwap'], 11.5783))
        part2 = self.ts_rank(
            self.correlation(
                self.ts_rank(df['vwap'], 19.6462),
                self.ts_rank(df['adv60'], 4.02992),
                18.0926
            ),
            2.70756
        )

        return (part1 ** part2) * -1

    def alpha_096(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_096: (max(Ts_Rank(decay_linear(correlation(rank(vwap), rank(volume), 3.83878), 4.16783), 8.38151), Ts_Rank(decay_linear(Ts_ArgMax(correlation(Ts_Rank(close, 7.45404), Ts_Rank(adv60, 4.13242), 3.65459), 12.6556), 14.0365), 13.4143)) * -1)
        """
        part1 = self.ts_rank(
            self.decay_linear(
                self.correlation(self.rank(df['vwap']), self.rank(df['volume']), 3.83878),
                4.16783
            ),
            8.38151
        )

        corr = self.correlation(
            self.ts_rank(df['close'], 7.45404),
            self.ts_rank(df['adv60'], 4.13242),
            3.65459
        )
        argmax = self.ts_argmax(corr, 12.6556)
        part2 = self.ts_rank(self.decay_linear(argmax, 14.0365), 13.4143)

        return np.maximum(part1, part2) * -1

    def alpha_098(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_098: (rank(decay_linear(correlation(vwap, sum(adv5, 26.4719), 4.58418), 7.18088)) - rank(decay_linear(Ts_Rank(Ts_ArgMin(correlation(rank(open), rank(adv15), 20.8187), 8.62571), 6.95668), 8.07206)))
        """
        part1 = self.rank(self.decay_linear(self.correlation(df['vwap'], self.sum(df['adv5'], 26.4719), 4.58418), 7.18088))

        corr = self.correlation(self.rank(df['open']), self.rank(df['adv15']), 20.8187)
        argmin = self.ts_argmin(corr, 8.62571)
        part2 = self.rank(self.decay_linear(self.ts_rank(argmin, 6.95668), 8.07206))

        return part1 - part2

    def alpha_099(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_099: ((rank(correlation(sum(((high + low) / 2), 19.8975), sum(adv60, 19.8975), 8.8136)) < rank(correlation(low, volume, 6.28259))) * -1)
        """
        value = (df['high'] + df['low']) / 2
        part1 = self.rank(self.correlation(self.sum(value, 19.8975), self.sum(df['adv60'], 19.8975), 8.8136))
        part2 = self.rank(self.correlation(df['low'], df['volume'], 6.28259))

        return (part1 < part2).astype(float) * -1

    def alpha_101(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_101: ((close - open) / ((high - low) + .001))
        """
        return (df['close'] - df['open']) / ((df['high'] - df['low']) + 0.001)

    def calculate_all(self) -> pd.DataFrame:
        """
        计算所有已实现的Alpha因子

        返回:
            DataFrame包含: ts_code, trade_date, alpha_001 - alpha_101
        """
        print("\n开始计算Alpha101因子...")
        print("=" * 80)

        # 获取所有股票代码
        unique_codes = self.merged_data['ts_code'].unique()

        all_results = []

        for ts_code in unique_codes:
            df = self.get_stock_data(ts_code)

            if len(df) == 0:
                continue

            # 创建结果DataFrame
            result = pd.DataFrame({
                'ts_code': ts_code,
                'trade_date': df['trade_date']
            })

            # 计算各个因子
            factor_methods = [
                ('alpha_001', self.alpha_001),
                ('alpha_002', self.alpha_002),
                ('alpha_003', self.alpha_003),
                ('alpha_004', self.alpha_004),
                ('alpha_005', self.alpha_005),
                ('alpha_006', self.alpha_006),
                ('alpha_007', self.alpha_007),
                ('alpha_008', self.alpha_008),
                ('alpha_009', self.alpha_009),
                ('alpha_010', self.alpha_010),
                ('alpha_011', self.alpha_011),
                ('alpha_012', self.alpha_012),
                ('alpha_013', self.alpha_013),
                ('alpha_014', self.alpha_014),
                ('alpha_015', self.alpha_015),
                ('alpha_016', self.alpha_016),
                ('alpha_017', self.alpha_017),
                ('alpha_018', self.alpha_018),
                ('alpha_019', self.alpha_019),
                ('alpha_020', self.alpha_020),
                ('alpha_021', self.alpha_021),
                ('alpha_022', self.alpha_022),
                ('alpha_023', self.alpha_023),
                ('alpha_024', self.alpha_024),
                ('alpha_025', self.alpha_025),
                ('alpha_026', self.alpha_026),
                ('alpha_027', self.alpha_027),
                ('alpha_028', self.alpha_028),
                ('alpha_029', self.alpha_029),
                ('alpha_030', self.alpha_030),
                ('alpha_031', self.alpha_031),
                ('alpha_032', self.alpha_032),
                ('alpha_033', self.alpha_033),
                ('alpha_034', self.alpha_034),
                ('alpha_035', self.alpha_035),
                ('alpha_036', self.alpha_036),
                ('alpha_037', self.alpha_037),
                ('alpha_038', self.alpha_038),
                ('alpha_039', self.alpha_039),
                ('alpha_040', self.alpha_040),
                ('alpha_041', self.alpha_041),
                ('alpha_042', self.alpha_042),
                ('alpha_043', self.alpha_043),
                ('alpha_044', self.alpha_044),
                ('alpha_045', self.alpha_045),
                ('alpha_046', self.alpha_046),
                ('alpha_047', self.alpha_047),
                ('alpha_049', self.alpha_049),
                ('alpha_050', self.alpha_050),
                ('alpha_051', self.alpha_051),
                ('alpha_052', self.alpha_052),
                ('alpha_053', self.alpha_053),
                ('alpha_054', self.alpha_054),
                ('alpha_055', self.alpha_055),
                ('alpha_056', self.alpha_056),
                ('alpha_057', self.alpha_057),
                ('alpha_060', self.alpha_060),
                ('alpha_061', self.alpha_061),
                ('alpha_062', self.alpha_062),
                ('alpha_064', self.alpha_064),
                ('alpha_065', self.alpha_065),
                ('alpha_066', self.alpha_066),
                ('alpha_068', self.alpha_068),
                ('alpha_071', self.alpha_071),
                ('alpha_072', self.alpha_072),
                ('alpha_073', self.alpha_073),
                ('alpha_074', self.alpha_074),
                ('alpha_075', self.alpha_075),
                ('alpha_077', self.alpha_077),
                ('alpha_078', self.alpha_078),
                ('alpha_083', self.alpha_083),
                ('alpha_084', self.alpha_084),
                ('alpha_085', self.alpha_085),
                ('alpha_086', self.alpha_086),
                ('alpha_088', self.alpha_088),
                ('alpha_092', self.alpha_092),
                ('alpha_094', self.alpha_094),
                ('alpha_096', self.alpha_096),
                ('alpha_098', self.alpha_098),
                ('alpha_099', self.alpha_099),
                ('alpha_101', self.alpha_101),
            ]

            for factor_name, factor_func in factor_methods:
                try:
                    result[factor_name] = factor_func(df)
                except Exception as e:
                    print(f"  ⚠️  {ts_code} {factor_name} 计算失败: {e}")
                    result[factor_name] = np.nan

            all_results.append(result)

            if len(all_results) % 10 == 0:
                print(f"  已处理 {len(all_results)} 只股票...")

        if all_results:
            final_result = pd.concat(all_results, ignore_index=True)
            print(f"\n✓ 计算完成，共 {len(final_result)} 条记录")
            return final_result
        else:
            print("\n❌ 无有效结果")
            return pd.DataFrame()


def calculate_alpha101_factors(ts_codes: List[str], start_date: str, end_date: str,
                               output_path: Optional[str] = None) -> pd.DataFrame:
    """
    计算Alpha101因子主函数

    参数:
        ts_codes: 股票代码列表
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        output_path: 输出路径，None则使用默认路径

    返回:
        包含Alpha101因子的DataFrame
    """
    print("=" * 80)
    print("Alpha101因子计算")
    print("=" * 80)
    print(f"股票数量: {len(ts_codes)}")
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"已实现因子: 77个")
    print(f"未实现因子: 24个 (需要行业中性化)")
    print("=" * 80)

    # 创建计算器
    calculator = Alpha101Calculator(ts_codes, start_date, end_date)

    # 计算因子
    result = calculator.calculate_all()

    # 保存结果
    if len(result) > 0 and output_path:
        result.to_csv(output_path, index=False)
        print(f"\n✓ 结果已保存: {output_path}")
        print(f"  记录数: {len(result):,}")
        print(f"  股票数: {result['ts_code'].nunique()}")
        print(f"  日期范围: {result['trade_date'].min()} ~ {result['trade_date'].max()}")

    return result


if __name__ == "__main__":
    # 示例使用
    # ts_codes = ['000001.SZ', '000002.SZ', '600519.SH']
    # result = calculate_alpha101_factors(ts_codes, '20240101', '20241231',
    #                                     output_path='/home/zcy/alpha006_20251223/results/factor/alpha101_factors.csv')
    pass
