# 增强策略执行器 - 数据库版
# 用于执行聚宽策略V3的数据库适配版本，包含全面的性能追踪

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple

# 添加项目路径
sys.path.append('/home/zcy/alpha006_20251223')

# 导入策略
try:
    from strategies.runners.聚宽策略V3_数据库版 import (
        initialize, select_and_adjust, check_market_status,
        Context, Portfolio, Position, get_current_price
    )
except ImportError as e:
    print(f"导入策略失败: {e}")
    print("请确保策略文件存在")
    sys.exit(1)

# 导入项目配置
from core.config.settings import DATABASE_CONFIG, TRADING_COSTS, BACKTEST_CONFIG
from core.utils.db_connection import DBConnection

# 初始化数据库连接
db = DBConnection(DATABASE_CONFIG)


class BacktestPerformanceTracker:
    """回测性能追踪器"""

    def __init__(self, start_date, end_date, initial_capital=1000000):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital

        # 性能指标
        self.daily_nav = []  # 每日净值
        self.rebalance_records = []  # 调仓记录
        self.daily_returns = []  # 每日收益率
        self.drawdowns = []  # 回撤记录

        # 跟踪变量
        self.current_nav = initial_capital
        self.max_nav = initial_capital
        self.peak_nav = initial_capital
        self.trading_days = 0

    def record_rebalance(self, date: datetime, stocks: List[Dict], portfolio: Portfolio):
        """记录调仓信息"""
        stock_count = len(stocks)

        # 计算调仓时的持仓价值
        holdings_value = 0
        for stock in stocks:
            code = stock['code']
            if code in portfolio.positions:
                holdings_value += portfolio.positions[code].value

        cash_ratio = portfolio.cash / portfolio.total_value * 100

        record = {
            'date': date.strftime('%Y-%m-%d'),
            'stock_count': stock_count,
            'holdings_value': holdings_value,
            'cash': portfolio.cash,
            'cash_ratio': cash_ratio,
            'total_value': portfolio.total_value,
            'stocks': [s['code'] for s in stocks]
        }

        self.rebalance_records.append(record)

        print(f"【调仓记录】{date.strftime('%Y-%m-%d')} | " +
              f"持仓数: {stock_count} | " +
              f"持仓市值: {holdings_value:,.2f} | " +
              f"现金占比: {cash_ratio:.1f}% | " +
              f"总资产: {portfolio.total_value:,.2f}")

        return record

    def record_daily(self, date: datetime, portfolio: Portfolio):
        """记录每日净值"""
        nav = portfolio.total_value
        self.daily_nav.append({
            'date': date.strftime('%Y-%m-%d'),
            'nav': nav,
            'cash': portfolio.cash,
            'positions_value': nav - portfolio.cash
        })

        # 计算当日收益率
        if len(self.daily_nav) > 1:
            prev_nav = self.daily_nav[-2]['nav']
            daily_return = (nav - prev_nav) / prev_nav
            self.daily_returns.append({
                'date': date.strftime('%Y-%m-%d'),
                'return': daily_return
            })

            # 更新最大回撤
            if nav > self.peak_nav:
                self.peak_nav = nav
            drawdown = (self.peak_nav - nav) / self.peak_nav
            self.drawdowns.append({
                'date': date.strftime('%Y-%m-%d'),
                'drawdown': drawdown
            })

            if drawdown > 0:
                print(f"【每日监控】{date.strftime('%Y-%m-%d')} | " +
                      f"净值: {nav:,.2f} | " +
                      f"当日: {daily_return*100:+.2f}% | " +
                      f"回撤: {drawdown*100:.2f}%")

        self.current_nav = nav
        if nav > self.max_nav:
            self.max_nav = nav
        self.trading_days += 1

    def get_performance_metrics(self) -> Dict:
        """计算性能指标"""
        if len(self.daily_nav) < 2:
            return {}

        # 总收益率
        total_return = (self.current_nav - self.initial_capital) / self.initial_capital

        # 年化收益率
        trading_days = len(self.daily_nav)
        annualized_return = (1 + total_return) ** (252 / trading_days) - 1 if trading_days > 0 else 0

        # 最大回撤
        max_drawdown = 0
        if self.drawdowns:
            max_drawdown = max(d['drawdown'] for d in self.drawdowns)

        # 夏普比率 (简化计算，假设无风险利率为2%)
        if len(self.daily_returns) > 1:
            returns = [r['return'] for r in self.daily_returns]
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return > 0:
                sharpe = (mean_return * 252 - 0.02) / (std_return * np.sqrt(252))
            else:
                sharpe = 0
        else:
            sharpe = 0

        # 胜率
        if len(self.daily_returns) > 0:
            positive_returns = sum(1 for r in self.daily_returns if r['return'] > 0)
            win_rate = positive_returns / len(self.daily_returns)
        else:
            win_rate = 0

        # 调仓次数
        rebalance_count = len(self.rebalance_records)

        # 平均持仓数量
        avg_holdings = np.mean([r['stock_count'] for r in self.rebalance_records]) if self.rebalance_records else 0

        return {
            '初始资金': self.initial_capital,
            '最终净值': self.current_nav,
            '总收益率': total_return,
            '年化收益率': annualized_return,
            '最大回撤': max_drawdown,
            '夏普比率': sharpe,
            '胜率': win_rate,
            '交易天数': trading_days,
            '调仓次数': rebalance_count,
            '平均持仓数': avg_holdings,
            '总交易日': len(self.daily_nav)
        }

    def save_results(self, output_dir: str, prefix: str = "backtest"):
        """保存回测结果"""
        import os

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"{prefix}_{timestamp}"

        # 1. 保存调仓记录
        if self.rebalance_records:
            rebalance_df = pd.DataFrame(self.rebalance_records)
            rebalance_path = os.path.join(output_dir, f"{base_filename}_rebalance.csv")
            rebalance_df.to_csv(rebalance_path, index=False, encoding='utf-8-sig')
            print(f"✅ 调仓记录已保存: {rebalance_path}")

        # 2. 保存每日净值
        if self.daily_nav:
            nav_df = pd.DataFrame(self.daily_nav)
            nav_path = os.path.join(output_dir, f"{base_filename}_nav.csv")
            nav_df.to_csv(nav_path, index=False, encoding='utf-8-sig')
            print(f"✅ 每日净值已保存: {nav_path}")

        # 3. 保存每日收益率
        if self.daily_returns:
            returns_df = pd.DataFrame(self.daily_returns)
            returns_path = os.path.join(output_dir, f"{base_filename}_returns.csv")
            returns_df.to_csv(returns_path, index=False, encoding='utf-8-sig')
            print(f"✅ 每日收益率已保存: {returns_path}")

        # 4. 保存回撤数据
        if self.drawdowns:
            drawdown_df = pd.DataFrame(self.drawdowns)
            drawdown_path = os.path.join(output_dir, f"{base_filename}_drawdown.csv")
            drawdown_df.to_csv(drawdown_path, index=False, encoding='utf-8-sig')
            print(f"✅ 回撤数据已保存: {drawdown_path}")

        # 5. 保存性能指标
        metrics = self.get_performance_metrics()
        metrics_path = os.path.join(output_dir, f"{base_filename}_metrics.json")
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        print(f"✅ 性能指标已保存: {metrics_path}")

        # 6. 生成回测报告
        report_path = os.path.join(output_dir, f"{base_filename}_report.md")
        self._generate_report(report_path, metrics)
        print(f"✅ 回测报告已保存: {report_path}")

        return {
            'rebalance': rebalance_path if self.rebalance_records else None,
            'nav': nav_path if self.daily_nav else None,
            'returns': returns_path if self.daily_returns else None,
            'drawdown': drawdown_path if self.drawdowns else None,
            'metrics': metrics_path,
            'report': report_path
        }

    def _generate_report(self, report_path: str, metrics: Dict):
        """生成回测报告"""
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# 策略回测报告\n\n")
            f.write(f"**回测周期**: {self.start_date} 至 {self.end_date}\n\n")
            f.write(f"**初始资金**: {metrics['初始资金']:,.2f} 元\n\n")
            f.write(f"**最终净值**: {metrics['最终净值']:,.2f} 元\n\n")
            f.write(f"**调仓次数**: {metrics['调仓次数']} 次\n\n")
            f.write(f"**交易天数**: {metrics['交易天数']} 天\n\n")
            f.write(f"## 关键指标\n\n")
            f.write(f"- **总收益率**: {metrics['总收益率']*100:.2f}%\n")
            f.write(f"- **年化收益率**: {metrics['年化收益率']*100:.2f}%\n")
            f.write(f"- **最大回撤**: {metrics['最大回撤']*100:.2f}%\n")
            f.write(f"- **夏普比率**: {metrics['夏普比率']:.4f}\n")
            f.write(f"- **胜率**: {metrics['胜率']*100:.2f}%\n")
            f.write(f"- **平均持仓数**: {metrics['平均持仓数']:.1f} 只\n\n")

            f.write(f"## 调仓详情\n\n")
            if self.rebalance_records:
                f.write("| 日期 | 持仓数 | 持仓市值 | 现金占比 | 总资产 |\n")
                f.write("|------|--------|----------|----------|--------|\n")
                for record in self.rebalance_records:
                    f.write(f"| {record['date']} | {record['stock_count']} | " +
                           f"{record['holdings_value']:,.0f} | " +
                           f"{record['cash_ratio']:.1f}% | " +
                           f"{record['total_value']:,.0f} |\n")
            else:
                f.write("无调仓记录\n")


def run_enhanced_backtest(start_date, end_date, rebalance_day=6, output_dir=None):
    """
    运行增强版回测

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        rebalance_day: 调仓日 (每月几号)
        output_dir: 输出目录 (默认为results/backtest)
    """
    print("="*100)
    print("增强版策略回测启动")
    print("="*100)
    print(f"回测周期: {start_date} 至 {end_date}")
    print(f"调仓日: 每月{rebalance_day}日")
    print(f"初始资金: {BACKTEST_CONFIG['initial_capital']:,.2f} 元")
    print("="*100)

    # 转换日期
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    # 初始化性能追踪器
    if output_dir is None:
        output_dir = "/home/zcy/alpha006_20251223/results/backtest"

    tracker = BacktestPerformanceTracker(
        start_date=start_date,
        end_date=end_date,
        initial_capital=BACKTEST_CONFIG['initial_capital']
    )

    # 初始化策略
    context = Context(start_dt)
    initialize(context)

    # 确保portfolio有正确的初始值
    context.portfolio.total_value = BACKTEST_CONFIG['initial_capital']
    context.portfolio.cash = BACKTEST_CONFIG['initial_capital']
    context.portfolio.max_total_value = BACKTEST_CONFIG['initial_capital']

    print(f"\n策略初始化完成")
    print(f"初始状态 - 总资产: {context.portfolio.total_value:,.2f}, 现金: {context.portfolio.cash:,.2f}")

    # 生成交易日历
    current_dt = start_dt
    rebalance_count = 0
    daily_check_count = 0

    # 记录初始状态
    tracker.record_daily(start_dt, context.portfolio)

    while current_dt <= end_dt:
        # 检查是否为交易日
        date_str = current_dt.strftime('%Y%m%d')
        sql = f"SELECT COUNT(*) as cnt FROM daily_kline WHERE trade_date = %s"
        result = db.execute_query(sql, (date_str,))

        if result and result[0]['cnt'] > 0:
            # 是交易日
            context.current_dt = current_dt

            # 检查是否需要调仓
            if current_dt.day == rebalance_day:
                print(f"\n{'='*100}")
                print(f"【{current_dt.strftime('%Y-%m-%d')}】执行调仓 (第{rebalance_count+1}次)")
                print(f"{'='*100}")

                # 执行调仓前的资产状态
                print(f"调仓前状态 - 总资产: {context.portfolio.total_value:,.2f}, 现金: {context.portfolio.cash:,.2f}")

                # 执行调仓
                select_and_adjust(context)

                # 获取当前持仓信息用于记录
                current_stocks = []
                for code, pos in context.portfolio.positions.items():
                    if pos.total_amount > 0:
                        current_stocks.append({'code': code, 'amount': pos.total_amount})

                # 记录调仓
                tracker.record_rebalance(current_dt, current_stocks, context.portfolio)
                rebalance_count += 1

                # 更新最大净值
                if context.portfolio.total_value > context.portfolio.max_total_value:
                    context.portfolio.max_total_value = context.portfolio.total_value

            else:
                # 每日监控
                daily_check_count += 1
                if daily_check_count % 10 == 0:  # 每10天显示一次监控
                    check_market_status(context)

                # 更新最大净值（用于回撤计算）
                if context.portfolio.total_value > context.portfolio.max_total_value:
                    context.portfolio.max_total_value = context.portfolio.total_value

            # 记录每日净值
            tracker.record_daily(current_dt, context.portfolio)

        current_dt += timedelta(days=1)

    print(f"\n{'='*100}")
    print(f"回测完成！")
    print(f"共执行 {rebalance_count} 次调仓")
    print(f"共记录 {tracker.trading_days} 个交易日")
    print(f"{'='*100}")

    # 显示性能指标
    metrics = tracker.get_performance_metrics()
    if metrics:
        print(f"\n📊 性能指标汇总:")
        print(f"  初始资金: {metrics['初始资金']:,.2f} 元")
        print(f"  最终净值: {metrics['最终净值']:,.2f} 元")
        print(f"  总收益率: {metrics['总收益率']*100:.2f}%")
        print(f"  年化收益率: {metrics['年化收益率']*100:.2f}%")
        print(f"  最大回撤: {metrics['最大回撤']*100:.2f}%")
        print(f"  夏普比率: {metrics['夏普比率']:.4f}")
        print(f"  胜率: {metrics['胜率']*100:.2f}%")
        print(f"  平均持仓数: {metrics['平均持仓数']:.1f} 只")

    # 保存结果
    print(f"\n💾 保存回测结果...")
    file_paths = tracker.save_results(output_dir, prefix="backtest")

    print(f"\n✅ 回测完成！所有结果已保存到: {output_dir}")

    return tracker, file_paths


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='增强版聚宽策略V3 - 数据库版执行器')
    parser.add_argument('--mode', type=str, default='test',
                       choices=['test', 'backtest', 'factor', 'dbcheck', 'enhanced_backtest'],
                       help='运行模式: test(单日测试), backtest(基础回测), enhanced_backtest(增强回测), factor(因子分析), dbcheck(数据库检查)')
    parser.add_argument('--date', type=str, default=None,
                       help='测试日期 (YYYY-MM-DD)')
    parser.add_argument('--start', type=str, default=None,
                       help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=None,
                       help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--stock', type=str, default=None,
                       help='股票代码 (用于因子分析)')
    parser.add_argument('--rebalance', type=int, default=6,
                       help='调仓日 (默认6号)')
    parser.add_argument('--output', type=str, default=None,
                       help='输出目录 (默认为results/backtest)')

    args = parser.parse_args()

    if args.mode == 'dbcheck':
        # 导入原执行器的函数
        from strategy_executor import check_database_connection
        check_database_connection()
        return

    if args.mode == 'test':
        # 导入原执行器的函数
        from strategy_executor import run_single_day_test
        if not args.date:
            # 使用最近一个交易日
            result = db.execute_query("SELECT MAX(trade_date) as max_date FROM daily_kline")
            if result and result[0]['max_date']:
                max_date = result[0]['max_date']
                test_date = datetime.strptime(max_date, '%Y%m%d').strftime('%Y-%m-%d')
            else:
                test_date = '2025-01-03'
        else:
            test_date = args.date

        run_single_day_test(test_date)

    elif args.mode == 'backtest':
        # 导入原执行器的函数
        from strategy_executor import run_backtest
        if not args.start or not args.end:
            print("请指定回测开始和结束日期")
            return

        run_backtest(args.start, args.end, args.rebalance)

    elif args.mode == 'enhanced_backtest':
        if not args.start or not args.end:
            print("请指定回测开始和结束日期")
            return

        run_enhanced_backtest(args.start, args.end, args.rebalance, args.output)

    elif args.mode == 'factor':
        # 导入原执行器的函数
        from strategy_executor import show_factor_analysis
        if not args.date or not args.stock:
            print("请指定日期和股票代码")
            return

        show_factor_analysis(args.date, args.stock)


if __name__ == '__main__':
    main()