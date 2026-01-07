"""
动量因子 - alpha_pluse - factors/momentum/factor_alpha_pluse.py

功能:
- 计算alpha_pluse因子 (成交量异常放量信号)
- 基于20日内成交量突破统计

因子定义:
    1. 构造规则: 每个交易日T往前20个交易日内，统计满足「t日交易量=其往前14日均值的1.4-3.5倍」的交易日数量
    2. 赋值规则: 数量在2-4个（含）则T日alpha_pluse=1，否则=0

计算逻辑:
    - 对每个交易日T，回溯20个交易日窗口
    - 在窗口内，对每个交易日t，计算其前14日成交量均值
    - 判断t日成交量是否在1.4-3.5倍范围内
    - 统计满足条件的交易日数量
    - 如果数量∈[2,4]，则alpha_pluse=1，否则=0

数据来源:
    - daily_kline表: ts_code, trade_date, vol

输出字段:
    - ts_code: 股票代码
    - trade_date: 交易日期
    - alpha_pluse: 因子值 (0或1)
    - count_20d: 20日内满足条件的数量
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from core.utils.data_loader import load_industry_data
from core.utils.db_connection import db
from core.constants.config import TABLE_DAILY_KLINE


class VolExp20Dv2Factor:
    """alpha_pluse因子计算类"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化因子计算参数

        Args:
            params: 因子参数字典
                {
                    'window_20d': 20,           # 回溯窗口
                    'lookback_14d': 14,         # 成交量均值计算周期
                    'lower_mult': 1.4,          # 下限倍数
                    'upper_mult': 3.5,          # 上限倍数
                    'min_count': 2,             # 最小满足数量
                    'max_count': 4              # 最大满足数量
                }
        """
        self.params = params or {
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.4,
            'upper_mult': 3.5,
            'min_count': 2,
            'max_count': 4,
        }

    def calculate(self, df_price: pd.DataFrame) -> pd.DataFrame:
        """
        计算alpha_pluse因子

        Args:
            df_price: 价格数据 (ts_code, trade_date, vol)

        Returns:
            DataFrame包含:
                ts_code, trade_date, alpha_pluse, count_20d
        """
        print(f"\\n{'='*80}")
        print("alpha_pluse因子计算流程")
        print(f"{'='*80}")

        # 参数
        window_20d = self.params['window_20d']
        lookback_14d = self.params['lookback_14d']
        lower_mult = self.params['lower_mult']
        upper_mult = self.params['upper_mult']
        min_count = self.params['min_count']
        max_count = self.params['max_count']

        print(f"\\n参数配置:")
        print(f"  回溯窗口: {window_20d} 日")
        print(f"  成交量均值周期: {lookback_14d} 日")
        print(f"  倍数范围: [{lower_mult}, {upper_mult}]")
        print(f"  满足数量范围: [{min_count}, {max_count}]")

        results = []
        stock_count = 0

        # 按股票分组计算
        for ts_code, group in df_price.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            if len(group) < window_20d + lookback_14d:
                continue

            # 计算14日成交量均值
            group['vol_14_mean'] = group['vol'].rolling(
                window=lookback_14d, min_periods=lookback_14d
            ).mean()

            # 标记每个交易日是否满足条件
            # 条件: vol ∈ [vol_14_mean * lower_mult, vol_14_mean * upper_mult]
            group['condition'] = (
                (group['vol'] >= group['vol_14_mean'] * lower_mult) &
                (group['vol'] <= group['vol_14_mean'] * upper_mult) &
                group['vol_14_mean'].notna()
            )

            # 计算20日滚动满足数量
            # 注意: 需要回溯20日，包括当前日
            def count_conditions(idx):
                """统计当前日往前20日内满足条件的数量"""
                if idx < window_20d - 1:
                    return np.nan

                # 获取窗口数据
                window_data = group.iloc[idx - window_20d + 1:idx + 1]
                count = window_data['condition'].sum()
                return count

            # 应用滚动计算
            group['count_20d'] = [count_conditions(i) for i in range(len(group))]

            # 计算alpha_pluse
            group['alpha_pluse'] = (
                (group['count_20d'] >= min_count) &
                (group['count_20d'] <= max_count)
            ).astype(int)

            # 保留结果
            result_group = group[[
                'ts_code', 'trade_date', 'alpha_pluse', 'count_20d'
            ]].copy()

            # 过滤掉计算窗口不足的数据
            result_group = result_group.dropna()

            if len(result_group) > 0:
                results.append(result_group)

            stock_count += 1
            if stock_count % 100 == 0:
                print(f"  已处理 {stock_count} 只股票...")

        if not results:
            print("❌ 未计算出任何结果")
            return pd.DataFrame()

        # 合并结果
        final_result = pd.concat(results, ignore_index=True)

        # 统计
        total_signals = final_result['alpha_pluse'].sum()
        total_data = len(final_result)

        print(f"\\n{'='*80}")
        print("计算完成")
        print(f"{'='*80}")
        print(f"处理股票数: {stock_count}")
        print(f"总数据条数: {total_data:,}")
        print(f"有效信号数: {total_signals:,}")
        print(f"信号比例: {total_signals/total_data:.4f}")

        # 统计分布
        if total_data > 0:
            count_dist = final_result['count_20d'].value_counts().sort_index()
            print(f"\\n20日内满足条件数量分布:")
            for count, freq in count_dist.items():
                print(f"  {count}: {freq} 条 ({freq/total_data:.4f})")

        return final_result

    def calculate_by_period(self,
                           start_date: str,
                           end_date: str,
                           industry_path: Optional[str] = None) -> pd.DataFrame:
        """
        按时间段计算alpha_pluse因子

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            industry_path: 行业数据路径（可选，用于输出行业信息）

        Returns:
            因子DataFrame
        """
        print(f"\\n{'='*80}")
        print(f"计算alpha_pluse因子: {start_date} ~ {end_date}")
        print(f"{'='*80}")

        # 1. 获取价格数据
        sql = f"""
        SELECT ts_code, trade_date, vol
        FROM {TABLE_DAILY_KLINE}
        WHERE trade_date >= %s AND trade_date <= %s
          AND vol IS NOT NULL AND vol > 0
        ORDER BY ts_code, trade_date
        """
        data = db.execute_query(sql, (start_date, end_date))
        df_price = pd.DataFrame(data)

        if len(df_price) == 0:
            print("❌ 未获取到价格数据")
            return pd.DataFrame()

        print(f"✓ 价格数据: {len(df_price):,} 条")

        # 转换数据类型
        df_price['trade_date'] = pd.to_datetime(df_price['trade_date'], format='%Y%m%d')
        df_price['vol'] = df_price['vol'].astype(float)

        # 2. 计算因子
        result = self.calculate(df_price)

        # 3. 如果提供了行业数据，添加行业信息
        if len(result) > 0 and industry_path:
            try:
                df_industry = load_industry_data(industry_path)
                result = result.merge(df_industry, on='ts_code', how='left')
                result['l1_name'] = result['l1_name'].fillna('其他')
            except Exception as e:
                print(f"⚠️  加载行业数据失败: {e}")

        return result

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
            'date_count': factor_df['trade_date'].nunique(),
            'signal_count': factor_df['alpha_pluse'].sum(),
            'signal_ratio': factor_df['alpha_pluse'].mean(),
            'count_mean': factor_df['count_20d'].mean(),
            'count_std': factor_df['count_20d'].std(),
            'count_min': factor_df['count_20d'].min(),
            'count_max': factor_df['count_20d'].max(),
        }

        if 'l1_name' in factor_df.columns:
            stats['industry_count'] = factor_df['l1_name'].nunique()

        return stats

    def get_daily_stats(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """
        获取每日统计

        Args:
            factor_df: 因子DataFrame

        Returns:
            每日统计DataFrame
        """
        if len(factor_df) == 0:
            return pd.DataFrame()

        daily_stats = factor_df.groupby('trade_date').agg({
            'alpha_pluse': ['sum', 'mean', 'count'],
            'count_20d': ['mean', 'std']
        }).round(4)

        daily_stats.columns = [
            'signal_count', 'signal_ratio', 'total_stocks',
            'avg_count', 'std_count'
        ]

        return daily_stats

    def get_detail_by_stock(self, factor_df: pd.DataFrame, ts_code: str,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取指定股票的详细计算过程

        Args:
            factor_df: 因子DataFrame
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            详细计算过程DataFrame
        """
        mask = factor_df['ts_code'] == ts_code

        if start_date:
            mask &= (factor_df['trade_date'] >= pd.to_datetime(start_date))
        if end_date:
            mask &= (factor_df['trade_date'] <= pd.to_datetime(end_date))

        detail = factor_df[mask].copy()
        detail = detail.sort_values('trade_date')

        return detail


# ==================== 因子版本配置 ====================
FACTOR_VERSIONS = {
    'standard': {
        'name': '标准版',
        'params': {
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.4,
            'upper_mult': 3.5,
            'min_count': 2,
            'max_count': 4,
        }
    },
    'conservative': {
        'name': '保守版',
        'params': {
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.5,
            'upper_mult': 3.0,
            'min_count': 3,
            'max_count': 4,
        }
    },
    'aggressive': {
        'name': '激进版',
        'params': {
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.3,
            'upper_mult': 4.0,
            'min_count': 2,
            'max_count': 5,
        }
    },
}


def create_factor(version: str = 'standard') -> VolExp20Dv2Factor:
    """
    创建指定版本的alpha_pluse因子计算器

    Args:
        version: 因子版本 ('standard', 'conservative', 'aggressive')

    Returns:
        VolExp20Dv2Factor实例
    """
    if version not in FACTOR_VERSIONS:
        raise ValueError(f"未知版本: {version}, 可用版本: {list(FACTOR_VERSIONS.keys())}")

    config = FACTOR_VERSIONS[version]
    print(f"\\n创建因子: {config['name']} (版本: {version})")
    print(f"参数: {config['params']}")

    return VolExp20Dv2Factor(config['params'])
