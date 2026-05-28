from qe.user.trading_v2 import create_listen_key_v2
from qe.ws.client import WebSocketService


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
