"""V2 trading dataclasses and enums.

These types mirror the wire format of the V2 strategy-api endpoints
(`/strategy-api/.../v2/...`). All Decimal-like quantities, prices, ratios
are represented as `str` to avoid float precision loss, matching the V2
upgrade contract documented in
`backend-server/docs/frontend-v2-api-upgrade.md`.

The dataclasses use lowerCamelCase attribute names because they map 1:1
to JSON keys produced/consumed by the backend. SDK methods themselves
are exposed as snake_case (Pythonic) and accept either a dataclass
instance via ``request=`` or plain keyword arguments.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, asdict
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Union


# ---------------------------------------------------------------------------
# Enums / status constants
# ---------------------------------------------------------------------------


class MasterOrderStatusV2(str, Enum):
    """V2 母单状态全集（V1 ``MasterOrderStatus`` 仅暴露 NEW/COMPLETED）。

    母单状态在 V2 接口里按用途分两类：

    1. 详情 / 推送返回：保留全部 9 个细分状态（``NEW`` / ``WAITING`` /
       ``PROCESSING`` / ``PAUSED`` / ``CANCELLED`` / ``COMPLETED`` /
       ``COMPLETED_WITHTAIL`` / ``REJECTED`` / ``EXPIRED``）。
    2. 列表查询过滤（``GET /user/trading/v2/master-orders`` 的 ``status``
       入参）：后端只接受 **2 个聚合值**：

       - ``NEW``       → 所有"运行中"母单（``NEW`` / ``WAITING`` /
         ``PROCESSING`` / ``PAUSED`` 以及内部 ``CANCEL`` /
         ``CANCEL_REJECT`` / ``CLEANING`` 中间态）
       - ``COMPLETED`` → 所有"非运行中"母单（``CANCELLED`` / ``COMPLETED`` /
         ``COMPLETED_WITHTAIL`` / ``REJECTED`` / ``EXPIRED``）

       传其它细分状态会被后端按字面值精确匹配，结果通常为空。**列表过滤请
       使用 ``MasterOrderStatusV2.NEW`` 或 ``MasterOrderStatusV2.COMPLETED``。**

    其它 V2 接口（batch-cancel / update 等）保持细分状态语义，不受影响。
    """

    NEW = "NEW"
    WAITING = "WAITING"
    PROCESSING = "PROCESSING"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    COMPLETED_WITHTAIL = "COMPLETED_WITHTAIL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


# 完整的 V2 母单状态字面量集合，供调用方做白名单校验。
MASTER_ORDER_STATUSES_V2 = frozenset(s.value for s in MasterOrderStatusV2)


# 创建/查询母单时允许的市场类型。V2 文档第 2 节定义。
_MARKET_TYPES = frozenset({"SPOT", "PERP"})

# 创建/查询母单时允许的交易所。V2 文档第 2 节定义。
_EXCHANGES = frozenset({"Binance", "OKX", "LTP", "Deribit", "Hyperliquid", "Bybit"})

# V2 文档默认 pageSize 上限；>100 会被 V2 接口明确拒绝。
PAGE_SIZE_MAX = 100


DecimalLike = Union[str, int, float, Decimal]


def _to_decimal_str(value: Optional[DecimalLike]) -> Optional[str]:
    """Render a Decimal-like value as the canonical string used by V2.

    - ``None``  -> ``None`` (caller drops the field)
    - ``str``   -> as-is (trusted; V2 does not require numeric reformat)
    - ``Decimal`` / numeric -> non-scientific decimal string
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        # bool is a subclass of int; reject explicitly so we do not turn
        # ``True`` into ``"1"`` for a notional field.
        raise TypeError("decimal field cannot be bool")
    if isinstance(value, Decimal):
        # Avoid scientific notation; ``format(d, 'f')`` is the
        # documented way to print a Decimal in plain notation.
        return format(value, "f")
    if isinstance(value, (int, float)):
        return format(Decimal(repr(value)), "f")
    raise TypeError(
        f"decimal field must be str/int/float/Decimal, got {type(value).__name__}"
    )


def _drop_none(d: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


# ---------------------------------------------------------------------------
# Exchange API key (3.3)
# ---------------------------------------------------------------------------


@dataclass
class ExchangeApiV2Info:
    """Single API Key binding row returned by V2 ``GET /exchange-apis``."""

    apiKeyId: Optional[str] = None
    # Deprecated response aliases kept for SDK source compatibility.
    apiKeyUuid: Optional[str] = None
    id: Optional[str] = None
    createdAt: Optional[str] = None
    accountName: Optional[str] = None
    exchange: Optional[str] = None
    apiKey: Optional[str] = None
    status: Optional[str] = None
    isValid: Optional[bool] = None
    isTradingEnabled: Optional[bool] = None
    isDefault: Optional[bool] = None
    isPm: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExchangeApiV2Info":
        payload = dict(data)
        if payload.get("apiKeyId") is None:
            payload["apiKeyId"] = payload.get("apiKeyUuid") or payload.get("id")
        if payload.get("apiKeyUuid") is None:
            payload["apiKeyUuid"] = payload.get("apiKeyId")
        if payload.get("id") is None:
            payload["id"] = payload.get("apiKeyId")
        return cls(**{k: payload.get(k) for k in _field_names(cls)})


@dataclass
class ExchangeApiListV2Reply:
    items: List[ExchangeApiV2Info] = field(default_factory=list)
    total: int = 0
    page: int = 0
    pageSize: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExchangeApiListV2Reply":
        items_raw = data.get("items") or []
        return cls(
            items=[ExchangeApiV2Info.from_dict(it) for it in items_raw],
            total=int(data.get("total") or 0),
            page=int(data.get("page") or 0),
            pageSize=int(data.get("pageSize") or 0),
        )


# ---------------------------------------------------------------------------
# Create master order (4.x)
# ---------------------------------------------------------------------------


@dataclass
class CreateMasterOrderV2Request:
    """V2 ``POST /user/trading/v2/master-orders`` 请求体。

    Decimal 类字段（``totalQuantity``、``orderNotional``、``worstPrice``、
    ``makerRateLimit``、``povLimit``、``povMinLimit``、``upTolerance``、
    ``lowTolerance``）允许传 ``str | int | float | Decimal``，序列化时统一
    转为 ``str``（与后端约定一致）。
    """

    apiKeyId: str = ""
    exchange: str = ""
    marketType: str = ""
    symbol: str = ""
    side: str = ""
    algorithm: str = ""

    executionDurationSeconds: Optional[int] = None
    startTimeMs: Optional[int] = None

    totalQuantity: Optional[DecimalLike] = None
    orderNotional: Optional[DecimalLike] = None

    marginType: Optional[str] = None
    reduceOnly: Optional[bool] = None
    isMargin: Optional[bool] = None

    worstPrice: Optional[DecimalLike] = None

    mustComplete: Optional[bool] = None
    makerRateLimit: Optional[DecimalLike] = None
    povLimit: Optional[DecimalLike] = None
    povMinLimit: Optional[DecimalLike] = None
    upTolerance: Optional[DecimalLike] = None
    lowTolerance: Optional[DecimalLike] = None
    strictUpBound: Optional[bool] = None
    tailOrderProtection: Optional[bool] = None
    enableMake: Optional[bool] = None
    isTargetPosition: Optional[bool] = None

    clientOrderId: Optional[str] = None
    notes: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        decimal_fields = {
            "totalQuantity",
            "orderNotional",
            "worstPrice",
            "makerRateLimit",
            "povLimit",
            "povMinLimit",
            "upTolerance",
            "lowTolerance",
        }
        out: Dict[str, Any] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if v is None:
                continue
            if f.name in decimal_fields:
                out[f.name] = _to_decimal_str(v)
            else:
                out[f.name] = v
        return out


@dataclass
class CreateMasterOrderV2Reply:
    masterOrderId: Optional[str] = None
    status: Optional[str] = None
    clientOrderId: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CreateMasterOrderV2Reply":
        return cls(**{k: data.get(k) for k in _field_names(cls)})


# ---------------------------------------------------------------------------
# Master order info (5.3)
# ---------------------------------------------------------------------------


@dataclass
class MasterOrderV2Info:
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    masterOrderId: Optional[str] = None
    clientOrderId: Optional[str] = None
    apiKeyId: Optional[str] = None
    # Deprecated response alias kept for SDK source compatibility.
    apiKeyUuid: Optional[str] = None
    tradingAccount: Optional[str] = None
    exchange: Optional[str] = None
    marketType: Optional[str] = None
    category: Optional[str] = None
    symbol: Optional[str] = None
    baseCurrency: Optional[str] = None
    quoteCurrency: Optional[str] = None
    side: Optional[str] = None
    marginType: Optional[str] = None
    reduceOnly: Optional[bool] = None
    isMargin: Optional[bool] = None
    algorithm: Optional[str] = None
    totalQuantity: Optional[str] = None
    orderNotional: Optional[str] = None
    startTimeMs: Optional[int] = None
    executionDurationSeconds: Optional[int] = None
    worstPrice: Optional[str] = None
    mustComplete: Optional[bool] = None
    makerRateLimit: Optional[str] = None
    povLimit: Optional[str] = None
    povMinLimit: Optional[str] = None
    upTolerance: Optional[str] = None
    lowTolerance: Optional[str] = None
    strictUpBound: Optional[bool] = None
    tailOrderProtection: Optional[bool] = None
    enableMake: Optional[bool] = None
    isTargetPosition: Optional[bool] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    rejectReason: Optional[str] = None
    finishedMs: Optional[int] = None
    cumFilledQty: Optional[str] = None
    cumFilledNotional: Optional[str] = None
    avgFilledPrice: Optional[str] = None
    makerRate: Optional[str] = None
    completedQuantity: Optional[str] = None
    commission: Optional[Dict[str, str]] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MasterOrderV2Info":
        payload = dict(data)
        if payload.get("apiKeyId") is None:
            payload["apiKeyId"] = payload.get("apiKeyUuid")
        if payload.get("apiKeyUuid") is None:
            payload["apiKeyUuid"] = payload.get("apiKeyId")
        names = _field_names(cls)
        kwargs: Dict[str, Any] = {}
        for name in names:
            if name in payload:
                kwargs[name] = payload[name]
        # Normalise epoch-millis fields that may come back as numeric/string.
        for ms_field in ("startTimeMs", "finishedMs", "executionDurationSeconds"):
            if kwargs.get(ms_field) is not None:
                try:
                    kwargs[ms_field] = int(kwargs[ms_field])
                except (TypeError, ValueError):
                    pass
        return cls(**kwargs)


@dataclass
class MasterOrderListV2Reply:
    items: List[MasterOrderV2Info] = field(default_factory=list)
    total: int = 0
    page: int = 0
    pageSize: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MasterOrderListV2Reply":
        items_raw = data.get("items") or []
        return cls(
            items=[MasterOrderV2Info.from_dict(it) for it in items_raw],
            total=int(data.get("total") or 0),
            page=int(data.get("page") or 0),
            pageSize=int(data.get("pageSize") or 0),
        )


# ---------------------------------------------------------------------------
# Order fills (6.x)
# ---------------------------------------------------------------------------


# Decimal-shaped 字段名，from_dict 时强制规范化成 ``str``：V2 后端契约规定这
# 些字段以 string 返回（避免 JS 精度丢失），但为了兼容历史/异常返回 number 的
# 情况，这里在反序列化时统一转 string。
_ORDER_FILL_V2_DECIMAL_FIELDS = frozenset({
    "filledNotional",
    "filledQuantity",
    "averagePrice",
    "price",
    "quantity",
})


def _coerce_decimal_field(value: Any) -> Optional[str]:
    """Normalise a decimal-shaped JSON value (str / int / float / Decimal /
    None) into a plain string. Returns ``None`` if the input is ``None``.
    Falls back to ``str(value)`` for other types so unexpected payloads do
    not crash deserialization.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (int, float)):
        return format(Decimal(repr(value)), "f")
    return str(value)


@dataclass
class OrderFillV2Info:
    id: Optional[str] = None
    orderCreatedTime: Optional[str] = None
    masterOrderId: Optional[str] = None
    exchange: Optional[str] = None
    category: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    filledNotional: Optional[str] = None
    filledQuantity: Optional[str] = None
    averagePrice: Optional[str] = None
    price: Optional[str] = None
    status: Optional[str] = None
    rejectReason: Optional[str] = None
    baseCurrency: Optional[str] = None
    quoteCurrency: Optional[str] = None
    orderType: Optional[str] = None
    orderId: Optional[str] = None
    quantity: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OrderFillV2Info":
        kwargs: Dict[str, Any] = {}
        for name in _field_names(cls):
            v = data.get(name)
            if name in _ORDER_FILL_V2_DECIMAL_FIELDS:
                kwargs[name] = _coerce_decimal_field(v)
            else:
                kwargs[name] = v
        return cls(**kwargs)


@dataclass
class OrderFillListV2Reply:
    items: List[OrderFillV2Info] = field(default_factory=list)
    total: int = 0
    page: int = 0
    pageSize: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OrderFillListV2Reply":
        items_raw = data.get("items") or []
        return cls(
            items=[OrderFillV2Info.from_dict(it) for it in items_raw],
            total=int(data.get("total") or 0),
            page=int(data.get("page") or 0),
            pageSize=int(data.get("pageSize") or 0),
        )


# ---------------------------------------------------------------------------
# Master order action replies (7.x)
# ---------------------------------------------------------------------------


@dataclass
class MasterOrderActionV2Reply:
    success: Optional[bool] = None
    message: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MasterOrderActionV2Reply":
        return cls(**{k: data.get(k) for k in _field_names(cls)})


@dataclass
class UpdateMasterOrderV2Request:
    """V2 ``PUT /user/trading/v2/master-orders/{masterOrderId}/update`` 请求体。

    所有字段可选；只填需要更新的字段。
    """

    totalQuantity: Optional[DecimalLike] = None
    orderNotional: Optional[DecimalLike] = None
    upTolerance: Optional[DecimalLike] = None
    lowTolerance: Optional[DecimalLike] = None
    enableMake: Optional[bool] = None
    makerRateLimit: Optional[DecimalLike] = None
    strictUpBound: Optional[bool] = None
    povLimit: Optional[DecimalLike] = None
    povMinLimit: Optional[DecimalLike] = None
    tailOrderProtection: Optional[bool] = None
    mustComplete: Optional[bool] = None
    executionDurationSeconds: Optional[int] = None
    worstPrice: Optional[DecimalLike] = None

    def to_payload(self) -> Dict[str, Any]:
        decimal_fields = {
            "totalQuantity",
            "orderNotional",
            "upTolerance",
            "lowTolerance",
            "makerRateLimit",
            "povLimit",
            "povMinLimit",
            "worstPrice",
        }
        out: Dict[str, Any] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if v is None:
                continue
            if f.name in decimal_fields:
                out[f.name] = _to_decimal_str(v)
            else:
                out[f.name] = v
        return out


@dataclass
class BatchCancelV2FailedItem:
    masterOrderId: Optional[str] = None
    reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BatchCancelV2FailedItem":
        return cls(**{k: data.get(k) for k in _field_names(cls)})


@dataclass
class BatchCancelV2Reply:
    successCount: int = 0
    failedOrders: List[BatchCancelV2FailedItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BatchCancelV2Reply":
        failed_raw = data.get("failedOrders") or []
        return cls(
            successCount=int(data.get("successCount") or 0),
            failedOrders=[BatchCancelV2FailedItem.from_dict(it) for it in failed_raw],
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_FIELD_NAME_CACHE: Dict[type, List[str]] = {}


def _field_names(cls) -> List[str]:
    if cls in _FIELD_NAME_CACHE:
        return _FIELD_NAME_CACHE[cls]
    names = [f.name for f in fields(cls)]
    _FIELD_NAME_CACHE[cls] = names
    return names


def validate_market_type(market_type: str) -> None:
    if market_type not in _MARKET_TYPES:
        raise ValueError(
            f"marketType must be one of {sorted(_MARKET_TYPES)}, got {market_type!r}"
        )


def validate_exchange(exchange: str) -> None:
    if exchange not in _EXCHANGES:
        raise ValueError(
            f"exchange must be one of {sorted(_EXCHANGES)}, got {exchange!r}"
        )


def validate_master_order_status_v2(status: str) -> None:
    if status not in MASTER_ORDER_STATUSES_V2:
        raise ValueError(
            f"status must be one of {sorted(MASTER_ORDER_STATUSES_V2)}, got {status!r}"
        )


def to_decimal_str(value: Optional[DecimalLike]) -> Optional[str]:
    """Public helper – external code may want to reuse our coercion."""
    return _to_decimal_str(value)


def dataclass_to_payload(obj: Any) -> Dict[str, Any]:
    """asdict() variant that drops ``None`` values and uses ``to_payload``
    if the dataclass provides one (request types do).
    """
    if hasattr(obj, "to_payload"):
        return obj.to_payload()
    return _drop_none(asdict(obj))


__all__ = [
    "MasterOrderStatusV2",
    "MASTER_ORDER_STATUSES_V2",
    "PAGE_SIZE_MAX",
    "DecimalLike",
    "ExchangeApiV2Info",
    "ExchangeApiListV2Reply",
    "CreateMasterOrderV2Request",
    "CreateMasterOrderV2Reply",
    "MasterOrderV2Info",
    "MasterOrderListV2Reply",
    "OrderFillV2Info",
    "OrderFillListV2Reply",
    "MasterOrderActionV2Reply",
    "UpdateMasterOrderV2Request",
    "BatchCancelV2FailedItem",
    "BatchCancelV2Reply",
    "validate_market_type",
    "validate_exchange",
    "validate_master_order_status_v2",
    "to_decimal_str",
    "dataclass_to_payload",
]
