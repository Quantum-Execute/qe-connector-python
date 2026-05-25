from qe.lib.trading_enums import Exchange
from qe.lib.trading_v2_types import validate_exchange


def test_bybit_exchange_enum_value():
    assert Exchange.BYBIT.value == "Bybit"


def test_bybit_is_valid_v2_exchange():
    validate_exchange("Bybit")
