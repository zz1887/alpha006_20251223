"""
alpha_pluse与alpha_peg因子计算 - 20250919单日批量计算

功能:
1. 读取20250919当日可交易股票数据
2. 计算alpha_pluse因子（基于20日窗口）
3. 计算alpha_peg因子（基于财务数据）
4. 输出Excel文档并验证计算逻辑

输出:
- results/output/factor_values_20250919.xlsx
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, '/home/zcy/alpha006_20251223')

from core.utils.db_connection import db
from core.constants.config import TABLE_DAILY_BASIC, TABLE_FINA_INDICATOR, TABLE_DAILY_KLINE, TABLE_INDUSTRY


class FactorCalculator20250919:
    """20250919因子计算器"""

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
        self.results = []
        self.validation_samples = []
        self.missing_data_stocks = []
        self.invalid_stocks = []

    def get_trading_days_needed(self):
        """获取需要的交易日范围"""
        # 需要往前34天（20日窗口+14日均值，最大需要34天）
        end_date = self.target_date_dt
        start_date = end_date - timedelta(days=50)  # 多取几天确保足够

        sql = f"""
        SELECT DISTINCT trade_date
        FROM {TABLE_DAILY_KLINE}
        WHERE trade_date >= %s AND trade_date <= %s
        ORDER BY trade_date
        """

        data = db.execute_query(sql, (start_date.strftime('%Y%m%d'), self.target_date))
        trading_days = [row['trade_date'] for row in data]

        print(f"✓ 获取交易日: {len(trading_days)} 天")
        print(f"  范围: {trading_days[0]} ~ {trading_days[-1]}")

        return trading_days

    def get_tradable_stocks(self):
        """获取20250919当日可交易股票"""
        print(f"\n{'='*80}")
        print("步骤1: 获取20250919可交易股票")
        print(f"{'='*80}")

        # 获取当日所有股票
        sql = f"""
        SELECT DISTINCT ts_code
        FROM {TABLE_DAILY_KLINE}
        WHERE trade_date = %s
        """
        data = db.execute_query(sql, (self.target_date,))
        all_stocks = [row['ts_code'] for row in data]

        print(f"当日有交易记录的股票: {len(all_stocks)} 只")

        # 过滤ST股票
        sql_st = "SELECT ts_code FROM stock_st WHERE type = 'ST'"
        st_data = db.execute_query(sql_st, ())
        st_stocks = set([row['ts_code'] for row in st_data])
        print(f"ST股票: {len(st_stocks)} 只")

        # 过滤
        valid_stocks = []
        for stock in all_stocks:
            # 过滤ST
            if stock in st_stocks:
                self.invalid_stocks.append({'ts_code': stock, 'reason': 'ST股票'})
                continue

            valid_stocks.append(stock)

        print(f"✅ 有效可交易股票: {len(valid_stocks)} 只")
        print(f"❌ 过滤股票: {len(self.invalid_stocks)} 只")

        return valid_stocks

    def get_price_data(self, stocks, trading_days):
        """获取价格和成交量数据"""
        print(f"\n{'='*80}")
        print("步骤2: 获取价格和成交量数据")
        print(f"{'='*80}")

        if not stocks:
            print("❌ 无有效股票")
            return pd.DataFrame()

        # 构建IN查询
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

        if len(df) == 0:
            print("❌ 未获取到价格数据")
            return pd.DataFrame()

        # 数据类型转换
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df['vol'] = df['vol'].astype(float)

        print(f"✓ 获取到 {len(df):,} 条价格数据")
        print(f"  股票数: {df['ts_code'].nunique()}")
        print(f"  日期数: {df['trade_date'].nunique()}")

        return df

    def get_fina_data(self, stocks):
        """获取财务数据"""
        print(f"\n{'='*80}")
        print("步骤3: 获取财务数据")
        print(f"{'='*80}")

        if not stocks:
            print("❌ 无有效股票")
            return pd.DataFrame(), pd.DataFrame()

        # 获取PE数据
        placeholders = ','.join(['%s'] * len(stocks))
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

        print(f"✓ PE数据: {len(df_pe):,} 条")

        # 获取财务数据（获取所有历史财报，用于前向填充）
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

        print(f"✓ 财务数据: {len(df_fina):,} 条")

        return df_pe, df_fina

    def get_industry_data(self, stocks):
        """获取行业数据"""
        if not stocks:
            return pd.DataFrame()

        try:
            placeholders = ','.join(['%s'] * len(stocks))
            sql = f"""
            SELECT ts_code, l1_name
            FROM {TABLE_INDUSTRY}
            WHERE ts_code IN ({placeholders})
            """

            data = db.execute_query(sql, stocks)
            df = pd.DataFrame(data)
            print(f"✓ 行业数据: {len(df):,} 条")
            return df
        except Exception as e:
            print(f"⚠️  无法获取行业数据: {e}")
            return pd.DataFrame()

    def calculate_alpha_pluse(self, price_df):
        """计算alpha_pluse因子"""
        print(f"\n{'='*80}")
        print("步骤4: 计算alpha_pluse因子")
        print(f"{'='*80}")

        if len(price_df) == 0:
            print("❌ 无价格数据")
            return pd.DataFrame()

        params = self.pluse_params
        results = []
        validation_stocks = ['600000.SH', '000001.SZ', '600036.SH', '000858.SZ', '600519.SH']  # 常见股票用于验证

        # 按股票分组
        for ts_code, group in price_df.groupby('ts_code'):
            group = group.sort_values('trade_date').copy()

            # 检查数据完整性
            if len(group) < params['window_20d'] + params['lookback_14d']:
                self.missing_data_stocks.append({
                    'ts_code': ts_code,
                    'reason': f'数据不足(仅有{len(group)}天，需要{params["window_20d"] + params["lookback_14d"]}天)'
                })
                continue

            # 计算14日成交量均值
            group['vol_14_mean'] = group['vol'].rolling(
                window=params['lookback_14d'], min_periods=params['lookback_14d']
            ).mean()

            # 标记满足条件的交易日
            group['condition'] = (
                (group['vol'] >= group['vol_14_mean'] * params['lower_mult']) &
                (group['vol'] <= group['vol_14_mean'] * params['upper_mult']) &
                group['vol_14_mean'].notna()
            )

            # 计算20日滚动满足数量
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

            # 获取20250919当日结果
            target_row = group[group['trade_date'] == self.target_date_dt]

            if len(target_row) > 0:
                row = target_row.iloc[0]
                result = {
                    'ts_code': ts_code,
                    'trade_date': self.target_date,
                    'alpha_pluse': int(row['alpha_pluse']),
                    'count_20d': row['count_20d'],
                    'vol': row['vol'],
                    'vol_14_mean': row['vol_14_mean'],
                }
                results.append(result)

                # 保存验证样本
                if ts_code in validation_stocks:
                    detail = group[['trade_date', 'vol', 'vol_14_mean', 'condition', 'count_20d', 'alpha_pluse']].tail(20)
                    self.validation_samples.append({
                        'ts_code': ts_code,
                        'detail': detail
                    })

        df_result = pd.DataFrame(results)

        if len(df_result) > 0:
            print(f"✅ 计算完成: {len(df_result)} 只股票")
            print(f"  信号数: {df_result['alpha_pluse'].sum()}")
            print(f"  信号比例: {df_result['alpha_pluse'].mean():.4f}")

        return df_result

    def calculate_alpha_peg(self, df_pe, df_fina, df_industry):
        """计算alpha_peg因子"""
        print(f"\n{'='*80}")
        print("步骤5: 计算alpha_peg因子")
        print(f"{'='*80}")

        if len(df_pe) == 0 or len(df_fina) == 0:
            print("❌ 缺少PE或财务数据")
            return pd.DataFrame()

        # 1. 对财务数据按股票分组，创建映射
        fina_map = {}
        for ts_code, group in df_fina.groupby('ts_code'):
            # 按公告日排序
            group = group.sort_values('ann_date')
            # 创建日期到增长率的映射
            fina_map[ts_code] = dict(zip(group['ann_date'], group['dt_netprofit_yoy']))

        # 2. 为每个PE记录查找对应的财务数据
        results = []
        for _, row in df_pe.iterrows():
            ts_code = row['ts_code']
            trade_date = row['trade_date']
            pe_ttm = row['pe_ttm']

            if ts_code not in fina_map:
                continue

            # 查找最近一期已公告的财报
            fina_dates = sorted(fina_map[ts_code].keys())
            valid_dates = [d for d in fina_dates if d <= trade_date]

            if not valid_dates:
                continue

            # 取最近一期
            latest_ann_date = valid_dates[-1]
            dt_netprofit_yoy = fina_map[ts_code][latest_ann_date]

            # 计算alpha_peg
            if dt_netprofit_yoy != 0:
                alpha_peg = pe_ttm / dt_netprofit_yoy
                results.append({
                    'ts_code': ts_code,
                    'trade_date': trade_date,
                    'pe_ttm': pe_ttm,
                    'dt_netprofit_yoy': dt_netprofit_yoy,
                    'alpha_peg': alpha_peg,
                    'ann_date': latest_ann_date,
                    '备注': ''
                })
            else:
                results.append({
                    'ts_code': ts_code,
                    'trade_date': trade_date,
                    'pe_ttm': pe_ttm,
                    'dt_netprofit_yoy': dt_netprofit_yoy,
                    'alpha_peg': np.nan,
                    'ann_date': latest_ann_date,
                    '备注': 'dt_netprofit_yoy为零'
                })

        if not results:
            print("❌ 无有效计算结果")
            return pd.DataFrame()

        df_result = pd.DataFrame(results)

        # 3. 合并行业数据
        if len(df_industry) > 0:
            df_result = df_result.merge(df_industry, on='ts_code', how='left')
            df_result['l1_name'] = df_result['l1_name'].fillna('其他')
        else:
            df_result['l1_name'] = '其他'

        # 4. 分行业排名
        df_result['industry_rank'] = df_result.groupby(['trade_date', 'l1_name'])['alpha_peg'].rank(ascending=True, method='first')

        print(f"✅ 计算完成: {len(df_result)} 只股票")
        print(f"  有效值: {df_result['alpha_peg'].notna().sum()}")
        print(f"  NaN值: {df_result['alpha_peg'].isna().sum()}")

        return df_result

    def export_to_excel(self, df_pluse, df_peg):
        """导出到Excel"""
        print(f"\n{'='*80}")
        print("步骤6: 导出到Excel")
        print(f"{'='*80}")

        # 合并结果
        if len(df_pluse) > 0 and len(df_peg) > 0:
            df_merged = pd.merge(
                df_pluse[['ts_code', 'alpha_pluse', 'count_20d']],
                df_peg[['ts_code', 'alpha_peg', '备注']],
                on='ts_code',
                how='outer'
            )
        elif len(df_pluse) > 0:
            df_merged = df_pluse[['ts_code', 'alpha_pluse', 'count_20d']].copy()
            df_merged['alpha_peg'] = np.nan
            df_merged['备注'] = '无财务数据'
        elif len(df_peg) > 0:
            df_merged = df_peg[['ts_code', 'alpha_peg', '备注']].copy()
            df_merged['alpha_pluse'] = np.nan
            df_merged['count_20d'] = np.nan
        else:
            print("❌ 无数据可导出")
            return

        # 添加交易日
        df_merged['交易日'] = self.target_date

        # 重命名列
        df_merged.rename(columns={
            'ts_code': '股票代码',
            'alpha_pluse': 'alpha_pluse',
            'alpha_peg': 'alpha_peg',
            'count_20d': '20日满足天数',
        }, inplace=True)

        # 选择输出列
        output_cols = ['股票代码', '交易日', 'alpha_pluse', 'alpha_peg', '备注']
        if '20日满足天数' in df_merged.columns:
            output_cols.insert(3, '20日满足天数')

        df_output = df_merged[output_cols].copy()

        # 格式化
        df_output['alpha_pluse'] = pd.to_numeric(df_output['alpha_pluse'], errors='coerce').fillna(0).astype(int)
        df_output['alpha_peg'] = pd.to_numeric(df_output['alpha_peg'], errors='coerce').round(4)
        df_output['备注'] = df_output['备注'].fillna('')

        # 排序
        df_output = df_output.sort_values('股票代码')

        # 创建输出目录
        output_dir = '/home/zcy/alpha006_20251223/results/output'
        os.makedirs(output_dir, exist_ok=True)

        # 保存Excel
        excel_path = os.path.join(output_dir, f'factor_values_{self.target_date}.xlsx')

        # 尝试使用openpyxl，如果失败则使用CSV
        try:
            # 使用openpyxl引擎支持格式设置
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df_output.to_excel(writer, sheet_name='因子值', index=False)

                # 获取workbook和worksheet
                workbook = writer.book
                worksheet = writer.sheets['因子值']

                # 设置列宽
                for idx, col in enumerate(df_output.columns, 1):
                    max_len = max(df_output[col].astype(str).apply(len).max(), len(col)) + 2
                    worksheet.column_dimensions[chr(64 + idx)].width = min(max_len, 30)

                # 设置表头居中
                for cell in worksheet[1]:
                    cell.alignment = pd.ExcelWriter(workbook).book.active.cell(1, 1).alignment
                    cell.alignment = cell.alignment.copy(horizontal='center', vertical='center')

            print(f"✅ Excel文件已保存: {excel_path}")
            print(f"  记录数: {len(df_output)}")

            return excel_path, df_output

        except ImportError:
            # 如果没有openpyxl，保存为CSV
            csv_path = excel_path.replace('.xlsx', '.csv')
            df_output.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"⚠️  未安装openpyxl，已保存为CSV: {csv_path}")
            print(f"  可用Excel打开并另存为.xlsx格式")
            print(f"  记录数: {len(df_output)}")
            return csv_path, df_output

    def print_validation(self, df_pluse):
        """打印验证明细"""
        if not self.validation_samples:
            return

        print(f"\n{'='*80}")
        print("计算验证明细（随机抽样）")
        print(f"{'='*80}")

        for sample in self.validation_samples:
            ts_code = sample['ts_code']
            detail = sample['detail']

            print(f"\n股票 {ts_code} 最近20天计算明细:")
            print(f"{'日期':<12} {'成交量':<10} {'14日均值':<12} {'满足':<6} {'20日计数':<10} {'alpha_pluse':<12}")
            print("-" * 75)

            for _, row in detail.iterrows():
                date = row['trade_date'].strftime('%Y-%m-%d')
                vol = row['vol']
                mean = row['vol_14_mean']
                cond = '✓' if row['condition'] else '✗'
                count = row['count_20d']
                alpha = row['alpha_pluse']

                print(f"{date:<12} {vol:<10.0f} {mean:<12.2f} {cond:<6} {count:<10} {alpha:<12}")

    def print_summary(self, df_pluse, df_peg, excel_path, df_output):
        """打印执行总结"""
        print(f"\n{'='*80}")
        print("执行总结")
        print(f"{'='*80}")

        print(f"\n📊 数据统计:")
        print(f"  目标日期: {self.target_date}")
        print(f"  有效可交易股票: {len(self.get_tradable_stocks())} 只")
        print(f"  alpha_pluse计算完成: {len(df_pluse)} 只")
        print(f"  alpha_peg计算完成: {len(df_peg)} 只")
        print(f"  最终输出: {len(df_output)} 只")

        if len(df_pluse) > 0:
            print(f"\n📈 alpha_pluse统计:")
            print(f"  信号数: {df_pluse['alpha_pluse'].sum()}")
            print(f"  信号比例: {df_pluse['alpha_pluse'].mean():.4f}")
            print(f"  20日满足天数均值: {df_pluse['count_20d'].mean():.2f}")

        if len(df_peg) > 0:
            print(f"\n📊 alpha_peg统计:")
            print(f"  有效值: {len(df_peg)}")
            print(f"  均值: {df_peg['alpha_peg'].mean():.4f}")
            print(f"  中位数: {df_peg['alpha_peg'].median():.4f}")

        print(f"\n⚠️  异常情况:")
        print(f"  过滤股票: {len(self.invalid_stocks)} 只")
        print(f"  数据不足: {len(self.missing_data_stocks)} 只")

        if len(self.invalid_stocks) > 0:
            print(f"\n  过滤股票示例:")
            for item in self.invalid_stocks[:5]:
                print(f"    {item['ts_code']}: {item['reason']}")

        if len(self.missing_data_stocks) > 0:
            print(f"\n  数据不足股票示例:")
            for item in self.missing_data_stocks[:5]:
                print(f"    {item['ts_code']}: {item['reason']}")

        print(f"\n✅ 输出文件: {excel_path}")
        print(f"  保存路径: {os.path.dirname(excel_path)}")
        print(f"  文件大小: {os.path.getsize(excel_path) / 1024:.2f} KB")

        # 显示前10行
        print(f"\n📄 Excel内容预览 (前10行):")
        print(df_output.head(10).to_string(index=False))

    def run(self):
        """主执行流程"""
        print("\n" + "="*80)
        print("alpha_pluse与alpha_peg因子计算 - 20250919")
        print("="*80)

        start_time = datetime.now()

        # 1. 获取交易日
        trading_days = self.get_trading_days_needed()

        # 2. 获取可交易股票
        valid_stocks = self.get_tradable_stocks()

        if not valid_stocks:
            print("❌ 无有效股票，程序退出")
            return

        # 3. 获取数据
        price_df = self.get_price_data(valid_stocks, trading_days)
        df_pe, df_fina = self.get_fina_data(valid_stocks)
        df_industry = self.get_industry_data(valid_stocks)

        # 4. 计算因子
        df_pluse = self.calculate_alpha_pluse(price_df)
        df_peg = self.calculate_alpha_peg(df_pe, df_fina, df_industry)

        # 5. 验证计算
        self.print_validation(df_pluse)

        # 6. 导出Excel
        excel_path, df_output = self.export_to_excel(df_pluse, df_peg)

        # 7. 打印总结
        self.print_summary(df_pluse, df_peg, excel_path, df_output)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"\n⏱️  执行耗时: {duration:.2f} 秒")


if __name__ == "__main__":
    calculator = FactorCalculator20250919()
    calculator.run()
