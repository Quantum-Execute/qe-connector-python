# 更新日志（Changelog）

本文件记录 `qe-connector`（Python SDK）的用户可见变更。

## 1.1.1 - 2026-05-11

### 修复 / 调整（V2 联调发现的 2 处问题）

- **`OrderFillV2Info.from_dict` 数值兼容**：后端契约规定 `filledNotional`
  / `filledQuantity` / `averagePrice` / `price` / `quantity` 均为 string，但旧
  版本/异常后端可能仍返回 number。`from_dict` 现在会安全地把 `int` / `float`
  / `Decimal` 强制转为非科学计数法的 string（`format(Decimal(repr(value)), "f")`），
  避免 `/order-fills` fills 非空时崩溃。
- **`MasterOrderStatusV2` 列表过滤语义澄清**：在枚举 docstring 上补充说明
  列表查询 `GET /user/trading/v2/master-orders` 只接受聚合值：`NEW`（=运行
  中全部状态）/ `COMPLETED`（=非运行中全部状态）；详情/推送仍按 8 种细
  分状态返回。建议列表过滤显式使用 `MasterOrderStatusV2.NEW` 或
  `MasterOrderStatusV2.COMPLETED`。

### 已知约束（不在本次修复范围）

- `qe.api.API.send_request` 对 `POST` / `PUT` 仍把 payload 放到 query string
  （走 `requests` 的 `params=`）。后端 V2 已新增 "body + query 合并解析"
  以兼容此行为；如需切换到 JSON body 走法请提专门 issue 讨论（影响其它
  Binance 风格端点的兼容性）。

## 1.1.0 - 2026-05-10

### 新增
- **V2 strategy-api 客户端封装**：覆盖 `/strategy-api/.../v2/...` 全部转发接口，与 V1 并存（V1 行为不变）。
  - `User.list_exchange_apis_v2()` → `GET /user/exchange/v2/exchange-apis`
  - `User.create_master_order_v2()` → `POST /user/trading/v2/master-orders`
  - `User.list_master_orders_v2()` → `GET /user/trading/v2/master-orders`
  - `User.get_master_order_v2(masterOrderId)` → `GET /user/trading/v2/master-orders/{id}`
  - `User.get_master_order_by_client_order_id_v2(clientOrderId)` → `GET /user/trading/v2/master-orders/by-client-order-id/{id}`
  - `User.list_order_fills_v2()` → `GET /user/trading/v2/order-fills`
  - `User.cancel_master_order_v2()` / `pause_master_order_v2()` / `resume_master_order_v2()` → `PUT /user/trading/v2/master-orders/{id}/{cancel|pause|resume}`
  - `User.update_master_order_v2()` → `PUT /user/trading/v2/master-orders/{id}/update`
  - `User.batch_cancel_master_orders_v2()` → `PUT /user/trading/v2/master-orders/batch-cancel`
- **V2 类型层**（`qe.lib.trading_v2_types`，亦在 `qe`、`qe.lib` 重新导出）：
  - 请求体 dataclass：`CreateMasterOrderV2Request`、`UpdateMasterOrderV2Request`
  - 响应/记录 dataclass：`CreateMasterOrderV2Reply`、`MasterOrderV2Info`、`OrderFillV2Info`、`ExchangeApiV2Info`、`MasterOrderActionV2Reply`、`BatchCancelV2Reply`、`BatchCancelV2FailedItem`
  - 列表分页：`MasterOrderListV2Reply`、`OrderFillListV2Reply`、`ExchangeApiListV2Reply`
  - 状态枚举：`MasterOrderStatusV2 = NEW/WAITING/PROCESSING/PAUSED/CANCELLED/COMPLETED/REJECTED/EXPIRED`
- **客户端校验**（与 backend-server 入参校验语义一致）：
  - `executionDurationSeconds` 必须 > 10
  - `totalQuantity` / `orderNotional` 二选一
  - `isTargetPosition=True` 时必须用 `totalQuantity`，禁止 `orderNotional`
  - `marketType ∈ {SPOT, PERP}`、`exchange ∈ {Binance, OKX, LTP, Deribit, Hyperliquid}`
- **Decimal 字符串化**：`totalQuantity / orderNotional / worstPrice / makerRateLimit / povLimit / povMinLimit / upTolerance / lowTolerance / limitPrice` 接受 `str | int | float | Decimal`，序列化时统一转 `str`，避免 JS 浮点精度问题。
- **示例**：`examples/user/v2/end_to_end_v2.py`（创建 → 列表 → 详情 → 子单 → 取消）、`list_exchange_apis_v2.py`、`batch_cancel_master_orders_v2.py`。

### 变更
- **`qe.__version__`**：升级到 `1.1.0`，并修复 `qe/__init__.py` 内重复硬编码的旧版本号（之前为 `1.0.4`，现统一从 `qe/__version__.py` 读取）。

### 兼容性
- V1 方法（`create_master_order`、`get_master_orders` 等）签名 / 路径 / 字段命名 **完全不变**；旧业务无需迁移。
- V2 字段使用 lowerCamelCase（与后端 wire format 1:1），dataclass 属性名同样为 camelCase；方法名为 snake_case（Python 习惯）。

### 隐藏字段说明（V2）
- 子单：不再返回 `fee`、`tradingAccount`；`subOrderId` → `orderId`，`filledValue` → `filledNotional`。
- 母单：不再返回 `id`、`userUid`、`apiKey`、`accountType`、`limitPrice/limitPriceString`、`takemakefeediff`、`algoStartTimeMs`、`completionProgress` 等内部字段；`apiKeyUuid` 取代 `apiKeyId/apiKey`，`cumFilledQty/cumFilledNotional/avgFilledPrice` 取代旧的 `filledQuantity/filledNotional/averagePrice`，`worstPrice` 取代 `limitPrice`。
- API Key：不再返回 `verificationMethod`、`balance`。

## 1.0.27 - 2026-04-12

### 新增
- **Hyperliquid 支持**：`Exchange` 枚举新增 `HYPERLIQUID = "Hyperliquid"`
- **暂停母单接口**：新增 `pause_master_order()` 方法，支持 `PUT /user/trading/master-orders/{masterOrderId}/pause`
  - 参数：`masterOrderId`（必填）、`reason`（可选）
- **恢复母单接口**：新增 `resume_master_order()` 方法，支持 `PUT /user/trading/master-orders/{masterOrderId}/resume`
  - 参数：`masterOrderId`（必填）
- **修改母单参数接口**：新增 `update_master_order_params()` 方法，支持 `PUT /user/trading/master-orders/{masterOrderId}/update`
  - 必填参数：`masterOrderId`
  - 可选参数：`orderNotional`、`totalQuantity`、`upTolerance`、`lowTolerance`、`enableMake`、`makerRateLimit`、`strictUpBound`、`povLimit`、`povMinLimit`、`limitPrice`、`worstPrice`、`tailOrderProtection`、`mustComplete`、`executionDurationSeconds`

### 变更
- **成交记录响应**：`get_order_fills()` 返回字段文档补充 `orderId`（子订单ID）、`quantity`（下单数量）、`createdAt`（数据创建时间）、`updatedAt`（最后修改时间）
- **`limitPrice` 参数标记为 Deprecated**：建议使用 `worstPrice` 替代，`limitPrice` 保留以兼容旧版本

## 1.0.25 - 2026-03-08

### 新增
- **币对品种枚举**：`Category` 新增 `PERP_CM = "perp_cm"`，用于表示 Binance 币本位合约

### 变更
- **创建母单接口**：新增 Binance 币本位合约限制校验
  - 当 `exchange=Binance`、`marketType=PERP` 且 `marginType=C` 时，仅允许使用 `totalQuantity`
  - `orderNotional` 在上述场景下不可用
  - `totalQuantity` 单位为张，且输入值必须为整数

### 文档
- README：补充 `marginType` 对 `C`（币本位）的支持说明
- README：补充 `isCoin=true` 时返回币本位合约可用交易对，仅 Binance 可用
- README：更新母单响应与筛选参数中的 `category` 说明，支持 `perp_cm`
- README：补充 Binance `perp_cm` 场景下 `totalQuantity` / `orderNotional` 的使用限制

## 1.0.24 - 2026-01-29

### 新增
- **通过client_order_id获取母单详情接口**：新增 `get_master_order_detail_by_client_order_id()` 方法，支持 `GET /user/trading/master-orders/by-client-order-id/{clientOrderId}`
- **创建母单入参**：`create_master_order()` 新增 `clientOrderId` 参数，支持用户自定义订单ID

### 变更
- **母单数据响应**：母单列表/母单详情新增 `clientOrderId` 字段返回

### 文档
- README：补充"通过client_order_id获取母单详情"用法，并在"创建主订单"参数中增加 `clientOrderId` 说明

## 1.0.23 - 2026-01-17

### 修复
- **获取母单详情接口**：修复 `get_master_order_detail()` 方法导出，支持 `GET /user/trading/master-orders/{masterOrderId}`

## 1.0.22 - 2026-01-17

### 新增
- **获取母单详情接口**：新增 `get_master_order_detail()` 方法，支持 `GET /user/trading/master-orders/{masterOrderId}`

### 变更
- **创建母单入参**：`create_master_order()` 新增 `executionDurationSeconds`（秒级执行时长；当提供且>0时优先使用，且必须大于10秒）
- **母单数据响应**：母单列表/母单详情新增 `executionDurationSeconds` 字段返回

### 文档
- README：补充“获取母单详情”用法，并在“创建主订单”参数中增加 `executionDurationSeconds` 说明

## 1.0.21 -2026-01-07

### 文档
- **Boost 算法支持交易对更新**：更新 `create_master_order()` 中 BoostVWAP、BoostTWAP 算法支持的交易对说明（仅Binance交易所可用。）
  - 现货支持的交易对：BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,LTCUSDT,AVAXUSDT,XLMUSDT,XRPUSDT,DOGEUSDT,CRVUSDT
  - 永续合约支持的交易对：BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,LTCUSDT,AVAXUSDT,XLMUSDT,XRPUSDT,DOGEUSDT,ADAUSDT,BCHUSDT,FILUSDT,1000SATSUSDT,CRVUSDT

## 1.0.20 - 2026-01-06

### 变更
- **创建母单入参**：新增 `create_master_order()` 入参：`enableMake`，是否允许挂单
- **TCA 分析接口响应格式**：`get_tca_analysis()` 返回的字典字段名更新
  - 响应字段名从 snake_case 改为 PascalCase，与后端接口和 Excel 表头一致
  - 字段顺序与 Excel 表头保持一致
- **母单数据响应格式**：更新 `get_master_orders()` 返回类型
  - 新增字段`makerRate`，被动成交率
  - 新增字段`enableMake`，是否允许挂单
  - 新增字段`tailOrderProtection`，尾单保护开关
  - 新增字段`commission`，手续费明细，格式为字典

### 文档
- **创建母单入参文档更新**：
    - 新增入参字段描述
- **TCA 分析接口文档更新**：
  - 更新响应字段描述表格，使用 Excel 表头字段名（PascalCase）
  - 更新示例代码以使用新的字段名
  - 字段描述添加中文描述
- **母单数据响应接口文档更新**：
  - 更新响应字段描述
- **示例代码更新**：更新 `examples/user/get_tca_analysis.py` 以使用新的 PascalCase 字段名
 
## 1.0.20rc1 - 2025-12-28

### 变更
- **TCA 分析接口响应格式**：`get_tca_analysis()` 返回的字典字段名更新
  - 响应字段名从 snake_case 改为 PascalCase，与后端接口和 Excel 表头一致
  - 字段顺序与 Excel 表头保持一致

### 文档
- **TCA 分析接口文档更新**：
  - 更新响应字段描述表格，使用 Excel 表头字段名（PascalCase）
  - 更新示例代码以使用新的字段名
  - 字段描述直接使用 Excel 表头名称
- **示例代码更新**：更新 `examples/user/get_tca_analysis.py` 以使用新的 PascalCase 字段名

## 1.0.19 - 2025-12-26

### 新增
- **TCA 分析接口**：新增 `get_tca_analysis()` 方法，支持查询 TCA（Transaction Cost Analysis）分析数据
  - 接口路径：`GET /user/trading/tca-analysis`（签名鉴权）
  - 支持参数：`symbol`、`category`、`apikey`、`startTime`、`endTime`
  - 返回类型：后端 `message` 原样（`list[dict]`）
- **示例文件**：新增 `examples/user/get_tca_analysis.py`

### 变更
- **创建母单接口**：移除 `endTime` 参数（该字段已废弃，不再使用）
- **executionDuration 参数类型**：从 `str` 改为 `int`，统一为数字类型

### 文档
- **参数描述更新**：
  - `makerRateLimit`：补充范围说明（包含0和1，输入0.1代表10%）
  - `povLimit`：补充范围说明（包含0和1，输入0.1代表10%）
  - `upTolerance`：更新范围说明（不包含0和1，最小输入0.0001，最大输入0.9999）
  - `lowTolerance`：更新范围说明（不包含0和1，最小输入0.0001，最大输入0.9999）

## 1.0.18 - 2025-12-15

### 新增
- **Deribit 支持**：`Exchange` 枚举新增 `DERIBIT = "Deribit"`。

### 变更
- **Deribit(BTCUSD/ETHUSD) 下单限制**：当 `exchange=Deribit` 且 `symbol` 为 `BTCUSD` 或 `ETHUSD` 时：
  - 仅允许使用 `totalQuantity`（单位：USD）
  - 禁止使用 `orderNotional`

### 文档
- README：`exchange` 可选值补充 `Deribit`，并补充 Deribit BTCUSD/ETHUSD 的数量字段说明。

