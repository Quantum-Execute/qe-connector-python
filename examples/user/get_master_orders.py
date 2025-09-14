#!/usr/bin/env python

import logging

from qe.lib import MasterOrderStatus
from qe.user import User as Client
from qe.lib.utils import config_logging
from qe.error import ClientError, APIError

from examples.utils.prepare_env import get_api_key

config_logging(logging, logging.DEBUG)
logger = logging.getLogger(__name__)

api_key, api_secret = get_api_key()

client = Client(api_key, api_secret)

try:
    # Get all master orders
    response = client.get_master_orders()
    logger.info(f"Total master orders: {response.get('total', 0)}")
    
    # Get with pagination and filters
    response = client.get_master_orders(
        page=1,
        pageSize=20,
        status=MasterOrderStatus.NEW,  # PENDING, WORKING, FILLED, CANCELLED, FAILED
        exchange="binance",
        symbol="BTCUSDT",
        startTime="2024-01-01T00:00:00Z",
        endTime="2024-12-31T23:59:59Z"
    )
    
    for order in response.get('items', []):
        logger.info(
            "Order ID: {}, Symbol: {}, Side: {}, Status: {}, "
            "Filled: {}/{}, Avg Price: {}".format(
                order['masterOrderId'],
                order['symbol'],
                order['side'],
                order['status'],
                order['filledQuantity'],
                order['totalQuantity'],
                order['averagePrice']
            )
        )
    
    # Get specific order details
    if response.get('items'):
        first_order = response['items'][0]
        logger.info(f"Algorithm: {first_order['algorithm']}")
        logger.info(f"Algorithm Type: {first_order['algorithmType']}")
        logger.info(f"Strategy Type: {first_order.get('strategyType', 'N/A')}")
        logger.info(f"Execution Duration: {first_order.get('executionDuration', 'N/A')} seconds")
        logger.info(f"Completion Progress: {first_order.get('completionProgress', 0)}%")
    
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
