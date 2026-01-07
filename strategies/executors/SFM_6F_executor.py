"""
六因子策略执行器

负责六因子策略的具体执行逻辑
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
sys.path.insert(0, '/home/zcy/alpha006_20251223')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    # 尝试导入新路径的配置
    from strategies.configs.SFM_6F_M_V1 import get_strategy_config
except ImportError:
    # 回退到旧路径
    from config.strategies.six_factor_monthly import get_strategy_config

# 导入核心模块
from core.utils.data_loader import data_loader
from core.utils.db_connection import db
from core.config.params import get_strategy_param, get_factor_param

# 导入因子计算函数
try:
    from factors.price.PRI_TREND_4D_V2 import create_factor as create_alpha_010
    from factors.price.PRI_STR_10D_V2 import create_factor as create_alpha_038
    from factors.price.PRI_POS_120D_V2 import create_factor as create_alpha_120cq
    from factors.momentum.VOL_EXP_20D_V2 import create_factor as create_alpha_pluse
    from factors.valuation.VAL_GROW_行业_Q import calc_alpha_peg_industry as create_alpha_peg
    from factors.volume.MOM_CR_20D_V2 import create_factor as create_cr_qfq
    logger.info("✅ 所有因子模块导入成功")
except ImportError as e:
    # 如果新路径不存在，尝试旧路径
    logger.warning(f"导入新路径因子失败: {e}，尝试旧路径")
    try:
        from code.factor_v1 import calculate_alpha006_factor_v1 as create_alpha_010
        from code.factor_v3 import calculate_alpha006_factor_v3 as create_alpha_038
        from code.calc_alpha_peg_industry import calc_alpha_peg_industry as create_alpha_peg
        from code.alpha_120cq import create_factor as create_alpha_120cq
        from code.alpha_pluse import create_factor as create_alpha_pluse
        from code.cr_qfq import create_factor as create_cr_qfq
        logger.info("✅ 旧路径因子模块导入成功")
    except ImportError as e2:
        logger.error(f"因子导入失败: {e2}")
        raise


def execute(start_date: str, end_date: str, version: str = 'standard', **kwargs) -> bool:
    """
    执行六因子策略回测

    Args:
        start_date: 开始日期
        end_date: 结束日期
        version: 策略版本
        **kwargs: 其他参数

    Returns:
        是否成功
    """
    try:
        logger.info(f"开始执行六因子策略: {start_date} ~ {end_date}, 版本: {version}")

        # 1. 加载配置
        config = get_strategy_config()
        params = config['factors']

        # 2. 获取交易日期
        trading_days = data_loader.get_trading_days(start_date, end_date)
        if not trading_days:
            logger.error("无有效交易数据")
            return False

        logger.info(f"获取交易日: {len(trading_days)}天")

        # 3. 月末调仓日期
        rebalance_dates = get_monthly_rebalance_dates(trading_days)
        logger.info(f"调仓日期: {len(rebalance_dates)}次")

        # 4. 运行回测
        results = run_backtest(rebalance_dates, params, config)

        # 5. 保存结果
        save_results(results, start_date, end_date, version)

        logger.info("六因子策略执行完成")
        return True

    except Exception as e:
        logger.error(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_monthly_rebalance_dates(trading_days: List[str]) -> List[str]:
    """
    获取月末调仓日期

    逻辑:
    1. 找到每个月的最后一天
    2. 如果最后一天是交易日，直接使用
    3. 否则找到最近的交易日
    """
    if not trading_days:
        return []

    # 转换为datetime
    dates = [datetime.strptime(d, '%Y%m%d') for d in trading_days]

    rebalance_dates = []
    current_month = None

    for date in dates:
        month_key = (date.year, date.month)

        if month_key != current_month:
            # 新月份，找到上个月的调仓日
            if current_month is not None:
                # 找到上个月最后一天的交易日
                last_day = date.replace(day=1) - timedelta(days=1)  # 上个月最后一天
                nearest = find_nearest_trading_day(last_day, dates)
                if nearest:
                    rebalance_dates.append(nearest.strftime('%Y%m%d'))

            current_month = month_key

    # 处理最后一个月份
    if dates:
        last_date = dates[-1]
        last_day = last_date.replace(day=1) + timedelta(days=32)
        last_day = last_day.replace(day=1) - timedelta(days=1)
        nearest = find_nearest_trading_day(last_day, dates)
        if nearest:
            rebalance_dates.append(nearest.strftime('%Y%m%d'))

    return sorted(set(rebalance_dates))


def find_nearest_trading_day(target_date: datetime, trading_dates: List[datetime]) -> Optional[datetime]:
    """找到最近的交易日"""
    if target_date in trading_dates:
        return target_date

    # 查找前后交易日
    prev_dates = [d for d in trading_dates if d < target_date]
    next_dates = [d for d in trading_dates if d > target_date]

    if prev_dates and next_dates:
        prev = prev_dates[-1]
        next = next_dates[0]

        prev_dist = (target_date - prev).days
        next_dist = (next - target_date).days

        return prev if prev_dist <= next_dist else next
    elif prev_dates:
        return prev_dates[-1]
    elif next_dates:
        return next_dates[0]
    else:
        return None


def run_backtest(rebalance_dates: List[str], params: Dict, config: Dict) -> Dict[str, Any]:
    """
    运行回测核心逻辑

    Args:
        rebalance_dates: 调仓日期列表
        params: 因子参数
        config: 策略配置

    Returns:
        回测结果
    """
    results = {
        'dates': [],
        'group_returns': {},
        'metrics': {},
        'trades': []
    }

    # 初始化
    for i in range(1, 6):
        results['group_returns'][f'group_{i}'] = []

    # 逐期回测
    for i, rebalance_date in enumerate(rebalance_dates):
        if i == len(rebalance_dates) - 1:
            break

        start_date = rebalance_date
        end_date = rebalance_dates[i + 1]

        logger.info(f"回测期间: {start_date} ~ {end_date}")

        # 计算因子
        factor_data = calculate_factors(start_date, params)

        # 选股分组
        groups = select_stocks_by_groups(factor_data, config)

        # 计算收益
        returns = calculate_period_returns(groups, start_date, end_date)

        # 记录结果
        results['dates'].append(end_date)
        for group_name, group_return in returns.items():
            results['group_returns'][group_name].append(group_return)

    # 计算性能指标
    results['metrics'] = calculate_metrics(results, config)

    return results


def calculate_factors(date: str, params: Dict) -> pd.DataFrame:
    """
    计算所有因子

    Args:
        date: 计算日期
        params: 因子参数

    Returns:
        因子数据框
    """
    logger.info(f"计算因子: {date}")

    # 获取可交易股票
    stocks = data_loader.get_tradable_stocks(date)

    # 计算各因子（简化版，实际应调用具体因子函数）
    factor_data = pd.DataFrame({'ts_code': stocks})

    # 这里应该调用实际的因子计算函数
    # 为简化，这里返回占位符

    return factor_data


def select_stocks_by_groups(factor_data: pd.DataFrame, config: Dict) -> Dict[str, List[str]]:
    """
    按因子得分分组选股

    Args:
        factor_data: 因子数据
        config: 配置

    Returns:
        各组股票列表
    """
    # 计算综合得分
    factor_data['score'] = factor_data['ts_code'].hash()  # 占位符

    # 分组
    n_groups = 5
    factor_data['group'] = pd.qcut(factor_data['score'], n_groups, labels=False) + 1

    groups = {}
    for i in range(1, n_groups + 1):
        group_stocks = factor_data[factor_data['group'] == i]['ts_code'].tolist()
        groups[f'group_{i}'] = group_stocks

    return groups


def calculate_period_returns(groups: Dict[str, List[str]], start_date: str, end_date: str) -> Dict[str, float]:
    """
    计算期间收益

    Args:
        groups: 分组股票
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        各组收益
    """
    returns = {}

    for group_name, stocks in groups.items():
        if not stocks:
            returns[group_name] = 0.0
            continue

        # 获取价格数据
        price_data = data_loader.get_price_data(stocks, start_date, end_date)

        if price_data.empty:
            returns[group_name] = 0.0
            continue

        # 计算等权收益
        start_prices = price_data.groupby('ts_code')['close'].first()
        end_prices = price_data.groupby('ts_code')['close'].last()

        individual_returns = (end_prices - start_prices) / start_prices
        returns[group_name] = individual_returns.mean()

    return returns


def calculate_metrics(results: Dict, config: Dict) -> Dict[str, float]:
    """
    计算性能指标

    Args:
        results: 回测结果
        config: 配置

    Returns:
        性能指标
    """
    metrics = {}

    # 计算各组指标
    for group_name, returns in results['group_returns'].items():
        if returns:
            returns_array = np.array(returns)
            metrics[f'{group_name}_cumulative'] = (1 + returns_array).prod() - 1
            metrics[f'{group_name}_annual'] = ((1 + metrics[f'{group_name}_cumulative']) ** (12/len(returns))) - 1
            metrics[f'{group_name}_sharpe'] = np.mean(returns_array) / np.std(returns_array) * np.sqrt(12) if np.std(returns_array) > 0 else 0

    # 多空组合
    if 'group_1' in results['group_returns'] and 'group_5' in results['group_returns']:
        group1 = np.array(results['group_returns']['group_1'])
        group5 = np.array(results['group_returns']['group_5'])
        long_short = group1 - group5
        metrics['long_short_cumulative'] = (1 + long_short).prod() - 1
        metrics['long_short_sharpe'] = np.mean(long_short) / np.std(long_short) * np.sqrt(12) if np.std(long_short) > 0 else 0

    return metrics


def save_results(results: Dict, start_date: str, end_date: str, version: str):
    """
    保存结果

    Args:
        results: 回测结果
        start_date: 开始日期
        end_date: 结束日期
        version: 版本
    """
    import pandas as pd

    # 创建输出目录
    output_dir = f"/home/zcy/alpha006_20251223/results/strategies/six_factor_{start_date}_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)

    # 保存收益数据
    returns_df = pd.DataFrame({
        'date': results['dates'],
        **{k: v for k, v in results['group_returns'].items()}
    })
    returns_df.to_csv(f"{output_dir}/returns.csv", index=False)

    # 保存指标
    metrics_df = pd.DataFrame([results['metrics']])
    metrics_df.to_csv(f"{output_dir}/metrics.csv", index=False)

    logger.info(f"结果保存至: {output_dir}")

    # 打印关键指标
    print("\n" + "="*60)
    print("回测结果摘要")
    print("="*60)
    for key, value in results['metrics'].items():
        if 'cumulative' in key or 'sharpe' in key:
            print(f"{key}: {value:.4f}")
    print("="*60)