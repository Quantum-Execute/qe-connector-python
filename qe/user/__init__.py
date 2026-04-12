from qe.api import API


class User(API):
    def __init__(self, api_key=None, api_secret=None, **kwargs):
        if "base_url" not in kwargs:
            kwargs["base_url"] = "https://api.quantumexecute.com"
        super().__init__(api_key, api_secret, **kwargs)

    # CONVERT
    from qe.user.exchange import list_exchange_apis
    from qe.user.trading import get_master_orders
    from qe.user.trading import get_master_order_detail
    from qe.user.trading import get_master_order_detail_by_client_order_id
    from qe.user.trading import get_order_fills
    from qe.user.trading import get_tca_analysis
    from qe.user.trading import create_master_order
    from qe.user.trading import pause_master_order
    from qe.user.trading import resume_master_order
    from qe.user.trading import update_master_order_params
    from qe.user.trading import cancel_master_order
    from qe.user.trading import create_listen_key

    # Exchange balance / position / account queries
    from qe.user.exchange_balance import get_account_balance
    from qe.user.exchange_balance import get_margin_balance
    from qe.user.exchange_balance import get_pv1_balance
    from qe.user.exchange_balance import get_okx_account_balance
    from qe.user.exchange_balance import get_fapi_position_side_dial
    from qe.user.exchange_balance import get_papi_um_position_side_dual
    from qe.user.exchange_balance import get_okx_account_positions
    from qe.user.exchange_balance import get_okx_account_max_size
    from qe.user.exchange_balance import get_ltp_position
    from qe.user.exchange_balance import get_deribit_position
    from qe.user.exchange_balance import get_um_account
    from qe.user.exchange_balance import get_cm_account
    from qe.user.exchange_balance import get_pv1_account
    from qe.user.exchange_balance import get_dapi_account
    from qe.user.exchange_balance import get_fapi_account
    from qe.user.exchange_balance import get_cross_margin_account_detail
    from qe.user.exchange_balance import get_ltp_account
    from qe.user.exchange_balance import get_ltp_portfolio_asset
    from qe.user.exchange_balance import get_deribit_account
    from qe.user.exchange_balance import get_hyperliquid_spot_balance
    from qe.user.exchange_balance import get_hyperliquid_positions
