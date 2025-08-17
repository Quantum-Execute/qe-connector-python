#!/usr/bin/env python

import logging
from qe.user import User as Client
from qe.lib.utils import config_logging
from qe.error import ClientError, APIError

from examples.utils.prepare_env import get_api_key

config_logging(logging, logging.DEBUG)
logger = logging.getLogger(__name__)

api_key, api_secret = get_api_key()

client = Client(api_key, api_secret)

try:
    # Get all order fills
    response = client.get_order_fills()
    logger.info(f"Total order fills: {response.get('total', 0)}")
    
    # Get with filters
    response = client.get_order_fills(
        page=1,
        pageSize=50,
        masterOrderId="12345678",  # Filter by specific master order
        symbol="BTCUSDT",
        startTime="2024-01-01T00:00:00Z",
        endTime="2024-12-31T23:59:59Z"
    )
    
    total_value = 0
    total_fee = 0
    
    for fill in response.get('items', []):
        logger.info(
            "Fill ID: {}, Time: {}, Symbol: {}, Side: {}, "
            "Qty: {}, Price: {}, Value: {}, Fee: {}".format(
                fill['id'],
                fill['orderCreatedTime'],
                fill['symbol'],
                fill['side'],
                fill['filledQuantity'],
                fill['avgPrice'],
                fill['filledValue'],
                fill['fee']
            )
        )
        total_value += fill.get('filledValue', 0)
        total_fee += fill.get('fee', 0)
    
    logger.info(f"Total Value: {total_value}, Total Fees: {total_fee}")
    
    # Get fills by sub order ID
    response = client.get_order_fills(
        subOrderId="sub_order_123"
    )
    logger.info(f"Fills for sub order: {len(response.get('items', []))}")
    
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
