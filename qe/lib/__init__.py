"""QE Library 导出"""

# 导出交易枚举
from qe.lib.trading_enums import (
    MasterOrderStatus,
    Algorithm,
    StrategyType,
    MarketType,
    OrderSide,
    MarginType,
    Exchange,
    Category,
    TradingPairMarketType
)

# 导出传输类型枚举
from qe.lib.enums import TransferType

# V2 trading dataclasses / status set
from qe.lib.trading_v2_types import (
    MasterOrderStatusV2,
    MASTER_ORDER_STATUSES_V2,
    PAGE_SIZE_MAX,
    DecimalLike,
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

__all__ = [
    # 交易枚举 (V1 + 共享)
    'MasterOrderStatus',
    'Algorithm',
    'StrategyType',
    'MarketType',
    'OrderSide',
    'MarginType',
    'Exchange',
    'Category',
    'TradingPairMarketType',
    # 传输枚举
    'TransferType',
    # V2 类型
    'MasterOrderStatusV2',
    'MASTER_ORDER_STATUSES_V2',
    'PAGE_SIZE_MAX',
    'DecimalLike',
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
