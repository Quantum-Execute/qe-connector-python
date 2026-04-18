from qe.user.trading import create_master_order


class DummyClient:
    def __init__(self):
        self.calls = []

    def sign_request(self, method, url_path, payload=None):
        self.calls.append((method, url_path, payload or {}))
        return payload or {}


def test_create_master_order_passes_notes():
    client = DummyClient()

    create_master_order(
        client,
        algorithm="TWAP",
        exchange="Binance",
        symbol="BTCUSDT",
        marketType="SPOT",
        side="buy",
        apiKeyId="test-account-id",
        notes="desk-a",
    )

    assert len(client.calls) == 1
    method, url_path, payload = client.calls[0]
    assert method == "POST"
    assert url_path == "/user/trading/master-orders"
    assert payload["notes"] == "desk-a"
