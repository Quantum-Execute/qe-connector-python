"""V2 exchange-api endpoints under ``/strategy-api/user/exchange/v2/...``.

V2 出参隐藏 ``verificationMethod`` 与 ``balance``；其余字段与 V1 兼容。
"""
from __future__ import annotations

import warnings
from typing import Optional

from qe.lib.trading_enums import Exchange
from qe.lib.trading_v2_types import PAGE_SIZE_MAX


def list_exchange_apis_v2(self, **kwargs):
    """List exchange APIs (V2).

    ``GET /strategy-api/user/exchange/v2/exchange-apis``

    Keyword Args:
        page (int, optional): 1-based page number.
        pageSize (int, optional): Items per page; max 100 (clamped server-side).
        exchange (str, optional): Filter by exchange name.
        recvWindow (int, optional): Max 60000.

    Returns:
        dict: Raw response. Use :meth:`ExchangeApiListV2Reply.from_dict` for
        typed access.
    """
    page_size: Optional[int] = kwargs.get("pageSize")
    if page_size is not None and page_size > PAGE_SIZE_MAX:
        warnings.warn(
            f"pageSize {page_size} exceeds V2 limit {PAGE_SIZE_MAX}; "
            "the server will clamp it to 100.",
            UserWarning,
            stacklevel=2,
        )

    if "exchange" in kwargs and isinstance(kwargs["exchange"], Exchange):
        kwargs["exchange"] = kwargs["exchange"].value

    url_path = "/user/exchange/v2/exchange-apis"
    return self.sign_request("GET", url_path, {**kwargs})
