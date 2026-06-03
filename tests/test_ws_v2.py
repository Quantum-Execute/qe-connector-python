import asyncio
import json
import threading

from qe.user.trading_v2 import create_listen_key_v2
from qe.ws.client import WebSocketService
from qe.ws.types import WebSocketEventHandlers


class DummyClient:
    def __init__(self):
        self.calls = []

    def sign_request(self, method, url_path, payload=None):
        self.calls.append((method, url_path, payload or {}))
        return {"listenKey": "lk", "expireAt": "1778863931", "success": True}


def test_create_listen_key_v2_uses_v2_route():
    client = DummyClient()

    reply = create_listen_key_v2(client)

    assert reply["listenKey"] == "lk"
    assert client.calls == [("POST", "/user/trading/v2/listen-key", {})]


def test_websocket_service_defaults_to_v2_ws_url():
    service = WebSocketService(client=None, base_url="wss://example.test")
    service.listen_key = "lk"

    assert service._get_websocket_url() == "wss://example.test/api/ws/v2?listen_key=lk"


def test_websocket_service_can_build_legacy_v1_url():
    service = WebSocketService(client=None, base_url="wss://example.test", version="v1")
    service.listen_key = "lk"

    assert service._get_websocket_url() == "wss://example.test/api/ws?listen_key=lk"


def test_v2_master_data_lower_camel_case_dispatches_typed_master_order():
    service = WebSocketService(client=None)
    seen = []
    service.set_handlers(WebSocketEventHandlers(on_master_order=seen.append))

    payload = {
        "type": "master_data",
        "messageId": "msg-1",
        "userId": "user-1",
        "data": json.dumps(
            {
                "masterOrderId": "DOGEUSDT-20260601-2061345820651737088",
                "clientOrderId": "py-sdk-qty-1",
                "symbol": "DOGEUSDT",
                "side": "buy",
                "totalQuantity": "100",
                "cumFilledQty": "100",
                "executionDurationSeconds": "60",
                "marketType": "SPOT",
                "status": "COMPLETED",
            }
        ),
    }

    asyncio.run(service._handle_message(json.dumps(payload)))

    assert len(seen) == 1
    assert seen[0].master_order_id == "DOGEUSDT-20260601-2061345820651737088"
    assert seen[0].client_id == "py-sdk-qty-1"
    assert seen[0].qty == 100.0
    assert seen[0].duration_secs == 60.0
    assert seen[0].category == "SPOT"
    assert seen[0].symbol == "DOGEUSDT"
    assert seen[0].status == "COMPLETED"


def test_v2_order_data_lower_camel_case_dispatches_typed_order():
    service = WebSocketService(client=None)
    seen = []
    service.set_handlers(WebSocketEventHandlers(on_order=seen.append))

    payload = {
        "type": "order_data",
        "messageId": "msg-2",
        "userId": "user-1",
        "data": json.dumps(
            {
                "id": "195840221",
                "masterOrderId": "DOGEUSDT-20260601-2061345820651737088",
                "orderId": "exchange-order-1",
                "symbol": "DOGEUSDT",
                "category": "spot",
                "side": "buy",
                "price": "0.25",
                "quantity": "100",
                "filledQuantity": "100",
                "filledNotional": "25",
                "averagePrice": "0.25",
                "status": "FILLED",
                "orderCreatedTime": "1719999999000",
                "orderType": "LIMIT",
            }
        ),
    }

    asyncio.run(service._handle_message(json.dumps(payload)))

    assert len(seen) == 1
    assert seen[0].master_order_id == "DOGEUSDT-20260601-2061345820651737088"
    assert seen[0].order_id == "exchange-order-1"
    assert seen[0].price == 0.25
    assert seen[0].quantity == 100.0
    assert seen[0].fill_qty == 100.0
    assert seen[0].fill_price == 0.25
    assert seen[0].cum_filled_qty == 100.0
    assert seen[0].status == "FILLED"


def test_websocket_close_runs_on_original_event_loop():
    service = WebSocketService(client=None)
    owner_loop = asyncio.new_event_loop()
    started = threading.Event()

    def run_owner_loop():
        asyncio.set_event_loop(owner_loop)
        started.set()
        owner_loop.run_forever()

    owner_thread = threading.Thread(target=run_owner_loop)
    owner_thread.start()
    started.wait(timeout=1)

    class LoopBoundWebSocket:
        closed = False

        async def close(self):
            if asyncio.get_running_loop() is not owner_loop:
                raise RuntimeError("closed on the wrong event loop")
            self.closed = True
            owner_loop.call_soon(owner_loop.stop)

    fake_ws = LoopBoundWebSocket()
    service.websocket = fake_ws
    service._is_connected = True
    service._loop = owner_loop

    try:
        service.close()
        assert fake_ws.closed is True
    finally:
        if owner_loop.is_running():
            owner_loop.call_soon_threadsafe(owner_loop.stop)
        owner_thread.join(timeout=1)
        owner_loop.close()


def test_websocket_close_can_run_from_original_event_loop():
    async def run_case():
        service = WebSocketService(client=None)
        owner_loop = asyncio.get_running_loop()

        class LoopBoundWebSocket:
            closed = False

            async def close(self):
                if asyncio.get_running_loop() is not owner_loop:
                    raise RuntimeError("closed on the wrong event loop")
                self.closed = True

        fake_ws = LoopBoundWebSocket()
        service.websocket = fake_ws
        service._is_connected = True
        service._loop = owner_loop

        service.close()
        await asyncio.sleep(0)

        assert fake_ws.closed is True

    asyncio.run(run_case())
