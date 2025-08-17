#!/usr/bin/env python

import logging
from qe.user import User as Client
from qe.lib.utils import config_logging
from qe.error import ClientError, APIError

from examples.utils.prepare_env import get_api_key

config_logging(logging, logging.DEBUG)
logger = logging.getLogger(__name__)

api_key, api_secret = get_api_key()

# client = Client(api_key, api_secret, base_url="http://127.0.0.1:8000/strategy-api")
client = Client(api_key, api_secret)

try:
    # Create a TWAP order (based on Go test example)
    response = client.create_master_order(
        algorithm="TWAP",
        algorithmType="TWAP",
        exchange="Binance",  # Note: capitalized as in Go example
        symbol="BTCUSDT",
        marketType="SPOT",
        side="buy",  # lowercase as in Go example
        apiKeyId="0b057efbbcea46db885ae66c98d20849",  # Get from list_exchange_apis
        orderNotional=200,  # $200 notional value
        strategyType="TWAP-1",
        startTime="2025-08-17T19:34:34+08:00",
        endTime="2025-08-19T01:44:35+08:00",
        executionDuration="5",  # 5 seconds intervals
        mustComplete=True,
        reduceOnly=False,
        worstPrice=-1,  # -1 means no worst price limit
        upTolerance="-1",
        lowTolerance="-1"
    )
    
    if response.get('success'):
        logger.info(f"Master order created successfully. ID: {response.get('masterOrderId')}")
    else:
        logger.error(f"Failed to create order: {response.get('message')}")
    
    # Create a VWAP order with notional value
    response = client.create_master_order(
        algorithm="TWAP",
        algorithmType="TWAP",
        exchange="Binance",  # Note: capitalized as in Go example
        symbol="BTCUSDT",
        marketType="SPOT",
        side="sell",  # lowercase as in Go example
        apiKeyId="0b057efbbcea46db885ae66c98d20849",  # Get from list_exchange_apis
        orderNotional=200,  # $200 notional value
        strategyType="TWAP-1",
        startTime="2025-08-17T19:34:34+08:00",
        endTime="2025-08-19T01:44:35+08:00",
        executionDuration="5",  # 5 seconds intervals
        mustComplete=True,
        reduceOnly=False,
        worstPrice=-1,  # -1 means no worst price limit
        upTolerance="-1",
        lowTolerance="-1"
    )
    logger.info(response)
    
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
