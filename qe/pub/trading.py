from qe.lib.trading_enums import Exchange, TradingPairMarketType


def _normalize_trading_pair_filters(kwargs):
    """Serialize SDK enums to the public API's string query values."""
    params = dict(kwargs)
    if isinstance(params.get("exchange"), Exchange):
        params["exchange"] = params["exchange"].value
    if isinstance(params.get("marketType"), TradingPairMarketType):
        params["marketType"] = params["marketType"].value
    return params


def trading_pairs(self, **kwargs):
    """Get trading pairs list (PUBLIC)
    
    Get list of trading pairs
    
    GET /pub/trading-pairs
    
    Keyword Args:
        page (int, optional): Page number for pagination
        pageSize (int, optional): Number of items per page
        exchange (Exchange | str, optional): Exchange name filter
        marketType (TradingPairMarketType | str, optional): Market type filter
        isCoin (bool, optional): Coin filter
    """
    return self.query("/pub/trading-pairs", _normalize_trading_pair_filters(kwargs))


def trading_pairs_v2(self, **kwargs):
    """Get the V2 public trading-pair list.

    ``GET /pub/v2/trading-pairs``

    Keyword Args:
        exchange (Exchange | str, optional): Exchange name filter.
        marketType (TradingPairMarketType | str, optional): ``SPOT`` or ``PERP``.
        isCoin (bool, optional): Whether to return coin-margined contracts.
    """
    return self.query("/pub/v2/trading-pairs", _normalize_trading_pair_filters(kwargs))
