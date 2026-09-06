from qe.lib import (
    Algorithm,
    Exchange,
    MarginType,
    MarketType,
    OrderSide,
    TradingPairMarketType,
)
from qe.pub import Pub
from qe.user.trading import create_master_order
from qe.user.trading_v2 import create_master_order_v2


class DummyTradingClient:
    def __init__(self):
        self.calls = []
        self.json_calls = []

    def sign_request(self, method, path, payload=None):
        self.calls.append((method, path, payload or {}))
        return {"masterOrderId": "mo-bitget"}

    def sign_json_request(self, method, path, body=None, query=None):
        self.json_calls.append((method, path, body or {}, query or {}))
        return {"masterOrderId": "mo-bitget-v2"}


class DummyPubClient:
    def __init__(self):
        self.calls = []

    def query(self, path, payload=None):
        self.calls.append((path, payload or {}))
        return {"items": []}


def test_exchange_enum_includes_bitget():
    assert Exchange.BITGET.value == "Bitget"


def test_v1_bitget_spot_margin_create_preserves_wire_payload():
    client = DummyTradingClient()

    create_master_order(
        client,
        algorithm=Algorithm.TWAP,
        exchange=Exchange.BITGET,
        symbol="BTCUSDT",
        marketType=MarketType.SPOT,
        side=OrderSide.BUY,
        apiKeyId="bitget-key",
        orderNotional=100,
        isMargin=True,
        isTargetPosition=False,
    )

    assert client.calls == [
        (
            "POST",
            "/user/trading/master-orders",
            {
                "algorithm": "TWAP",
                "algorithmType": "TWAP",
                "exchange": "Bitget",
                "symbol": "BTCUSDT",
                "marketType": "SPOT",
                "side": "buy",
                "apiKeyId": "bitget-key",
                "orderNotional": 100,
                "isMargin": True,
                "tailOrderProtection": True,
                "enableMake": True,
                "isTargetPosition": False,
            },
        )
    ]


def test_v1_bitget_perp_u_target_and_coin_margin_payloads():
    target_client = DummyTradingClient()
    create_master_order(
        target_client,
        algorithm=Algorithm.TWAP,
        exchange=Exchange.BITGET,
        symbol="BTCUSDT",
        marketType=MarketType.PERP,
        side=OrderSide.BUY,
        apiKeyId="bitget-key",
        totalQuantity=0.25,
        marginType=MarginType.U,
        isTargetPosition=True,
    )
    target_payload = target_client.calls[-1][2]
    assert target_payload["exchange"] == "Bitget"
    assert target_payload["marketType"] == "PERP"
    assert target_payload["marginType"] == "U"
    assert target_payload["totalQuantity"] == 0.25
    assert target_payload["isTargetPosition"] is True
    assert "orderNotional" not in target_payload

    coin_client = DummyTradingClient()
    create_master_order(
        coin_client,
        algorithm=Algorithm.TWAP,
        exchange=Exchange.BITGET,
        symbol="BTCUSD_CM",
        marketType=MarketType.PERP,
        side=OrderSide.SELL,
        apiKeyId="bitget-key",
        totalQuantity=2,
        marginType=MarginType.C,
        isTargetPosition=False,
    )
    coin_payload = coin_client.calls[-1][2]
    assert coin_payload["exchange"] == "Bitget"
    assert coin_payload["symbol"] == "BTCUSD_CM"
    assert coin_payload["marketType"] == "PERP"
    assert coin_payload["marginType"] == "C"
    assert coin_payload["totalQuantity"] == 2
    assert coin_payload["isTargetPosition"] is False


def test_v2_bitget_spot_margin_create_preserves_wire_payload():
    client = DummyTradingClient()

    create_master_order_v2(
        client,
        apiKeyId="bitget-key",
        exchange=Exchange.BITGET,
        marketType=MarketType.SPOT,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        algorithm=Algorithm.TWAP,
        executionDurationSeconds=60,
        orderNotional="100",
        povLimit="0.8",
        isMargin=True,
        isTargetPosition=False,
    )

    assert client.json_calls == [
        (
            "POST",
            "/user/trading/v2/master-orders",
            {
                "apiKeyId": "bitget-key",
                "exchange": "Bitget",
                "marketType": "SPOT",
                "symbol": "BTCUSDT",
                "side": "buy",
                "algorithm": "TWAP",
                "executionDurationSeconds": 60,
                "isMargin": True,
                "isTargetPosition": False,
                "orderNotional": "100",
                "povLimit": "0.8",
            },
            {},
        )
    ]


def test_v2_bitget_perp_u_target_and_coin_margin_payloads():
    for margin_type, is_target, quantity in (
        (MarginType.U, True, "0.25"),
        (MarginType.C, False, "2"),
    ):
        client = DummyTradingClient()
        create_master_order_v2(
            client,
            apiKeyId="bitget-key",
            exchange=Exchange.BITGET,
            marketType=MarketType.PERP,
            symbol="BTCUSDT" if margin_type is MarginType.U else "BTCUSD_CM",
            side=OrderSide.BUY,
            algorithm=Algorithm.TWAP,
            executionDurationSeconds=60,
            totalQuantity=quantity,
            povLimit="0.8",
            marginType=margin_type,
            isTargetPosition=is_target,
        )

        method, path, body, query = client.json_calls[-1]
        assert method == "POST"
        assert path == "/user/trading/v2/master-orders"
        assert query == {}
        assert body["exchange"] == "Bitget"
        assert body["symbol"] == (
            "BTCUSDT" if margin_type is MarginType.U else "BTCUSD_CM"
        )
        assert body["marketType"] == "PERP"
        assert body["marginType"] == margin_type.value
        assert body["totalQuantity"] == quantity
        assert body["povLimit"] == "0.8"
        assert body["isTargetPosition"] is is_target
        assert "orderNotional" not in body


def test_v1_and_v2_trading_pairs_serialize_bitget_enums_and_paths():
    client = DummyPubClient()

    Pub.trading_pairs(
        client,
        exchange=Exchange.BITGET,
        marketType=TradingPairMarketType.SPOT,
        isCoin=False,
        page=1,
        pageSize=20,
    )
    Pub.trading_pairs_v2(
        client,
        exchange=Exchange.BITGET,
        marketType=TradingPairMarketType.PERP,
        isCoin=True,
    )

    assert client.calls == [
        (
            "/pub/trading-pairs",
            {
                "exchange": "Bitget",
                "marketType": "SPOT",
                "isCoin": False,
                "page": 1,
                "pageSize": 20,
            },
        ),
        (
            "/pub/v2/trading-pairs",
            {"exchange": "Bitget", "marketType": "PERP", "isCoin": True},
        ),
    ]
