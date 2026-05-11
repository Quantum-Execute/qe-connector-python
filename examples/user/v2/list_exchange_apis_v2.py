#!/usr/bin/env python
"""V2 ``GET /strategy-api/user/exchange/v2/exchange-apis`` 示例。

V2 出参隐藏 ``verificationMethod`` 与 ``balance``；其余字段与 V1 相同。
"""
from __future__ import annotations

import logging

from qe.user import User as Client
from qe.lib.utils import config_logging
from qe.lib.trading_v2_types import ExchangeApiListV2Reply
from qe.error import APIError, ClientError

from examples.utils.prepare_env import get_api_key


config_logging(logging, logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    api_key, api_secret, _ = get_api_key()
    client = Client(
        api_key,
        api_secret,
        base_url="https://testapiqe.ziyang-huang.com/strategy-api",
    )

    raw = client.list_exchange_apis_v2(page=1, pageSize=50, exchange="Binance")
    reply = ExchangeApiListV2Reply.from_dict(raw)

    logger.info("V2 exchange APIs total=%s page=%s pageSize=%s",
                reply.total, reply.page, reply.pageSize)
    for item in reply.items:
        logger.info(
            "id=%s exchange=%s account=%s status=%s isValid=%s isTradingEnabled=%s isDefault=%s isPm=%s",
            item.id,
            item.exchange,
            item.accountName,
            item.status,
            item.isValid,
            item.isTradingEnabled,
            item.isDefault,
            item.isPm,
        )


if __name__ == "__main__":
    try:
        main()
    except APIError as e:
        logger.error("API Error: code=%s reason=%s msg=%s trace=%s", e.code, e.reason, e.message, e.trace_id)
    except ClientError as e:
        logger.error("Client Error: status=%s code=%s msg=%s", e.status_code, e.error_code, e.error_message)
