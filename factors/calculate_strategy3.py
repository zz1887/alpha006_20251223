"""
策略3综合得分计算 - 20251229
根据策略3公式计算当天所有个股的综合得分

策略3公式:
综合得分 = 0.20 * (1 - alpha_pluse) +              # 量能（反向，因为alpha_pluse是0/1）
           0.25 * (-行业标准化alpha_peg) +           # 估值（负向因子）
           0.15 * alpha_120cq +                     # 位置（正向）
           0.20 * (cr_qfq / cr_qfq.max()) +         # 动量（标准化）
           0.20 * (-alpha_038 / alpha_038.min())    # 强度（负向因子）

数据日期: 20251229
输出: 包含综合得分的Excel文件
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, '/home/zcy/alpha006_20251223')

from core.utils.db_connection import db
from core.constants.config import TABLE_DAILY_KLINE, TABLE_DAILY_BASIC, TABLE_FINA_INDICATOR


class Strategy3Calculator20251229:
    """策略3综合得分计算器 - 20251229"""

    def __init__(self):
        self.target_date = '20251229'
        self.target_date_dt = pd.to_datetime('20251229', format='%Y%m%d')
        self.nan_reasons = {}  # 记录缺失原因

        # alpha_pluse参数
        self.pluse_params = {
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.4,
            'upper_mult': 3.5,
            'min_count': 2,
            'max_count': 4,
        }

        # alpha_038参数
        self.alpha_038_window = 10

        # alpha_120cq参数
        self.alpha_120cq_window = 120
        self.alpha_120cq_min_days = 30

    def get_tradable_stocks(self):
        """获取20251229可交易股票"""
        print("=" * 80)
        print("步骤1: 获取20251229可交易股票")
        print("=" * 80)

        # 获取当天有交易的股票
        sql = f"""
        SELECT DISTINCT ts_code
        FROM {TABLE_DAILY_KLINE}
        WHERE trade_date = %s
        """
        data = db.execute_query(sql, (self.target_date,))
        all_stocks = [row['ts_code'] for row in data]

        # 过滤ST股票
        sql_st = "SELECT ts_code FROM stock_st WHERE type = 'ST'"
        st_data = db.execute_query(sql_st, ())
        st_stocks = set([row['ts_code'] for row in st_data])

        valid_stocks = []
        for stock in all_stocks:
            if stock in st_stocks:
                self.nan_reasons[stock] = 'ST股票'
                continue
            valid_stocks.append(stock)

        print(f"当日有交易: {len(all_stocks)} 只")
        print(f"ST过滤: {len(st_stocks)} 只")
        print(f"✅ 有效股票: {len(valid_stocks)} 只")

        return valid_stocks

    def get_trading_days_needed(self):
        """获取需要的交易日范围"""
        # alpha_pluse需要34天（20+14）
        # alpha_038需要10天
        # alpha_120cq需要120天
        # 取最大值：120天 + 20天缓冲 = 140天

        end_date = self.target_date_dt
        start_date = end_date - timedelta(days=160)

        sql = f"""
        SELECT DISTINCT trade_date
        FROM {TABLE_DAILY_KLINE}
        WHERE trade_date >= %s AND trade_date <= %s
        ORDER BY trade_date
        """

        data = db.execute_query(sql, (start_date.strftime('%Y%m%d'), self.target_date))
        trading_days = [row['trade_date'] for row in data]

        print(f"✓ 获取交易日: {len(trading_days)} 天")
        return trading_days

    def get_price_data(self, stocks, trading_days):
        """获取价格和成交量数据"""
        print("\n" + "=" * 80)
        print("步骤2: 获取价格和成交量数据")
        print("=" * 80)

        if not stocks:
            return pd.DataFrame()

        placeholders_days = ','.join(['%s'] * len(trading_days))
        placeholders_stocks = ','.join(['%s'] * len(stocks))

        sql = f"""
        SELECT ts_code, trade_date, open, high, low, close, vol
        FROM {TABLE_DAILY_KLINE}
        WHERE trade_date IN ({placeholders_days})
          AND ts_code IN ({placeholders_stocks})
        ORDER BY ts_code, trade_date
        """

        params = trading_days + stocks
        data = db.execute_query(sql, params)
        df = pd.DataFrame(data)

        if len(df) == 0:
            print("❌ 未获取到价格数据")
            return pd.DataFrame()

        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['vol'] = pd.to_numeric(df['vol'], errors='coerce')

        print(f"✓ 价格数据: {len(df):,} 条")
        print(f"✓ 股票数量: {df['ts_code'].nunique()} 只")

        return df

    def get_fina_data(self, stocks):
        """获取财务数据"""
        print("\n" + "=" * 80)
        print("步骤3: 获取财务数据")
        print("=" * 80)

        if not stocks:
            return pd.DataFrame(), pd.DataFrame()

        placeholders = ','.join(['%s'] * len(stocks))

        # PE数据
        sql_pe = f"""
        SELECT ts_code, trade_date, pe_ttm
        FROM {TABLE_DAILY_BASIC}
        WHERE trade_date = %s
          AND ts_code IN ({placeholders})
          AND pe_ttm IS NOT NULL
          AND pe_ttm > 0
        """
        data_pe = db.execute_query(sql_pe, [self.target_date] + stocks)
        df_pe = pd.DataFrame(data_pe)

        # 财务数据
        sql_fina = f"""
        SELECT ts_code, ann_date, dt_netprofit_yoy
        FROM {TABLE_FINA_INDICATOR}
        WHERE ann_date <= %s
          AND ts_code IN ({placeholders})
          AND update_flag = '1'
          AND dt_netprofit_yoy IS NOT NULL
          AND dt_netprofit_yoy != 0
        ORDER BY ts_code, ann_date
        """
        data_fina = db.execute_query(sql_fina, [self.target_date] + stocks)
        df_fina = pd.DataFrame(data_fina)

        print(f"✓ PE数据: {len(df_pe):,} 条")
        print(f"✓ 财务数据: {len(df_fina):,} 条")

        return df_pe, df_fina

    def get_industry_data(self, stocks):
        """获取申万一级行业"""
        if not stocks:
            return pd.DataFrame()

        try:
            placeholders = ','.join(['%s'] * len(stocks))
            sql = f"""
            SELECT ts_code, l1_name
            FROM sw_industry
            WHERE ts_code IN ({placeholders})
            """
            data = db.execute_query(sql, stocks)
            df = pd.DataFrame(data)
            print(f"✓ 行业数据: {len(df):,} 条")
            return df
        except Exception as e:
            print(f"⚠️  无法获取行业数据: {e}")
            return pd.DataFrame()

    def get_cr_qfq_data(self, stocks):
        """从stk_factor_pro获取cr_qfq数据"""
        print("\n" + "=" * 80)
        print("步骤4: 获取cr_qfq指标")
        print("=" * 80)

        if not stocks:
            return pd.DataFrame()

        placeholders = ','.join(['%s'] * len(stocks))
        sql = f"""
        SELECT ts_code, trade_date, cr_qfq
        FROM stk_factor_pro
        WHERE trade_date = %s
          AND ts_code IN ({placeholders})
        """
        data = db.execute_query(sql, [self.target_date] + stocks)
        df = pd.DataFrame(data)

        print(f"✓ cr_qfq数据: {len(df):,} 条")
        return df

    def calculate_alpha_pluse(self, price_df):
        """计算alpha_pluse因子"""
        print("\n" + "=" * 80)
        print("步骤5: 计算alpha_pluse因子")
        print("=" * 80)

        if len(price_df) == 0:
            return pd.DataFrame()

        params = self.pluse_params
        results = []

        for ts_code, group in price_df.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            if len(group) < params['window_20d'] + params['lookback_14d']:
                self.nan_reasons[ts_code] = f"数据不足({len(group)}天<{params['window_20d'] + params['lookback_14d']}天)"
                continue

            # 计算14日均值
            group['vol_14_mean'] = group['vol'].rolling(
                window=params['lookback_14d'], min_periods=params['lookback_14d']
            ).mean()

            # 标记条件
            group['condition'] = (
                (group['vol'] >= group['vol_14_mean'] * params['lower_mult']) &
                (group['vol'] <= group['vol_14_mean'] * params['upper_mult']) &
                group['vol_14_mean'].notna()
            )

            # 20日滚动计数
            def count_conditions(idx):
                if idx < params['window_20d'] - 1:
                    return np.nan
                window_data = group.iloc[idx - params['window_20d'] + 1:idx + 1]
                return window_data['condition'].sum()

            group['count_20d'] = [count_conditions(i) for i in range(len(group))]

            # 计算alpha_pluse
            group['alpha_pluse'] = (
                (group['count_20d'] >= params['min_count']) &
                (group['count_20d'] <= params['max_count'])
            ).astype(int)

            # 获取目标日期结果
            target_row = group[group['trade_date'] == self.target_date_dt]
            if len(target_row) > 0:
                row = target_row.iloc[0]
                results.append({
                    'ts_code': ts_code,
                    'alpha_pluse': int(row['alpha_pluse']),
                    'count_20d': row['count_20d'],
                })

        df_result = pd.DataFrame(results)

        if len(df_result) > 0:
            print(f"✅ 计算完成: {len(df_result)} 只股票")
            print(f"  信号数: {df_result['alpha_pluse'].sum()}")

        return df_result

    def calculate_alpha_peg(self, df_pe, df_fina):
        """计算原始alpha_peg"""
        print("\n" + "=" * 80)
        print("步骤6: 计算原始alpha_peg")
        print("=" * 80)

        if len(df_pe) == 0 or len(df_fina) == 0:
            return pd.DataFrame()

        # 创建财务数据映射
        fina_map = {}
        for ts_code, group in df_fina.groupby('ts_code'):
            group = group.sort_values('ann_date')
            fina_map[ts_code] = dict(zip(group['ann_date'], group['dt_netprofit_yoy']))

        results = []
        for _, row in df_pe.iterrows():
            ts_code = row['ts_code']
            pe_ttm = row['pe_ttm']

            if ts_code not in fina_map:
                self.nan_reasons[ts_code] = '无财务数据'
                continue

            # 查找最近一期财报
            fina_dates = sorted(fina_map[ts_code].keys())
            valid_dates = [d for d in fina_dates if d <= self.target_date]

            if not valid_dates:
                self.nan_reasons[ts_code] = '无有效财报'
                continue

            latest_ann_date = valid_dates[-1]
            dt_netprofit_yoy = fina_map[ts_code][latest_ann_date]

            if dt_netprofit_yoy != 0:
                alpha_peg_raw = pe_ttm / dt_netprofit_yoy
                results.append({
                    'ts_code': ts_code,
                    'alpha_peg_raw': alpha_peg_raw,
                })
            else:
                self.nan_reasons[ts_code] = 'dt_netprofit_yoy为零'

        df_result = pd.DataFrame(results)

        if len(df_result) > 0:
            print(f"✅ 计算完成: {len(df_result)} 只股票")

        return df_result

    def calculate_industry_zscore(self, df_peg, df_industry):
        """计算行业Z-Score标准化"""
        print("\n" + "=" * 80)
        print("步骤7: 计算行业Z-Score标准化")
        print("=" * 80)

        if len(df_peg) == 0:
            return pd.DataFrame()

        df_peg = df_peg.copy()
        df_peg['alpha_peg_raw'] = pd.to_numeric(df_peg['alpha_peg_raw'], errors='coerce')

        # 合并行业
        if len(df_industry) > 0:
            df_industry_unique = df_industry.drop_duplicates(subset=['ts_code'], keep='first')
            df_merged = df_peg.merge(df_industry_unique, on='ts_code', how='left')
            df_merged['l1_name'] = df_merged['l1_name'].fillna('其他')
        else:
            df_merged = df_peg.copy()
            df_merged['l1_name'] = '其他'

        # 计算Z-Score
        def zscore(group):
            values = group['alpha_peg_raw'].astype(float)
            mean = values.mean()
            std = values.std()
            if std == 0 or pd.isna(std) or len(values) < 2:
                return pd.Series([0.0] * len(group), index=group.index)
            return (values - mean) / std

        df_merged['alpha_peg_zscore'] = df_merged.groupby('l1_name').apply(zscore).reset_index(level=0, drop=True)

        # 统计
        industry_stats = df_merged.groupby('l1_name')['alpha_peg_raw'].agg(['count', 'mean', 'std'])
        print(f"\n  行业统计 (前10):")
        for industry, row in list(industry_stats.iterrows())[:10]:
            print(f"    {industry}: {int(row['count'])}只, 均值={row['mean']:.4f}, 标准差={row['std']:.4f}")

        return df_merged

    def calculate_alpha_038(self, price_df):
        """计算alpha_038因子"""
        print("\n" + "=" * 80)
        print("步骤8: 计算alpha_038因子")
        print("=" * 80)

        if len(price_df) == 0:
            return pd.DataFrame()

        results = []

        for ts_code, group in price_df.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            # 检查是否有足够的数据
            if len(group) < self.alpha_038_window:
                self.nan_reasons[ts_code] = f"数据不足({len(group)}天<{self.alpha_038_window}天)"
                continue

            # 获取目标日期数据
            target_row = group[group['trade_date'] == self.target_date_dt]
            if len(target_row) == 0:
                self.nan_reasons[ts_code] = "目标日期无数据"
                continue

            # 获取10日窗口数据（含目标日）
            window_data = group.tail(self.alpha_038_window).copy()

            # 检查目标日是否在窗口内
            if target_row.iloc[0]['trade_date'] != window_data.iloc[-1]['trade_date']:
                self.nan_reasons[ts_code] = "目标日期不在窗口末尾"
                continue

            try:
                # 1. Ts_Rank(close, 10)
                close_values = window_data['close'].values
                target_close = target_row.iloc[0]['close']
                close_rank = (close_values <= target_close).sum()

                # 2. close/open
                target_open = target_row.iloc[0]['open']
                if pd.isna(target_open) or target_open == 0:
                    self.nan_reasons[ts_code] = "open为NaN或0"
                    continue

                close_over_open = target_close / target_open

                results.append({
                    'ts_code': ts_code,
                    'close_rank': close_rank,
                    'close_over_open': close_over_open,
                })

            except Exception as e:
                self.nan_reasons[ts_code] = f"计算错误: {str(e)}"

        df_result = pd.DataFrame(results)

        if len(df_result) == 0:
            print("❌ 无有效计算结果")
            return pd.DataFrame()

        print(f"✓ 有效计算: {len(df_result)} 只股票")

        # 计算rank(close_over_open)
        df_result['rank_close_over_open'] = df_result['close_over_open'].rank(ascending=False, method='min')

        # 计算最终alpha_038
        df_result['alpha_038'] = (-1 * df_result['close_rank']) * df_result['rank_close_over_open']

        print(f"✓ alpha_038统计:")
        print(f"  均值: {df_result['alpha_038'].mean():.4f}")
        print(f"  最小值: {df_result['alpha_038'].min():.4f}")
        print(f"  最大值: {df_result['alpha_038'].max():.4f}")

        return df_result[['ts_code', 'alpha_038']]

    def calculate_alpha_120cq(self, price_df, excel_df):
        """计算alpha_120cq因子"""
        print("\n" + "=" * 80)
        print("步骤9: 计算alpha_120cq因子")
        print("=" * 80)

        results = []
        excel_stocks = excel_df['ts_code'].tolist()

        for stock in excel_stocks:
            stock_data = price_df[price_df['ts_code'] == stock].sort_values('trade_date')

            if len(stock_data) == 0:
                self.nan_reasons[stock] = "无价格数据"
                results.append({'ts_code': stock, 'alpha_120cq': np.nan})
                continue

            target_row = stock_data[stock_data['trade_date'] == self.target_date_dt]

            if len(target_row) == 0:
                self.nan_reasons[stock] = "目标日期无数据"
                results.append({'ts_code': stock, 'alpha_120cq': np.nan})
                continue

            target_close = target_row.iloc[0]['close']

            if pd.isna(target_close) or target_close <= 0:
                self.nan_reasons[stock] = "当日收盘价异常"
                results.append({'ts_code': stock, 'alpha_120cq': np.nan})
                continue

            window_data = stock_data[stock_data['trade_date'] <= self.target_date_dt]

            if len(window_data) < self.alpha_120cq_min_days:
                self.nan_reasons[stock] = f"有效收盘价不足{self.alpha_120cq_min_days}个"
                results.append({'ts_code': stock, 'alpha_120cq': np.nan})
                continue

            window_120 = window_data.tail(self.alpha_120cq_window)
            N = len(window_120)

            if N < self.alpha_120cq_min_days:
                self.nan_reasons[stock] = f"有效收盘价不足{self.alpha_120cq_min_days}个"
                results.append({'ts_code': stock, 'alpha_120cq': np.nan})
                continue

            close_values = window_120['close'].values
            rank = (close_values <= target_close).sum()

            if N == 1:
                alpha_120cq = 0.5
            else:
                alpha_120cq = (rank - 1) / (N - 1)

            results.append({
                'ts_code': stock,
                'alpha_120cq': alpha_120cq,
            })

        df_result = pd.DataFrame(results)

        valid_count = df_result['alpha_120cq'].notna().sum()
        print(f"✓ 有效计算: {valid_count:,} 只")
        print(f"✓ NaN数量: {df_result['alpha_120cq'].isna().sum():,} 只")

        return df_result

    def merge_all_factors(self, df_pluse, df_peg_zscore, df_cr, df_alpha038, df_alpha120cq):
        """合并所有因子"""
        print("\n" + "=" * 80)
        print("步骤10: 合并所有因子")
        print("=" * 80)

        # 以alpha_peg为基础
        if len(df_peg_zscore) == 0:
            print("❌ 无alpha_peg数据，无法合并")
            return pd.DataFrame()

        df_final = df_peg_zscore[['ts_code', 'l1_name', 'alpha_peg_raw', 'alpha_peg_zscore']].copy()

        # 合并alpha_pluse
        if len(df_pluse) > 0:
            df_final = df_final.merge(
                df_pluse[['ts_code', 'alpha_pluse', 'count_20d']],
                on='ts_code',
                how='left'
            )
        else:
            df_final['alpha_pluse'] = np.nan
            df_final['count_20d'] = np.nan

        # 合并cr_qfq
        if len(df_cr) > 0:
            df_final = df_final.merge(
                df_cr[['ts_code', 'cr_qfq']],
                on='ts_code',
                how='left'
            )
        else:
            df_final['cr_qfq'] = np.nan

        # 合并alpha_038
        if len(df_alpha038) > 0:
            df_final = df_final.merge(
                df_alpha038[['ts_code', 'alpha_038']],
                on='ts_code',
                how='left'
            )
        else:
            df_final['alpha_038'] = np.nan

        # 合并alpha_120cq
        if len(df_alpha120cq) > 0:
            df_final = df_final.merge(
                df_alpha120cq[['ts_code', 'alpha_120cq']],
                on='ts_code',
                how='left'
            )
        else:
            df_final['alpha_120cq'] = np.nan

        # 添加交易日
        df_final['trade_date'] = self.target_date

        # 添加备注
        df_final['备注'] = df_final['ts_code'].map(self.nan_reasons).fillna('')

        print(f"✅ 合并完成: {len(df_final)} 条记录")

        # 统计缺失
        for col in ['alpha_pluse', 'alpha_peg_zscore', 'cr_qfq', 'alpha_038', 'alpha_120cq']:
            if col in df_final.columns:
                nan_count = df_final[col].isna().sum()
                if nan_count > 0:
                    print(f"  {col}缺失: {nan_count}条")

        return df_final

    def calculate_comprehensive_score(self, df):
        """计算策略3综合得分"""
        print("\n" + "=" * 80)
        print("步骤11: 计算策略3综合得分")
        print("=" * 80)

        df_result = df.copy()

        # 确保所有因子都是数值型
        for col in ['alpha_pluse', 'alpha_peg_zscore', 'alpha_120cq', 'cr_qfq', 'alpha_038']:
            if col in df_result.columns:
                df_result[col] = pd.to_numeric(df_result[col], errors='coerce')

        # 填充缺失值（用极端值替代，确保不被选中）
        df_result['alpha_pluse'] = df_result['alpha_pluse'].fillna(0)  # 默认为0（无信号）
        df_result['alpha_peg_zscore'] = df_result['alpha_peg_zscore'].fillna(9999)  # 极差估值
        df_result['alpha_120cq'] = df_result['alpha_120cq'].fillna(0)  # 默认位置0
        df_result['cr_qfq'] = df_result['cr_qfq'].fillna(-9999)  # 极差动量
        df_result['alpha_038'] = df_result['alpha_038'].fillna(0)  # 默认强度0

        # 计算各因子的标准化值
        # 1. alpha_pluse: 1 - alpha_pluse (因为0/1，反向)
        factor_1 = 1 - df_result['alpha_pluse']

        # 2. -行业标准化alpha_peg (负向因子，越小越好，所以取负)
        factor_2 = -df_result['alpha_peg_zscore']

        # 3. alpha_120cq (正向，已经是0-1)
        factor_3 = df_result['alpha_120cq']

        # 4. cr_qfq标准化 (除以最大值)
        cr_max = df_result['cr_qfq'].max()
        if cr_max > 0:
            factor_4 = df_result['cr_qfq'] / cr_max
        else:
            factor_4 = 0

        # 5. -alpha_038标准化 (负向因子，除以最小值取负)
        alpha_038_min = df_result['alpha_038'].min()
        if alpha_038_min < 0:
            factor_5 = -df_result['alpha_038'] / alpha_038_min
        else:
            factor_5 = 0

        # 计算综合得分
        df_result['综合得分'] = (
            0.20 * factor_1 +
            0.25 * factor_2 +
            0.15 * factor_3 +
            0.20 * factor_4 +
            0.20 * factor_5
        )

        # 添加各因子权重明细（便于验证）
        df_result['因子1_量能'] = factor_1
        df_result['因子2_估值'] = factor_2
        df_result['因子3_位置'] = factor_3
        df_result['因子4_动量'] = factor_4
        df_result['因子5_强度'] = factor_5

        print(f"✅ 综合得分计算完成")
        print(f"  得分范围: {df_result['综合得分'].min():.4f} ~ {df_result['综合得分'].max():.4f}")
        print(f"  平均得分: {df_result['综合得分'].mean():.4f}")

        return df_result

    def export_results(self, df_final):
        """导出结果"""
        print("\n" + "=" * 80)
        print("步骤12: 导出结果")
        print("=" * 80)

        output_dir = '/home/zcy/alpha006_20251223/results/output'
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 选择输出列
        output_columns = [
            '股票代码', '交易日', '申万一级行业',
            'alpha_pluse', '行业标准化alpha_peg', 'alpha_120cq', 'cr_qfq', 'alpha_038',
            '综合得分',
            '因子1_量能', '因子2_估值', '因子3_位置', '因子4_动量', '因子5_强度',
            '备注'
        ]

        # 重命名列
        df_output = df_final.copy()
        df_output.rename(columns={
            'ts_code': '股票代码',
            'trade_date': '交易日',
            'l1_name': '申万一级行业',
            'alpha_peg_zscore': '行业标准化alpha_peg',
        }, inplace=True)

        # 确保所有列都存在
        for col in output_columns:
            if col not in df_output.columns:
                df_output[col] = ''

        df_export = df_output[output_columns].copy()

        # 格式化
        df_export['交易日'] = df_export['交易日'].astype(str)
        numeric_cols = ['alpha_pluse', '行业标准化alpha_peg', 'alpha_120cq', 'cr_qfq', 'alpha_038',
                       '综合得分', '因子1_量能', '因子2_估值', '因子3_位置', '因子4_动量', '因子5_强度']
        for col in numeric_cols:
            df_export[col] = pd.to_numeric(df_export[col], errors='coerce').round(4)

        # 排序（按综合得分降序）
        df_export = df_export.sort_values('综合得分', ascending=False)

        # 保存完整文件
        full_path = os.path.join(output_dir, f'strategy3_comprehensive_scores_{timestamp}.xlsx')
        df_export.to_excel(full_path, index=False)
        print(f"✅ 完整结果已保存: {full_path}")

        # 保存前100名
        top100_path = os.path.join(output_dir, f'strategy3_top100_{timestamp}.xlsx')
        df_export.head(100).to_excel(top100_path, index=False)
        print(f"✅ 前100名已保存: {top100_path}")

        # 保存统计摘要
        summary_path = os.path.join(output_dir, f'strategy3_summary_{timestamp}.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("策略3综合得分计算 - 20251229\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"数据日期: {self.target_date}\n")
            f.write(f"计算时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("数据统计:\n")
            f.write(f"  总股票数: {len(df_export)}\n")
            f.write(f"  有效数据: {df_export['综合得分'].notna().sum()}\n")
            f.write(f"  缺失数据: {df_export['综合得分'].isna().sum()}\n\n")

            f.write("综合得分统计:\n")
            stats = df_export['综合得分'].describe()
            for key, value in stats.items():
                f.write(f"  {key}: {value:.4f}\n")

            f.write("\n前10名股票:\n")
            top10 = df_export.head(10)[['股票代码', '申万一级行业', '综合得分', 'alpha_pluse', '行业标准化alpha_peg', 'alpha_120cq', 'cr_qfq', 'alpha_038']]
            f.write(top10.to_string())

        print(f"✅ 统计摘要已保存: {summary_path}")

        return full_path, top100_path, summary_path

    def print_summary(self, df_final):
        """打印执行总结"""
        print("\n" + "=" * 80)
        print("执行总结")
        print("=" * 80)

        print(f"\n📊 数据统计:")
        print(f"  目标日期: {self.target_date}")
        print(f"  总记录数: {len(df_final)}")
        print(f"  有效记录: {df_final['综合得分'].notna().sum()}")
        print(f"  缺失记录: {df_final['综合得分'].isna().sum()}")

        if df_final['综合得分'].notna().sum() > 0:
            print(f"\n📈 综合得分统计:")
            valid_data = df_final['综合得分'].dropna()
            print(f"  均值: {valid_data.mean():.4f}")
            print(f"  标准差: {valid_data.std():.4f}")
            print(f"  最小值: {valid_data.min():.4f}")
            print(f"  最大值: {valid_data.max():.4f}")
            print(f"  中位数: {valid_data.median():.4f}")

        print(f"\n📝 前10名优质个股:")
        top10 = df_final[df_final['综合得分'].notna()].nlargest(10, '综合得分')
        for _, row in top10.iterrows():
            print(f"  {row['ts_code']}  {row['l1_name']:<8} 得分={row['综合得分']:.4f}")

        if len(self.nan_reasons) > 0:
            from collections import Counter
            reason_counts = Counter(self.nan_reasons.values())
            print(f"\n⚠️  数据缺失原因:")
            for reason, count in reason_counts.most_common():
                print(f"  {reason}: {count}只")

    def run(self):
        """主执行流程"""
        print("\n" + "=" * 80)
        print("策略3综合得分计算 - 20251229")
        print("=" * 80)
        print("公式: 综合得分 = 0.20*(1-alpha_pluse) + 0.25*(-alpha_peg) + 0.15*alpha_120cq")
        print("        + 0.20*(cr_qfq/max) + 0.20*(-alpha_038/min)")
        print("=" * 80)

        start_time = datetime.now()

        # 1. 获取可交易股票
        valid_stocks = self.get_tradable_stocks()
        if not valid_stocks:
            print("❌ 无有效股票")
            return

        # 2. 获取交易日
        trading_days = self.get_trading_days_needed()

        # 3. 获取数据
        price_df = self.get_price_data(valid_stocks, trading_days)
        if price_df.empty:
            return

        df_pe, df_fina = self.get_fina_data(valid_stocks)
        df_industry = self.get_industry_data(valid_stocks)
        df_cr = self.get_cr_qfq_data(valid_stocks)

        # 4. 计算因子
        df_pluse = self.calculate_alpha_pluse(price_df)
        df_peg = self.calculate_alpha_peg(df_pe, df_fina)
        df_peg_zscore = self.calculate_industry_zscore(df_peg, df_industry)
        df_alpha038 = self.calculate_alpha_038(price_df)

        # 5. 为alpha_120cq准备基础数据
        # 需要以alpha_peg_zscore为基础合并
        if len(df_peg_zscore) > 0:
            df_temp = df_peg_zscore[['ts_code']].copy()
            df_alpha120cq = self.calculate_alpha_120cq(price_df, df_temp)
        else:
            df_alpha120cq = pd.DataFrame()

        # 6. 合并所有因子
        df_merged = self.merge_all_factors(df_pluse, df_peg_zscore, df_cr, df_alpha038, df_alpha120cq)
        if df_merged.empty:
            return

        # 7. 计算综合得分
        df_final = self.calculate_comprehensive_score(df_merged)

        # 8. 导出结果
        self.export_results(df_final)

        # 9. 打印总结
        self.print_summary(df_final)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\n⏱️  执行耗时: {duration:.2f} 秒")
        print("\n✅ 任务完成！")


if __name__ == "__main__":
    calculator = Strategy3Calculator20251229()
    calculator.run()
