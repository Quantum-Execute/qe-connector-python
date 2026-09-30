import pytest

from qe.lib.trading_v2_types import CreateMasterOrderV2Request, MasterOrderV2Info
from qe.user.trading_v2 import create_master_order_v2
from test_v2_pagination import DummyClient


def request(**kwargs):
    return CreateMasterOrderV2Request(
        apiKeyId="binding", exchange="OKX", marketType="SPOT", symbol="BTCUSDT",
        side="buy", algorithm="TWAP", executionDurationSeconds=60, totalQuantity="1", **kwargs,
    )


@pytest.mark.parametrize("action", [None, 0, 1, 10])
@pytest.mark.parametrize("typed", [True, False])
def test_timeout_action_transmission(action, typed):
    client = DummyClient()
    if typed:
        create_master_order_v2(client, request=request(maxTriggerWaitTimeoutAction=action))
    else:
        create_master_order_v2(client, request=request(), maxTriggerWaitTimeoutAction=action)
    body = client.json_calls[-1][2]
    assert body.get("maxTriggerWaitTimeoutAction") == action
    assert ("maxTriggerWaitTimeoutAction" in body) == (action is not None)


@pytest.mark.parametrize("action", [-1, 11, 0.5, 1.0, True, "1", "", float("nan"), float("inf")])
@pytest.mark.parametrize("typed", [True, False])
def test_invalid_timeout_action_never_sent(action, typed):
    client = DummyClient()
    with pytest.raises(ValueError, match="maxTriggerWaitTimeoutAction"):
        if typed:
            create_master_order_v2(client, request=request(maxTriggerWaitTimeoutAction=action))
        else:
            create_master_order_v2(client, request=request(), maxTriggerWaitTimeoutAction=action)
    assert client.json_calls == []


def test_timeout_action_zero_override_and_response():
    client = DummyClient()
    create_master_order_v2(client, request=request(maxTriggerWaitTimeoutAction=10), maxTriggerWaitTimeoutAction=0)
    assert client.json_calls[-1][2]["maxTriggerWaitTimeoutAction"] == 0
    assert MasterOrderV2Info.from_dict({"maxTriggerWaitTimeoutAction": 10}).maxTriggerWaitTimeoutAction == 10
    assert MasterOrderV2Info.from_dict({}).maxTriggerWaitTimeoutAction is None
