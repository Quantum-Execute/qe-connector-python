"""V2 trading endpoints under ``/strategy-api/user/trading/v2/...``.

Method naming intentionally mirrors V1 with a ``_v2`` suffix so V1 callers
keep working untouched. All methods reuse the existing
:meth:`API.sign_request` (HMAC / RSA / Ed25519) pipeline – signature, retry
and timeout behaviour are unchanged.

Reference: ``backend-server/docs/frontend-v2-api-upgrade.md`` sections 4–7.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Union

from qe.lib.trading_enums import Algorithm, Exchange, MarketType, OrderSide, MarginType
from qe.lib.trading_v2_types import (
    PAGE_SIZE_MAX,
    CreateMasterOrderV2Request,
    MasterOrderStatusV2,
    UpdateMasterOrderV2Request,
    to_decimal_str,
    validate_exchange,
    validate_market_type,
)
from qe.lib.utils import check_required_parameters

_BASE_PATH = "/user/trading/v2/master-orders"
_FILLS_PATH = "/user/trading/v2/order-fills"
_TCA_PATH = "/user/trading/v2/tca-analysis"
_LISTEN_KEY_PATH = "/user/trading/v2/listen-key"


# Decimal-shaped fields accepted via **kwargs in create_master_order_v2.
_CREATE_DECIMAL_KWARGS = (
    "totalQuantity",
    "orderNotional",
    "worstPrice",
    "makerRateLimit",
    "povLimit",
    "povMinLimit",
    "upTolerance",
    "lowTolerance",
)

# Pass-through kwargs for create_master_order_v2 (non-decimal).
_CREATE_PASSTHROUGH_KWARGS = (
    "executionDurationSeconds",
    "startTimeMs",
    "marginType",
    "reduceOnly",
    "isMargin",
    "mustComplete",
    "strictUpBound",
    "tailOrderProtection",
    "enableMake",
    "isTargetPosition",
    "clientOrderId",
    "notes",
    "recvWindow",
)

_UNSUPPORTED_CREATE_V2_FIELDS = frozenset({"limitPrice", "limitPriceString"})
_UNSUPPORTED_UPDATE_V2_FIELDS = frozenset({"limitPrice", "limitPriceString"})


def _reject_unsupported_v2_fields(params: Dict[str, Any], unsupported: frozenset[str]) -> None:
    for field in unsupported:
        if field in params:
            raise ValueError(f"{field} is not supported in V2; use worstPrice")


def _coerce_enum(value: Any) -> Any:
    """Convert ``str``-Enum members to their string value."""
    if isinstance(value, (Algorithm, Exchange, MarketType, OrderSide, MarginType)):
        return value.value
    if isinstance(value, MasterOrderStatusV2):
        return value.value
    return value


def _check_page_size(page_size: Optional[int]) -> None:
    if page_size is not None and page_size > PAGE_SIZE_MAX:
        raise ValueError(f"pageSize {page_size} exceeds V2 limit {PAGE_SIZE_MAX}")


def _normalize_pagination_kwargs(kwargs: Dict[str, Any]) -> None:
    if "page_size" in kwargs and "pageSize" not in kwargs:
        kwargs["pageSize"] = kwargs.pop("page_size")


def _split_v2_body_query(params: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    query: Dict[str, Any] = {}
    body = dict(params)
    if "recvWindow" in body:
        query["recvWindow"] = body.pop("recvWindow")
    return body, query


def _default_pov_limit_for_algorithm(algorithm: Any) -> str:
    value = _coerce_enum(algorithm)
    if value == "POV":
        return "0.05"
    return "1"


def _validate_pov_limit(value: Any) -> None:
    try:
        numeric = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("povLimit must be between 0 and 1") from exc
    if numeric < 0 or numeric > 1:
        raise ValueError("povLimit must be between 0 and 1")


# ---------------------------------------------------------------------------
# Create / list / detail
# ---------------------------------------------------------------------------


def create_master_order_v2(
    self,
    request: Optional[CreateMasterOrderV2Request] = None,
    *,
    apiKeyId: Optional[str] = None,
    exchange: Union[Exchange, str, None] = None,
    marketType: Union[MarketType, str, None] = None,
    symbol: Optional[str] = None,
    side: Union[OrderSide, str, None] = None,
    algorithm: Union[Algorithm, str, None] = None,
    **kwargs,
):
    """Create a new V2 master order.

    ``POST /strategy-api/user/trading/v2/master-orders``

    Two equivalent calling conventions:

    1. Pass a ready-built :class:`CreateMasterOrderV2Request`::

           req = CreateMasterOrderV2Request(
               apiKeyId="...", exchange="Binance", marketType="PERP",
               symbol="BTCUSDT", side="buy", algorithm="TWAP",
               executionDurationSeconds=3600, totalQuantity="0.5",
               worstPrice="70000",
           )
           reply = client.create_master_order_v2(req)

    2. Pass keyword arguments directly (mirrors the V1 method shape)::

           reply = client.create_master_order_v2(
               apiKeyId="...", exchange="Binance", marketType="PERP",
               symbol="BTCUSDT", side="buy", algorithm="TWAP",
               executionDurationSeconds=3600, totalQuantity="0.5",
           )

    All Decimal-shaped kwargs (``totalQuantity``, ``orderNotional``,
    ``worstPrice``, ``makerRateLimit``, ``povLimit``, ``povMinLimit``,
    ``upTolerance``, ``lowTolerance``) accept ``str`` / ``int`` / ``float`` /
    ``Decimal`` and are serialised as ``str``.

    Returns:
        dict: Raw response body as returned by the server. Use
        :meth:`CreateMasterOrderV2Reply.from_dict` for typed access.
    """
    if request is not None:
        params = request.to_payload()
    else:
        params = {}

    for field in _UNSUPPORTED_CREATE_V2_FIELDS:
        if field in kwargs:
            raise ValueError(f"{field} is not supported in V2; use worstPrice")

    # Required core fields – kwargs override the dataclass when both
    # are supplied (matches ``dict.update`` semantics).
    if apiKeyId is not None:
        params["apiKeyId"] = apiKeyId
    if exchange is not None:
        params["exchange"] = _coerce_enum(exchange)
    if marketType is not None:
        params["marketType"] = _coerce_enum(marketType)
    if symbol is not None:
        params["symbol"] = symbol
    if side is not None:
        params["side"] = _coerce_enum(side)
    if algorithm is not None:
        params["algorithm"] = _coerce_enum(algorithm)

    # Optional kwargs.
    for k in _CREATE_PASSTHROUGH_KWARGS:
        if k in kwargs and kwargs[k] is not None:
            params[k] = _coerce_enum(kwargs[k])
    for k in _CREATE_DECIMAL_KWARGS:
        if k in kwargs and kwargs[k] is not None:
            params[k] = to_decimal_str(kwargs[k])
    _reject_unsupported_v2_fields(params, _UNSUPPORTED_CREATE_V2_FIELDS)

    # Required field check (after merge).
    check_required_parameters([
        [params.get("apiKeyId"), "apiKeyId"],
        [params.get("exchange"), "exchange"],
        [params.get("marketType"), "marketType"],
        [params.get("symbol"), "symbol"],
        [params.get("side"), "side"],
        [params.get("algorithm"), "algorithm"],
    ])

    # ------------------------------------------------------------------
    # Client-side validation – mirrors backend-server / Go SDK semantics.
    # ------------------------------------------------------------------
    validate_exchange(params["exchange"])
    validate_market_type(params["marketType"])

    duration = params.get("executionDurationSeconds")
    if duration is None:
        raise ValueError("executionDurationSeconds is required")
    if duration is not None:
        try:
            duration_int = int(duration)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "executionDurationSeconds must be an integer number of seconds"
            ) from exc
        if duration_int <= 10:
            raise ValueError(
                "executionDurationSeconds must be greater than 10"
            )
        params["executionDurationSeconds"] = duration_int

    has_qty = params.get("totalQuantity") is not None
    has_notional = params.get("orderNotional") is not None
    if has_qty == has_notional:
        # Both set OR both empty -> reject.
        raise ValueError(
            "exactly one of totalQuantity / orderNotional must be provided"
        )

    if params.get("isTargetPosition") is True:
        if not has_qty:
            raise ValueError(
                "totalQuantity is required when isTargetPosition is True"
            )
        if has_notional:
            raise ValueError(
                "orderNotional is not allowed when isTargetPosition is True"
            )

    if "startTimeMs" in params and params["startTimeMs"] is not None:
        try:
            params["startTimeMs"] = int(params["startTimeMs"])
        except (TypeError, ValueError) as exc:
            raise ValueError("startTimeMs must be an integer epoch milliseconds") from exc

    if params.get("povLimit") is None:
        params["povLimit"] = _default_pov_limit_for_algorithm(params["algorithm"])
    _validate_pov_limit(params["povLimit"])

    body, query = _split_v2_body_query(params)
    return self.sign_json_request("POST", _BASE_PATH, body, query)


def list_master_orders_v2(self, **kwargs):
    """List V2 master orders.

    ``GET /strategy-api/user/trading/v2/master-orders``

    Keyword Args:
        page (int, optional): 1-based page number.
        pageSize (int, optional): Items per page; max 100.
        status (str, optional): One of ``MasterOrderStatusV2``.
        exchange (str, optional): Filter by exchange.
        symbol (str, optional): Filter by trading pair.
        algorithm (str, optional): TWAP / VWAP / POV.
        apiKeyId (str, optional): Filter by API Key binding ID.
        startTime (str, optional): RFC3339/ISO 8601 lower bound.
        endTime (str, optional): RFC3339/ISO 8601 upper bound.
        masterOrderId (str, optional): Exact filter by master order ID.
        recvWindow (int, optional): Max 60000.

    Returns:
        dict: Raw paginated response. Use
        :meth:`MasterOrderListV2Reply.from_dict` for typed access.
    """
    _normalize_pagination_kwargs(kwargs)
    if "apiKeyUuid" in kwargs and "apiKeyId" not in kwargs:
        kwargs["apiKeyId"] = kwargs.pop("apiKeyUuid")
    _check_page_size(kwargs.get("pageSize"))
    if "status" in kwargs:
        kwargs["status"] = _coerce_enum(kwargs["status"])
    if "exchange" in kwargs:
        kwargs["exchange"] = _coerce_enum(kwargs["exchange"])
    if "algorithm" in kwargs:
        kwargs["algorithm"] = _coerce_enum(kwargs["algorithm"])
    return self.sign_request("GET", _BASE_PATH, {**kwargs})


def get_master_order_v2(self, masterOrderId: str, **kwargs):
    """Fetch a V2 master order detail by master order ID.

    ``GET /strategy-api/user/trading/v2/master-orders/{masterOrderId}``
    """
    check_required_parameters([[masterOrderId, "masterOrderId"]])
    url_path = f"{_BASE_PATH}/{masterOrderId}"
    return self.sign_request("GET", url_path, {**kwargs})


def get_master_order_by_client_order_id_v2(self, clientOrderId: str, **kwargs):
    """Fetch a V2 master order detail by client order ID.

    ``GET /strategy-api/user/trading/v2/master-orders/by-client-order-id/{clientOrderId}``
    """
    check_required_parameters([[clientOrderId, "clientOrderId"]])
    url_path = f"{_BASE_PATH}/by-client-order-id/{clientOrderId}"
    return self.sign_request("GET", url_path, {**kwargs})


# ---------------------------------------------------------------------------
# Order fills
# ---------------------------------------------------------------------------


def list_order_fills_v2(self, **kwargs):
    """List V2 order fills.

    ``GET /strategy-api/user/trading/v2/order-fills``

    Keyword Args:
        page (int, optional): 1-based page number.
        pageSize (int, optional): Items per page; max 100.
        masterOrderId (str, optional): Filter by parent master order.
        orderId (str, optional): Exchange order ID (V2 replaces ``subOrderId``).
        clientOrderId (str, optional): Filter by user-defined order ID.
        symbol (str, optional): Trading pair.
        status (str, optional): Child order status filter.
        startTime / endTime (str, optional): RFC3339/ISO 8601 bounds.
        recvWindow (int, optional): Max 60000.
    """
    _normalize_pagination_kwargs(kwargs)
    _check_page_size(kwargs.get("pageSize"))
    return self.sign_request("GET", _FILLS_PATH, {**kwargs})


# ---------------------------------------------------------------------------
# TCA analysis
# ---------------------------------------------------------------------------


def get_tca_analysis_v2(self, **kwargs):
    """Get V2 TCA analysis data.

    ``GET /strategy-api/user/trading/v2/tca-analysis``

    Keyword Args:
        symbol (str, optional): Trading symbol filter.
        category (str, optional): Trading category: spot, perp, or perp_cm.
        strategy (str, optional): Execution algorithm filter: TWAP, VWAP, or POV.
        apiKeyId (str, optional): API Key binding ID filter.
        startTime (int, optional): Start time in epoch milliseconds.
        endTime (int, optional): End time in epoch milliseconds.
        recvWindow (int, optional): Max 60000.

    Returns:
        list[dict]: TCA rows returned directly from the response ``message``.
    """
    if "apiKeyUuid" in kwargs and "apiKeyId" not in kwargs:
        kwargs["apiKeyId"] = kwargs.pop("apiKeyUuid")
    return self.sign_request("GET", _TCA_PATH, {**kwargs})


def create_listen_key_v2(self, **kwargs):
    """Create a listenKey for the V2 WebSocket route.

    ``POST /strategy-api/user/trading/v2/listen-key``
    """
    return self.sign_request("POST", _LISTEN_KEY_PATH, kwargs or {})


# ---------------------------------------------------------------------------
# Master order actions: cancel / pause / resume / update / batch-cancel
# ---------------------------------------------------------------------------


def cancel_master_order_v2(self, masterOrderId: str, *, reason: Optional[str] = None, **kwargs):
    """Cancel a V2 master order.

    ``PUT /strategy-api/user/trading/v2/master-orders/{masterOrderId}/cancel``
    """
    check_required_parameters([[masterOrderId, "masterOrderId"]])
    params: Dict[str, Any] = {"masterOrderId": masterOrderId}
    if reason is not None:
        params["reason"] = reason
    params.update({k: v for k, v in kwargs.items() if v is not None})
    url_path = f"{_BASE_PATH}/{masterOrderId}/cancel"
    params.pop("masterOrderId", None)
    body, query = _split_v2_body_query(params)
    return self.sign_json_request("PUT", url_path, body, query)


def pause_master_order_v2(self, masterOrderId: str, *, reason: Optional[str] = None, **kwargs):
    """Pause a running V2 master order.

    ``PUT /strategy-api/user/trading/v2/master-orders/{masterOrderId}/pause``
    """
    check_required_parameters([[masterOrderId, "masterOrderId"]])
    params: Dict[str, Any] = {"masterOrderId": masterOrderId}
    if reason is not None:
        params["reason"] = reason
    params.update({k: v for k, v in kwargs.items() if v is not None})
    url_path = f"{_BASE_PATH}/{masterOrderId}/pause"
    params.pop("masterOrderId", None)
    body, query = _split_v2_body_query(params)
    return self.sign_json_request("PUT", url_path, body, query)


def resume_master_order_v2(self, masterOrderId: str, *, reason: Optional[str] = None, **kwargs):
    """Resume a paused V2 master order.

    ``PUT /strategy-api/user/trading/v2/master-orders/{masterOrderId}/resume``
    """
    check_required_parameters([[masterOrderId, "masterOrderId"]])
    params: Dict[str, Any] = {"masterOrderId": masterOrderId}
    if reason is not None:
        params["reason"] = reason
    params.update({k: v for k, v in kwargs.items() if v is not None})
    url_path = f"{_BASE_PATH}/{masterOrderId}/resume"
    params.pop("masterOrderId", None)
    body, query = _split_v2_body_query(params)
    return self.sign_json_request("PUT", url_path, body, query)


def update_master_order_v2(
    self,
    masterOrderId: str,
    request: Optional[UpdateMasterOrderV2Request] = None,
    **kwargs,
):
    """Update parameters of a running V2 master order. Only provided fields
    are updated; everything else stays as-is.

    ``PUT /strategy-api/user/trading/v2/master-orders/{masterOrderId}/update``

    Args:
        masterOrderId (str): Required path param.
        request (UpdateMasterOrderV2Request, optional): Typed body.
            ``kwargs`` (when present) override fields from ``request``.

    Keyword Args (all optional):
        totalQuantity, orderNotional, upTolerance, lowTolerance,
        enableMake, makerRateLimit, strictUpBound, povLimit, povMinLimit,
        worstPrice, tailOrderProtection, mustComplete,
        executionDurationSeconds.
    """
    check_required_parameters([[masterOrderId, "masterOrderId"]])

    for field in _UNSUPPORTED_UPDATE_V2_FIELDS:
        if field in kwargs:
            raise ValueError(f"{field} is not supported in V2; use worstPrice")

    if request is not None:
        params: Dict[str, Any] = request.to_payload()
    else:
        params = {}
    _reject_unsupported_v2_fields(params, _UNSUPPORTED_UPDATE_V2_FIELDS)

    decimal_kwargs = {
        "totalQuantity",
        "orderNotional",
        "upTolerance",
        "lowTolerance",
        "makerRateLimit",
        "povLimit",
        "povMinLimit",
        "worstPrice",
    }
    passthrough_kwargs = {
        "enableMake",
        "strictUpBound",
        "tailOrderProtection",
        "mustComplete",
        "executionDurationSeconds",
        "recvWindow",
    }
    for k, v in kwargs.items():
        if v is None:
            continue
        if k in decimal_kwargs:
            params[k] = to_decimal_str(v)
        elif k in passthrough_kwargs:
            params[k] = v
        else:
            raise ValueError(f"{k} is not a supported V2 update field")

    if "executionDurationSeconds" in params and params["executionDurationSeconds"] is not None:
        try:
            duration_int = int(params["executionDurationSeconds"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "executionDurationSeconds must be an integer number of seconds"
            ) from exc
        if duration_int <= 10:
            raise ValueError("executionDurationSeconds must be greater than 10")
        params["executionDurationSeconds"] = duration_int

    url_path = f"{_BASE_PATH}/{masterOrderId}/update"
    body, query = _split_v2_body_query(params)
    return self.sign_json_request("PUT", url_path, body, query)


def batch_cancel_master_orders_v2(
    self,
    masterOrderIds: Iterable[str],
    *,
    reason: Optional[str] = None,
    **kwargs,
):
    """Batch-cancel V2 master orders.

    ``PUT /strategy-api/user/trading/v2/master-orders/batch-cancel``

    Args:
        masterOrderIds (Iterable[str]): Master order IDs to cancel.
        reason (str, optional): Cancellation reason applied to all IDs.

    Returns:
        dict: ``{"successCount": int, "failedOrders": [...]}``. Use
        :meth:`BatchCancelV2Reply.from_dict` for typed access.
    """
    ids: List[str] = [str(x) for x in masterOrderIds]
    if not ids:
        raise ValueError("masterOrderIds must not be empty")

    params: Dict[str, Any] = {"masterOrderIds": ids}
    if reason is not None:
        params["reason"] = reason
    params.update({k: v for k, v in kwargs.items() if v is not None})

    url_path = f"{_BASE_PATH}/batch-cancel"
    body, query = _split_v2_body_query(params)
    return self.sign_json_request("PUT", url_path, body, query)
