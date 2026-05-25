import pytest

from qe.lib.trading_v2_types import (
    MASTER_ORDER_STATUSES_V2,
    CreateMasterOrderV2Request,
    UpdateMasterOrderV2Request,
    MasterOrderStatusV2,
    MasterOrderV2Info,
)
from qe.user.exchange_v2 import list_exchange_apis_v2
from qe.user.trading_v2 import (
    create_master_order_v2,
    list_master_orders_v2,
    list_order_fills_v2,
    update_master_order_v2,
)


class DummyClient:
    def __init__(self):
        self.calls = []
        self.json_calls = []

    def sign_request(self, method, url_path, payload=None):
        self.calls.append((method, url_path, payload or {}))
        return {"items": [], "total": 0, "page": 1, "pageSize": 20}

    def sign_json_request(self, method, url_path, body=None, query=None):
        self.json_calls.append((method, url_path, body or {}, query or {}))
        return body or {}


class LegacyRequest:
    def to_payload(self):
        return {
            "apiKeyId": "dummy-api-key-id",
            "exchange": "Binance",
            "marketType": "SPOT",
            "symbol": "DOGEUSDT",
            "side": "buy",
            "algorithm": "TWAP",
            "executionDurationSeconds": 15,
            "orderNotional": "6",
            "limitPrice": "0.1",
        }


def test_v2_list_methods_send_page_size_as_lower_camel_case():
    client = DummyClient()

    list_exchange_apis_v2(client, page=1, page_size=20)
    list_master_orders_v2(client, page=1, page_size=20)
    list_order_fills_v2(client, page=1, page_size=20)

    for _, _, payload in client.calls:
        assert payload["pageSize"] == 20
        assert "page_size" not in payload


def test_v2_list_methods_reject_oversized_page_size():
    client = DummyClient()

    for fn in (list_exchange_apis_v2, list_master_orders_v2, list_order_fills_v2):
        with pytest.raises(ValueError, match="pageSize 101 exceeds V2 limit 100"):
            fn(client, page=1, page_size=101)


def test_master_order_v2_info_decodes_trading_account():
    info = MasterOrderV2Info.from_dict({
        "masterOrderId": "mo_account",
        "tradingAccount": "pm-account",
    })

    assert info.tradingAccount == "pm-account"


def test_master_order_status_v2_includes_completed_with_tail():
    assert MasterOrderStatusV2.COMPLETED_WITHTAIL.value == "COMPLETED_WITHTAIL"
    assert "COMPLETED_WITHTAIL" in MASTER_ORDER_STATUSES_V2


def test_create_master_order_v2_requires_execution_duration_seconds():
    client = DummyClient()

    with pytest.raises(ValueError, match="executionDurationSeconds is required"):
        create_master_order_v2(
            client,
            apiKeyId="dummy-api-key-id",
            exchange="Binance",
            marketType="SPOT",
            symbol="DOGEUSDT",
            side="buy",
            algorithm="TWAP",
            orderNotional="6",
        )

    assert client.calls == []
    assert client.json_calls == []


def test_create_master_order_v2_no_longer_exposes_limit_price_fields():
    assert "limitPrice" not in CreateMasterOrderV2Request.__dataclass_fields__
    assert "limitPriceString" not in CreateMasterOrderV2Request.__dataclass_fields__
    assert "limitPrice" not in UpdateMasterOrderV2Request.__dataclass_fields__


def test_create_master_order_v2_rejects_legacy_limit_price_kwargs():
    base = {
        "apiKeyId": "dummy-api-key-id",
        "exchange": "Binance",
        "marketType": "SPOT",
        "symbol": "DOGEUSDT",
        "side": "buy",
        "algorithm": "TWAP",
        "executionDurationSeconds": 15,
        "orderNotional": "6",
    }

    for field in ("limitPrice", "limitPriceString"):
        client = DummyClient()
        with pytest.raises(ValueError, match=f"{field} is not supported in V2"):
            create_master_order_v2(client, **base, **{field: "0.1"})
        assert client.json_calls == []


def test_create_master_order_v2_rejects_legacy_limit_price_from_request_payload():
    client = DummyClient()

    with pytest.raises(ValueError, match="limitPrice is not supported in V2"):
        create_master_order_v2(client, request=LegacyRequest())

    assert client.json_calls == []


def test_create_master_order_v2_applies_algorithm_pov_limit_defaults():
    cases = [
        ("TWAP", "1"),
        ("VWAP", "1"),
        ("POV", "0.05"),
    ]

    for algorithm, expected in cases:
        client = DummyClient()
        create_master_order_v2(
            client,
            apiKeyId="dummy-api-key-id",
            exchange="Binance",
            marketType="SPOT",
            symbol="DOGEUSDT",
            side="buy",
            algorithm=algorithm,
            executionDurationSeconds=15,
            orderNotional="6",
        )
        _, _, body, _ = client.json_calls[-1]
        assert body["povLimit"] == expected


def test_create_master_order_v2_rejects_pov_limit_above_one():
    client = DummyClient()

    with pytest.raises(ValueError, match="povLimit must be between 0 and 1"):
        create_master_order_v2(
            client,
            apiKeyId="dummy-api-key-id",
            exchange="Binance",
            marketType="SPOT",
            symbol="DOGEUSDT",
            side="buy",
            algorithm="TWAP",
            executionDurationSeconds=15,
            orderNotional="6",
            povLimit="1.01",
        )

    assert client.json_calls == []


def test_update_master_order_v2_rejects_legacy_limit_price_kwargs():
    client = DummyClient()

    with pytest.raises(ValueError, match="limitPrice is not supported in V2"):
        update_master_order_v2(client, "mo_123", limitPrice="0.1")

    assert client.json_calls == []


def test_update_master_order_v2_rejects_legacy_limit_price_from_request_payload():
    client = DummyClient()

    with pytest.raises(ValueError, match="limitPrice is not supported in V2"):
        update_master_order_v2(client, "mo_123", request=LegacyRequest())

    assert client.json_calls == []
