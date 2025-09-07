#!/usr/bin/env python

import logging
from qe.status import Status as Client
from qe.lib.utils import config_logging
from qe.error import ClientError, APIError

config_logging(logging, logging.DEBUG)
logger = logging.getLogger(__name__)

client = Client()

try:
    # Ping the server
    response = client.ping()
    logger.info("Ping successful - server is reachable")
    
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
