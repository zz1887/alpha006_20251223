"""
回测规则 - 分行业排名选股 - backtest/rules/industry_rank_rule.py

功能:
- 分行业排名选股规则
- 每行业选择前N名个股
- T+20持有策略

策略规则:
    1. 分行业计算alpha_peg因子
    2. 每行业按因子值排序
    3. 选择每行业前N名
    4. T日等权重买入
    5. 持有M天后卖出
"""

import pandas as pd
from typing import Optional, Dict, Any
from core.utils.data_loader import load_industry_data, get_price_data, get_index_data
from core.utils.data_processor import calculate_alpha_peg_factor
from backtest.engine.backtest_engine import T20BacktestEngine, compare_with_benchmark, calculate_benchmark_performance


class IndustryRankRule:
    """分行业排名选股规则"""

    def __init__(self,
                 top_n: int = 3,
                 holding_days: int = 20,
                 outlier_sigma: float = 3.0,
                 normalization: Optional[str] = None):
        """
        初始化选股规则

        Args:
            top_n: 每行业选股数量
            holding_days: 持有天数
            outlier_sigma: 异常值阈值
            normalization: 标准化方法
        """
        self.top_n = top_n
        self.holding_days = holding_days
        self.outlier_sigma = outlier_sigma
        self.normalization = normalization

    def select_stocks(self,
                      df_pe: pd.DataFrame,
                      df_fina: pd.DataFrame,
                      df_industry: pd.DataFrame) -> pd.DataFrame:
        """
        选股逻辑

        Args:
            df_pe: PE数据
            df_fina: 财务数据
            df_industry: 行业数据

        Returns:
            选股DataFrame
        """
        # 计算因子
        factor_df = calculate_alpha_peg_factor(
            df_pe=df_pe,
            df_fina=df_fina,
            df_industry=df_industry,
            outlier_sigma=self.outlier_sigma,
            normalization=self.normalization,
            industry_specific=True
        )

        if len(factor_df) == 0:
            return pd.DataFrame()

        # 每行业选择前N名
        selected = []
        for (trade_date, industry), group in factor_df.groupby(['trade_date', 'l1_name']):
            top_n_stocks = group.nsmallest(self.top_n, 'alpha_peg')[
                ['ts_code', 'trade_date', 'l1_name', 'alpha_peg', 'industry_rank']
            ]
            selected.append(top_n_stocks)

        df_selected = pd.concat(selected, ignore_index=True)
        return df_selected

    def run_backtest(self,
                     start_date: str,
                     end_date: str,
                     industry_path: Optional[str] = None,
                     initial_capital: float = 1000000.0) -> dict:
        """
        运行完整回测

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            industry_path: 行业数据路径
            initial_capital: 初始资金

        Returns:
            回测结果
        """
        print("\n" + "="*80)
        print("分行业排名选股规则回测")
        print("="*80)
        print(f"参数: 每行业前{self.top_n}名, 持有{self.holding_days}天")
        print(f"时间: {start_date} ~ {end_date}")
        print(f"初始资金: {initial_capital:,.0f}")
        print("="*80)

        from core.utils.db_connection import db
        from core.constants.config import TABLE_DAILY_BASIC, TABLE_FINA_INDICATOR

        # 1. 获取数据
        print("\n【步骤1】获取数据...")

        # PE数据
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

        # 财务数据
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

        # 行业数据
        df_industry = load_industry_data(industry_path)

        # 价格数据
        price_df = get_price_data(start_date, end_date)

        # 基准数据
        index_df = get_index_data(start_date, end_date)

        # 2. 选股
        print("\n【步骤2】选股...")
        selected_df = self.select_stocks(df_pe, df_fina, df_industry)

        if len(selected_df) == 0:
            print("❌ 选股失败")
            return {}

        print(f"✓ 选中: {len(selected_df):,} 条")

        # 3. 运行回测
        print("\n【步骤3】运行回测...")
        engine = T20BacktestEngine(
            initial_capital=initial_capital,
            holding_days=self.holding_days
        )

        results = engine.run_backtest(selected_df, price_df, start_date, end_date)

        # 4. 对比基准
        if len(index_df) > 0:
            benchmark_nav = calculate_benchmark_performance(index_df, initial_capital)
            results['benchmark'] = benchmark_nav

            excess_results = compare_with_benchmark(results, benchmark_nav)
            if excess_results:
                results['excess_summary'] = {
                    'excess_return': excess_results['excess_return'],
                    'excess_win_rate': excess_results['excess_win_rate']
                }

        # 5. 保存结果
        print("\n【步骤4】保存结果...")
        self._save_results(results, start_date, end_date)

        return results

    def _save_results(self, results: Dict[str, Any], start_date: str, end_date: str):
        """保存回测结果"""
        import os
        from datetime import datetime
        from core.constants.config import PATH_CONFIG

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = PATH_CONFIG['results_backtest']

        # 保存每日净值
        if len(results['daily_nav']) > 0:
            nav_file = f"nav_t{self.holding_days}_{start_date}_{end_date}_{timestamp}.csv"
            nav_path = os.path.join(output_dir, nav_file)
            results['daily_nav'].to_csv(nav_path, index=False)
            print(f"✓ 每日净值: {nav_path}")

        # 保存交易记录
        if len(results['trade_records']) > 0:
            trade_file = f"trades_t{self.holding_days}_{start_date}_{end_date}_{timestamp}.csv"
            trade_path = os.path.join(output_dir, trade_file)
            results['trade_records'].to_csv(trade_path, index=False)
            print(f"✓ 交易记录: {trade_path}")

        # 保存绩效汇总
        summary_file = f"summary_t{self.holding_days}_{start_date}_{end_date}_{timestamp}.txt"
        summary_path = os.path.join(output_dir, summary_file)
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"alpha_peg T+{self.holding_days}策略回测总结\n")
            f.write(f"时间范围: {start_date} ~ {end_date}\n")
            f.write(f"回测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("绩效指标:\n")
            for key, value in results['summary'].items():
                if isinstance(value, float):
                    f.write(f"  {key}: {value:.6f}\n")
                else:
                    f.write(f"  {key}: {value}\n")
            if 'excess_summary' in results:
                f.write("\n超额收益:\n")
                for key, value in results['excess_summary'].items():
                    f.write(f"  {key}: {value:.4f}\n")
        print(f"✓ 绩效汇总: {summary_path}")


# ==================== 预设策略配置 ====================
STRATEGY_PRESETS = {
    't20_standard': {
        'name': 'T+20标准策略',
        'top_n': 3,
        'holding_days': 20,
        'outlier_sigma': 3.0,
        'normalization': None,
        'description': '每行业前3名，持有20天'
    },
    't10_short': {
        'name': 'T+10短线策略',
        'top_n': 3,
        'holding_days': 10,
        'outlier_sigma': 3.0,
        'normalization': None,
        'description': '每行业前3名，持有10天'
    },
    't5_quick': {
        'name': 'T+5快线策略',
        'top_n': 3,
        'holding_days': 5,
        'outlier_sigma': 3.0,
        'normalization': None,
        'description': '每行业前3名，持有5天'
    },
    't30_long': {
        'name': 'T+30长线策略',
        'top_n': 3,
        'holding_days': 30,
        'outlier_sigma': 3.0,
        'normalization': None,
        'description': '每行业前3名，持有30天'
    },
    'conservative': {
        'name': '保守策略',
        'top_n': 2,
        'holding_days': 20,
        'outlier_sigma': 2.5,
        'normalization': None,
        'description': '每行业前2名，严格筛选，持有20天'
    },
    'aggressive': {
        'name': '激进策略',
        'top_n': 5,
        'holding_days': 20,
        'outlier_sigma': 3.5,
        'normalization': None,
        'description': '每行业前5名，宽松筛选，持有20天'
    },
}


def create_strategy(preset_name: str = 't20_standard') -> IndustryRankRule:
    """
    创建预设策略

    Args:
        preset_name: 预设策略名称

    Returns:
        IndustryRankRule实例
    """
    if preset_name not in STRATEGY_PRESETS:
        raise ValueError(f"未知预设: {preset_name}, 可用: {list(STRATEGY_PRESETS.keys())}")

    config = STRATEGY_PRESETS[preset_name]
    print(f"\n创建策略: {config['name']}")
    print(f"描述: {config['description']}")

    return IndustryRankRule(
        top_n=config['top_n'],
        holding_days=config['holding_days'],
        outlier_sigma=config['outlier_sigma'],
        normalization=config['normalization']
    )
