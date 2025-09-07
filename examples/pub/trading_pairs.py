#!/usr/bin/env python

import logging
from qe.pub import Pub as Client
from qe.lib.utils import config_logging
from qe.error import ClientError, APIError
from qe.lib import TradingPairMarketType

config_logging(logging, logging.DEBUG)
logger = logging.getLogger(__name__)

client = Client()

try:
    # Get all trading pairs
    response = client.trading_pairs()
    logger.info(f"Total trading pairs: {response.get('total', 0)}")
    
    # Get trading pairs with pagination
    response = client.trading_pairs(page=1, pageSize=10)
    logger.info(f"Page 1 trading pairs: {len(response.get('items', []))}")
    
    for pair in response.get('items', []):
        logger.info(f"Symbol: {pair['symbol']}, Exchange: {pair['exchange']}, Market: {pair['marketType']}")
    
    # Filter by exchange
    response = client.trading_pairs(exchange="Binance")
    logger.info(f"Binance trading pairs: {len(response.get('items', []))}")
    
    # Filter by market type using string
    response = client.trading_pairs(marketType="SPOT")
    logger.info(f"Spot trading pairs (string): {len(response.get('items', []))}")
    
    # Filter by market type using enum (recommended)
    response = client.trading_pairs(marketType=TradingPairMarketType.SPOT)
    logger.info(f"Spot trading pairs (enum): {len(response.get('items', []))}")
    
    # Filter by futures market type using enum
    response = client.trading_pairs(marketType=TradingPairMarketType.FUTURES)
    logger.info(f"Futures trading pairs (enum): {len(response.get('items', []))}")
    
    # Filter by coin type
    response = client.trading_pairs(isCoin=True)
    logger.info(f"Coin trading pairs: {len(response.get('items', []))}")
    
    # Combined filters with enum
    response = client.trading_pairs(
        exchange="Binance",
        marketType=TradingPairMarketType.SPOT,
        page=1,
        pageSize=5
    )
    logger.info(f"Filtered trading pairs: {len(response.get('items', []))}")
    
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
