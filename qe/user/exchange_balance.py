# ─────────────────────────────────────────────────────────────────────────────
# 余额类
# ─────────────────────────────────────────────────────────────────────────────

def get_account_balance(self, binding_id, **kwargs):
    """Get Binance spot account balance (USER_DATA)

    GET /user/exchange-apis/account-balance

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/account-balance",
        {"bindingId": binding_id, **kwargs},
    )


def get_margin_balance(self, binding_id, **kwargs):
    """Get Binance futures account balance (USER_DATA)

    GET /user/exchange-apis/margin-balance

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/margin-balance",
        {"bindingId": binding_id, **kwargs},
    )


def get_pv1_balance(self, binding_id, **kwargs):
    """Get Binance PAPI PV1 balance (USER_DATA)

    GET /user/exchange-apis/pv1-balance

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/pv1-balance",
        {"bindingId": binding_id, **kwargs},
    )


def get_okx_account_balance(self, binding_id, **kwargs):
    """Get OKX account balance (USER_DATA)

    GET /user/exchange-apis/okx-account-balance

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/okx-account-balance",
        {"bindingId": binding_id, **kwargs},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 持仓类
# ─────────────────────────────────────────────────────────────────────────────

def get_fapi_position_side_dial(self, binding_id, **kwargs):
    """Get Binance FAPI position side dual status (USER_DATA)

    GET /user/exchange-apis/fapi-position-side-dial

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/fapi-position-side-dial",
        {"bindingId": binding_id, **kwargs},
    )


def get_papi_um_position_side_dual(self, binding_id, **kwargs):
    """Get Binance PAPI UM position side dual status (USER_DATA)

    GET /user/exchange-apis/papi-um-position-side-dual

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/papi-um-position-side-dual",
        {"bindingId": binding_id, **kwargs},
    )


def get_okx_account_positions(self, binding_id, **kwargs):
    """Get OKX account positions (USER_DATA)

    GET /user/exchange-apis/okx-account-positions

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/okx-account-positions",
        {"bindingId": binding_id, **kwargs},
    )


def get_okx_account_max_size(self, binding_id, inst_id, td_mode, **kwargs):
    """Get OKX account max order size (USER_DATA)

    GET /user/exchange-apis/okx-account-max-size

    Args:
        binding_id (str): Exchange API Key binding UUID
        inst_id (str): Product ID, e.g. BTC-USDT-SWAP
        td_mode (str): Trade mode: cross, isolated, cash

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/okx-account-max-size",
        {"bindingId": binding_id, "instId": inst_id, "tdMode": td_mode, **kwargs},
    )


def get_ltp_position(self, binding_id, **kwargs):
    """Get LTP account positions (USER_DATA)

    GET /user/exchange-apis/ltp-position

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        sym (str, optional): Trading pair symbol; omit to query all positions
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/ltp-position",
        {"bindingId": binding_id, **kwargs},
    )


def get_deribit_position(self, binding_id, **kwargs):
    """Get Deribit account positions (USER_DATA)

    GET /user/exchange-apis/deribit-position

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/deribit-position",
        {"bindingId": binding_id, **kwargs},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 账户类
# ─────────────────────────────────────────────────────────────────────────────

def get_um_account(self, binding_id, **kwargs):
    """Get Binance PAPI UM account (USER_DATA)

    GET /user/exchange-apis/um-account

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/um-account",
        {"bindingId": binding_id, **kwargs},
    )


def get_cm_account(self, binding_id, **kwargs):
    """Get Binance PAPI CM account (USER_DATA)

    GET /user/exchange-apis/cm-account

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/cm-account",
        {"bindingId": binding_id, **kwargs},
    )


def get_pv1_account(self, binding_id, **kwargs):
    """Get Binance PAPI PV1 account (USER_DATA)

    GET /user/exchange-apis/pv1-account

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/pv1-account",
        {"bindingId": binding_id, **kwargs},
    )


def get_dapi_account(self, binding_id, **kwargs):
    """Get Binance DAPI account (USER_DATA)

    GET /user/exchange-apis/dapi-account

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/dapi-account",
        {"bindingId": binding_id, **kwargs},
    )


def get_fapi_account(self, binding_id, **kwargs):
    """Get Binance FAPI account (USER_DATA)

    GET /user/exchange-apis/fapi-account

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/fapi-account",
        {"bindingId": binding_id, **kwargs},
    )


def get_cross_margin_account_detail(self, binding_id, **kwargs):
    """Get Binance cross margin account detail (USER_DATA)

    GET /user/exchange-apis/cross-margin-account-detail

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/cross-margin-account-detail",
        {"bindingId": binding_id, **kwargs},
    )


def get_ltp_account(self, binding_id, **kwargs):
    """Get LTP account info (USER_DATA)

    GET /user/exchange-apis/ltp-account

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/ltp-account",
        {"bindingId": binding_id, **kwargs},
    )


def get_ltp_portfolio_asset(self, binding_id, **kwargs):
    """Get LTP portfolio assets (USER_DATA)

    GET /user/exchange-apis/ltp-portfolio-asset

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/ltp-portfolio-asset",
        {"bindingId": binding_id, **kwargs},
    )


def get_deribit_account(self, binding_id, **kwargs):
    """Get Deribit account info (USER_DATA)

    GET /user/exchange-apis/deribit-account

    Args:
        binding_id (str): Exchange API Key binding UUID

    Keyword Args:
        recvWindow (int, optional): The value cannot be greater than 60000
    """
    return self.sign_request(
        "GET",
        "/user/exchange-apis/deribit-account",
        {"bindingId": binding_id, **kwargs},
    )
