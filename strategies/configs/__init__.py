"""
文件input(依赖外部什么): core.config, strategies.configs.SFM_6F_M_V1, etc.
文件output(提供什么): 策略配置统一导入接口
文件pos(系统局部地位): 策略配置层，提供所有策略的配置参数管理
文件功能:
    1. 6因子月度策略配置（V1/V2版本）
    2. 5因子月度策略配置（标准/保守/激进版本）
    3. 策略参数获取函数
    4. 策略信息查询

使用示例:
    from strategies.configs import (
        sfm_6f_m_v1_config,
        sfm_6f_m_v1_params,
        SFM_6F_M_V1_INFO
    )

    # 获取策略配置
    config = sfm_6f_m_v1_config()
    params = sfm_6f_m_v1_params()

    # 查看策略信息
    print(SFM_6F_M_V1_INFO)

返回值:
    Dict: 策略配置字典
    Dict: 策略参数字典
    Dict: 策略信息字典

配置版本:
    1. SFM_6F_M_V1 - 6因子月度策略V1版
    2. SFM_6F_M_V2 - 6因子月度策略V2版
    3. MFM_5F_M_V1 - 5因子月度策略标准版
    4. MFM_5F_M_CON - 5因子月度策略保守版
    5. MFM_5F_M_AGG - 5因子月度策略激进版
"""

# 导入新框架的配置
from .SFM_6F_M_V1 import (
    get_strategy_config as sfm_6f_m_v1_config,
    get_strategy_params as sfm_6f_m_v1_params,
    STRATEGY_INFO as SFM_6F_M_V1_INFO
)

from .SFM_6F_M_V2 import (
    get_strategy_config as sfm_6f_m_v2_config,
    get_strategy_params as sfm_6f_m_v2_params,
    STRATEGY_INFO as SFM_6F_M_V2_INFO
)

from .MFM_5F_M_V1 import (
    get_strategy_config as mfm_5f_m_v1_config,
    get_strategy_params as mfm_5f_m_v1_params,
    STRATEGY_INFO as MFM_5F_M_V1_INFO
)

from .MFM_5F_M_CON import (
    get_strategy_config as mfm_5f_m_con_config,
    get_strategy_params as mfm_5f_m_con_params,
    STRATEGY_INFO as MFM_5F_M_CON_INFO
)

from .MFM_5F_M_AGG import (
    get_strategy_config as mfm_5f_m_agg_config,
    get_strategy_params as mfm_5f_m_agg_params,
    STRATEGY_INFO as MFM_5F_M_AGG_INFO
)

__all__ = [
    # 6因子月度策略
    'sfm_6f_m_v1_config',
    'sfm_6f_m_v1_params',
    'SFM_6F_M_V1_INFO',
    'sfm_6f_m_v2_config',
    'sfm_6f_m_v2_params',
    'SFM_6F_M_V2_INFO',

    # 5因子月度策略
    'mfm_5f_m_v1_config',
    'mfm_5f_m_v1_params',
    'MFM_5F_M_V1_INFO',
    'mfm_5f_m_con_config',
    'mfm_5f_m_con_params',
    'MFM_5F_M_CON_INFO',
    'mfm_5f_m_agg_config',
    'mfm_5f_m_agg_params',
    'MFM_5F_M_AGG_INFO',
]
