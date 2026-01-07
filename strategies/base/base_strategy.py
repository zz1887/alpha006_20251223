"""
基础策略基类

定义所有策略必须实现的接口和公共方法
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, name: str, version: str = 'standard'):
        """
        初始化策略

        Args:
            name: 策略名称
            version: 策略版本
        """
        self.name = name
        self.version = version
        self.config = None
        self.results = None

    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        """加载策略配置"""
        pass

    @abstractmethod
    def prepare_data(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """准备数据"""
        pass

    @abstractmethod
    def calculate_signals(self, data: Dict[str, Any]) -> pd.DataFrame:
        """计算交易信号"""
        pass

    @abstractmethod
    def run_backtest(self, signals: pd.DataFrame) -> Dict[str, Any]:
        """运行回测"""
        pass

    @abstractmethod
    def generate_report(self, results: Dict[str, Any]) -> str:
        """生成报告"""
        pass

    def execute(self, start_date: str, end_date: str, **kwargs) -> Dict[str, Any]:
        """
        执行完整策略流程

        Args:
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数

        Returns:
            策略结果字典
        """
        try:
            logger.info(f"开始执行策略: {self.name} v{self.version}")

            # 1. 加载配置
            logger.info("步骤1: 加载配置")
            self.config = self.load_config()

            # 2. 准备数据
            logger.info("步骤2: 准备数据")
            data = self.prepare_data(start_date, end_date)

            # 3. 计算信号
            logger.info("步骤3: 计算交易信号")
            signals = self.calculate_signals(data)

            # 4. 运行回测
            logger.info("步骤4: 运行回测")
            results = self.run_backtest(signals)

            # 5. 生成报告
            logger.info("步骤5: 生成报告")
            report = self.generate_report(results)

            self.results = {
                'signals': signals,
                'backtest': results,
                'report': report,
                'config': self.config
            }

            logger.info(f"策略执行完成: {self.name}")
            return self.results

        except Exception as e:
            logger.error(f"策略执行失败: {e}")
            raise

    def get_performance_metrics(self) -> Dict[str, float]:
        """获取性能指标"""
        if not self.results or 'backtest' not in self.results:
            return {}

        backtest = self.results['backtest']
        return backtest.get('metrics', {})