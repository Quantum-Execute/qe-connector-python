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
    # List all exchange APIs
    response = client.list_exchange_apis()
    logger.info(f"Total exchange APIs: {response.get('total', 0)}")
    
    # List with pagination
    response = client.list_exchange_apis(page=1, pageSize=10)
    for api in response.get('items', []):
        logger.info(f"Exchange: {api['exchange']}, Account: {api['accountName']}, Status: {api['status']}")
    
    # Filter by exchange
    response = client.list_exchange_apis(exchange="Binance")
    logger.info(f"Binance APIs: {len(response.get('items', []))}")
    
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
