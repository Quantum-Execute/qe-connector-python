#!/usr/bin/env python
"""
创建母单的示例代码

这个示例展示了两种创建母单的方式：
1. 使用枚举类型（推荐，提供类型安全）
2. 使用字符串（向后兼容）
"""

import logging
import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from qe.user import User as Client
from qe.lib.utils import config_logging
from qe.error import ClientError, APIError
# 导入交易枚举（新功能）
from qe.lib import Algorithm, Exchange, MarketType, OrderSide, StrategyType, MarginType

from examples.utils.prepare_env import get_api_key

config_logging(logging, logging.DEBUG)
logger = logging.getLogger(__name__)

# 主流交易对列表
MAIN_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
    "SOLUSDT", "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT",
    "UNIUSDT", "LTCUSDT", "BCHUSDT", "ATOMUSDT", "XLMUSDT",
    "VETUSDT", "FILUSDT", "TRXUSDT", "EOSUSDT", "AAVEUSDT",
    "SUSHIUSDT", "SNXUSDT", "YFIUSDT", "COMPUSDT", "MKRUSDT",
    "UMAUSDT", "BALUSDT", "CRVUSDT", "1INCHUSDT", "ALPHAUSDT",
    "ZENUSDT", "SKLUSDT", "GRTUSDT", "LRCUSDT", "OMGUSDT",
    "ZRXUSDT", "BATUSDT", "ENJUSDT", "MANAUSDT", "SANDUSDT",
    "AXSUSDT", "CHZUSDT", "FLOWUSDT", "NEARUSDT", "FTMUSDT",
    "MATICUSDT", "ICPUSDT", "THETAUSDT", "HBARUSDT", "XTZUSDT"
]

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


def create_single_order(client, api_key_id, order_params, order_id):
    """创建单个订单的函数"""
    try:
        symbol = random.choice(MAIN_SYMBOLS)
        side = random.choice([OrderSide.BUY, OrderSide.SELL])
        
        response = client.create_master_order(
            algorithm=Algorithm.TWAP,
            exchange=Exchange.BINANCE,
            symbol="DOGEUSDT",
            marketType=MarketType.SPOT,
            side="sell",
            apiKeyId=api_key_id,
            totalQuantity="1000",
            strategyType=StrategyType.TWAP_1,
            # startTime=order_params['startTime'],
            # endTime=order_params['endTime'],
            executionDuration="1",
            mustComplete=True,
            reduceOnly=False,
            upTolerance="-1",
            lowTolerance="-1",
            tailOrderProtection=True,
            isTargetPosition=False,
            isMargin=True
        )
        
        if response.get('success'):
            logger.info(f"✅ 订单 {order_id} 创建成功 - Symbol: {symbol}, Side: {side.value}, ID: {response.get('masterOrderId')}")
            return {'success': True, 'order_id': order_id, 'symbol': symbol, 'side': side.value, 'master_order_id': response.get('masterOrderId')}
        else:
            logger.error(f"❌ 订单 {order_id} 创建失败 - Symbol: {symbol}, Side: {side.value}, Error: {response.get('message')}")
            return {'success': False, 'order_id': order_id, 'symbol': symbol, 'side': side.value, 'error': response.get('message')}
            
    except Exception as e:
        logger.error(f"❌ 订单 {order_id} 异常 - Error: {str(e)}")
        return {'success': False, 'order_id': order_id, 'error': str(e)}


def run_concurrent_orders(client, api_key_id, order_params, num_orders=100):
    """并发执行指定数量的订单创建"""
    logger.info(f"🚀 开始并发创建 {num_orders} 个订单...")
    
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=50) as executor:  # 限制最大并发数为50
        # 提交所有任务
        future_to_order = {
            executor.submit(create_single_order, client, api_key_id, order_params, i+1): i+1 
            for i in range(num_orders)
        }
        
        # 收集结果
        for future in as_completed(future_to_order):
            order_id = future_to_order[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"❌ 订单 {order_id} 执行异常: {str(e)}")
                results.append({'success': False, 'order_id': order_id, 'error': str(e)})
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 统计结果
    success_count = sum(1 for r in results if r.get('success', False))
    failed_count = len(results) - success_count
    
    logger.info(f"📊 并发执行完成 - 总订单: {len(results)}, 成功: {success_count}, 失败: {failed_count}, 耗时: {duration:.2f}秒")
    
    return results


api_key, api_secret,api_key_id = get_api_key()

# client = Client(api_key, api_secret, base_url="http://127.0.0.1:8000/strategy-api")
client = Client(api_key, api_secret, base_url="https://testapiqe.ziyang-huang.com/strategy-api")
# client = Client(api_key, api_secret)

# 可选：显示所有可用的枚举值
# show_available_enums()

try:
    # ====================================================================
    # 并发创建订单测试 - 100并发运行10轮，随机主流symbol
    # ====================================================================
    logger.info("=" * 80)
    logger.info("🚀 开始并发订单创建测试 - 100并发运行10轮，随机主流symbol")
    logger.info("=" * 80)
    
    # 订单参数
    startTime = "2025-10-31T23:30:00+08:00"
    endTime = "2025-11-01T01:54:00+08:00"
    orderNotional = 0.1
    
    order_params = {
        'startTime': startTime,
        'endTime': endTime,
        'totalQuantity': orderNotional
    }
    
    # 总体统计
    total_rounds = 1
    orders_per_round = 1
    all_results = []
    round_stats = []
    
    logger.info(f"📋 测试配置: {total_rounds}轮 × {orders_per_round}订单 = {total_rounds * orders_per_round}个订单")
    logger.info(f"🎯 随机Symbol池: {len(MAIN_SYMBOLS)}个主流交易对")
    logger.info(f"⚙️  最大并发数: 50")
    
    # 执行10轮并发测试
    for round_num in range(1, total_rounds + 1):
        logger.info(f"\n🔄 第 {round_num}/{total_rounds} 轮开始...")
        round_start_time = time.time()
        
        # 执行当前轮的并发订单创建
        round_results = run_concurrent_orders(client, api_key_id, order_params, orders_per_round)
        
        round_end_time = time.time()
        round_duration = round_end_time - round_start_time
        
        # 统计当前轮结果
        round_success = sum(1 for r in round_results if r.get('success', False))
        round_failed = len(round_results) - round_success
        round_stats.append({
            'round': round_num,
            'success': round_success,
            'failed': round_failed,
            'duration': round_duration
        })
        
        all_results.extend(round_results)
        
        logger.info(f"📊 第 {round_num} 轮完成 - 成功: {round_success}, 失败: {round_failed}, 耗时: {round_duration:.2f}秒")
        
        # 轮次间短暂休息
        if round_num < total_rounds:
            logger.info("⏸️  轮次间休息2秒...")
            time.sleep(2)
    
    # ====================================================================
    # 最终统计报告
    # ====================================================================
    logger.info("\n" + "=" * 80)
    logger.info("📈 最终测试报告")
    logger.info("=" * 80)
    
    # 总体统计
    total_orders = len(all_results)
    total_success = sum(1 for r in all_results if r.get('success', False))
    total_failed = total_orders - total_success
    success_rate = (total_success / total_orders * 100) if total_orders > 0 else 0
    
    # 计算总耗时
    total_duration = sum(stat['duration'] for stat in round_stats)
    avg_duration_per_round = total_duration / len(round_stats) if round_stats else 0
    
    # Symbol使用统计
    symbol_usage = {}
    for result in all_results:
        if 'symbol' in result:
            symbol = result['symbol']
            symbol_usage[symbol] = symbol_usage.get(symbol, 0) + 1
    
    # 按使用次数排序
    top_symbols = sorted(symbol_usage.items(), key=lambda x: x[1], reverse=True)[:10]
    
    logger.info(f"📊 总体统计:")
    logger.info(f"   • 总订单数: {total_orders}")
    logger.info(f"   • 成功订单: {total_success}")
    logger.info(f"   • 失败订单: {total_failed}")
    logger.info(f"   • 成功率: {success_rate:.2f}%")
    logger.info(f"   • 总耗时: {total_duration:.2f}秒")
    logger.info(f"   • 平均每轮耗时: {avg_duration_per_round:.2f}秒")
    
    logger.info(f"\n📈 轮次详情:")
    for stat in round_stats:
        round_success_rate = (stat['success'] / orders_per_round * 100) if orders_per_round > 0 else 0
        logger.info(f"   第{stat['round']:2d}轮: 成功{stat['success']:3d}, 失败{stat['failed']:3d}, 成功率{round_success_rate:5.1f}%, 耗时{stat['duration']:6.2f}秒")
    
    logger.info(f"\n🎯 热门Symbol使用统计 (前10名):")
    for i, (symbol, count) in enumerate(top_symbols, 1):
        usage_rate = (count / total_orders * 100) if total_orders > 0 else 0
        logger.info(f"   {i:2d}. {symbol:10s}: {count:3d}次 ({usage_rate:5.1f}%)")
    
    # 错误统计
    error_stats = {}
    for result in all_results:
        if not result.get('success', False) and 'error' in result:
            error = result['error']
            error_stats[error] = error_stats.get(error, 0) + 1
    
    if error_stats:
        logger.info(f"\n❌ 错误统计:")
        for error, count in sorted(error_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"   • {error}: {count}次")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ 并发订单创建测试完成!")
    logger.info("=" * 80)
    
    # # Create a POV order using enums
    # logger.info("\n示例2: 使用枚举创建 POV 合约订单")
    # response = client.create_master_order(
    #     algorithm=Algorithm.TWAP,                       # POV 算法
    #     exchange=Exchange.BINANCE,
    #     symbol="CFXUSDT",
    #     marketType=MarketType.SPOT,                    # 合约市场
    #     side=OrderSide.SELL,                          # 卖出
    #     apiKeyId=api_key_id,
    #     orderNotional=orderNotional,                            # $1000 notional value
    #     strategyType=StrategyType.TWAP_1,                # POV 策略
    #     startTime=startTime,
    #     endTime=endTime,
    #     executionDuration="5",
    #     marginType=MarginType.U,                      # U本位保证金
    #     reduceOnly=False,
    #     mustComplete=True,
    #     notes="POV 合约订单示例",
    #     tailOrderProtection=True,
    #     isMargin=True
    # )
    # logger.info(f"POV order response: {response}")

    
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
