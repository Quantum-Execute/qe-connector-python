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
    # Get user new listen key
    response = client.create_listen_key()
    logger.info(f"Total master orders: {response.get('total', 0)}")

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
