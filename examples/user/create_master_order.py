#!/usr/bin/env python
"""
创建母单的示例代码

这个示例展示了两种创建母单的方式：
1. 使用枚举类型（推荐，提供类型安全）
2. 使用字符串（向后兼容）
"""

import logging
from qe.user import User as Client
from qe.lib.utils import config_logging
from qe.error import ClientError, APIError
# 导入交易枚举（新功能）
from qe.lib import Algorithm, Exchange, MarketType, OrderSide, StrategyType, MarginType

from examples.utils.prepare_env import get_api_key

config_logging(logging, logging.DEBUG)
logger = logging.getLogger(__name__)

def show_available_enums():
    """展示所有可用的枚举值"""
    print("\n" + "="*60)
    print("可用的枚举值:")
    print("="*60)
    
    print("\n算法 (Algorithm):")
    for algo in Algorithm:
        print(f"  - Algorithm.{algo.name} = '{algo.value}'")
    
    print("\n策略类型 (StrategyType):")
    for strategy in StrategyType:
        print(f"  - StrategyType.{strategy.name} = '{strategy.value}'")
    
    print("\n市场类型 (MarketType):")
    for market in MarketType:
        print(f"  - MarketType.{market.name} = '{market.value}'")
    
    print("\n订单方向 (OrderSide):")
    for side in OrderSide:
        print(f"  - OrderSide.{side.name} = '{side.value}'")
    
    print("\n保证金类型 (MarginType):")
    for margin in MarginType:
        print(f"  - MarginType.{margin.name} = '{margin.value}'")
    
    print("\n交易所 (Exchange):")
    for exchange in Exchange:
        print(f"  - Exchange.{exchange.name} = '{exchange.value}'")
    
    print("\n" + "="*60 + "\n")


api_key, api_secret = get_api_key()

# client = Client(api_key, api_secret, base_url="http://127.0.0.1:8000/strategy-api")
client = Client(api_key, api_secret)

# 可选：显示所有可用的枚举值
# show_available_enums()

try:
    # ====================================================================
    # 方式1: 使用枚举创建订单（推荐 - 提供类型安全和代码提示）
    # ====================================================================
    logger.info("=" * 60)
    logger.info("示例1: 使用枚举创建 TWAP 订单（推荐方式）")
    logger.info("=" * 60)
    
    # Create a TWAP order using enums
    response = client.create_master_order(
        algorithm=Algorithm.TWAP,                      # 使用算法枚举
        exchange=Exchange.BINANCE,                     # 使用交易所枚举
        symbol="BTCUSDT",
        marketType=MarketType.SPOT,                    # 使用市场类型枚举
        side=OrderSide.BUY,                           # 使用订单方向枚举
        apiKeyId="0b057efbbcea46db885ae66c98d20849",  # Get from list_exchange_apis
        orderNotional=200,                             # $200 notional value
        strategyType=StrategyType.TWAP_1,             # 使用策略类型枚举
        startTime="2025-09-02T19:54:34+08:00",
        endTime="2025-09-03T01:44:35+08:00",
        executionDuration="5",                         # 5 seconds intervals
        mustComplete=True,
        reduceOnly=False,
        worstPrice=-1,                                # -1 means no worst price limit
        upTolerance="-1",
        lowTolerance="-1",
        tailOrderProtection=True                      # 新参数：尾单保护（默认为 True）
    )
    
    if response.get('success'):
        logger.info(f"✅ Master order created successfully with enums. ID: {response.get('masterOrderId')}")
    else:
        logger.error(f"❌ Failed to create order: {response.get('message')}")
    
    # Create a POV order using enums
    logger.info("\n示例2: 使用枚举创建 POV 合约订单")
    response = client.create_master_order(
        algorithm=Algorithm.POV,                       # POV 算法
        exchange=Exchange.BINANCE,
        symbol="BTCUSDT",
        marketType=MarketType.PERP,                    # 合约市场
        side=OrderSide.SELL,                          # 卖出
        apiKeyId="0b057efbbcea46db885ae66c98d20849",
        orderNotional=1000,                            # $1000 notional value
        strategyType=StrategyType.POV,                # POV 策略
        startTime="2025-09-02T19:54:34+08:00",
        endTime="2025-09-03T01:44:35+08:00",
        povLimit=0.2,                                  # POV 限制 20%
        povMinLimit=0.05,                              # 新参数：最小 POV 5%
        marginType=MarginType.U,                      # U本位保证金
        reduceOnly=False,
        mustComplete=True,
        notes="POV 合约订单示例"
    )
    logger.info(f"POV order response: {response}")

    
except APIError as error:
    logger.error(
        "API Error. code: {}, reason: {}, message: {}, trace: {}".format(
            error.code, error.reason, error.message, error.trace_id
        )
    )
except ClientError as error:
    logger.error(
        "Client Error. status: {}, error code: {}, error message: {}".format(
            error.status_code, error.error_code, error.error_message
        )
    )
