import pytest

from qe.lib.trading_v2_types import MasterOrderV2Info
from qe.user.exchange_v2 import list_exchange_apis_v2
from qe.user.trading_v2 import list_master_orders_v2, list_order_fills_v2


class DummyClient:
    def __init__(self):
        self.calls = []

    def sign_request(self, method, url_path, payload=None):
        self.calls.append((method, url_path, payload or {}))
        return {"items": [], "total": 0, "page": 1, "pageSize": 20}


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
