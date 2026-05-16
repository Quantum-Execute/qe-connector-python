#!/usr/bin/env python
"""V2 strategy-api end-to-end demo.

Walks through the V2 happy path against `/strategy-api/.../v2/...`:

1. List exchange APIs (V2)
2. Create a V2 master order (TWAP, SPOT, sell)
3. List master orders (V2)
4. Fetch the just-created master order (V2)
5. Fetch its order fills (V2)
6. Cancel the master order (V2)

Compared with V1, V2 hides internal fields (``apiKey/apiKeyName``,
``balance``, ``fee``, …), keeps ``tradingAccount`` on master orders for
display, and renames a few:
``cumFilledQty/cumFilledNotional/avgFilledPrice``, ``orderId`` (was
``subOrderId``) and ``filledNotional`` (was ``filledValue``).

Run::

    python -m examples.user.v2.end_to_end_v2
"""
from __future__ import annotations

import logging
import time

from qe.user import User as Client
from qe.lib.utils import config_logging
from qe.lib.trading_enums import Algorithm, Exchange, MarketType, OrderSide
from qe.lib.trading_v2_types import (
    CreateMasterOrderV2Reply,
    CreateMasterOrderV2Request,
    ExchangeApiListV2Reply,
    MasterOrderListV2Reply,
    MasterOrderStatusV2,
    MasterOrderV2Info,
    OrderFillListV2Reply,
)
from qe.error import APIError, ClientError

from examples.utils.prepare_env import get_api_key

config_logging(logging, logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    api_key, api_secret, api_key_id = get_api_key()

    # `base_url` already contains the `/strategy-api` prefix; the SDK appends
    # `/user/.../v2/...` per V2 spec.
    client = Client(
        api_key,
        api_secret,
        base_url="https://testapiqe.ziyang-huang.com/strategy-api",
    )

    # ----- 1. Exchange API keys -----------------------------------------
    raw = client.list_exchange_apis_v2(page=1, pageSize=20)
    apis = ExchangeApiListV2Reply.from_dict(raw)
    logger.info("V2 exchange APIs: total=%s, page items=%s", apis.total, len(apis.items))
    for k in apis.items[:3]:
        logger.info("  - id=%s exchange=%s account=%s pm=%s", k.id, k.exchange, k.accountName, k.isPm)

    # ----- 2. Create master order ---------------------------------------
    req = CreateMasterOrderV2Request(
        apiKeyId=api_key_id,
        exchange=Exchange.BINANCE.value,
        marketType=MarketType.SPOT.value,
        symbol="DOGEUSDT",
        side=OrderSide.SELL.value,
        algorithm=Algorithm.TWAP.value,
        executionDurationSeconds=120,
        # 立即执行：不填 startTimeMs。
        totalQuantity="1000",
        worstPrice="0.05",
        mustComplete=True,
        tailOrderProtection=True,
        clientOrderId=f"PY-V2-{int(time.time() * 1000)}",
        notes="frontend v2 sdk demo",
    )
    create_raw = client.create_master_order_v2(req)
    created = CreateMasterOrderV2Reply.from_dict(create_raw)
    logger.info(
        "V2 created: masterOrderId=%s clientOrderId=%s status=%s",
        created.masterOrderId,
        created.clientOrderId,
        created.status,
    )

    # ----- 3. List master orders ----------------------------------------
    list_raw = client.list_master_orders_v2(
        page=1,
        pageSize=20,
        status=MasterOrderStatusV2.PROCESSING.value,
    )
    orders = MasterOrderListV2Reply.from_dict(list_raw)
    logger.info("V2 active master orders: total=%s", orders.total)
    for o in orders.items[:5]:
        logger.info(
            "  - %s %s %s/%s side=%s status=%s cumFilled=%s/%s avg=%s",
            o.masterOrderId,
            o.algorithm,
            o.baseCurrency,
            o.quoteCurrency,
            o.side,
            o.status,
            o.cumFilledQty,
            o.totalQuantity,
            o.avgFilledPrice,
        )

    # ----- 4. Fetch detail ----------------------------------------------
    detail_raw = client.get_master_order_v2(created.masterOrderId)
    detail = MasterOrderV2Info.from_dict(detail_raw)
    logger.info(
        "V2 detail: status=%s startTimeMs=%s finishedMs=%s worstPrice=%s commission=%s",
        detail.status,
        detail.startTimeMs,
        detail.finishedMs,
        detail.worstPrice,
        detail.commission,
    )

    # ----- 5. Fetch order fills -----------------------------------------
    fills_raw = client.list_order_fills_v2(
        masterOrderId=created.masterOrderId,
        page=1,
        pageSize=20,
    )
    fills = OrderFillListV2Reply.from_dict(fills_raw)
    logger.info("V2 fills: total=%s", fills.total)
    for f in fills.items[:5]:
        logger.info(
            "  - orderId=%s type=%s qty=%s filledQty=%s filledNotional=%s avg=%s status=%s",
            f.orderId,
            f.orderType,
            f.quantity,
            f.filledQuantity,
            f.filledNotional,
            f.averagePrice,
            f.status,
        )

    # ----- 6. Cancel the master order -----------------------------------
    cancel_raw = client.cancel_master_order_v2(
        created.masterOrderId,
        reason="end-to-end demo cleanup",
    )
    logger.info("V2 cancel reply: %s", cancel_raw)


if __name__ == "__main__":
    try:
        main()
    except APIError as e:
        logger.error("API Error: code=%s reason=%s msg=%s trace=%s", e.code, e.reason, e.message, e.trace_id)
    except ClientError as e:
        logger.error("Client Error: status=%s code=%s msg=%s", e.status_code, e.error_code, e.error_message)
