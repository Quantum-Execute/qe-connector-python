from qe.lib.trading_enums import Exchange, TradingPairMarketType, MarketType


def _normalize_trading_pair_filters(kwargs):
    """Serialize SDK enums to the public API's string query values."""
    params = dict(kwargs)
    if isinstance(params.get("exchange"), Exchange):
        params["exchange"] = params["exchange"].value
    if isinstance(params.get("marketType"), (TradingPairMarketType, MarketType)):
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
        marketType (TradingPairMarketType | str, optional): ``SPOT``, ``PERP`` or ``OPTION`` (Deribit).
        isCoin (bool, optional): PERP filter; not an option settlement selector.
        symbol (str, optional): Exact published contract name. For an active
            option, resolves price tiers and sets rulesReady=true. List-only
            option rows are not complete executable price rules.

    Returns a dict containing items, including option identity, base-asset
    quantity rules, premium tickSize/tickSizeSteps, and rulesReady.
    """
    return self.query("/pub/v2/trading-pairs", _normalize_trading_pair_filters(kwargs))
