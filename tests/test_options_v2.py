import asyncio
import json
from decimal import Decimal
from urllib.parse import parse_qs, urlencode

import pytest

from qe.error import APIError
from qe.lib.trading_enums import Exchange, MarketType, OrderSide, TradingPairMarketType
from qe.lib.trading_v2_types import CreateMasterOrderV2Request, MasterOrderV2Info, OrderFillV2Info, UpdateMasterOrderV2Request
from qe.pub import Pub
from qe.user import User
from qe.ws.client import WebSocketService
from qe.ws.types import WebSocketEventHandlers


class Response:
    status_code = 200
    headers = {}

    def __init__(self, body):
        self.body = body
        self.text = json.dumps(body)

    def json(self):
        return self.body


def option_request(**overrides):
    return dict(apiKeyId="binding-id", exchange=Exchange.DERIBIT,
                marketType=MarketType.OPTION, symbol="SOL_USDC-25DEC26-100-C",
                side=OrderSide.BUY, algorithm="TWAP", totalQuantity="10",
                worstPrice="0.125", **overrides)


@pytest.mark.parametrize("typed", [False, True])
@pytest.mark.parametrize("symbol,quantity,price", [
    ("SOL_USDC-25DEC26-100-C", "10", "0.125"),
    ("BTC-25DEC26-100000-P", "0.1", "0.0005"),
    ("ETH-25DEC26-3000-C", "0.1", "0.0001"),
    ("SOL_USDC-25DEC26-100-C", "10", "-1"),
    ("BTC-25DEC26-100000-P", "0.1", "-1"),
    ("ETH-25DEC26-3000-C", "0.1", "-1"),
])
def test_option_create_preserves_units_and_signs_target_direction(monkeypatch, typed, symbol, quantity, price):
    client = User("key", "secret", base_url="https://example.test")
    captured = {}
    monkeypatch.setattr("qe.api.get_timestamp", lambda: 1792540800000)

    def post(**kwargs):
        captured.update(kwargs)
        return Response({"code": 200, "message": {"masterOrderId": "option-order", "status": "NEW"}})

    monkeypatch.setattr(client.session, "post", post)
    params = option_request(isTargetPosition=True, expectedExecutionSide=OrderSide.SELL,
                            mustComplete=False, tailOrderProtection=False)
    params.update(symbol=symbol, totalQuantity=Decimal(quantity), worstPrice=Decimal(price))
    if typed:
        client.create_master_order_v2(CreateMasterOrderV2Request(**params))
    else:
        client.create_master_order_v2(**params)
    body = captured["json"]
    assert body["symbol"] == symbol
    assert body["totalQuantity"] == quantity
    assert body["worstPrice"] == price
    assert body["side"] == "buy"
    assert body["expectedExecutionSide"] == "sell"
    assert body["executionDurationSeconds"] == 1800
    assert body["mustComplete"] is False and body["tailOrderProtection"] is False
    query = parse_qs(captured["params"])
    assert set(query) == {"timestamp", "signature"}
    values = {key: str(value.value if hasattr(value, "value") else value).lower()
              if isinstance(value, bool) else str(value.value if hasattr(value, "value") else value)
              for key, value in body.items()}
    values["timestamp"] = query["timestamp"][0]
    assert query["signature"] == [client._get_sign(urlencode(sorted(values.items())))]


@pytest.mark.parametrize("typed", [False, True])
@pytest.mark.parametrize("side", ["buy", "sell"])
@pytest.mark.parametrize("price", ["-1", -1, Decimal("-1")])
def test_option_automatic_premium_create_and_amend(monkeypatch, typed, side, price):
    client = User("key", "secret")
    sent = []
    monkeypatch.setattr(client, "sign_json_request", lambda *args: sent.append(args))
    params = option_request()
    params.update(side=side, worstPrice=price)
    if typed:
        client.create_master_order_v2(CreateMasterOrderV2Request(**params))
    else:
        client.create_master_order_v2(**params)
    assert sent[0][0:2] == ("POST", "/user/trading/v2/master-orders")
    assert sent[0][2]["marketType"] == "OPTION"
    assert sent[0][2]["side"] == side
    assert sent[0][2]["worstPrice"] == "-1"
    for premium in ["0.125", price]:
        if typed:
            client.update_master_order_v2("option-order", UpdateMasterOrderV2Request(worstPrice=premium))
        else:
            client.update_master_order_v2("option-order", worstPrice=premium)
    assert [request[2]["worstPrice"] for request in sent] == ["-1", "0.125", "-1"]
    assert all(request[0:2] == ("PUT", "/user/trading/v2/master-orders/option-order/update") for request in sent[1:])


@pytest.mark.parametrize("typed", [False, True])
@pytest.mark.parametrize("changes", [
    {"exchange": "Binance"}, {"orderNotional": "10", "totalQuantity": None},
    {"isMargin": True}, {"worstPrice": None}, {"worstPrice": "0"},
    {"worstPrice": "-2"}, {"worstPrice": "-0.5"}, {"worstPrice": "-1.0"},
    {"worstPrice": ""}, {"worstPrice": "NaN"}, {"worstPrice": "Inf"}, {"totalQuantity": "0"},
    {"isTargetPosition": True}, {"isTargetPosition": True, "expectedExecutionSide": "long"},
    {"triggerPrice": "0.1"}, {"triggerPrice1": "0.1", "maxTriggerWaitSecs": 0},
    {"triggerPrice": "0.1", "maxTriggerWaitSecs": float("inf")},
    {"worstPrice": "-1", "totalQuantity": "-1"},
    {"worstPrice": "-1", "totalQuantity": "-1", "isTargetPosition": True, "expectedExecutionSide": "sell"},
    {"worstPrice": "-1", "isTargetPosition": True},
    {"worstPrice": "-1", "triggerPrice": "0.1"},
])
def test_invalid_option_requests_do_not_reach_http(monkeypatch, changes, typed):
    client = User("key", "secret")
    monkeypatch.setattr(client.session, "post", lambda **_: pytest.fail("invalid option sent"))
    params = option_request()
    params.update(changes)
    with pytest.raises(ValueError):
        if typed:
            client.create_master_order_v2(CreateMasterOrderV2Request(**params))
        else:
            client.create_master_order_v2(**params)


def test_zero_target_and_direction_change_error(monkeypatch):
    client = User("key", "secret")

    def post(**kwargs):
        assert kwargs["json"]["totalQuantity"] == "0"
        assert kwargs["json"]["expectedExecutionSide"] == "sell"
        return Response({"code": 409, "reason": "OPTION_DIRECTION_CHANGED", "message": "refresh position"})

    monkeypatch.setattr(client.session, "post", post)
    params = option_request(isTargetPosition=True, expectedExecutionSide="sell")
    params["totalQuantity"] = "0"
    with pytest.raises(APIError) as err:
        client.create_master_order_v2(**params)
    assert err.value.reason == "OPTION_DIRECTION_CHANGED"


def test_exact_option_query_preserves_price_tiers(monkeypatch):
    client = Pub(base_url="https://example.test")
    symbol = "AVAX_USDC-25DEC26-10d3-C"
    item = {"symbol": symbol, "marketType": "OPTION", "contractSize": "100",
            "optionType": "call", "strike": "10.3", "expirationTimestamp": "1798185600000",
            "tickSize": "0.0001", "stepSize": "100", "minOrderQty": "100",
            "rulesReady": True, "tickSizeSteps": [{"abovePrice": "0.005", "tickSize": "0.0005"}]}

    def get(**kwargs):
        assert kwargs["url"].endswith("/pub/v2/trading-pairs")
        query = parse_qs(kwargs["params"])
        assert query["marketType"] == ["OPTION"]
        assert query["exchange"] == ["Deribit"] and query["symbol"] == [symbol]
        return Response({"code": 200, "message": {"items": [item]}})

    monkeypatch.setattr(client.session, "get", get)
    for market in (MarketType.OPTION, TradingPairMarketType.OPTION):
        assert client.trading_pairs_v2(exchange=Exchange.DERIBIT, marketType=market, symbol=symbol)["items"] == [item]


@pytest.mark.parametrize("timestamp", [1798185600000, "1798185600000"])
def test_option_metadata_survives_http_models_and_ws_dispatch(timestamp):
    meta = dict(optionType="put", strike="100000", expirationTimestamp=timestamp,
                contractSize="1", contractType="reversed", underlyingIndex="btc_usd")
    data = dict(masterOrderId="option-order", symbol="BTC-25DEC26-100000-P",
                category="option", marketType="OPTION", quoteCurrency="BTC",
                baseCurrency="BTC", optionMetadata=meta)
    for cls in (MasterOrderV2Info, OrderFillV2Info):
        result = cls.from_dict(data)
        assert result.optionMetadata.expirationTimestamp == 1798185600000
        assert result.optionMetadata.strike == "100000"
        assert result.quoteCurrency == "BTC"
        assert cls.from_dict({"symbol": "BTCUSDT"}).optionMetadata is None
    seen = []
    ws = WebSocketService(client=None)
    ws.set_handlers(WebSocketEventHandlers(on_master_order=seen.append, on_order=seen.append))
    for event in ("master_data", "order_data"):
        asyncio.run(ws._handle_message(json.dumps({"type": event, "data": json.dumps(data)})))
    assert len(seen) == 2
    assert all(msg.option_metadata.contractType == "reversed" and msg.quote_currency == "BTC" for msg in seen)


@pytest.mark.parametrize("market", ["SPOT", "PERP", "OPTION"])
def test_defaults_and_validation_do_not_leak_to_other_markets(monkeypatch, market):
    client = User("key", "secret")
    sent = []

    def post(**kwargs):
        sent.append(kwargs["json"])
        return Response({"code": 200, "message": {"masterOrderId": "test", "status": "NEW"}})

    monkeypatch.setattr(client.session, "post", post)
    params = option_request(executionDurationSeconds=0, triggerPrice="0", triggerPrice1="", maxTriggerWaitSecs=0)
    params["marketType"] = market
    if market != "OPTION":
        with pytest.raises(ValueError):
            client.create_master_order_v2(**params)
        assert not sent
        params.update(executionDurationSeconds=300, worstPrice="-1", isTargetPosition=True)
    client.create_master_order_v2(**params)
    assert sent[0]["executionDurationSeconds"] == (1800 if market == "OPTION" else 300)
    assert not {"expectedExecutionSide", "mustComplete", "tailOrderProtection"}.intersection(sent[0])


def test_active_option_trigger_with_finite_wait(monkeypatch):
    client = User("key", "secret")
    sent = []
    monkeypatch.setattr(client, "sign_json_request", lambda *args: sent.append(args[2]))
    client.create_master_order_v2(**option_request(triggerPrice1="0.001", maxTriggerWaitSecs=120))
    assert sent[0]["triggerPrice1"] == "0.001" and sent[0]["maxTriggerWaitSecs"] == 120


@pytest.mark.parametrize("typed", [False, True])
@pytest.mark.parametrize("field", ["triggerPrice", "triggerPrice1"])
@pytest.mark.parametrize("price,valid", [
    ("", True), (" \t ", True), ("0.0", True), ("0e9999999999", True),
    (" 0.125 ", True), (".125", True), ("1.", True), ("+0.125", True),
    ("1.25e-1", True), ("1e-10", True), ("1e19", True),
    ("99999999999999999999.1234567891", True),
    ("0001.1234567891000", True), ("1.234567891234e3", True),
    ("1_000", False), ("1/2", False), ("0x1p-1", False),
    ("-0", False), ("-0.125", False), ("NaN", False), ("Inf", False),
    ("1e20", False), ("1e-11", False), ("1e9999999999", False),
    ("65000.12345678901", False), ("99999999999999999999.99999999991", False),
])
def test_option_trigger_prices_follow_backend_contract(monkeypatch, typed, field, price, valid):
    # backend-server normalizeTriggerPrice: exact DECIMAL(30,10), including exponents.
    client = User("key", "secret")
    sent = []
    monkeypatch.setattr(client, "sign_json_request", lambda *args: sent.append(args[2]))
    params = option_request(maxTriggerWaitSecs=120)
    params[field] = price
    call_kwargs = {"request": CreateMasterOrderV2Request(**params)} if typed else params
    if valid:
        client.create_master_order_v2(**call_kwargs)
        assert sent[0][field] == price
    else:
        with pytest.raises(ValueError, match="trigger"):
            client.create_master_order_v2(**call_kwargs)
        assert not sent


@pytest.mark.parametrize("price", [" 0.125 ", " -1 "])
@pytest.mark.parametrize("typed", [False, True])
def test_option_premium_limit_accepts_backend_whitespace(monkeypatch, price, typed):
    client = User("key", "secret")
    sent = []
    monkeypatch.setattr(client, "sign_json_request", lambda *args: sent.append(args[2]))
    params = option_request()
    params["worstPrice"] = price
    if typed:
        client.create_master_order_v2(CreateMasterOrderV2Request(**params))
    else:
        client.create_master_order_v2(**params)
    assert sent[0]["worstPrice"] == price


def test_optional_metadata_and_public_exports():
    from qe import OptionMetadata
    from qe.lib import OptionMetadata as LibOptionMetadata

    assert OptionMetadata is LibOptionMetadata
    for cls in (MasterOrderV2Info, OrderFillV2Info):
        assert cls.from_dict({"optionMetadata": None}).optionMetadata is None
    seen = []
    ws = WebSocketService(client=None)
    ws.set_handlers(WebSocketEventHandlers(on_master_order=seen.append, on_order=seen.append))
    for event in ("master_data", "order_data"):
        asyncio.run(ws._handle_message(json.dumps({"type": event, "data": {"symbol": "BTCUSDT", "optionMetadata": None}})))
    assert len(seen) == 2
    assert all(msg.option_metadata is None for msg in seen)
