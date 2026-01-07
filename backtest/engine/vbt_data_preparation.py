"""
vectorbt数据准备模块 - backtest/engine/vbt_data_preparation.py

功能:
- 从数据库获取alpha_peg因子数据
- 获取价格数据和基准数据
- 按行业分组并选择前3名
- 生成vectorbt所需的信号矩阵
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from datetime import datetime

from core.utils.db_connection import db
from core.utils.data_loader import load_industry_data, get_price_data, get_index_data
from core.utils.data_processor import calculate_alpha_peg_factor
from core.constants.config import TABLE_DAILY_BASIC, TABLE_FINA_INDICATOR


class VBTDataPreparation:
    """vectorbt数据准备类"""

    def __init__(self, start_date: str, end_date: str):
        """
        初始化数据准备器

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        """
        self.start_date = start_date
        self.end_date = end_date
        self.factor_df = None
        self.selected_df = None
        self.price_df = None
        self.index_df = None

    def load_factor_data(self, outlier_sigma: float = 3.0,
                        normalization: Optional[str] = None) -> pd.DataFrame:
        """
        加载并计算alpha_peg因子数据

        Args:
            outlier_sigma: 异常值阈值
            normalization: 标准化方法

        Returns:
            因子DataFrame
        """
        print(f"\n{'='*80}")
        print("步骤1: 加载alpha_peg因子数据")
        print(f"时间区间: {self.start_date} ~ {self.end_date}")
        print(f"{'='*80}")

        # 1. 获取PE数据
        sql_pe = f"""
        SELECT ts_code, trade_date, pe_ttm
        FROM {TABLE_DAILY_BASIC}
        WHERE trade_date >= %s AND trade_date <= %s
          AND pe_ttm IS NOT NULL AND pe_ttm > 0
        ORDER BY ts_code, trade_date
        """
        data_pe = db.execute_query(sql_pe, (self.start_date, self.end_date))
        df_pe = pd.DataFrame(data_pe)
        print(f"✓ PE数据: {len(df_pe):,} 条")

        # 2. 获取财务数据
        sql_fina = f"""
        SELECT ts_code, ann_date, dt_netprofit_yoy
        FROM {TABLE_FINA_INDICATOR}
        WHERE ann_date >= %s AND ann_date <= %s
          AND update_flag = '1'
          AND dt_netprofit_yoy IS NOT NULL
          AND dt_netprofit_yoy != 0
        ORDER BY ts_code, ann_date
        """
        data_fina = db.execute_query(sql_fina, (self.start_date, self.end_date))
        df_fina = pd.DataFrame(data_fina)
        print(f"✓ 财务数据: {len(df_fina):,} 条")

        # 3. 加载行业数据
        df_industry = load_industry_data()

        # 4. 计算因子
        self.factor_df = calculate_alpha_peg_factor(
            df_pe=df_pe,
            df_fina=df_fina,
            df_industry=df_industry,
            outlier_sigma=outlier_sigma,
            normalization=normalization,
            industry_specific=True
        )

        print(f"✓ 因子数据: {len(self.factor_df):,} 条")
        return self.factor_df

    def select_top_n_by_industry(self, top_n: int = 3) -> pd.DataFrame:
        """
        每行业选择前N名个股

        Args:
            top_n: 每行业选股数量

        Returns:
            选股DataFrame
        """
        print(f"\n{'='*80}")
        print(f"步骤2: 每行业选择前{top_n}名个股")
        print(f"{'='*80}")

        if self.factor_df is None:
            raise ValueError("请先调用load_factor_data()加载因子数据")

        selected = []

        for (trade_date, industry), group in self.factor_df.groupby(['trade_date', 'l1_name']):
            # 按alpha_peg排序（越小越好），取前N名
            top_n_stocks = group.nsmallest(top_n, 'alpha_peg')[
                ['ts_code', 'trade_date', 'l1_name', 'alpha_peg', 'industry_rank']
            ]
            selected.append(top_n_stocks)

        self.selected_df = pd.concat(selected, ignore_index=True)

        print(f"✓ 选中记录数: {len(self.selected_df):,}")
        print(f"✓ 平均每日选股: {len(self.selected_df) / self.selected_df['trade_date'].nunique():.1f} 只")
        print(f"✓ 涉及股票数: {self.selected_df['ts_code'].nunique()}")
        print(f"✓ 涉及行业数: {self.selected_df['l1_name'].nunique()}")

        return self.selected_df

    def load_price_data(self) -> pd.DataFrame:
        """
        加载价格数据

        Returns:
            价格DataFrame
        """
        print(f"\n{'='*80}")
        print("步骤3: 加载价格数据")
        print(f"{'='*80}")

        self.price_df = get_price_data(self.start_date, self.end_date)
        print(f"✓ 价格数据: {len(self.price_df):,} 条")

        return self.price_df

    def load_index_data(self) -> pd.DataFrame:
        """
        加载基准指数数据

        Returns:
            指数DataFrame
        """
        print(f"\n{'='*80}")
        print("步骤4: 加载基准指数数据")
        print(f"{'='*80}")

        self.index_df = get_index_data(self.start_date, self.end_date)
        print(f"✓ 基准指数: {len(self.index_df):,} 条")

        return self.index_df

    def generate_signal_matrix(self) -> pd.DataFrame:
        """
        生成vectorbt所需的信号矩阵

        Returns:
            信号矩阵 (trade_date x ts_code), 1表示持有，0表示不持有
        """
        print(f"\n{'='*80}")
        print("步骤5: 生成信号矩阵")
        print(f"{'='*80}")

        if self.selected_df is None:
            raise ValueError("请先调用select_top_n_by_industry()进行选股")

        # 创建日期-股票的透视表
        signal_matrix = self.selected_df.pivot_table(
            index='trade_date',
            columns='ts_code',
            values='alpha_peg',
            aggfunc='count',
            fill_value=0
        )

        # 转换为1/0信号
        signal_matrix = (signal_matrix > 0).astype(int)

        print(f"✓ 信号矩阵形状: {signal_matrix.shape}")
        print(f"✓ 交易日数: {len(signal_matrix)}")
        print(f"✓ 股票数: {len(signal_matrix.columns)}")
        print(f"✓ 日均持有股票数: {signal_matrix.sum(axis=1).mean():.1f}")

        return signal_matrix

    def prepare_all(self, outlier_sigma: float = 3.0,
                   normalization: Optional[str] = None,
                   top_n: int = 3) -> Dict[str, Any]:
        """
        一次性准备所有数据

        Args:
            outlier_sigma: 异常值阈值
            normalization: 标准化方法
            top_n: 每行业选股数量

        Returns:
            包含所有数据的字典
        """
        self.load_factor_data(outlier_sigma, normalization)
        self.select_top_n_by_industry(top_n)
        self.load_price_data()
        self.load_index_data()
        signal_matrix = self.generate_signal_matrix()

        return {
            'factor_df': self.factor_df,
            'selected_df': self.selected_df,
            'price_df': self.price_df,
            'index_df': self.index_df,
            'signal_matrix': signal_matrix,
            'start_date': self.start_date,
            'end_date': self.end_date
        }
