"""
QE Connector Python SDK
"""
from .api import API
from .error import (
    Error,
    ClientError,
    APIError,
    ServerError,
    ParameterRequiredError,
    ParameterValueError,
    ParameterTypeError,
    ParameterArgumentError,
    WebsocketClientError
)

# WebSocket相关导入
from .ws import (
    WebSocketService,
    WebSocketEventHandlers,
    ClientPushMessage,
    MasterOrderMessage,
    OrderMessage,
    FillMessage,
    BaseThirdPartyMessage,
    ClientMessageType,
    ThirdPartyMessageType
)

# V2 trading dataclasses / status set re-exported at top level for convenience.
from .lib.trading_v2_types import (
    MasterOrderStatusV2,
    MASTER_ORDER_STATUSES_V2,
    PAGE_SIZE_MAX,
    ExchangeApiV2Info,
    ExchangeApiListV2Reply,
    CreateMasterOrderV2Request,
    CreateMasterOrderV2Reply,
    MasterOrderV2Info,
    MasterOrderListV2Reply,
    OrderFillV2Info,
    OrderFillListV2Reply,
    MasterOrderActionV2Reply,
    UpdateMasterOrderV2Request,
    BatchCancelV2FailedItem,
    BatchCancelV2Reply,
)

from .__version__ import __version__

__all__ = [
    'API',
    'Error',
    'ClientError',
    'APIError',
    'ServerError',
    'ParameterRequiredError',
    'ParameterValueError',
    'ParameterTypeError',
    'ParameterArgumentError',
    'WebsocketClientError',
    'WebSocketService',
    'WebSocketEventHandlers',
    'ClientPushMessage',
    'MasterOrderMessage',
    'OrderMessage',
    'FillMessage',
    'BaseThirdPartyMessage',
    'ClientMessageType',
    'ThirdPartyMessageType',
    # V2 trading types
    'MasterOrderStatusV2',
    'MASTER_ORDER_STATUSES_V2',
    'PAGE_SIZE_MAX',
    'ExchangeApiV2Info',
    'ExchangeApiListV2Reply',
    'CreateMasterOrderV2Request',
    'CreateMasterOrderV2Reply',
    'MasterOrderV2Info',
    'MasterOrderListV2Reply',
    'OrderFillV2Info',
    'OrderFillListV2Reply',
    'MasterOrderActionV2Reply',
    'UpdateMasterOrderV2Request',
    'BatchCancelV2FailedItem',
    'BatchCancelV2Reply',
]
