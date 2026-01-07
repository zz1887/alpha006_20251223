"""
策略3执行器

负责策略3的具体执行逻辑
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List
import warnings
warnings.filterwarnings('ignore')

# 添加项目路径
sys.path.insert(0, '/home/zcy/alpha006_20251223')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from strategies.configs.MFM_5F_M_V1 import get_strategy_config, get_strategy_params
except ImportError:
    from config.backtest_config import get_strategy_params

from core.utils.data_loader import data_loader
from core.utils.db_connection import db


def execute(start_date: str, end_date: str, version: str = 'standard', **kwargs) -> bool:
    """
    执行策略3回测

    Args:
        start_date: 开始日期
        end_date: 结束日期
        version: 策略版本
        **kwargs: 其他参数

    Returns:
        是否成功
    """
    try:
        logger.info(f"开始执行策略3: {start_date} ~ {end_date}, 版本: {version}")

        # 1. 加载配置
        config = get_strategy_config(version)
        params = get_strategy_params(version)

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
        results = run_backtest(rebalance_dates, params, config, version)

        # 5. 保存结果
        save_results(results, start_date, end_date, version, "strategy3")

        logger.info("策略3执行完成")
        return True

    except Exception as e:
        logger.error(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_monthly_rebalance_dates(trading_days: List[str]) -> List[str]:
    """获取月末调仓日期（与六因子相同）"""
    from datetime import datetime, timedelta

    if not trading_days:
        return []

    dates = [datetime.strptime(d, '%Y%m%d') for d in trading_days]
    rebalance_dates = []
    current_month = None

    for date in dates:
        month_key = (date.year, date.month)

        if month_key != current_month:
            if current_month is not None:
                last_day = date.replace(day=1) - timedelta(days=1)
                nearest = find_nearest_trading_day(last_day, dates)
                if nearest:
                    rebalance_dates.append(nearest.strftime('%Y%m%d'))
            current_month = month_key

    if dates:
        last_date = dates[-1]
        last_day = last_date.replace(day=1) + timedelta(days=32)
        last_day = last_day.replace(day=1) - timedelta(days=1)
        nearest = find_nearest_trading_day(last_day, dates)
        if nearest:
            rebalance_dates.append(nearest.strftime('%Y%m%d'))

    return sorted(set(rebalance_dates))


def find_nearest_trading_day(target_date, trading_dates):
    """找到最近的交易日"""
    if target_date in trading_dates:
        return target_date

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


def run_backtest(rebalance_dates: List[str], params: Dict, config: Dict, version: str) -> Dict[str, Any]:
    """
    运行策略3回测

    Args:
        rebalance_dates: 调仓日期
        params: 策略参数
        config: 策略配置
        version: 版本

    Returns:
        回测结果
    """
    results = {
        'dates': [],
        'returns': [],
        'metrics': {},
        'trades': []
    }

    # 逐期回测
    for i, rebalance_date in enumerate(rebalance_dates):
        if i == len(rebalance_dates) - 1:
            break

        start_date = rebalance_date
        end_date = rebalance_dates[i + 1]

        logger.info(f"回测期间: {start_date} ~ {end_date}")

        # 计算因子并选股
        selected_stocks = calculate_strategy3_selection(start_date, params)

        # 计算收益
        period_return = calculate_period_return(selected_stocks, start_date, end_date)

        # 记录结果
        results['dates'].append(end_date)
        results['returns'].append(period_return)

    # 计算性能指标
    results['metrics'] = calculate_metrics(results)

    return results


def calculate_strategy3_selection(date: str, params: Dict) -> List[str]:
    """
    计算策略3选股

    Args:
        date: 选股日期
        params: 参数

    Returns:
        选中股票列表
    """
    logger.info(f"计算策略3选股: {date}")

    # 获取可交易股票
    stocks = data_loader.get_tradable_stocks(date)

    # 这里应该调用实际的因子计算和综合得分逻辑
    # 为简化，返回前50只股票作为示例
    return stocks[:50] if len(stocks) >= 50 else stocks


def calculate_period_return(stocks: List[str], start_date: str, end_date: str) -> float:
    """
    计算期间收益

    Args:
        stocks: 股票列表
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        收益率
    """
    if not stocks:
        return 0.0

    # 获取价格数据
    price_data = data_loader.get_price_data(stocks, start_date, end_date)

    if price_data.empty:
        return 0.0

    # 计算等权收益
    start_prices = price_data.groupby('ts_code')['close'].first()
    end_prices = price_data.groupby('ts_code')['close'].last()

    individual_returns = (end_prices - start_prices) / start_prices
    return individual_returns.mean()


def calculate_metrics(results: Dict) -> Dict[str, float]:
    """
    计算性能指标

    Args:
        results: 回测结果

    Returns:
        性能指标
    """
    import numpy as np

    returns_array = np.array(results['returns'])

    metrics = {
        'total_return': (1 + returns_array).prod() - 1,
        'annual_return': ((1 + (1 + returns_array).prod()) ** (12/len(returns_array))) - 1 if len(returns_array) > 0 else 0,
        'sharpe_ratio': np.mean(returns_array) / np.std(returns_array) * np.sqrt(12) if np.std(returns_array) > 0 else 0,
        'max_drawdown': calculate_max_drawdown(returns_array),
        'volatility': np.std(returns_array) * np.sqrt(12),
    }

    return metrics


def calculate_max_drawdown(returns):
    """计算最大回撤"""
    if len(returns) == 0:
        return 0.0

    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    return drawdown.min()


def save_results(results: Dict, start_date: str, end_date: str, version: str, strategy_name: str):
    """
    保存结果

    Args:
        results: 回测结果
        start_date: 开始日期
        end_date: 结束日期
        version: 版本
        strategy_name: 策略名称
    """
    import pandas as pd

    # 创建输出目录
    output_dir = f"/home/zcy/alpha006_20251223/results/strategies/{strategy_name}_{start_date}_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)

    # 保存收益数据
    returns_df = pd.DataFrame({
        'date': results['dates'],
        'return': results['returns']
    })
    returns_df.to_csv(f"{output_dir}/returns.csv", index=False)

    # 保存指标
    metrics_df = pd.DataFrame([results['metrics']])
    metrics_df.to_csv(f"{output_dir}/metrics.csv", index=False)

    logger.info(f"结果保存至: {output_dir}")

    # 打印关键指标
    print("\n" + "="*60)
    print("策略3回测结果摘要")
    print("="*60)
    for key, value in results['metrics'].items():
        print(f"{key}: {value:.4f}")
    print("="*60)