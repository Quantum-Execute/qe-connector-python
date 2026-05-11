#!/usr/bin/env python
"""V2 批量取消母单示例。

``PUT /strategy-api/user/trading/v2/master-orders/batch-cancel``

返回 ``{"successCount": N, "failedOrders": [{masterOrderId, reason}, ...]}``。
"""
from __future__ import annotations

import logging

from qe.user import User as Client
from qe.lib.utils import config_logging
from qe.lib.trading_v2_types import (
    BatchCancelV2Reply,
    MasterOrderListV2Reply,
    MasterOrderStatusV2,
)
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

    # 收集当前正在执行 + 等待中的母单一次性批量取消。
    candidate_ids: list[str] = []
    for status in (MasterOrderStatusV2.PROCESSING.value, MasterOrderStatusV2.WAITING.value):
        raw = client.list_master_orders_v2(page=1, pageSize=100, status=status)
        page = MasterOrderListV2Reply.from_dict(raw)
        candidate_ids.extend(o.masterOrderId for o in page.items if o.masterOrderId)

    if not candidate_ids:
        logger.info("nothing to cancel")
        return

    logger.info("batch cancelling %d master orders", len(candidate_ids))
    raw_reply = client.batch_cancel_master_orders_v2(
        candidate_ids,
        reason="cleanup via SDK demo",
    )
    reply = BatchCancelV2Reply.from_dict(raw_reply)
    logger.info("V2 batch-cancel: success=%s failed=%s", reply.successCount, len(reply.failedOrders))
    for failed in reply.failedOrders:
        logger.info("  failed masterOrderId=%s reason=%s", failed.masterOrderId, failed.reason)


if __name__ == "__main__":
    try:
        main()
    except APIError as e:
        logger.error("API Error: code=%s reason=%s msg=%s trace=%s", e.code, e.reason, e.message, e.trace_id)
    except ClientError as e:
        logger.error("Client Error: status=%s code=%s msg=%s", e.status_code, e.error_code, e.error_message)
