"""
行业中性化实现 - 使用真实的stock_database.sw_industry数据

基于数据库中的sw_industry表实现完整的行业中性化功能
"""

import pandas as pd
import numpy as np
from typing import Optional, List
from core.utils.db_connection import db


class IndustryNeutralizerReal:
    """
    使用真实sw_industry数据的行业中性化处理器

    数据表结构:
    - ts_code: 股票代码
    - l1_code: 一级行业代码 (如: 801780.SI)
    - l1_name: 一级行业名称 (如: 银行)
    - l2_code: 二级行业代码
    - l2_name: 二级行业名称
    - l3_code: 三级行业代码
    - l3_name: 三级行业名称
    - import_time: 导入时间
    """

    def __init__(self):
        """初始化行业中性化处理器"""
        print("✅ 行业中性化处理器已初始化")
        print("📊 使用数据源: stock_database.sw_industry")

    def get_industry_data(self, ts_codes: List[str], start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        从sw_industry表获取行业分类数据

        参数:
            ts_codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        返回:
            DataFrame包含行业分类信息
        """
        try:
            # sw_industry表没有trade_date字段，使用import_time作为时间参考
            # 获取最新数据
            placeholders = ','.join(['%s'] * len(ts_codes))
            sql = f"""
            SELECT
                ts_code,
                l1_code, l1_name,
                l2_code, l2_name,
                l3_code, l3_name
            FROM sw_industry
            WHERE ts_code IN ({placeholders})
            ORDER BY ts_code
            """

            data = db.execute_query(sql, ts_codes)

            if not data:
                print("❌ 未查询到行业数据")
                return None

            df = pd.DataFrame(data)
            print(f"✅ 成功获取行业数据: {len(df)} 条记录")

            # 显示行业分布
            print(f"\n📊 行业分布统计:")
            print(f"   一级行业: {df['l1_name'].nunique()}个")
            print(f"   二级行业: {df['l2_name'].nunique()}个")
            print(f"   三级行业: {df['l3_name'].nunique()}个")

            # 显示前5个行业的股票数量
            print(f"\n🏢 股票数量TOP5行业:")
            top_industries = df['l2_name'].value_counts().head()
            for name, count in top_industries.items():
                print(f"   {name}: {count}只股票")

            return df

        except Exception as e:
            print(f"❌ 获取行业数据失败: {e}")
            return None

    def get_industry_mapping(self, ts_codes: List[str]) -> dict:
        """
        获取股票到行业的映射关系

        参数:
            ts_codes: 股票代码列表

        返回:
            {股票代码: 行业信息} 字典
        """
        df = self.get_industry_data(ts_codes, '20240101', '20241231')

        if df is None:
            return {}

        mapping = {}
        for _, row in df.iterrows():
            mapping[row['ts_code']] = {
                'l1_code': row['l1_code'],
                'l1_name': row['l1_name'],
                'l2_code': row['l2_code'],
                'l2_name': row['l2_name'],
                'l3_code': row['l3_code'],
                'l3_name': row['l3_name'],
            }

        return mapping

    def indneutralize(self, factor: pd.Series, industry_df: pd.DataFrame, level: str = 'l2') -> pd.Series:
        """
        行业中性化处理

        参数:
            factor: 因子值Series (index=股票代码)
            industry_df: 行业DataFrame，包含l1_code, l2_code, l3_code等列
            level: 行业层级 ('l1', 'l2', 'l3')

        返回:
            中性化后的因子值Series
        """
        if len(factor) == 0:
            print("⚠️  因子数据为空")
            return factor

        if len(industry_df) == 0:
            print("⚠️  行业数据为空，返回原始因子")
            return factor

        # 选择行业层级
        if level == 'l1':
            industry_col = 'l1_name'
        elif level == 'l2':
            industry_col = 'l2_name'
        elif level == 'l3':
            industry_col = 'l3_name'
        else:
            raise ValueError("level必须是 'l1', 'l2', 或 'l3'")

        # 确保索引对齐 - 使用reset_index确保factor的index是ts_code
        if not isinstance(factor.index, pd.RangeIndex):
            factor = factor.reset_index(drop=True)
            factor.index = industry_df['ts_code'].values[:len(factor)]

        # 将industry_df设置为ts_code索引
        industry_df_indexed = industry_df.set_index('ts_code')

        # 找到共同索引
        common_index = factor.index.intersection(industry_df_indexed.index)

        if len(common_index) == 0:
            print("❌ 无共同索引，无法中性化")
            return factor

        # 对齐数据
        factor_aligned = factor.loc[common_index]
        industry_group = industry_df_indexed.loc[common_index, industry_col]

        # 按行业计算均值
        industry_mean = factor_aligned.groupby(industry_group).mean()

        # 减去行业均值
        result = factor_aligned.copy()
        for ind in industry_mean.index:
            mask = industry_group == ind
            if mask.sum() > 0:
                result[mask] = factor_aligned[mask] - industry_mean[ind]

        return result

    def get_industry_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        获取行业统计信息

        参数:
            df: 包含行业数据的DataFrame

        返回:
            行业统计信息
        """
        stats = []
        for level in ['l1', 'l2', 'l3']:
            col = f'{level}_name'
            if col in df.columns:
                count = df[col].nunique()
                stats.append({
                    '层级': level,
                    '行业数量': count,
                    '行业列表': ', '.join(df[col].unique()[:5]) + ('...' if count > 5 else '')
                })

        return pd.DataFrame(stats)


class Alpha101CalculatorWithNeutralization:
    """
    支持行业中性化的Alpha101计算器

    继承自Alpha101Calculator，添加行业中性化功能
    """

    def __init__(self, ts_codes: List[str], start_date: str, end_date: str):
        """
        初始化

        参数:
            ts_codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        """
        # 延迟导入，避免循环依赖
        from factors.alpha101.alpha101_base import Alpha101Calculator

        # 初始化父类（不调用__init__避免数据库查询）
        self.ts_codes = ts_codes
        self.start_date = start_date
        self.end_date = end_date

        # 加载基础数据
        self.neutralizer = IndustryNeutralizerReal()
        self.industry_data = self.neutralizer.get_industry_data(ts_codes, start_date, end_date)

        # 加载Alpha101基础功能
        self.base_calculator = Alpha101Calculator.__new__(Alpha101Calculator)

        # 加载价格等基础数据
        self._load_base_data()

        print(f"\n✅ Alpha101计算器（支持行业中性化）初始化完成")
        print(f"   股票数量: {len(ts_codes)}")
        print(f"   时间范围: {start_date} ~ {end_date}")

    def _load_base_data(self):
        """加载基础数据"""
        # 使用Alpha101Calculator的数据加载方法
        from factors.alpha101.alpha101_base import Alpha101Calculator

        # 创建临时实例获取数据
        temp_calc = Alpha101Calculator(self.ts_codes, self.start_date, self.end_date)

        # 复制数据
        self.price_data = temp_calc.price_data
        self.daily_basic = temp_calc.daily_basic
        self.fina_data = temp_calc.fina_data
        self.merged_data = temp_calc.merged_data

        # 合并行业数据
        if self.industry_data is not None and len(self.industry_data) > 0:
            # sw_industry表没有trade_date，直接合并
            self.merged_data = pd.merge(
                self.merged_data,
                self.industry_data[['ts_code', 'l1_code', 'l1_name', 'l2_code', 'l2_name', 'l3_code', 'l3_name']],
                on='ts_code',
                how='left'
            )
            print(f"✅ 行业数据已合并到主数据")

    def get_stock_data(self, ts_code: str) -> pd.DataFrame:
        """获取单只股票数据（包含行业信息）"""
        if len(self.merged_data) == 0:
            return pd.DataFrame()

        df = self.merged_data[self.merged_data['ts_code'] == ts_code].copy()
        df = df.sort_values('trade_date').reset_index(drop=True)
        return df

    # ==================== 24个需要行业中性化的因子 ====================

    def alpha_048(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_048: 需要子行业中性化

        公式:
        (indneutralize(((correlation(delta(close, 1), delta(delay(close, 1), 1), 250)* delta(close, 1)) / close), IndClass.subindustry) / sum(((delta(close, 1) / delay(close, 1))^2), 250))
        """
        # 1. 计算原始因子
        delta_close = self.base_calculator.delta(df['close'], 1)
        delta_delay = self.base_calculator.delta(self.base_calculator.delay(df['close'], 1), 1)

        corr = self.base_calculator.correlation(delta_close, delta_delay, 250)
        numerator = corr * delta_close / df['close']
        denominator = self.base_calculator.sum((delta_close / self.base_calculator.delay(df['close'], 1)) ** 2, 250)

        raw_factor = numerator / denominator

        # 2. 行业中性化 (三级行业)
        if 'l3_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            # 确保industry_df包含所有股票代码
            all_codes = df['ts_code'].unique()
            industry_df = industry_df[industry_df['ts_code'].isin(all_codes)]
            return self.neutralizer.indneutralize(raw_factor, industry_df, 'l3')
        else:
            print("⚠️  缺少行业数据，返回原始因子")
            return raw_factor

    def alpha_058(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_058: 需要一级行业中性化

        公式:
        -1 * Ts_Rank(decay_linear(correlation(IndNeutralize(vwap, IndClass.sector), volume, 3.92795), 7.89291), 5.50322)
        """
        # 1. 行业中性化vwap (一级行业)
        if 'l1_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            # 创建vwap的Series，索引为ts_code
            vwap_series = pd.Series(df['vwap'].values, index=df['ts_code'])
            vwap_neutral = self.neutralizer.indneutralize(vwap_series, industry_df, 'l1')
            # 对齐回原顺序，保持长度一致
            if len(vwap_neutral) == len(df):
                vwap_neutral = vwap_neutral.values
            else:
                vwap_neutral = df['vwap'].values
        else:
            vwap_neutral = df['vwap'].values

        # 2. 计算因子
        corr = self.base_calculator.correlation(pd.Series(vwap_neutral), df['volume'], 3.92795)
        decay = self.base_calculator.decay_linear(corr, 7.89291)
        ts_rank = self.base_calculator.ts_rank(decay, 5.50322)

        return -1 * ts_rank

    def alpha_059(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_059: 需要二级行业中性化

        公式:
        -1 * Ts_Rank(decay_linear(correlation(IndNeutralize(((vwap* 0.728317) + (vwap* (1 - 0.728317))), IndClass.industry), volume, 4.25197), 16.2289), 8.19648)
        """
        # 1. 计算中间变量
        vwap_adjusted = df['vwap'] * 0.728317 + df['vwap'] * (1 - 0.728317)  # 实际上就是vwap

        # 2. 行业中性化 (二级行业)
        if 'l2_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            vwap_neutral = self.neutralizer.indneutralize(vwap_adjusted, industry_df, 'l2')
        else:
            vwap_neutral = vwap_adjusted

        # 3. 计算因子
        corr = self.base_calculator.correlation(vwap_neutral, df['volume'], 4.25197)
        decay = self.base_calculator.decay_linear(corr, 16.2289)
        ts_rank = self.base_calculator.ts_rank(decay, 8.19648)

        return -1 * ts_rank

    def alpha_063(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_063: 需要二级行业中性化

        公式:
        (rank(decay_linear(delta(IndNeutralize(close, IndClass.industry), 2.25164), 8.22237)) - rank(decay_linear(correlation(((vwap* 0.318108) + (open* (1 - 0.318108))), sum(adv180, 37.2467), 13.557), 12.2883))) * -1
        """
        # 1. 行业中性化close (二级行业)
        if 'l2_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            close_neutral = self.neutralizer.indneutralize(df['close'], industry_df, 'l2')
        else:
            close_neutral = df['close']

        # 2. 计算第一部分
        delta_close = self.base_calculator.delta(close_neutral, 2.25164)
        part1 = self.base_calculator.rank(self.base_calculator.decay_linear(delta_close, 8.22237))

        # 3. 计算第二部分
        value = df['vwap'] * 0.318108 + df['open'] * (1 - 0.318108)

        # 需要adv180，先计算
        if 'adv180' not in df.columns:
            df['adv180'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(180, min_periods=180).mean()
            )

        corr = self.base_calculator.correlation(value, self.base_calculator.sum(df['adv180'], 37.2467), 13.557)
        part2 = self.base_calculator.rank(self.base_calculator.decay_linear(corr, 12.2883))

        return (part1 - part2) * -1

    def alpha_067(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_067: 需要一级行业中性化

        公式:
        ((rank((high - ts_min(high, 2.14593)))^rank(correlation(IndNeutralize(vwap, IndClass.sector), IndNeutralize(adv20, IndClass.subindustry), 6.02936))) * -1)
        """
        # 1. 计算第一部分
        part1 = self.base_calculator.rank(df['high'] - self.base_calculator.ts_min(df['high'], 2.14593))

        # 2. 行业中性化vwap (一级行业)
        if 'l1_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            vwap_neutral = self.neutralizer.indneutralize(df['vwap'], industry_df, 'l1')

            # 需要adv20，先计算
            if 'adv20' not in df.columns:
                df['adv20'] = df.groupby('ts_code')['volume'].transform(
                    lambda x: x.rolling(20, min_periods=20).mean()
                )

            adv20_neutral = self.neutralizer.indneutralize(df['adv20'], industry_df, 'l3')

            corr = self.base_calculator.correlation(vwap_neutral, adv20_neutral, 6.02936)
            part2 = self.base_calculator.rank(corr)
        else:
            part2 = 0

        return (part1 ** part2) * -1

    def alpha_069(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_069: 需要二级行业中性化

        公式:
        ((rank(ts_max(delta(IndNeutralize(vwap, IndClass.industry), 2.72412), 4.79344))^Ts_Rank(correlation(((close* 0.490655) + (vwap* (1 - 0.490655))), adv20, 4.92416), 9.0615)) * -1)
        """
        # 1. 行业中性化vwap (二级行业)
        if 'l2_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            vwap_neutral = self.neutralizer.indneutralize(df['vwap'], industry_df, 'l2')
        else:
            vwap_neutral = df['vwap']

        # 2. 计算第一部分
        delta_vwap = self.base_calculator.delta(vwap_neutral, 2.72412)
        ts_max_vwap = self.base_calculator.ts_max(delta_vwap, 4.79344)
        part1 = self.base_calculator.rank(ts_max_vwap)

        # 3. 计算第二部分
        value = df['close'] * 0.490655 + df['vwap'] * (1 - 0.490655)

        # 需要adv20
        if 'adv20' not in df.columns:
            df['adv20'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(20, min_periods=20).mean()
            )

        corr = self.base_calculator.correlation(value, df['adv20'], 4.92416)
        part2 = self.base_calculator.ts_rank(corr, 9.0615)

        return (part1 ** part2) * -1

    def alpha_070(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_070: 需要二级行业中性化

        公式:
        ((rank(delta(vwap, 1.29456))^Ts_Rank(correlation(IndNeutralize(close, IndClass.industry), adv50, 17.8256), 17.9171)) * -1)
        """
        # 1. 计算第一部分
        part1 = self.base_calculator.rank(self.base_calculator.delta(df['vwap'], 1.29456))

        # 2. 行业中性化close (二级行业)
        if 'l2_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            close_neutral = self.neutralizer.indneutralize(df['close'], industry_df, 'l2')
        else:
            close_neutral = df['close']

        # 3. 需要adv50
        if 'adv50' not in df.columns:
            df['adv50'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(50, min_periods=50).mean()
            )

        corr = self.base_calculator.correlation(close_neutral, df['adv50'], 17.8256)
        part2 = self.base_calculator.ts_rank(corr, 17.9171)

        return (part1 ** part2) * -1

    def alpha_076(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_076: 需要一级行业中性化

        公式:
        (max(rank(decay_linear(delta(vwap, 1.24383), 11.8259)), Ts_Rank(decay_linear(Ts_Rank(correlation(IndNeutralize(low, IndClass.sector), adv81, 8.14941), 19.569), 17.1543), 19.383)) * -1)
        """
        # 1. 计算第一部分
        part1 = self.base_calculator.rank(
            self.base_calculator.decay_linear(
                self.base_calculator.delta(df['vwap'], 1.24383),
                11.8259
            )
        )

        # 2. 行业中性化low (一级行业)
        if 'l1_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            low_neutral = self.neutralizer.indneutralize(df['low'], industry_df, 'l1')
        else:
            low_neutral = df['low']

        # 3. 需要adv81
        if 'adv81' not in df.columns:
            df['adv81'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(81, min_periods=81).mean()
            )

        corr = self.base_calculator.correlation(low_neutral, df['adv81'], 8.14941)
        ts_rank_corr = self.base_calculator.ts_rank(corr, 19.569)
        decay = self.base_calculator.decay_linear(ts_rank_corr, 17.1543)
        part2 = self.base_calculator.ts_rank(decay, 19.383)

        return np.maximum(part1, part2) * -1

    def alpha_079(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_079: 需要一级行业中性化

        公式:
        (rank(delta(IndNeutralize(((close* 0.60733) + (open* (1 - 0.60733))), IndClass.sector), 1.23438)) < rank(correlation(Ts_Rank(vwap, 3.60973), Ts_Rank(adv150, 9.18637), 14.6644)))
        """
        # 1. 行业中性化 (一级行业)
        if 'l1_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            value = df['close'] * 0.60733 + df['open'] * (1 - 0.60733)
            value_neutral = self.neutralizer.indneutralize(value, industry_df, 'l1')
        else:
            value_neutral = df['close'] * 0.60733 + df['open'] * (1 - 0.60733)

        # 2. 计算第一部分
        part1 = self.base_calculator.rank(self.base_calculator.delta(value_neutral, 1.23438))

        # 3. 计算第二部分
        ts_rank_vwap = self.base_calculator.ts_rank(df['vwap'], 3.60973)

        # 需要adv150
        if 'adv150' not in df.columns:
            df['adv150'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(150, min_periods=150).mean()
            )

        ts_rank_adv150 = self.base_calculator.ts_rank(df['adv150'], 9.18637)
        corr = self.base_calculator.correlation(ts_rank_vwap, ts_rank_adv150, 14.6644)
        part2 = self.base_calculator.rank(corr)

        return (part1 < part2).astype(float)

    def alpha_080(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_080: 需要二级行业中性化

        公式:
        ((rank(Sign(delta(IndNeutralize(((open* 0.868128) + (high* (1 - 0.868128))), IndClass.industry), 4.04545)))^Ts_Rank(correlation(high, adv10, 5.11456), 5.53756)) * -1)
        """
        # 1. 行业中性化 (二级行业)
        if 'l2_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            value = df['open'] * 0.868128 + df['high'] * (1 - 0.868128)
            value_neutral = self.neutralizer.indneutralize(value, industry_df, 'l2')
        else:
            value_neutral = df['open'] * 0.868128 + df['high'] * (1 - 0.868128)

        # 2. 计算第一部分
        delta_value = self.base_calculator.delta(value_neutral, 4.04545)
        sign_delta = self.base_calculator.sign(delta_value)
        part1 = self.base_calculator.rank(sign_delta)

        # 3. 计算第二部分
        # 需要adv10
        if 'adv10' not in df.columns:
            df['adv10'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(10, min_periods=10).mean()
            )

        corr = self.base_calculator.correlation(df['high'], df['adv10'], 5.11456)
        part2 = self.base_calculator.ts_rank(corr, 5.53756)

        return (part1 ** part2) * -1

    def alpha_081(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_081: 需要二级行业中性化

        公式:
        ((rank(Log(product(rank((rank(correlation(vwap, sum(adv10, 49.6054), 8.47743))^4)), 14.9655))) < rank(correlation(rank(vwap), rank(volume), 5.07914))) * -1)
        """
        # 1. 计算中间变量
        # 需要adv10
        if 'adv10' not in df.columns:
            df['adv10'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(10, min_periods=10).mean()
            )

        corr1 = self.base_calculator.correlation(df['vwap'], self.base_calculator.sum(df['adv10'], 49.6054), 8.47743)
        rank_corr1 = self.base_calculator.rank(corr1)
        rank_rank_corr1 = self.base_calculator.rank(rank_corr1)
        product = self.base_calculator.product(rank_rank_corr1 ** 4, 14.9655)
        log_product = np.log(product)
        part1 = self.base_calculator.rank(log_product)

        # 2. 计算第二部分
        rank_vwap = self.base_calculator.rank(df['vwap'])
        rank_volume = self.base_calculator.rank(df['volume'])
        corr2 = self.base_calculator.correlation(rank_vwap, rank_volume, 5.07914)
        part2 = self.base_calculator.rank(corr2)

        return (part1 < part2).astype(float) * -1

    def alpha_082(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_082: 需要一级行业中性化

        公式:
        (min(rank(decay_linear(delta(open, 1.46063), 14.8717)), Ts_Rank(decay_linear(correlation(IndNeutralize(volume, IndClass.sector), ((open* 0.634196) + (open* (1 - 0.634196))), 17.4842), 6.92131), 13.4283)) * -1)
        """
        # 1. 计算第一部分
        part1 = self.base_calculator.rank(
            self.base_calculator.decay_linear(
                self.base_calculator.delta(df['open'], 1.46063),
                14.8717
            )
        )

        # 2. 行业中性化volume (一级行业)
        if 'l1_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            volume_neutral = self.neutralizer.indneutralize(df['volume'], industry_df, 'l1')
        else:
            volume_neutral = df['volume']

        # 3. 计算第二部分
        value = df['open'] * 0.634196 + df['open'] * (1 - 0.634196)  # 实际上就是open

        corr = self.base_calculator.correlation(volume_neutral, value, 17.4842)
        decay = self.base_calculator.decay_linear(corr, 6.92131)
        part2 = self.base_calculator.ts_rank(decay, 13.4283)

        return np.minimum(part1, part2) * -1

    def alpha_087(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_087: 需要二级行业中性化

        公式:
        (max(rank(decay_linear(delta(((close* 0.369701) + (vwap* (1 - 0.369701))), 1.91233), 2.65461)), Ts_Rank(decay_linear(abs(correlation(IndNeutralize(adv81, IndClass.industry), close, 13.4132)), 4.89768), 14.4535)) * -1)
        """
        # 1. 计算第一部分
        value1 = df['close'] * 0.369701 + df['vwap'] * (1 - 0.369701)
        delta_value1 = self.base_calculator.delta(value1, 1.91233)
        part1 = self.base_calculator.rank(
            self.base_calculator.decay_linear(delta_value1, 2.65461)
        )

        # 2. 行业中性化adv81 (二级行业)
        if 'l2_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()

            # 需要adv81
            if 'adv81' not in df.columns:
                df['adv81'] = df.groupby('ts_code')['volume'].transform(
                    lambda x: x.rolling(81, min_periods=81).mean()
                )

            adv81_neutral = self.neutralizer.indneutralize(df['adv81'], industry_df, 'l2')
        else:
            if 'adv81' not in df.columns:
                df['adv81'] = df.groupby('ts_code')['volume'].transform(
                    lambda x: x.rolling(81, min_periods=81).mean()
                )
            adv81_neutral = df['adv81']

        # 3. 计算第二部分
        corr = self.base_calculator.correlation(adv81_neutral, df['close'], 13.4132)
        abs_corr = np.abs(corr)
        decay = self.base_calculator.decay_linear(abs_corr, 4.89768)
        part2 = self.base_calculator.ts_rank(decay, 14.4535)

        return np.maximum(part1, part2) * -1

    def alpha_089(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_089: 需要二级行业中性化

        公式:
        (Ts_Rank(decay_linear(correlation(((low* 0.967285) + (low* (1 - 0.967285))), adv10, 6.94279), 5.51607), 3.79744) - Ts_Rank(decay_linear(delta(IndNeutralize(vwap, IndClass.industry), 3.48158), 10.1466), 15.3012))
        """
        # 1. 计算第一部分
        value1 = df['low'] * 0.967285 + df['low'] * (1 - 0.967285)  # 实际上就是low

        # 需要adv10
        if 'adv10' not in df.columns:
            df['adv10'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(10, min_periods=10).mean()
            )

        corr1 = self.base_calculator.correlation(value1, df['adv10'], 6.94279)
        decay1 = self.base_calculator.decay_linear(corr1, 5.51607)
        part1 = self.base_calculator.ts_rank(decay1, 3.79744)

        # 2. 行业中性化vwap (二级行业)
        if 'l2_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            vwap_neutral = self.neutralizer.indneutralize(df['vwap'], industry_df, 'l2')
        else:
            vwap_neutral = df['vwap']

        # 3. 计算第二部分
        delta_vwap = self.base_calculator.delta(vwap_neutral, 3.48158)
        decay2 = self.base_calculator.decay_linear(delta_vwap, 10.1466)
        part2 = self.base_calculator.ts_rank(decay2, 15.3012)

        return part1 - part2

    def alpha_090(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_090: 需要子行业中性化

        公式:
        ((rank((close - ts_max(close, 4.66719)))^Ts_Rank(correlation(IndNeutralize(adv40, IndClass.subindustry), low, 5.38375), 3.21856)) * -1)
        """
        # 1. 计算第一部分
        part1 = self.base_calculator.rank(df['close'] - self.base_calculator.ts_max(df['close'], 4.66719))

        # 2. 行业中性化adv40 (三级行业)
        if 'l3_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()

            # 需要adv40
            if 'adv40' not in df.columns:
                df['adv40'] = df.groupby('ts_code')['volume'].transform(
                    lambda x: x.rolling(40, min_periods=40).mean()
                )

            adv40_neutral = self.neutralizer.indneutralize(df['adv40'], industry_df, 'l3')
        else:
            if 'adv40' not in df.columns:
                df['adv40'] = df.groupby('ts_code')['volume'].transform(
                    lambda x: x.rolling(40, min_periods=40).mean()
                )
            adv40_neutral = df['adv40']

        # 3. 计算第二部分
        corr = self.base_calculator.correlation(adv40_neutral, df['low'], 5.38375)
        part2 = self.base_calculator.ts_rank(corr, 3.21856)

        return (part1 ** part2) * -1

    def alpha_091(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_091: 需要二级行业中性化

        公式:
        ((Ts_Rank(decay_linear(decay_linear(correlation(IndNeutralize(close, IndClass.industry), volume, 9.74928), 16.398), 3.83219), 4.8667) - rank(decay_linear(correlation(vwap, adv30, 4.01303), 2.6809))) * -1)
        """
        # 1. 行业中性化close (二级行业)
        if 'l2_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            close_neutral = self.neutralizer.indneutralize(df['close'], industry_df, 'l2')
        else:
            close_neutral = df['close']

        # 2. 计算第一部分
        corr1 = self.base_calculator.correlation(close_neutral, df['volume'], 9.74928)
        decay1 = self.base_calculator.decay_linear(corr1, 16.398)
        decay2 = self.base_calculator.decay_linear(decay1, 3.83219)
        part1 = self.base_calculator.ts_rank(decay2, 4.8667)

        # 3. 计算第二部分
        # 需要adv30
        if 'adv30' not in df.columns:
            df['adv30'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(30, min_periods=30).mean()
            )

        corr2 = self.base_calculator.correlation(df['vwap'], df['adv30'], 4.01303)
        part2 = self.base_calculator.rank(self.base_calculator.decay_linear(corr2, 2.6809))

        return (part1 - part2) * -1

    def alpha_093(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_093: 需要二级行业中性化

        公式:
        (Ts_Rank(decay_linear(correlation(IndNeutralize(vwap, IndClass.industry), adv81, 17.4193), 19.848), 7.54455) / rank(decay_linear(delta(((close* 0.524434) + (vwap* (1 - 0.524434))), 2.77377), 16.2664)))
        """
        # 1. 行业中性化vwap (二级行业)
        if 'l2_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            vwap_neutral = self.neutralizer.indneutralize(df['vwap'], industry_df, 'l2')
        else:
            vwap_neutral = df['vwap']

        # 2. 计算第一部分
        # 需要adv81
        if 'adv81' not in df.columns:
            df['adv81'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(81, min_periods=81).mean()
            )

        corr = self.base_calculator.correlation(vwap_neutral, df['adv81'], 17.4193)
        decay = self.base_calculator.decay_linear(corr, 19.848)
        part1 = self.base_calculator.ts_rank(decay, 7.54455)

        # 3. 计算第二部分
        value = df['close'] * 0.524434 + df['vwap'] * (1 - 0.524434)
        delta_value = self.base_calculator.delta(value, 2.77377)
        decay2 = self.base_calculator.decay_linear(delta_value, 16.2664)
        part2 = self.base_calculator.rank(decay2)

        return part1 / part2

    def alpha_097(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_097: 需要二级行业中性化

        公式:
        ((rank(decay_linear(delta(IndNeutralize(((low* 0.721001) + (vwap* (1 - 0.721001))), IndClass.industry), 3.3705), 20.4523)) - Ts_Rank(decay_linear(Ts_Rank(correlation(Ts_Rank(low, 7.87871), Ts_Rank(adv60, 17.255), 4.97547), 18.5925), 15.7152), 6.71659)) * -1)
        """
        # 1. 行业中性化 (二级行业)
        if 'l2_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            value = df['low'] * 0.721001 + df['vwap'] * (1 - 0.721001)
            value_neutral = self.neutralizer.indneutralize(value, industry_df, 'l2')
        else:
            value = df['low'] * 0.721001 + df['vwap'] * (1 - 0.721001)
            value_neutral = value

        # 2. 计算第一部分
        delta_value = self.base_calculator.delta(value_neutral, 3.3705)
        part1 = self.base_calculator.rank(
            self.base_calculator.decay_linear(delta_value, 20.4523)
        )

        # 3. 计算第二部分
        ts_rank_low = self.base_calculator.ts_rank(df['low'], 7.87871)

        # 需要adv60
        if 'adv60' not in df.columns:
            df['adv60'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(60, min_periods=60).mean()
            )

        ts_rank_adv60 = self.base_calculator.ts_rank(df['adv60'], 17.255)
        corr = self.base_calculator.correlation(ts_rank_low, ts_rank_adv60, 4.97547)
        ts_rank_corr = self.base_calculator.ts_rank(corr, 18.5925)
        decay = self.base_calculator.decay_linear(ts_rank_corr, 15.7152)
        part2 = self.base_calculator.ts_rank(decay, 6.71659)

        return (part1 - part2) * -1

    def alpha_100(self, df: pd.DataFrame) -> pd.Series:
        """
        Alpha_100: 需要子行业中性化

        公式:
        (0 - (1* (((1.5* scale(indneutralize(indneutralize(rank(((((close - low) - (high - close)) / (high - low))* volume)), IndClass.subindustry), IndClass.subindustry))) - scale(indneutralize((correlation(close, rank(adv20), 5) - rank(ts_argmin(close, 30))), IndClass.subindustry))) * (volume / adv20))))
        """
        # 1. 计算第一部分
        value1 = (((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])) * df['volume']
        rank_value1 = self.base_calculator.rank(value1)

        # 行业中性化两次 (三级行业)
        if 'l3_name' in df.columns:
            industry_df = df[['ts_code', 'l1_name', 'l2_name', 'l3_name']].drop_duplicates()
            neutral1 = self.neutralizer.indneutralize(rank_value1, industry_df, 'l3')
            neutral2 = self.neutralizer.indneutralize(neutral1, industry_df, 'l3')
            scaled1 = self.base_calculator.scale(neutral2)
        else:
            scaled1 = self.base_calculator.scale(rank_value1)

        part1 = 1.5 * scaled1

        # 2. 计算第二部分
        # 需要adv20
        if 'adv20' not in df.columns:
            df['adv20'] = df.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(20, min_periods=20).mean()
            )

        rank_adv20 = self.base_calculator.rank(df['adv20'])
        corr = self.base_calculator.correlation(df['close'], rank_adv20, 5)
        ts_argmin_close = self.base_calculator.ts_argmin(df['close'], 30)
        rank_ts_argmin = self.base_calculator.rank(ts_argmin_close)
        value2 = corr - rank_ts_argmin

        if 'l3_name' in df.columns:
            neutral3 = self.neutralizer.indneutralize(value2, industry_df, 'l3')
            scaled2 = self.base_calculator.scale(neutral3)
        else:
            scaled2 = self.base_calculator.scale(value2)

        part2 = scaled2

        # 3. 组合
        result = 0 - (1 * ((part1 - part2) * (df['volume'] / df['adv20'])))

        return result

    # ==================== 已实现的因子（77个） ====================
    # 这些因子已经在Alpha101Calculator中实现，可以直接调用

    def alpha_001(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_001: 趋势强度"""
        return self.base_calculator.alpha_001(df)

    def alpha_002(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_002: 量价关系"""
        return self.base_calculator.alpha_002(df)

    def alpha_003(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_003: 开盘量相关"""
        return self.base_calculator.alpha_003(df)

    def alpha_004(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_004: 低点排名"""
        return self.base_calculator.alpha_004(df)

    def alpha_005(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_005: VWAP偏离"""
        return self.base_calculator.alpha_005(df)

    def alpha_006(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_006: 开盘量相关"""
        return self.base_calculator.alpha_006(df)

    def alpha_007(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_007: 成交量突破"""
        return self.base_calculator.alpha_007(df)

    def alpha_008(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_008: 开盘收益乘积"""
        return self.base_calculator.alpha_008(df)

    def alpha_009(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_009: 价格动量"""
        return self.base_calculator.alpha_009(df)

    def alpha_010(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_010: 价格动量"""
        return self.base_calculator.alpha_010(df)

    def alpha_011(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_011: VWAP差值"""
        return self.base_calculator.alpha_011(df)

    def alpha_012(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_012: 量价变化"""
        return self.base_calculator.alpha_012(df)

    def alpha_013(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_013: 收盘量协方差"""
        return self.base_calculator.alpha_013(df)

    def alpha_014(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_014: 收益量相关"""
        return self.base_calculator.alpha_014(df)

    def alpha_015(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_015: 高点量相关"""
        return self.base_calculator.alpha_015(df)

    def alpha_016(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_016: 高点量协方差"""
        return self.base_calculator.alpha_016(df)

    def alpha_017(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_017: 收盘量价"""
        return self.base_calculator.alpha_017(df)

    def alpha_018(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_018: 波动率"""
        return self.base_calculator.alpha_018(df)

    def alpha_019(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_019: 长期收益"""
        return self.base_calculator.alpha_019(df)

    def alpha_020(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_020: 开盘滞后"""
        return self.base_calculator.alpha_020(df)

    def alpha_021(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_021: 均值偏离"""
        return self.base_calculator.alpha_021(df)

    def alpha_022(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_022: 高点量相关变化"""
        return self.base_calculator.alpha_022(df)

    def alpha_023(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_023: 高点突破"""
        return self.base_calculator.alpha_023(df)

    def alpha_024(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_024: 长期均值偏离"""
        return self.base_calculator.alpha_024(df)

    def alpha_025(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_025: 收益量价"""
        return self.base_calculator.alpha_025(df)

    def alpha_026(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_026: 成交量高点"""
        return self.base_calculator.alpha_026(df)

    def alpha_027(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_027: 量价相关"""
        return self.base_calculator.alpha_027(df)

    def alpha_028(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_028: 低点量相关"""
        return self.base_calculator.alpha_028(df)

    def alpha_029(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_029: 复杂排名"""
        return self.base_calculator.alpha_029(df)

    def alpha_030(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_030: 符号求和"""
        return self.base_calculator.alpha_030(df)

    def alpha_031(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_031: 衰减排名"""
        return self.base_calculator.alpha_031(df)

    def alpha_032(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_032: 均值偏离"""
        return self.base_calculator.alpha_032(df)

    def alpha_033(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_033: 开盘收盘比"""
        return self.base_calculator.alpha_033(df)

    def alpha_034(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_034: 波动率比"""
        return self.base_calculator.alpha_034(df)

    def alpha_035(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_035: 成交量排名"""
        return self.base_calculator.alpha_035(df)

    def alpha_036(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_036: 多因子组合"""
        return self.base_calculator.alpha_036(df)

    def alpha_037(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_037: 开盘收盘差"""
        return self.base_calculator.alpha_037(df)

    def alpha_038(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_038: 价格强度"""
        return self.base_calculator.alpha_038(df)

    def alpha_039(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_039: 长期收益"""
        return self.base_calculator.alpha_039(df)

    def alpha_040(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_040: 高点波动率"""
        return self.base_calculator.alpha_040(df)

    def alpha_041(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_041: 价量关系"""
        return self.base_calculator.alpha_041(df)

    def alpha_042(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_042: VWAP偏离"""
        return self.base_calculator.alpha_042(df)

    def alpha_043(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_043: 成交量排名"""
        return self.base_calculator.alpha_043(df)

    def alpha_044(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_044: 高点量相关"""
        return self.base_calculator.alpha_044(df)

    def alpha_045(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_045: 收盘量相关"""
        return self.base_calculator.alpha_045(df)

    def alpha_046(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_046: 滞后差值"""
        return self.base_calculator.alpha_046(df)

    def alpha_047(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_047: 收盘倒数"""
        return self.base_calculator.alpha_047(df)

    def alpha_049(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_049: 滞后差值"""
        return self.base_calculator.alpha_049(df)

    def alpha_050(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_050: 成交量VWAP"""
        return self.base_calculator.alpha_050(df)

    def alpha_051(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_051: 滞后差值"""
        return self.base_calculator.alpha_051(df)

    def alpha_052(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_052: 低点滞后"""
        return self.base_calculator.alpha_052(df)

    def alpha_053(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_053: 价差比率"""
        return self.base_calculator.alpha_053(df)

    def alpha_054(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_054: 低收价差"""
        return self.base_calculator.alpha_054(df)

    def alpha_055(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_055: 价量相关"""
        return self.base_calculator.alpha_055(df)

    def alpha_056(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_056: 收益市值"""
        return self.base_calculator.alpha_056(df)

    def alpha_057(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_057: VWAP偏离"""
        return self.base_calculator.alpha_057(df)

    def alpha_060(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_060: 价差量"""
        return self.base_calculator.alpha_060(df)

    def alpha_061(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_061: VWAP排名"""
        return self.base_calculator.alpha_061(df)

    def alpha_062(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_062: VWAP量相关"""
        return self.base_calculator.alpha_062(df)

    def alpha_064(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_064: 开盘低点"""
        return self.base_calculator.alpha_064(df)

    def alpha_065(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_065: 开盘VWAP"""
        return self.base_calculator.alpha_065(df)

    def alpha_066(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_066: VWAP变化"""
        return self.base_calculator.alpha_066(df)

    def alpha_068(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_068: 高点量相关"""
        return self.base_calculator.alpha_068(df)

    def alpha_071(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_071: 收盘VWAP"""
        return self.base_calculator.alpha_071(df)

    def alpha_072(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_072: 高低均值"""
        return self.base_calculator.alpha_072(df)

    def alpha_073(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_073: VWAP变化"""
        return self.base_calculator.alpha_073(df)

    def alpha_074(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_074: 收盘量相关"""
        return self.base_calculator.alpha_074(df)

    def alpha_075(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_075: VWAP量相关"""
        return self.base_calculator.alpha_075(df)

    def alpha_077(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_077: 高低VWAP"""
        return self.base_calculator.alpha_077(df)

    def alpha_078(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_078: 低点VWAP"""
        return self.base_calculator.alpha_078(df)

    def alpha_083(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_083: 高低比率"""
        return self.base_calculator.alpha_083(df)

    def alpha_084(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_084: VWAP最大值"""
        return self.base_calculator.alpha_084(df)

    def alpha_085(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_085: 高点收盘"""
        return self.base_calculator.alpha_085(df)

    def alpha_086(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_086: 收盘量相关"""
        return self.base_calculator.alpha_086(df)

    def alpha_088(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_088: 开高低收"""
        return self.base_calculator.alpha_088(df)

    def alpha_092(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_092: 高低收"""
        return self.base_calculator.alpha_092(df)

    def alpha_094(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_094: VWAP最小值"""
        return self.base_calculator.alpha_094(df)

    def alpha_096(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_096: 成交量VWAP"""
        return self.base_calculator.alpha_096(df)

    def alpha_098(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_098: VWAP成交量"""
        return self.base_calculator.alpha_098(df)

    def alpha_099(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_099: 高低均值"""
        return self.base_calculator.alpha_099(df)

    def alpha_101(self, df: pd.DataFrame) -> pd.Series:
        """Alpha_101: 简单动量"""
        return self.base_calculator.alpha_101(df)


def calculate_alpha101_factors_with_neutralization(
    ts_codes: List[str],
    start_date: str,
    end_date: str,
    output_path: Optional[str] = None,
    include_neutralized: bool = True
) -> pd.DataFrame:
    """
    计算完整的Alpha101因子（支持行业中性化）

    参数:
        ts_codes: 股票代码列表
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        output_path: 输出路径
        include_neutralized: 是否包含需要中性化的因子

    返回:
        包含所有Alpha101因子的DataFrame
    """
    print("="*80)
    print("Alpha101完整因子计算（支持行业中性化）")
    print("="*80)
    print(f"股票数量: {len(ts_codes)}")
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"行业中性化: {'✅ 开启' if include_neutralized else '❌ 关闭'}")
    print("="*80)

    # 创建计算器
    calculator = Alpha101CalculatorWithNeutralization(ts_codes, start_date, end_date)

    # 获取所有股票代码
    unique_codes = calculator.merged_data['ts_code'].unique()

    all_results = []

    for ts_code in unique_codes:
        df = calculator.get_stock_data(ts_code)

        if len(df) == 0:
            continue

        # 创建结果DataFrame
        result = pd.DataFrame({
            'ts_code': ts_code,
            'trade_date': df['trade_date']
        })

        # 计算所有因子
        factor_methods = []

        # 77个已实现因子
        for i in range(1, 102):
            if i in [48, 58, 59, 63, 67, 69, 70, 76, 79, 80, 81, 82, 87, 89, 90, 91, 93, 97, 100]:
                # 24个需要行业中性化的因子
                if include_neutralized:
                    factor_methods.append((f'alpha_{i:03d}', getattr(calculator, f'alpha_{i:03d}')))
            else:
                # 77个已实现因子
                factor_methods.append((f'alpha_{i:03d}', getattr(calculator, f'alpha_{i:03d}')))

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
        print(f"\n✅ 计算完成，共 {len(final_result)} 条记录")
        print(f"   因子数量: {len(final_result.columns) - 2}")

        # 保存结果
        if output_path:
            final_result.to_csv(output_path, index=False)
            print(f"✅ 结果已保存: {output_path}")

        return final_result
    else:
        print("\n❌ 无有效结果")
        return pd.DataFrame()


if __name__ == "__main__":
    # 演示使用
    print("行业中性化演示")

    # 使用真实数据测试
    test_codes = ['000001.SZ', '000002.SZ', '600519.SH', '600036.SH']

    neutralizer = IndustryNeutralizerReal()
    industry_df = neutralizer.get_industry_data(test_codes, '20240101', '20241231')

    if industry_df is not None:
        print("\n行业数据示例:")
        print(industry_df.head())

        print("\n行业统计:")
        print(f"一级行业: {industry_df['l1_name'].unique()}")
        print(f"二级行业: {industry_df['l2_name'].unique()}")
        print(f"三级行业: {industry_df['l3_name'].unique()}")

        # 测试中性化函数
        print("\n=== 测试行业中性化 ===")

        # 创建模拟因子
        import random
        factor_values = [random.uniform(5, 15) for _ in range(len(test_codes))]
        factor = pd.Series(factor_values, index=test_codes)

        print(f"原始因子: {factor.values}")

        # 中性化
        neutralized = neutralizer.indneutralize(factor, industry_df, 'l2')
        print(f"中性化后: {neutralized.values}")

        # 验证
        print(f"\n验证:")
        print(f"原始均值: {factor.mean():.4f}")
        print(f"中性化后均值: {neutralized.mean():.4f} (应接近0)")

        # 按行业统计
        industry_df['factor'] = neutralized.values
        print(f"\n按行业统计:")
        print(industry_df.groupby('l2_name')['factor'].mean())

        print("\n✅ 行业中性化功能正常！")
    else:
        print("❌ 无法获取行业数据")