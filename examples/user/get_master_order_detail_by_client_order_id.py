#!/usr/bin/env python

import logging

from qe.user import User as Client
from qe.lib.utils import config_logging
from qe.error import ClientError, APIError

from examples.utils.prepare_env import get_api_key

config_logging(logging, logging.DEBUG)
logger = logging.getLogger(__name__)

api_key, api_secret, api_key_id = get_api_key()

# client = Client(api_key, api_secret, base_url="http://127.0.0.1:8000/strategy-api")
# client = Client(api_key, api_secret, base_url="https://testapiqe.ziyang-huang.com/strategy-api")
client = Client(api_key, api_secret)

try:
    # Example 1: Get master order detail by client_order_id
    # This assumes you have created an order with a clientOrderId
    client_order_id = "my-custom-order-id-001"
    
    logger.info(f"Fetching master order detail by client_order_id: {client_order_id}")
    response = client.get_master_order_detail_by_client_order_id(
        clientOrderId=client_order_id
    )
    
    master_order = response.get('masterOrder')
    if master_order:
        logger.info("=" * 60)
        logger.info("Master Order Details:")
        logger.info("=" * 60)
        logger.info(f"Master Order ID: {master_order.get('masterOrderId')}")
        logger.info(f"Client Order ID: {master_order.get('clientOrderId', 'N/A')}")
        logger.info(f"Algorithm: {master_order.get('algorithm')}")
        logger.info(f"Algorithm Type: {master_order.get('algorithmType')}")
        logger.info(f"Strategy Type: {master_order.get('strategyType', 'N/A')}")
        logger.info(f"Exchange: {master_order.get('exchange')}")
        logger.info(f"Symbol: {master_order.get('symbol')}")
        logger.info(f"Market Type: {master_order.get('marketType')}")
        logger.info(f"Side: {master_order.get('side')}")
        logger.info(f"Status: {master_order.get('status')}")
        logger.info(f"Total Quantity: {master_order.get('totalQuantity', 0)}")
        logger.info(f"Filled Quantity: {master_order.get('filledQuantity', 0)}")
        logger.info(f"Order Notional: {master_order.get('orderNotional', 0)}")
        logger.info(f"Average Price: {master_order.get('averagePrice', 0)}")
        logger.info(f"Completion Progress: {master_order.get('completionProgress', 0)}%")
        logger.info(f"Execution Duration: {master_order.get('executionDuration', 'N/A')} minutes")
        if master_order.get('executionDurationSeconds'):
            logger.info(f"Execution Duration (seconds): {master_order.get('executionDurationSeconds')} seconds")
        logger.info(f"Start Time: {master_order.get('startTime', 'N/A')}")
        logger.info(f"End Time: {master_order.get('endTime', 'N/A')}")
        logger.info(f"Created At: {master_order.get('createdAt', 'N/A')}")
        logger.info(f"Updated At: {master_order.get('updatedAt', 'N/A')}")
        logger.info(f"Notes: {master_order.get('notes', 'N/A')}")
        maker_rate = master_order.get('makerRate', 0)
        logger.info(f"Maker Rate: {maker_rate * 100:.2f}%" if maker_rate else "Maker Rate: 0.00%")
        logger.info(f"Tail Order Protection: {master_order.get('tailOrderProtection', False)}")
        logger.info(f"Enable Make: {master_order.get('enableMake', False)}")
        logger.info("=" * 60)
    else:
        logger.warning("No master order found in response")
    
    # Example 2: First create an order with clientOrderId, then query it
    logger.info("\n" + "=" * 60)
    logger.info("Example: Create order with clientOrderId and then query it")
    logger.info("=" * 60)
    
    # Note: This is a demonstration. In practice, you would:
    # 1. Create an order with clientOrderId using create_master_order()
    # 2. Then query it using get_master_order_detail_by_client_order_id()
    
    # Example workflow (commented out - uncomment and modify as needed):
    # from qe.lib import Algorithm, Exchange, MarketType, OrderSide, StrategyType
    # 
    # create_response = client.create_master_order(
    #     algorithm=Algorithm.TWAP,
    #     exchange=Exchange.BINANCE,
    #     symbol="BTCUSDT",
    #     marketType=MarketType.SPOT,
    #     side=OrderSide.BUY,
    #     apiKeyId=api_key_id,
    #     orderNotional=100,
    #     executionDuration=30,
    #     strategyType=StrategyType.TWAP_1,
    #     clientOrderId="demo-order-001"  # Set custom client order ID
    # )
    # 
    # if create_response.get('success'):
    #     master_order_id = create_response.get('masterOrderId')
    #     logger.info(f"Order created with masterOrderId: {master_order_id}")
    #     
    #     # Now query by clientOrderId
    #     detail_response = client.get_master_order_detail_by_client_order_id(
    #         clientOrderId="demo-order-001"
    #     )
    #     logger.info(f"Retrieved order by clientOrderId: {detail_response.get('masterOrder', {}).get('masterOrderId')}")
    
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
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
