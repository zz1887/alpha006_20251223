"""
多因子计算 - 20250919
包含: alpha_pluse, alpha_peg(原始+行业标准化), cr_qfq

输出: multi_factor_values_20250919.xlsx
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, '/home/zcy/alpha006_20251223')

from core.utils.db_connection import db
from core.constants.config import TABLE_DAILY_BASIC, TABLE_FINA_INDICATOR, TABLE_DAILY_KLINE


class MultiFactorCalculator:
    """多因子计算器"""

    def __init__(self):
        self.target_date = '20250919'
        self.target_date_dt = pd.to_datetime('20250919', format='%Y%m%d')

        # alpha_pluse参数
        self.pluse_params = {
            'window_20d': 20,
            'lookback_14d': 14,
            'lower_mult': 1.4,
            'upper_mult': 3.5,
            'min_count': 2,
            'max_count': 4,
        }

        # 结果存储
        self.nan_reasons = {}  # 记录NaN原因

    def get_trading_days_needed(self):
        """获取需要的交易日范围"""
        end_date = self.target_date_dt
        start_date = end_date - timedelta(days=50)

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

    def get_tradable_stocks(self):
        """获取可交易股票"""
        print(f"\n{'='*80}")
        print("步骤1: 获取20250919可交易股票")
        print(f"{'='*80}")

        sql = f"""
        SELECT DISTINCT ts_code
        FROM {TABLE_DAILY_KLINE}
        WHERE trade_date = %s
        """
        data = db.execute_query(sql, (self.target_date,))
        all_stocks = [row['ts_code'] for row in data]

        # 过滤ST
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

    def get_price_data(self, stocks, trading_days):
        """获取价格和成交量数据"""
        print(f"\n{'='*80}")
        print("步骤2: 获取价格和成交量数据")
        print(f"{'='*80}")

        if not stocks:
            return pd.DataFrame()

        placeholders_days = ','.join(['%s'] * len(trading_days))
        placeholders_stocks = ','.join(['%s'] * len(stocks))

        sql = f"""
        SELECT ts_code, trade_date, vol
        FROM {TABLE_DAILY_KLINE}
        WHERE trade_date IN ({placeholders_days})
          AND ts_code IN ({placeholders_stocks})
        ORDER BY ts_code, trade_date
        """

        params = trading_days + stocks
        data = db.execute_query(sql, params)
        df = pd.DataFrame(data)

        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df['vol'] = df['vol'].astype(float)

        print(f"✓ 价格数据: {len(df):,} 条")
        return df

    def get_fina_data(self, stocks):
        """获取财务数据"""
        print(f"\n{'='*80}")
        print("步骤3: 获取财务数据")
        print(f"{'='*80}")

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
        print(f"\n{'='*80}")
        print("步骤4: 获取cr_qfq指标")
        print(f"{'='*80}")

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
        print(f"\n{'='*80}")
        print("步骤5: 计算alpha_pluse因子")
        print(f"{'='*80}")

        if len(price_df) == 0:
            return pd.DataFrame()

        params = self.pluse_params
        results = []

        for ts_code, group in price_df.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            if len(group) < params['window_20d'] + params['lookback_14d']:
                self.nan_reasons[ts_code] = f"数据不足({len(group)}天<34天)"
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
        print(f"\n{'='*80}")
        print("步骤6: 计算原始alpha_peg")
        print(f"{'='*80}")

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
        print(f"\n{'='*80}")
        print("步骤7: 计算行业Z-Score标准化")
        print(f"{'='*80}")

        if len(df_peg) == 0:
            return pd.DataFrame()

        # 确保数据类型
        df_peg = df_peg.copy()
        df_peg['alpha_peg_raw'] = pd.to_numeric(df_peg['alpha_peg_raw'], errors='coerce')

        # 合并行业（去重）
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

    def merge_factors(self, df_pluse, df_peg_zscore, df_cr):
        """合并所有因子"""
        print(f"\n{'='*80}")
        print("步骤8: 合并所有因子并标注NaN")
        print(f"{'='*80}")

        # 以alpha_peg为基础（因为它需要PE和财务数据，限制最多）
        if len(df_peg_zscore) == 0:
            print("❌ 无alpha_peg数据，无法合并")
            return pd.DataFrame()

        # 合并alpha_pluse
        if len(df_pluse) > 0:
            df_final = df_peg_zscore.merge(
                df_pluse[['ts_code', 'alpha_pluse', 'count_20d']],
                on='ts_code',
                how='left'
            )
            # 标注alpha_pluse NaN原因
            mask = df_final['alpha_pluse'].isna()
            if mask.any():
                for stock in df_final.loc[mask, 'ts_code']:
                    if stock not in self.nan_reasons:
                        self.nan_reasons[stock] = 'alpha_pluse数据不足'
        else:
            df_final = df_peg_zscore.copy()
            df_final['alpha_pluse'] = np.nan
            df_final['count_20d'] = np.nan

        # 合并cr_qfq
        if len(df_cr) > 0:
            df_final = df_final.merge(
                df_cr[['ts_code', 'cr_qfq']],
                on='ts_code',
                how='left'
            )
            # 标注cr_qfq NaN原因
            mask = df_final['cr_qfq'].isna()
            if mask.any():
                for stock in df_final.loc[mask, 'ts_code']:
                    if stock not in self.nan_reasons:
                        self.nan_reasons[stock] = 'cr_qfq数据缺失'
        else:
            df_final['cr_qfq'] = np.nan

        # 添加交易日
        df_final['trade_date'] = self.target_date

        # 添加备注（NaN原因）
        df_final['备注'] = df_final['ts_code'].map(self.nan_reasons).fillna('')

        # 为alpha_pluse缺失的记录添加备注（如果还没有）
        mask_alpha = (df_final['alpha_pluse'].isna()) & (df_final['备注'] == '')
        df_final.loc[mask_alpha, '备注'] = 'alpha_pluse数据不足'

        print(f"✅ 合并完成: {len(df_final)} 条记录")
        print(f"  alpha_pluse缺失: {df_final['alpha_pluse'].isna().sum()} 条")
        print(f"  alpha_peg_raw缺失: {df_final['alpha_peg_raw'].isna().sum()} 条")
        print(f"  alpha_peg_zscore缺失: {df_final['alpha_peg_zscore'].isna().sum()} 条")
        print(f"  cr_qfq缺失: {df_final['cr_qfq'].isna().sum()} 条")
        print(f"  有备注记录: {(df_final['备注'] != '').sum()} 条")

        return df_final

    def export_to_excel(self, df_final):
        """导出Excel"""
        print(f"\n{'='*80}")
        print("步骤9: 导出Excel")
        print(f"{'='*80}")

        if len(df_final) == 0:
            print("❌ 无数据可导出")
            return

        # 选择和重命名列
        df_output = df_final[[
            'ts_code', 'trade_date', 'l1_name',
            'alpha_pluse', 'count_20d',
            'alpha_peg_raw', 'alpha_peg_zscore',
            'cr_qfq', '备注'
        ]].copy()

        df_output.rename(columns={
            'ts_code': '股票代码',
            'trade_date': '交易日',
            'l1_name': '申万一级行业',
            'alpha_pluse': 'alpha_pluse',
            'count_20d': '20日满足天数',
            'alpha_peg_raw': '原始alpha_peg',
            'alpha_peg_zscore': '行业标准化alpha_peg',
            'cr_qfq': 'cr_qfq',
        }, inplace=True)

        # 格式化
        df_output['交易日'] = df_output['交易日'].astype(str)
        df_output['alpha_pluse'] = pd.to_numeric(df_output['alpha_pluse'], errors='coerce').fillna(0).astype(int)
        df_output['20日满足天数'] = pd.to_numeric(df_output['20日满足天数'], errors='coerce').round(2)
        df_output['原始alpha_peg'] = pd.to_numeric(df_output['原始alpha_peg'], errors='coerce').round(4)
        df_output['行业标准化alpha_peg'] = pd.to_numeric(df_output['行业标准化alpha_peg'], errors='coerce').round(4)
        df_output['cr_qfq'] = pd.to_numeric(df_output['cr_qfq'], errors='coerce').round(4)
        df_output['备注'] = df_output['备注'].fillna('')

        # 排序
        df_output = df_output.sort_values('股票代码')

        # 创建输出目录
        output_dir = '/home/zcy/alpha006_20251223/results/output'
        os.makedirs(output_dir, exist_ok=True)

        # 保存Excel
        excel_path = os.path.join(output_dir, 'multi_factor_values_20250919.xlsx')

        try:
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df_output.to_excel(writer, sheet_name='多因子值', index=False)

                workbook = writer.book
                worksheet = writer.sheets['多因子值']

                # 设置列宽
                for idx, col in enumerate(df_output.columns, 1):
                    max_len = max(df_output[col].astype(str).apply(len).max(), len(col)) + 2
                    width = min(max_len, 20)
                    if col == '备注':
                        width = 30
                    worksheet.column_dimensions[chr(64 + idx)].width = width

                # 设置表头居中
                for cell in worksheet[1]:
                    cell.alignment = cell.alignment.copy(horizontal='center', vertical='center')

            print(f"✅ Excel文件已保存: {excel_path}")
            print(f"  记录数: {len(df_output)}")
            print(f"  文件大小: {os.path.getsize(excel_path) / 1024:.2f} KB")
            return excel_path, df_output

        except ImportError:
            csv_path = excel_path.replace('.xlsx', '.csv')
            df_output.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"⚠️  未安装openpyxl，已保存为CSV: {csv_path}")
            return csv_path, df_output

    def print_summary(self, df_final, excel_path, df_output):
        """打印执行总结"""
        print(f"\n{'='*80}")
        print("执行总结")
        print(f"{'='*80}")

        print(f"\n📊 数据统计:")
        print(f"  目标日期: {self.target_date}")
        print(f"  最终记录数: {len(df_final)}")

        print(f"\n📈 因子统计:")
        if 'alpha_pluse' in df_final.columns:
            valid = df_final['alpha_pluse'].notna().sum()
            signal = df_final['alpha_pluse'].sum()
            print(f"  alpha_pluse: {valid}只有效, {signal}个信号 ({signal/valid:.2%})")

        if 'alpha_peg_raw' in df_final.columns:
            valid = df_final['alpha_peg_raw'].notna().sum()
            mean = df_final['alpha_peg_raw'].mean()
            print(f"  原始alpha_peg: {valid}只有效, 均值={mean:.4f}")

        if 'alpha_peg_zscore' in df_final.columns:
            valid = df_final['alpha_peg_zscore'].notna().sum()
            mean = df_final['alpha_peg_zscore'].mean()
            std = df_final['alpha_peg_zscore'].std()
            print(f"  行业标准化alpha_peg: {valid}只有效, 均值={mean:.6f}, 标准差={std:.4f}")

        if 'cr_qfq' in df_final.columns:
            valid = df_final['cr_qfq'].notna().sum()
            mean = df_final['cr_qfq'].mean()
            print(f"  cr_qfq: {valid}只有效, 均值={mean:.4f}")

        print(f"\n⚠️  NaN统计:")
        for col in ['alpha_pluse', 'alpha_peg_raw', 'alpha_peg_zscore', 'cr_qfq']:
            if col in df_final.columns:
                nan_count = df_final[col].isna().sum()
                if nan_count > 0:
                    print(f"  {col}: {nan_count}条缺失")

        if len(self.nan_reasons) > 0:
            print(f"\n📝 NaN原因示例 (前5):")
            for i, (stock, reason) in enumerate(list(self.nan_reasons.items())[:5]):
                print(f"  {stock}: {reason}")

        print(f"\n✅ 输出文件: {excel_path}")

        # 显示前10行
        print(f"\n📄 Excel内容预览 (前10行):")
        print(df_output.head(10).to_string(index=False))

    def run(self):
        """主执行流程"""
        print("\n" + "="*80)
        print("多因子计算 - 20250919")
        print("因子: alpha_pluse, alpha_peg(原始+行业标准化), cr_qfq")
        print("="*80)

        start_time = datetime.now()

        # 1. 获取交易日
        trading_days = self.get_trading_days_needed()

        # 2. 获取可交易股票
        valid_stocks = self.get_tradable_stocks()

        if not valid_stocks:
            print("❌ 无有效股票")
            return

        # 3. 获取数据
        price_df = self.get_price_data(valid_stocks, trading_days)
        df_pe, df_fina = self.get_fina_data(valid_stocks)
        df_industry = self.get_industry_data(valid_stocks)
        df_cr = self.get_cr_qfq_data(valid_stocks)

        # 4. 计算因子
        df_pluse = self.calculate_alpha_pluse(price_df)
        df_peg = self.calculate_alpha_peg(df_pe, df_fina)
        df_peg_zscore = self.calculate_industry_zscore(df_peg, df_industry)

        # 5. 合并因子
        df_final = self.merge_factors(df_pluse, df_peg_zscore, df_cr)

        # 6. 导出
        excel_path, df_output = self.export_to_excel(df_final)

        # 7. 总结
        self.print_summary(df_final, excel_path, df_output)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\n⏱️  执行耗时: {duration:.2f} 秒")


if __name__ == "__main__":
    calculator = MultiFactorCalculator()
    calculator.run()
