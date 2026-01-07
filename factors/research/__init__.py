"""
文件input(依赖外部什么): pandas, numpy, scipy
文件output(提供什么): 因子研究工具统一导入
文件pos(系统局部地位): 因子研究层入口，提供相关性分析、IC分析、因子组合优化等功能
"""

from .correlation import FactorCorrelationAnalyzer
from .ic_analysis import ICAnalyzer
from .factor_combine import FactorCombiner
from .discovery import FactorDiscovery

__all__ = ['FactorCorrelationAnalyzer', 'ICAnalyzer', 'FactorCombiner', 'FactorDiscovery']
