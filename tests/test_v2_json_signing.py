import json
import urllib.parse

from qe.user import User


class DummyResponse:
    status_code = 200
    headers = {}
    text = '{"code":200,"message":{"successCount":0,"failedOrders":[]}}'

    def json(self):
        return json.loads(self.text)


def test_batch_cancel_v2_sends_business_fields_in_json_body_and_signs_them(monkeypatch):
    captured = {}

    def fake_put(**kwargs):
        captured.update(kwargs)
        return DummyResponse()

    monkeypatch.setattr("qe.api.get_timestamp", lambda: 1735372000000)

    client = User("api-key", "secret", base_url="https://api.example.com/strategy-api")
    monkeypatch.setattr(client.session, "put", fake_put)

    result = client.batch_cancel_master_orders_v2(["mo_001", "mo_002"], reason="risk_limit_breach")

    assert result == {"successCount": 0, "failedOrders": []}
    assert captured["url"] == (
        "https://api.example.com/strategy-api"
        "/user/trading/v2/master-orders/batch-cancel"
    )
    assert captured["json"] == {
        "masterOrderIds": ["mo_001", "mo_002"],
        "reason": "risk_limit_breach",
    }

    query = captured["params"]
    parsed_query = urllib.parse.parse_qs(query)
    assert set(parsed_query) == {"timestamp", "signature"}
    assert parsed_query["timestamp"] == ["1735372000000"]

    sign_values = {
        "masterOrderIds": json.dumps(["mo_001", "mo_002"], separators=(",", ":")),
        "reason": "risk_limit_breach",
        "timestamp": "1735372000000",
    }
    sign_string = urllib.parse.urlencode(sorted(sign_values.items()), doseq=True)
    assert sign_string == (
        "masterOrderIds=%5B%22mo_001%22%2C%22mo_002%22%5D"
        "&reason=risk_limit_breach&timestamp=1735372000000"
    )
    assert parsed_query["signature"] == [client._get_sign(sign_string)]
