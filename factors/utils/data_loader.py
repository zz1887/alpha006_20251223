"""
文件input(依赖外部什么): pandas, numpy, datetime, typing
文件output(提供什么): DataLoader类，提供统一的数据加载和缓存管理接口
文件pos(系统局部地位): 工具层，为因子计算和回测提供标准化数据加载服务
文件功能:
    1. 支持多数据源加载（数据库/文件/内存）
    2. 提供因子数据、价格数据、财务数据、行业数据加载
    3. 数据缓存管理，提升重复访问性能
    4. 数据格式标准化和验证

使用示例:
    from factors.utils.data_loader import DataLoader

    # 创建数据加载器
    loader = DataLoader(data_source='file')

    # 加载因子数据
    factor_df = loader.load_factor_data('alpha_peg', '20240101', '20241231')

    # 加载价格数据
    price_df = loader.load_price_data(['000001.SZ', '000002.SZ'], '20240101', '20241231')

    # 加载财务数据
    finance_df = loader.load_finance_data(['000001.SZ'], '20240101', '20241231', ['pe_ttm', 'dt_netprofit_yoy'])

    # 加载行业数据
    industry_df = loader.load_industry_data()

参数说明:
    data_source: 数据源类型 ('database', 'file', 'memory')
    factor_name: 因子名称
    ts_codes: 股票代码列表
    start_date: 开始日期 (格式: YYYYMMDD)
    end_date: 结束日期 (格式: YYYYMMDD)
    price_type: 价格类型 ('open', 'high', 'low', 'close')
    fields: 财务字段列表
    cache: 是否启用缓存

返回值:
    pd.DataFrame: 标准化数据 [ts_code, trade_date, ...]
    Dict[str, int]: 缓存信息
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime, timedelta


class DataLoader:
    """
    数据加载器

    功能：
    1. 从数据库/文件加载数据
    2. 数据格式标准化
    3. 数据缓存管理
    """

    def __init__(self, data_source: str = 'database'):
        """
        初始化

        Args:
            data_source: 数据源类型 ('database', 'file', 'memory')
        """
        self.data_source = data_source
        self.cache = {}

    def load_factor_data(self,
                        factor_name: str,
                        start_date: str,
                        end_date: str,
                        cache: bool = True) -> pd.DataFrame:
        """
        加载因子数据

        Args:
            factor_name: 因子名称
            start_date: 开始日期
            end_date: 结束日期
            cache: 是否使用缓存

        Returns:
            pd.DataFrame: 因子数据 [ts_code, trade_date, factor]
        """
        cache_key = f"{factor_name}_{start_date}_{end_date}"

        if cache and cache_key in self.cache:
            return self.cache[cache_key]

        if self.data_source == 'memory':
            # 从内存加载（测试用）
            raise NotImplementedError("内存数据源需要预先设置")

        elif self.data_source == 'file':
            # 从文件加载
            file_path = f"data/factors/{factor_name}_{start_date}_{end_date}.csv"
            df = pd.read_csv(file_path)
            df['trade_date'] = pd.to_datetime(df['trade_date'])

        else:
            # 从数据库加载（示例）
            # 实际实现需要连接数据库
            df = self._load_from_database(factor_name, start_date, end_date)

        if cache:
            self.cache[cache_key] = df

        return df

    def load_price_data(self,
                       ts_codes: List[str],
                       start_date: str,
                       end_date: str,
                       price_type: str = 'close') -> pd.DataFrame:
        """
        加载价格数据

        Args:
            ts_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            price_type: 价格类型 ('open', 'high', 'low', 'close')

        Returns:
            pd.DataFrame: 价格数据 [ts_code, trade_date, close]
        """
        cache_key = f"price_{price_type}_{start_date}_{end_date}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        if self.data_source == 'file':
            # 从文件加载
            file_path = f"data/price/price_{start_date}_{end_date}.csv"
            df = pd.read_csv(file_path)
            df['trade_date'] = pd.to_datetime(df['trade_date'])

            # 筛选股票
            if ts_codes:
                df = df[df['ts_code'].isin(ts_codes)]

            # 选择价格列
            df = df[['ts_code', 'trade_date', price_type]]
            df.columns = ['ts_code', 'trade_date', 'close']

        else:
            # 从数据库加载
            df = self._load_price_from_database(ts_codes, start_date, end_date, price_type)

        self.cache[cache_key] = df
        return df

    def load_finance_data(self,
                         ts_codes: List[str],
                         start_date: str,
                         end_date: str,
                         fields: List[str]) -> pd.DataFrame:
        """
        加载财务数据

        Args:
            ts_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            fields: 字段列表

        Returns:
            pd.DataFrame: 财务数据
        """
        if self.data_source == 'file':
            file_path = f"data/fina/fina_{start_date}_{end_date}.csv"
            df = pd.read_csv(file_path)
            df['trade_date'] = pd.to_datetime(df['trade_date'])

            if ts_codes:
                df = df[df['ts_code'].isin(ts_codes)]

            # 选择需要的字段
            required_cols = ['ts_code', 'trade_date'] + fields
            df = df[required_cols]

            return df

        else:
            return self._load_finance_from_database(ts_codes, start_date, end_date, fields)

    def load_industry_data(self, ts_codes: List[str] = None) -> pd.DataFrame:
        """
        加载行业分类数据

        Args:
            ts_codes: 股票代码列表，None表示全部

        Returns:
            pd.DataFrame: 行业数据 [ts_code, trade_date, industry]
        """
        cache_key = "industry_data"

        if cache_key in self.cache:
            df = self.cache[cache_key]
            if ts_codes:
                df = df[df['ts_code'].isin(ts_codes)]
            return df

        if self.data_source == 'file':
            df = pd.read_csv('data/industry/sw_industry.csv')
            df['trade_date'] = pd.to_datetime(df['trade_date'])

            if ts_codes:
                df = df[df['ts_code'].isin(ts_codes)]

            self.cache[cache_key] = df
            return df

        else:
            return self._load_industry_from_database(ts_codes)

    def _load_from_database(self, factor_name: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从数据库加载因子数据（需要实际实现）"""
        # 示例：返回空DataFrame
        return pd.DataFrame(columns=['ts_code', 'trade_date', 'factor'])

    def _load_price_from_database(self, ts_codes: List[str], start_date: str, end_date: str, price_type: str) -> pd.DataFrame:
        """从数据库加载价格数据（需要实际实现）"""
        return pd.DataFrame(columns=['ts_code', 'trade_date', 'close'])

    def _load_finance_from_database(self, ts_codes: List[str], start_date: str, end_date: str, fields: List[str]) -> pd.DataFrame:
        """从数据库加载财务数据（需要实际实现）"""
        return pd.DataFrame()

    def _load_industry_from_database(self, ts_codes: List[str]) -> pd.DataFrame:
        """从数据库加载行业数据（需要实际实现）"""
        return pd.DataFrame(columns=['ts_code', 'trade_date', 'industry'])

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()

    def get_cache_info(self) -> Dict[str, int]:
        """获取缓存信息"""
        return {k: len(v) for k, v in self.cache.items()}
