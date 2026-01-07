"""
估值因子 - alpha_peg - factors/valuation/factor_alpha_peg.py

功能:
- 计算alpha_peg因子 (PE_TTM / DT_NetProfit_YoY)
- 分行业优化处理
- 异常值处理和标准化

因子公式:
    alpha_peg = pe_ttm / dt_netprofit_yoy

数据来源:
    - pe_ttm: daily_basic表，日频PE_TTM
    - dt_netprofit_yoy: fina_indicator表，单季净利润同比增长率

优化策略:
    1. 分行业计算，避免跨行业比较偏差
    2. 行业特定异常值阈值 (3σ原则)
    3. 前向填充财报数据
    4. 可选标准化 (zscore/rank)
"""

import pandas as pd
from typing import Optional, Dict, Any
from core.utils.data_loader import load_industry_data, get_price_data, get_index_data
from core.utils.data_processor import calculate_alpha_peg_factor
from core.constants.config import FACTOR_ALPHA_PEG_PARAMS


class ValGrowQFactor:
    """alpha_peg因子计算类"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化因子计算参数

        Args:
            params: 因子参数字典
                {
                    'outlier_sigma': 3.0,      # 异常值阈值
                    'normalization': None,     # 标准化方法
                    'industry_specific': True  # 行业特定阈值
                }
        """
        self.params = params or FACTOR_ALPHA_PEG_PARAMS

    def calculate(self,
                  df_pe: pd.DataFrame,
                  df_fina: pd.DataFrame,
                  df_industry: pd.DataFrame) -> pd.DataFrame:
        """
        计算alpha_peg因子

        Args:
            df_pe: PE数据 (ts_code, trade_date, pe_ttm)
            df_fina: 财务数据 (ts_code, ann_date, dt_netprofit_yoy)
            df_industry: 行业数据 (ts_code, l1_name)

        Returns:
            DataFrame包含:
                ts_code, trade_date, l1_name, pe_ttm, dt_netprofit_yoy,
                alpha_peg, industry_rank
        """
        return calculate_alpha_peg_factor(
            df_pe=df_pe,
            df_fina=df_fina,
            df_industry=df_industry,
            outlier_sigma=self.params.get('outlier_sigma', 3.0),
            normalization=self.params.get('normalization', None),
            industry_specific=self.params.get('industry_specific', True)
        )

    def calculate_by_period(self,
                            start_date: str,
                            end_date: str,
                            industry_path: Optional[str] = None) -> pd.DataFrame:
        """
        按时间段计算alpha_peg因子

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            industry_path: 行业数据路径

        Returns:
            因子DataFrame
        """
        from core.utils.db_connection import db
        from core.constants.config import TABLE_DAILY_BASIC, TABLE_FINA_INDICATOR

        print(f"\n{'='*80}")
        print(f"计算alpha_peg因子: {start_date} ~ {end_date}")
        print(f"{'='*80}")

        # 1. 获取PE数据
        sql_pe = f"""
        SELECT ts_code, trade_date, pe_ttm
        FROM {TABLE_DAILY_BASIC}
        WHERE trade_date >= %s AND trade_date <= %s
          AND pe_ttm IS NOT NULL AND pe_ttm > 0
        ORDER BY ts_code, trade_date
        """
        data_pe = db.execute_query(sql_pe, (start_date, end_date))
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
        data_fina = db.execute_query(sql_fina, (start_date, end_date))
        df_fina = pd.DataFrame(data_fina)
        print(f"✓ 财务数据: {len(df_fina):,} 条")

        # 3. 加载行业数据
        df_industry = load_industry_data(industry_path)

        # 4. 计算因子
        return self.calculate(df_pe, df_fina, df_industry)

    def get_factor_stats(self, factor_df: pd.DataFrame) -> Dict[str, Any]:
        """
        获取因子统计信息

        Args:
            factor_df: 因子DataFrame

        Returns:
            统计信息字典
        """
        if len(factor_df) == 0:
            return {}

        stats = {
            'total_records': len(factor_df),
            'stock_count': factor_df['ts_code'].nunique(),
            'industry_count': factor_df['l1_name'].nunique(),
            'date_count': factor_df['trade_date'].nunique(),
            'alpha_peg_mean': factor_df['alpha_peg'].mean(),
            'alpha_peg_std': factor_df['alpha_peg'].std(),
            'alpha_peg_min': factor_df['alpha_peg'].min(),
            'alpha_peg_max': factor_df['alpha_peg'].max(),
            'rank_mean': factor_df['industry_rank'].mean(),
            'rank_std': factor_df['industry_rank'].std(),
        }

        return stats

    def select_top_n_by_industry(self,
                                 factor_df: pd.DataFrame,
                                 top_n: int = 3) -> pd.DataFrame:
        """
        每行业选择alpha_peg排名前N的个股

        Args:
            factor_df: 因子DataFrame
            top_n: 每行业选股数量

        Returns:
            选股DataFrame
        """
        print(f"\n{'='*80}")
        print(f"每行业选择前{top_n}名个股")
        print(f"{'='*80}")

        selected = []

        for (trade_date, industry), group in factor_df.groupby(['trade_date', 'l1_name']):
            # 排序并取前N
            top_n_stocks = group.nsmallest(top_n, 'alpha_peg')[
                ['ts_code', 'trade_date', 'l1_name', 'alpha_peg', 'industry_rank']
            ]
            selected.append(top_n_stocks)

        df_selected = pd.concat(selected, ignore_index=True)

        print(f"  选中记录数: {len(df_selected):,}")
        print(f"  平均每日选股: {len(df_selected) / factor_df['trade_date'].nunique():.1f} 只")

        return df_selected


# ==================== 因子版本配置 ====================
FACTOR_VERSIONS = {
    'basic': {
        'name': '基础版',
        'params': {
            'outlier_sigma': 3.0,
            'normalization': None,
            'industry_specific': False
        }
    },
    'industry_optimized': {
        'name': '行业优化版',
        'params': {
            'outlier_sigma': 3.0,
            'normalization': None,
            'industry_specific': True
        }
    },
    'zscore_normalized': {
        'name': 'Z-score标准化',
        'params': {
            'outlier_sigma': 3.0,
            'normalization': 'zscore',
            'industry_specific': True
        }
    },
    'rank_normalized': {
        'name': '排名标准化',
        'params': {
            'outlier_sigma': 3.0,
            'normalization': 'rank',
            'industry_specific': True
        }
    },
    'conservative': {
        'name': '保守版',
        'params': {
            'outlier_sigma': 2.5,
            'normalization': None,
            'industry_specific': True
        }
    },
    'aggressive': {
        'name': '激进版',
        'params': {
            'outlier_sigma': 3.5,
            'normalization': None,
            'industry_specific': True
        }
    },
}


def create_factor(version: str = 'industry_optimized') -> ValGrowQFactor:
    """
    创建指定版本的alpha_peg因子计算器

    Args:
        version: 因子版本 ('basic', 'industry_optimized', 'zscore_normalized',
                         'rank_normalized', 'conservative', 'aggressive')

    Returns:
        ValGrowQFactor实例
    """
    if version not in FACTOR_VERSIONS:
        raise ValueError(f"未知版本: {version}, 可用版本: {list(FACTOR_VERSIONS.keys())}")

    config = FACTOR_VERSIONS[version]
    print(f"\n创建因子: {config['name']} (版本: {version})")
    print(f"参数: {config['params']}")

    return ValGrowQFactor(config['params'])
