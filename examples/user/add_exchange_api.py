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
    # Add a new exchange API
    response = client.add_exchange_api(
        accountName="My Trading Account",
        exchange="binance",
        apiKey="your_exchange_api_key",
        apiSecret="your_exchange_api_secret",
        enableTrading=True,
        verificationMethod="RSA"  # or "HMAC"
    )
    
    if response.get('success'):
        logger.info(f"Exchange API added successfully. ID: {response.get('id')}")
    else:
        logger.error(f"Failed to add exchange API: {response.get('message')}")
    
    # Example with passphrase (for exchanges like OKX)
    response = client.add_exchange_api(
        accountName="OKX Account",
        exchange="okx",
        apiKey="your_okx_api_key",
        apiSecret="your_okx_api_secret",
        passphrase="your_passphrase",
        enableTrading=False  # Read-only access
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
