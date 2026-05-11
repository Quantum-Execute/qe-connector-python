#!/usr/bin/env python
"""Quantum-Execute /strategy-api V2 end-to-end live test (Python SDK).

Runs all 11 V2 endpoints against the test environment and prints a
result summary table. Designed as the Python counterpart of
``qe-connector-go/cmd/v2_e2e``.

Credentials are read from ``qe-connector-python/examples/config.ini``
``[keys]`` section. Per parent-agent instruction the ``apiKeyId`` used
in ``create_master_order_v2`` is taken directly from the same
``api_key_id`` field — we do NOT pick one from the
``list_exchange_apis_v2`` response.

Run::

    cd qe-connector-python
    python -m examples.user.v2.full_e2e_v2
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

from qe.error import APIError, ClientError
from qe.lib.trading_enums import Algorithm, Exchange, MarketType, OrderSide
from qe.lib.trading_v2_types import (
    BatchCancelV2Reply,
    CreateMasterOrderV2Reply,
    CreateMasterOrderV2Request,
    ExchangeApiListV2Reply,
    MasterOrderListV2Reply,
    MasterOrderStatusV2,
    MasterOrderV2Info,
    OrderFillListV2Reply,
    UpdateMasterOrderV2Request,
)
from qe.lib.utils import config_logging
from qe.user import User as Client

from examples.utils.prepare_env import get_api_key

config_logging(logging, logging.INFO)
logger = logging.getLogger("v2_e2e")

BASE_URL = "https://testapiqe.ziyang-huang.com/strategy-api"
CLIENT_ORDER_ID_TAG = "PY-V2-"
SYMBOL = "DOGEUSDT"


@dataclass
class Result:
    name: str
    method: str
    path: str
    ok: bool = False
    skip: bool = False
    err: str = ""
    detail: str = ""

    def status(self) -> str:
        if self.skip:
            return "⏭ SKIP"
        return "✅" if self.ok else "❌"


def _short(value, max_len: int = 240) -> str:
    s = str(value)
    return s if len(s) <= max_len else s[:max_len] + "..."


def _err_str(e: Exception) -> str:
    if isinstance(e, APIError):
        return f"APIError code={e.code} reason={e.reason} message={e.message} traceId={e.trace_id}"
    if isinstance(e, ClientError):
        return f"ClientError status={e.status_code} code={e.error_code} msg={e.error_message}"
    return f"{type(e).__name__}: {e}"


def _print_step(idx: int, total: int, r: Result) -> None:
    logger.info(
        "[%d/%d] %s %s → %s | %s | err=%s",
        idx, total, r.method, r.path, r.status(), _short(r.detail), _short(r.err),
    )


def main() -> int:
    api_key, api_secret, api_key_id = get_api_key()
    logger.info("api_key=%s... api_key_id=%s base=%s", api_key[:6], api_key_id, BASE_URL)

    client = Client(api_key, api_secret, base_url=BASE_URL)
    client.timeout = 60  # per-request HTTP timeout

    results: List[Result] = []
    client_order_id = f"{CLIENT_ORDER_ID_TAG}{int(time.time() * 1000)}"
    batch_client_order_ids: List[str] = []

    # ──────────────────────────────────────────────────────────────────
    # 1) GET /user/exchange/v2/exchange-apis
    # ──────────────────────────────────────────────────────────────────
    r = Result(
        name="List Exchange APIs",
        method="GET",
        path="/user/exchange/v2/exchange-apis",
    )
    try:
        raw = client.list_exchange_apis_v2(page=1, pageSize=20)
        reply = ExchangeApiListV2Reply.from_dict(raw)
        r.ok = True
        sample = ""
        if reply.items:
            it = reply.items[0]
            sample = f" | sample=[id={it.id} exchange={it.exchange} valid={it.isValid} trading={it.isTradingEnabled}]"
        r.detail = f"total={reply.total} page={reply.page} pageSize={reply.pageSize} items={len(reply.items)}{sample}"
    except Exception as e:
        r.err = _err_str(e)
    _print_step(1, 11, r)
    results.append(r)

    # ──────────────────────────────────────────────────────────────────
    # 2) POST /user/trading/v2/master-orders — create the primary order
    #
    # `worstPrice` is set *above* current market (DOGE ~ $0.06, we use
    # $5.0) for a sell so the algorithm never finds a counterparty —
    # order stays in PROCESSING for the full 180s, leaving the
    # downstream pause/resume/update/cancel tests something live to act
    # on. Setting it low (0.01) would let it fill instantly.
    # ──────────────────────────────────────────────────────────────────
    first_moid: Optional[str] = None
    used_own_order = False  # True iff first_moid was created by *this* run
    r = Result(
        name="Create Master Order",
        method="POST",
        path="/user/trading/v2/master-orders",
    )
    try:
        req = CreateMasterOrderV2Request(
            apiKeyId=api_key_id,
            exchange=Exchange.BINANCE.value,
            marketType=MarketType.SPOT.value,
            symbol=SYMBOL,
            side=OrderSide.SELL.value,
            algorithm=Algorithm.TWAP.value,
            executionDurationSeconds=600,
            totalQuantity="10",
            worstPrice="5.0",
            mustComplete=False,
            clientOrderId=client_order_id,
            notes="v2 e2e py run",
        )
        raw = client.create_master_order_v2(req)
        reply = CreateMasterOrderV2Reply.from_dict(raw)
        first_moid = reply.masterOrderId
        if first_moid:
            used_own_order = True
        r.ok = True
        r.detail = f"masterOrderId={reply.masterOrderId} clientOrderId={reply.clientOrderId} status={reply.status}"
    except Exception as e:
        r.err = _err_str(e)
    _print_step(2, 11, r)
    results.append(r)

    # If create failed, try to grab an existing GO-V2-* / PY-V2-*
    # live master order so we can still exercise the remaining
    # single-order action steps. The list endpoint's server-side status
    # filter is not strict (it returns mixed statuses) so we re-check
    # each item's own ``status`` against the live set client-side.
    LIVE_STATUSES = {
        MasterOrderStatusV2.PROCESSING.value,
        MasterOrderStatusV2.WAITING.value,
        MasterOrderStatusV2.PAUSED.value,
        MasterOrderStatusV2.NEW.value,
    }
    if not first_moid:
        logger.info("create failed — fallback: looking for an existing live master order")
        candidates: List[MasterOrderV2Info] = []
        for status_val in (
            MasterOrderStatusV2.PROCESSING,
            MasterOrderStatusV2.WAITING,
            MasterOrderStatusV2.PAUSED,
            MasterOrderStatusV2.NEW,
        ):
            try:
                raw = client.list_master_orders_v2(
                    page=1, pageSize=100, status=status_val.value,
                )
                lst = MasterOrderListV2Reply.from_dict(raw)
                logger.info(
                    "fallback list(%s) → total=%s items=%d (server pageSize=%s)",
                    status_val.value, lst.total, len(lst.items), lst.pageSize,
                )
            except Exception as e:
                logger.info("fallback list(%s) failed: %s", status_val.value, _err_str(e))
                continue
            for it in lst.items:
                if not it.clientOrderId or not it.masterOrderId:
                    continue
                if it.status not in LIVE_STATUSES:
                    continue
                if not (
                    it.clientOrderId.startswith("GO-V2-")
                    or it.clientOrderId.startswith("PY-V2-")
                ):
                    continue
                candidates.append(it)
        # Prefer PROCESSING > WAITING > NEW > PAUSED, then most-recent
        # createdAt (descending). createdAt is RFC3339-ish so lexical
        # string sort works as a chronological sort.
        priority = {
            MasterOrderStatusV2.PROCESSING.value: 0,
            MasterOrderStatusV2.WAITING.value: 1,
            MasterOrderStatusV2.NEW.value: 2,
            MasterOrderStatusV2.PAUSED.value: 3,
        }
        candidates.sort(
            key=lambda it: (priority.get(it.status, 9), -1 * len(it.createdAt or ""), it.createdAt or ""),
        )
        # Within each (status) group, prefer larger createdAt strings (newest).
        candidates.sort(
            key=lambda it: (priority.get(it.status, 9), it.createdAt or ""),
            reverse=False,
        )
        # Simple final pass: pick the highest-priority status, then newest createdAt.
        if candidates:
            best_pri = min(priority.get(c.status, 9) for c in candidates)
            same_pri = [c for c in candidates if priority.get(c.status, 9) == best_pri]
            picked = max(same_pri, key=lambda it: it.createdAt or "")
            first_moid = picked.masterOrderId
            logger.info(
                "fallback picked masterOrderId=%s (clientOrderId=%s status=%s createdAt=%s)",
                first_moid, picked.clientOrderId, picked.status, picked.createdAt,
            )
        else:
            logger.info("fallback: no live GO-V2-*/PY-V2-* order found")

    # ──────────────────────────────────────────────────────────────────
    # 3) GET /user/trading/v2/master-orders
    # ──────────────────────────────────────────────────────────────────
    r = Result(
        name="List Master Orders",
        method="GET",
        path="/user/trading/v2/master-orders",
    )
    try:
        raw = client.list_master_orders_v2(
            page=1, pageSize=20, status=MasterOrderStatusV2.PROCESSING.value,
        )
        lst = MasterOrderListV2Reply.from_dict(raw)
        r.ok = True
        sample = ""
        if lst.items:
            it = lst.items[0]
            sample = f" | sample=[id={it.masterOrderId} symbol={it.symbol} side={it.side} status={it.status}]"
        r.detail = f"total={lst.total} page={lst.page} pageSize={lst.pageSize} items={len(lst.items)} (status=PROCESSING){sample}"
    except Exception as e:
        r.err = _err_str(e)
    _print_step(3, 11, r)
    results.append(r)

    # ──────────────────────────────────────────────────────────────────
    # 4) GET /user/trading/v2/master-orders/{masterOrderId}
    #
    # Response shape: ``{"masterOrder": {...fields...}}`` — extract the
    # nested object before mapping to MasterOrderV2Info. (Matches the
    # Go SDK's `GetMasterOrderDetailV2Reply.MasterOrder`.)
    # ──────────────────────────────────────────────────────────────────
    r = Result(
        name="Master Order Detail",
        method="GET",
        path="/user/trading/v2/master-orders/{masterOrderId}",
    )
    if not first_moid:
        r.skip = True
        r.detail = "no eligible master order"
    else:
        try:
            raw = client.get_master_order_v2(first_moid)
            inner = raw.get("masterOrder", raw) if isinstance(raw, dict) else {}
            mo = MasterOrderV2Info.from_dict(inner)
            r.ok = True
            r.detail = (
                f"id={mo.masterOrderId} symbol={mo.symbol} side={mo.side} "
                f"algo={mo.algorithm} status={mo.status} totalQty={mo.totalQuantity}"
            )
        except Exception as e:
            r.err = _err_str(e)
    _print_step(4, 11, r)
    results.append(r)

    # ──────────────────────────────────────────────────────────────────
    # 5) GET /user/trading/v2/master-orders/by-client-order-id/{clientOrderId}
    # ──────────────────────────────────────────────────────────────────
    r = Result(
        name="Detail by ClientOrderId",
        method="GET",
        path="/user/trading/v2/master-orders/by-client-order-id/{clientOrderId}",
    )
    # Only safe when create returned success (we know our clientOrderId is on file).
    if not used_own_order:
        r.skip = True
        r.detail = "no master order created in this run (Python SDK create blocked)"
    else:
        try:
            raw = client.get_master_order_by_client_order_id_v2(client_order_id)
            inner = raw.get("masterOrder", raw) if isinstance(raw, dict) else {}
            mo = MasterOrderV2Info.from_dict(inner)
            r.ok = True
            r.detail = f"clientOrderId={client_order_id} → id={mo.masterOrderId} status={mo.status}"
        except Exception as e:
            r.err = _err_str(e)
    _print_step(5, 11, r)
    results.append(r)

    # Let the engine register sub-orders before fills/pause.
    time.sleep(5)

    # ──────────────────────────────────────────────────────────────────
    # 6) GET /user/trading/v2/order-fills
    # ──────────────────────────────────────────────────────────────────
    r = Result(
        name="List Order Fills",
        method="GET",
        path="/user/trading/v2/order-fills",
    )
    try:
        kwargs = {"page": 1, "pageSize": 20}
        if first_moid:
            kwargs["masterOrderId"] = first_moid
        raw = client.list_order_fills_v2(**kwargs)
        fills = OrderFillListV2Reply.from_dict(raw)
        r.ok = True
        sample = ""
        if fills.items:
            it = fills.items[0]
            sample = f" | sample=[orderId={it.orderId} status={it.status} qty={it.quantity} filled={it.filledQuantity}]"
        r.detail = f"total={fills.total} items={len(fills.items)}{sample}"
    except Exception as e:
        r.err = _err_str(e)
    _print_step(6, 11, r)
    results.append(r)

    # ──────────────────────────────────────────────────────────────────
    # 7) PUT /user/trading/v2/master-orders/{id}/pause
    # ──────────────────────────────────────────────────────────────────
    r = Result(
        name="Pause Master Order",
        method="PUT",
        path="/user/trading/v2/master-orders/{id}/pause",
    )
    if not first_moid:
        r.skip = True
        r.detail = "no eligible master order"
    else:
        try:
            raw = client.pause_master_order_v2(first_moid, reason="v2 e2e pause")
            success = bool(raw.get("success")) if isinstance(raw, dict) else False
            msg = raw.get("message") if isinstance(raw, dict) else ""
            r.ok = success
            r.detail = f"success={success} message={msg!r}"
            if not success:
                r.err = msg or "pause returned success=false"
        except Exception as e:
            r.err = _err_str(e)
    _print_step(7, 11, r)
    results.append(r)

    # ──────────────────────────────────────────────────────────────────
    # 8) PUT /user/trading/v2/master-orders/{id}/resume
    # ──────────────────────────────────────────────────────────────────
    r = Result(
        name="Resume Master Order",
        method="PUT",
        path="/user/trading/v2/master-orders/{id}/resume",
    )
    if not first_moid:
        r.skip = True
        r.detail = "no eligible master order"
    else:
        try:
            raw = client.resume_master_order_v2(first_moid, reason="v2 e2e resume")
            success = bool(raw.get("success")) if isinstance(raw, dict) else False
            msg = raw.get("message") if isinstance(raw, dict) else ""
            r.ok = success
            r.detail = f"success={success} message={msg!r}"
            if not success:
                r.err = msg or "resume returned success=false"
        except Exception as e:
            r.err = _err_str(e)
    _print_step(8, 11, r)
    results.append(r)

    # ──────────────────────────────────────────────────────────────────
    # 9) PUT /user/trading/v2/master-orders/{id}/update
    # ──────────────────────────────────────────────────────────────────
    r = Result(
        name="Update Master Order",
        method="PUT",
        path="/user/trading/v2/master-orders/{id}/update",
    )
    if not first_moid:
        r.skip = True
        r.detail = "no eligible master order"
    else:
        try:
            upd = UpdateMasterOrderV2Request(upTolerance="0.02", lowTolerance="0.02")
            raw = client.update_master_order_v2(first_moid, upd)
            success = bool(raw.get("success")) if isinstance(raw, dict) else False
            msg = raw.get("message") if isinstance(raw, dict) else ""
            r.ok = success
            r.detail = f"success={success} message={msg!r} (upTolerance=0.02 lowTolerance=0.02)"
            if not success:
                r.err = msg or "update returned success=false"
        except Exception as e:
            r.err = _err_str(e)
    _print_step(9, 11, r)
    results.append(r)

    # ──────────────────────────────────────────────────────────────────
    # 10) PUT /user/trading/v2/master-orders/{id}/cancel
    # ──────────────────────────────────────────────────────────────────
    r = Result(
        name="Cancel Master Order",
        method="PUT",
        path="/user/trading/v2/master-orders/{id}/cancel",
    )
    if not first_moid:
        r.skip = True
        r.detail = "no eligible master order"
    else:
        try:
            raw = client.cancel_master_order_v2(first_moid, reason="v2 e2e cancel")
            success = bool(raw.get("success")) if isinstance(raw, dict) else False
            msg = raw.get("message") if isinstance(raw, dict) else ""
            r.ok = success
            r.detail = f"success={success} message={msg!r}"
            if not success:
                r.err = msg or "cancel returned success=false"
        except Exception as e:
            r.err = _err_str(e)
    _print_step(10, 11, r)
    results.append(r)

    # ──────────────────────────────────────────────────────────────────
    # 11) PUT /user/trading/v2/master-orders/batch-cancel
    # ──────────────────────────────────────────────────────────────────
    batch_ids: List[str] = []
    for i in range(2):
        coid = f"{CLIENT_ORDER_ID_TAG}{int(time.time() * 1000)}-bat{i}"
        try:
            req = CreateMasterOrderV2Request(
                apiKeyId=api_key_id,
                exchange=Exchange.BINANCE.value,
                marketType=MarketType.SPOT.value,
                symbol=SYMBOL,
                side=OrderSide.SELL.value,
                algorithm=Algorithm.TWAP.value,
                executionDurationSeconds=600,
                totalQuantity="10",
                worstPrice="5.0",
                mustComplete=False,
                clientOrderId=coid,
                notes="v2 e2e batch",
            )
            raw = client.create_master_order_v2(req)
            mo = CreateMasterOrderV2Reply.from_dict(raw)
            if mo.masterOrderId:
                batch_ids.append(mo.masterOrderId)
                batch_client_order_ids.append(coid)
                logger.info("batch-prep created masterOrderId=%s", mo.masterOrderId)
        except Exception as e:
            logger.info("batch-prep create %d failed: %s", i, _err_str(e))

    r = Result(
        name="Batch Cancel",
        method="PUT",
        path="/user/trading/v2/master-orders/batch-cancel",
    )
    if not batch_ids:
        # fallback: pick any PROCESSING orders to operate on
        try:
            raw = client.list_master_orders_v2(
                page=1, pageSize=5, status=MasterOrderStatusV2.PROCESSING.value,
            )
            lst = MasterOrderListV2Reply.from_dict(raw)
            batch_ids = [it.masterOrderId for it in lst.items if it.masterOrderId]
        except Exception as e:
            logger.info("batch-cancel fallback list failed: %s", _err_str(e))
    if not batch_ids:
        r.skip = True
        r.detail = "no eligible master order"
    else:
        try:
            raw = client.batch_cancel_master_orders_v2(batch_ids, reason="v2 e2e batch-cancel")
            reply = BatchCancelV2Reply.from_dict(raw)
            r.ok = True
            failed_sample = ""
            if reply.failedOrders:
                fo = reply.failedOrders[0]
                failed_sample = f" | failedSample=[{fo.masterOrderId} → {fo.reason}]"
            r.detail = (
                f"ids={batch_ids} successCount={reply.successCount} "
                f"failed={len(reply.failedOrders)}{failed_sample}"
            )
        except Exception as e:
            r.err = _err_str(e)
    _print_step(11, 11, r)
    results.append(r)

    # ──────────────────────────────────────────────────────────────────
    # Cleanup: catch-all batch-cancel of any PY-V2-* residual orders
    # ──────────────────────────────────────────────────────────────────
    _cleanup_residuals(client)

    # ──────────────────────────────────────────────────────────────────
    # Print summary
    # ──────────────────────────────────────────────────────────────────
    print()
    print("=" * 88)
    print("  Python SDK V2 e2e summary")
    print("=" * 88)
    print(f"{'No.':<4} {'Endpoint':<30} {'HTTP':<6} {'Path':<60} Status")
    failed_count = 0
    for i, r in enumerate(results, 1):
        print(f"{i:<4} {r.name:<30} {r.method:<6} {r.path:<60} {r.status()}")
        if not r.ok and not r.skip:
            failed_count += 1
    for i, r in enumerate(results, 1):
        if r.err:
            print(f"  [{i}] {r.name} err: {r.err}")
        if r.detail:
            print(f"  [{i}] {r.name} detail: {r.detail}")
    print("=" * 88)
    if failed_count:
        print(f"[v2_e2e] {failed_count}/{len(results)} endpoints failed (excluding SKIP).")
        return 2
    print("[v2_e2e] all endpoints OK or SKIPPED.")
    return 0


def _cleanup_residuals(client: Client) -> None:
    """Best-effort cleanup of any GO-V2-* / PY-V2-* live orders.

    Tries the bulk endpoint first; falls back to per-order ``cancel``
    when the bulk call fails (Python SDK currently can't successfully
    invoke batch-cancel because it serialises params into the query
    string instead of the JSON body — see report).
    """
    logger.info("cleanup: scanning for residual GO-V2-* / PY-V2-* orders...")
    residuals: List[str] = []
    seen: set = set()
    for status in (
        MasterOrderStatusV2.PROCESSING,
        MasterOrderStatusV2.WAITING,
        MasterOrderStatusV2.PAUSED,
        MasterOrderStatusV2.NEW,
    ):
        try:
            raw = client.list_master_orders_v2(page=1, pageSize=100, status=status.value)
            lst = MasterOrderListV2Reply.from_dict(raw)
            for it in lst.items:
                if not it.clientOrderId or not it.masterOrderId:
                    continue
                if not (
                    it.clientOrderId.startswith("GO-V2-")
                    or it.clientOrderId.startswith("PY-V2-")
                ):
                    continue
                if it.masterOrderId in seen:
                    continue
                seen.add(it.masterOrderId)
                residuals.append(it.masterOrderId)
        except Exception as e:
            logger.info("cleanup list(%s) err: %s", status.value, _err_str(e))
    if not residuals:
        logger.info("cleanup: nothing to do.")
        return
    bulk_ok = False
    try:
        raw = client.batch_cancel_master_orders_v2(residuals, reason="v2 e2e cleanup")
        reply = BatchCancelV2Reply.from_dict(raw)
        bulk_ok = True
        logger.info(
            "cleanup batch-cancel: ids=%s successCount=%s failed=%s",
            residuals, reply.successCount, len(reply.failedOrders),
        )
    except Exception as e:
        logger.info("cleanup batch-cancel err: %s; falling back to per-order cancel", _err_str(e))
    if bulk_ok:
        return
    ok, fail = 0, 0
    for mid in residuals:
        try:
            raw = client.cancel_master_order_v2(mid, reason="v2 e2e cleanup")
            success = bool(raw.get("success")) if isinstance(raw, dict) else False
            if success:
                ok += 1
            else:
                fail += 1
                logger.info(
                    "cleanup cancel %s rejected: %s",
                    mid, raw.get("message") if isinstance(raw, dict) else raw,
                )
        except Exception as e:
            fail += 1
            logger.info("cleanup cancel %s err: %s", mid, _err_str(e))
    logger.info("cleanup per-order cancel: ok=%d fail=%d total=%d", ok, fail, len(residuals))


if __name__ == "__main__":
    raise SystemExit(main())
