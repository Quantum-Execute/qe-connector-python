#!/usr/bin/env python

import logging
import time
from datetime import datetime, timedelta
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
    # Get all TCA analysis data
    response = client.get_tca_analysis()
    logger.info(f"Total TCA analysis items: {len(response) if isinstance(response, list) else 0}")
    
    # Get TCA analysis with time range
    # Calculate time range: last 7 days
    end_time = int(time.time() * 1000)  # Current time in milliseconds
    start_time = int((time.time() - 365 * 24 * 3600) * 1000)  # 7 days ago
    
    response = client.get_tca_analysis(
        startTime=start_time,
        endTime=end_time
    )
    logger.info(f"TCA analysis items in last 7 days: {len(response) if isinstance(response, list) else 0}")
    
    # Get TCA analysis with symbol filter
    response = client.get_tca_analysis(
        symbol="BTCUSDT",
        startTime=start_time,
        endTime=end_time
    )
    
    if isinstance(response, list) and len(response) > 0:
        logger.info(f"Found {len(response)} TCA analysis items for BTCUSDT")
        
        # Display key metrics from first item
        first_item = response[0]
        logger.info("Sample TCA Analysis Data:")
        logger.info(f"  Master Order ID: {first_item.get('master_order_id', 'N/A')}")
        logger.info(f"  Symbol: {first_item.get('symbol', 'N/A')}")
        logger.info(f"  Category: {first_item.get('category', 'N/A')}")
        logger.info(f"  Side: {first_item.get('side', 'N/A')}")
        logger.info(f"  Strategy: {first_item.get('strategy', 'N/A')}")
        
        # Execution metrics
        if first_item.get('execution_rate') is not None:
            logger.info(f"  Execution Rate: {first_item.get('execution_rate') * 100:.2f}%")
        if first_item.get('make_fill_rate') is not None:
            logger.info(f"  Maker Fill Rate: {first_item.get('make_fill_rate') * 100:.2f}%")
        if first_item.get('take_fill_rate') is not None:
            logger.info(f"  Taker Fill Rate: {first_item.get('take_fill_rate') * 100:.2f}%")
        
        # Slippage metrics
        if first_item.get('twap_slippage_bps') is not None:
            logger.info(f"  TWAP Slippage: {first_item.get('twap_slippage_bps')} bps")
        if first_item.get('vwap_slippage_bps') is not None:
            logger.info(f"  VWAP Slippage: {first_item.get('vwap_slippage_bps')} bps")
        
        # PnL metrics
        if first_item.get('pnl_theory') is not None:
            logger.info(f"  Theoretical PnL: {first_item.get('pnl_theory')}")
        if first_item.get('pnl_realized') is not None:
            logger.info(f"  Realized PnL: {first_item.get('pnl_realized')}")
        if first_item.get('impact') is not None:
            logger.info(f"  Impact: {first_item.get('impact')}")
        
        # Price and quantity
        if first_item.get('weighted_avg_price') is not None:
            logger.info(f"  Weighted Avg Price: {first_item.get('weighted_avg_price')}")
        if first_item.get('order_qty') is not None:
            logger.info(f"  Order Quantity: {first_item.get('order_qty')}")
        if first_item.get('filled_qty') is not None:
            logger.info(f"  Filled Quantity: {first_item.get('filled_qty')}")
        
        # Execution duration
        if first_item.get('execution_duration') is not None:
            duration_minutes = first_item.get('execution_duration') / 60
            logger.info(f"  Execution Duration: {duration_minutes:.2f} minutes")
        
        # Timestamps
        if first_item.get('mo_created_at'):
            logger.info(f"  Order Created At: {first_item.get('mo_created_at')}")
        if first_item.get('created_at'):
            logger.info(f"  TCA Created At: {first_item.get('created_at')}")
    
    # Get TCA analysis with category filter
    response = client.get_tca_analysis(
        category="spot",
        startTime=start_time,
        endTime=end_time
    )
    logger.info(f"TCA analysis items for spot category: {len(response) if isinstance(response, list) else 0}")
    
    # Get TCA analysis with apikey filter
    if api_key_id:
        response = client.get_tca_analysis(
            apikey=api_key_id,
            startTime=start_time,
            endTime=end_time
        )
        logger.info(f"TCA analysis items for API key {api_key_id}: {len(response) if isinstance(response, list) else 0}")
    
    # Aggregate statistics
    if isinstance(response, list) and len(response) > 0:
        total_notional = 0
        total_maker_rate = 0
        total_twap_slippage = 0
        count_with_maker = 0
        count_with_slippage = 0
        
        for item in response:
            if item.get('notional') is not None:
                total_notional += item.get('notional', 0)
            if item.get('make_fill_rate') is not None:
                total_maker_rate += item.get('make_fill_rate', 0)
                count_with_maker += 1
            if item.get('twap_slippage_bps') is not None:
                total_twap_slippage += item.get('twap_slippage_bps', 0)
                count_with_slippage += 1
        
        logger.info("\nAggregate Statistics:")
        logger.info(f"  Total Notional: {total_notional:.2f}")
        if count_with_maker > 0:
            avg_maker_rate = (total_maker_rate / count_with_maker) * 100
            logger.info(f"  Average Maker Rate: {avg_maker_rate:.2f}%")
        if count_with_slippage > 0:
            avg_slippage = total_twap_slippage / count_with_slippage
            logger.info(f"  Average TWAP Slippage: {avg_slippage:.2f} bps")
    
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

