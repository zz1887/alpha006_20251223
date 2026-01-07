#!/usr/bin/env python3
"""
运行聚宽策略V3回测 - 20241001-20251201
调仓规则: 每月6日
"""

import sys
sys.path.insert(0, '/home/zcy/alpha006_20251223')

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import os

# 导入策略
from strategies.runners.聚宽策略V3_数据库版 import (
    initialize, select_and_adjust, check_market_status,
    Context, Portfolio, Position, get_current_price
)

from core.config.settings import DATABASE_CONFIG, BACKTEST_CONFIG, TRADING_COSTS
from core.utils.db_connection import DBConnection

# 初始化数据库
db = DBConnection(DATABASE_CONFIG)

class SimpleBacktestTracker:
    """简化的回测追踪器"""

    def __init__(self, start_date, end_date, initial_capital=1000000):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital

        # 记录数据
        self.rebalance_records = []
        self.daily_nav = []
        self.daily_returns = []
        self.drawdowns = []

        # 跟踪变量
        self.peak_nav = initial_capital
        self.max_drawdown = 0

    def record_rebalance(self, date, stock_count, portfolio):
        """记录调仓"""
        record = {
            'date': date.strftime('%Y-%m-%d'),
            'stock_count': stock_count,
            'total_value': portfolio.total_value,
            'cash': portfolio.cash,
            'cash_ratio': portfolio.cash / portfolio.total_value * 100
        }
        self.rebalance_records.append(record)

        print(f"【调仓记录】{date.strftime('%Y-%m-%d')} | " +
              f"持仓数: {stock_count} | " +
              f"总资产: {portfolio.total_value:,.2f} | " +
              f"现金占比: {portfolio.cash/portfolio.total_value*100:.1f}%")

    def record_daily(self, date, portfolio):
        """记录每日净值"""
        nav = portfolio.total_value
        self.daily_nav.append({'date': date.strftime('%Y-%m-%d'), 'nav': nav})

        # 计算收益率
        if len(self.daily_nav) > 1:
            prev_nav = self.daily_nav[-2]['nav']
            daily_return = (nav - prev_nav) / prev_nav
            self.daily_returns.append({'date': date.strftime('%Y-%m-%d'), 'return': daily_return})

            # 计算回撤
            if nav > self.peak_nav:
                self.peak_nav = nav
            drawdown = (self.peak_nav - nav) / self.peak_nav
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
            self.drawdowns.append({'date': date.strftime('%Y-%m-%d'), 'drawdown': drawdown})

    def get_metrics(self):
        """计算性能指标"""
        if len(self.daily_nav) < 2:
            return {}

        final_nav = self.daily_nav[-1]['nav']
        total_return = (final_nav - self.initial_capital) / self.initial_capital

        # 年化收益率
        trading_days = len(self.daily_nav)
        annualized_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 else 0

        # 夏普比率 (简化)
        if len(self.daily_returns) > 1:
            returns = [r['return'] for r in self.daily_returns]
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = (mean_return * 252 - 0.02) / (std_return * np.sqrt(252)) if std_return > 0 else 0
        else:
            sharpe = 0

        # 胜率
        positive_returns = sum(1 for r in self.daily_returns if r['return'] > 0)
        win_rate = positive_returns / len(self.daily_returns) if self.daily_returns else 0

        return {
            '初始资金': self.initial_capital,
            '最终净值': final_nav,
            '总收益率': total_return,
            '年化收益率': annualized_return,
            '最大回撤': self.max_drawdown,
            '夏普比率': sharpe,
            '胜率': win_rate,
            '调仓次数': len(self.rebalance_records),
            '交易天数': trading_days
        }

    def save_results(self, output_dir):
        """保存结果"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base = f"backtest_{timestamp}"

        # 保存调仓记录
        if self.rebalance_records:
            df = pd.DataFrame(self.rebalance_records)
            path = os.path.join(output_dir, f"{base}_rebalance.csv")
            df.to_csv(path, index=False, encoding='utf-8-sig')
            print(f"✅ 调仓记录: {path}")

        # 保存每日净值
        if self.daily_nav:
            df = pd.DataFrame(self.daily_nav)
            path = os.path.join(output_dir, f"{base}_nav.csv")
            df.to_csv(path, index=False, encoding='utf-8-sig')
            print(f"✅ 每日净值: {path}")

        # 保存性能指标
        metrics = self.get_metrics()
        path = os.path.join(output_dir, f"{base}_metrics.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        print(f"✅ 性能指标: {path}")

        # 生成报告
        report_path = os.path.join(output_dir, f"{base}_report.md")
        self._generate_report(report_path, metrics)
        print(f"✅ 回测报告: {report_path}")

        return metrics

    def _generate_report(self, path, metrics):
        """生成报告"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"# 策略回测报告\n\n")
            f.write(f"**回测周期**: {self.start_date} 至 {self.end_date}\n\n")
            f.write(f"**调仓规则**: 每月6日\n\n")
            f.write(f"## 关键指标\n\n")
            for key, value in metrics.items():
                if isinstance(value, float):
                    if '收益率' in key or '回撤' in key or '胜率' in key:
                        f.write(f"- **{key}**: {value*100:.2f}%\n")
                    else:
                        f.write(f"- **{key}**: {value:.4f}\n")
                else:
                    f.write(f"- **{key}**: {value}\n")

            f.write(f"\n## 调仓详情\n\n")
            if self.rebalance_records:
                f.write("| 日期 | 持仓数 | 总资产 | 现金占比 |\n")
                f.write("|------|--------|--------|----------|\n")
                for r in self.rebalance_records:
                    f.write(f"| {r['date']} | {r['stock_count']} | {r['total_value']:,.0f} | {r['cash_ratio']:.1f}% |\n")


def run_backtest(start_date, end_date, rebalance_day=6):
    """运行回测"""
    print("="*80)
    print("聚宽策略V3 - 回测执行")
    print("="*80)
    print(f"周期: {start_date} 至 {end_date}")
    print(f"调仓日: 每月{rebalance_day}日")
    print(f"初始资金: {BACKTEST_CONFIG['initial_capital']:,.2f}")
    print("="*80)

    # 转换日期
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    # 初始化追踪器
    tracker = SimpleBacktestTracker(start_date, end_date, BACKTEST_CONFIG['initial_capital'])

    # 初始化策略
    context = Context(start_dt)
    initialize(context)

    # 设置初始资金
    context.portfolio.total_value = BACKTEST_CONFIG['initial_capital']
    context.portfolio.cash = BACKTEST_CONFIG['initial_capital']
    context.portfolio.max_total_value = BACKTEST_CONFIG['initial_capital']

    print(f"\n策略初始化完成")
    print(f"初始状态 - 总资产: {context.portfolio.total_value:,.2f}")

    # 记录初始状态
    tracker.record_daily(start_dt, context.portfolio)

    # 开始回测
    current_dt = start_dt
    rebalance_count = 0

    while current_dt <= end_dt:
        # 检查交易日
        date_str = current_dt.strftime('%Y%m%d')
        sql = "SELECT COUNT(*) as cnt FROM daily_kline WHERE trade_date = %s"
        result = db.execute_query(sql, (date_str,))

        if result and result[0]['cnt'] > 0:
            context.current_dt = current_dt

            # 检查是否调仓
            if current_dt.day == rebalance_day:
                print(f"\n{'='*80}")
                print(f"【{current_dt.strftime('%Y-%m-%d')}】执行调仓 (第{rebalance_count+1}次)")
                print(f"{'='*80}")

                # 执行调仓
                select_and_adjust(context)

                # 统计持仓
                stock_count = sum(1 for pos in context.portfolio.positions.values() if pos.total_amount > 0)

                # 记录调仓
                tracker.record_rebalance(current_dt, stock_count, context.portfolio)
                rebalance_count += 1

                # 更新峰值
                if context.portfolio.total_value > context.portfolio.max_total_value:
                    context.portfolio.max_total_value = context.portfolio.total_value

            else:
                # 每日监控（每10天显示一次）
                if rebalance_count > 0 and current_dt.day % 10 == 0:
                    check_market_status(context)

                # 更新峰值
                if context.portfolio.total_value > context.portfolio.max_total_value:
                    context.portfolio.max_total_value = context.portfolio.total_value

            # 记录每日净值
            tracker.record_daily(current_dt, context.portfolio)

        current_dt += timedelta(days=1)

    print(f"\n{'='*80}")
    print(f"回测完成！共执行 {rebalance_count} 次调仓")
    print(f"{'='*80}")

    # 显示结果
    metrics = tracker.get_metrics()
    if metrics:
        print(f"\n📊 性能指标:")
        for key, value in metrics.items():
            if isinstance(value, float):
                if '收益率' in key or '回撤' in key or '胜率' in key:
                    print(f"  {key}: {value*100:.2f}%")
                else:
                    print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")

    # 保存结果
    print(f"\n💾 保存结果...")
    output_dir = "/home/zcy/alpha006_20251223/results/backtest"
    metrics = tracker.save_results(output_dir)

    print(f"\n✅ 完成！结果已保存到: {output_dir}")
    return metrics


if __name__ == "__main__":
    # 运行回测
    metrics = run_backtest("2024-10-01", "2025-12-01", rebalance_day=6)

    print("\n" + "="*80)
    print("回测执行完毕")
    print("="*80)