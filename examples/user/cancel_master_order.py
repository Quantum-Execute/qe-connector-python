#!/usr/bin/env python

import logging
from qe.user import User as Client
from qe.lib.utils import config_logging
from qe.error import ClientError, APIError

from examples.utils.prepare_env import get_api_key

config_logging(logging, logging.DEBUG)
logger = logging.getLogger(__name__)

api_key, api_secret,api_key_id = get_api_key()

# client = Client(api_key, api_secret, base_url="http://127.0.0.1:8000/strategy-api")
# client = Client(api_key, api_secret, base_url="https://testapiqe.ziyang-huang.com/strategy-api")
client = Client(api_key, api_secret)


try:
    # First, get active orders to find one to cancel
    # response = client.get_master_orders(
    #     status="WORKING",  # Get only active orders
    #     page=1,
    #     pageSize=1
    # )
    #
    # if response.get('items'):
    #     order_to_cancel = response['items'][0]
    #     master_order_id = 'BATUSDT-20251030-1983897337069973504'
    #
    #     logger.info(f"Cancelling order: {master_order_id}")
    #     logger.info(f"Symbol: {order_to_cancel['symbol']}, Side: {order_to_cancel['side']}")
    #     logger.info(f"Filled: {order_to_cancel['filledQuantity']}/{order_to_cancel['totalQuantity']}")
    #
    #     # Cancel the order
    #     cancel_response = client.cancel_master_order(
    #         masterOrderId=master_order_id,
    #         reason="User requested cancellation"
    #     )
    #
    #     if cancel_response.get('success'):
    #         logger.info(f"Order cancelled successfully: {cancel_response.get('message')}")
    #     else:
    #         logger.error(f"Failed to cancel order: {cancel_response.get('message')}")
    # else:
    #     logger.info("No active orders found to cancel")
    #
    # Example: Cancel specific order by ID
    specific_order_id = "BATUSDT-20251030-1983897337069973504"
    try:
        response = client.cancel_master_order(
            masterOrderId=specific_order_id,
            reason="Market conditions changed"
        )
        logger.info(f"Cancel result: {response}")
    except APIError as error:
        if error.code == 404:
            logger.error(f"Order {specific_order_id} not found or already completed")
        else:
            raise
    
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
