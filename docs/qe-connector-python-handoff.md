# qe-connector-python 交接文档

> 本文面向接手 `qe-connector-python` 的 SDK 维护、后端联调和发布同学。当前仓库是 Quantum Execute Strategy API 的 Python 官方 SDK，重点维护 V1 兼容层、Strategy API V2 母单交易接口、交易所账户/余额代理接口、公共交易对和 WebSocket 推送。

## 1. 项目定位

`qe-connector-python` 是外部用户在 Python 项目中调用 QE 平台 API 的客户端封装，不直接访问交易所，也不负责解密用户交易所 API Key。调用方传入 QE 平台签发的 Strategy API Key / Secret，SDK 负责：

- 在请求中加入 `timestamp`、`signature` 和 `X-MBX-APIKEY`。
- 封装 `User`、`Pub`、`Status`、`WebSocketService` 等入口。
- 保留 V1 方法，新增 `_v2` 后缀的 Strategy API V2 方法。
- 对 V2 JSON body 写接口使用后端一致的 body+query 合并签名。
- 提供 V2 dataclass，帮助调用方构造/解析 lowerCamelCase wire format。

和其它项目的关系：

- 后端 V2 契约参考 [backend-server/docs/frontend-v2-api-upgrade.md](../../backend-server/docs/frontend-v2-api-upgrade.md)。
- WebSocket 服务端行为参考 [backend-server/docs/websocket-api.md](../../backend-server/docs/websocket-api.md)。
- 外部文档站交接参考 [QE-API-Key/docs/qe-api-key-handoff.md](../../QE-API-Key/docs/qe-api-key-handoff.md)。
- Go SDK 交接参考 [qe-connector-go/docs/qe-connector-go-handoff.md](../../qe-connector-go/docs/qe-connector-go-handoff.md)。

需要特别注意：

- SDK endpoint 常量写的是 `/user/...`、`/pub/...`，没有硬编码 `/strategy-api`。如果部署要求显式前缀，应在 `base_url` 中带上 `/strategy-api`，不要改 endpoint 常量。
- `apiKeyId` 是用户绑定的交易所账户 ID；初始化 SDK 的 `api_key` 是 Strategy API Key。
- 算法侧如果拿到的是 `ApiKeyToken`，应先调用后端 `/task/get-api-key` 获取/解密 Strategy API Key 与 Secret，再创建 `User(api_key, api_secret, ...)`。

## 2. 快速启动

当前包信息：

| 项 | 当前值 |
| --- | --- |
| PyPI 包名 | `qe-connector` |
| Python 版本 | `>=3.8` |
| SDK 版本 | `qe/__version__.py` 中 `__version__ = "1.3.1"` |
| 测试矩阵 | `tox.ini` 中 `py38,py39,310,311` |

安装开发依赖后运行：

```bash
python -m pytest
```

聚焦 V2 签名、分页和 WebSocket：

```bash
python -m pytest tests/test_v2_json_signing.py tests/test_v2_pagination.py tests/test_ws_v2.py
```

如需跑 Python 版本矩阵：

```bash
tox
```

基础使用：

```python
from qe.user import User
from qe.lib.trading_enums import Exchange, MarketType, OrderSide, Algorithm

client = User(api_key, api_secret)

reply = client.create_master_order_v2(
    apiKeyId="exchange-api-binding-id",
    exchange=Exchange.BINANCE,
    marketType=MarketType.PERP,
    symbol="BTCUSDT",
    side=OrderSide.BUY,
    algorithm=Algorithm.TWAP,
    executionDurationSeconds=3600,
    totalQuantity="0.1",
    worstPrice="90000",
)
```

如果需要走带前缀的网关：

```python
client = User(api_key, api_secret, base_url="https://api.quantumexecute.com/strategy-api")
```

当前 `User` 默认 `base_url` 是 `https://api.quantumexecute.com`。是否需要 `/strategy-api` 取决于部署层转发规则。

## 3. 目录结构

| 路径 | 说明 |
| --- | --- |
| `setup.py` | 包元数据、依赖、Python 版本要求 |
| `qe/__version__.py` | SDK 版本号 |
| `qe/api.py` | Base API、签名、Session、响应解析 |
| `qe/user/__init__.py` | `User` 类，把 V1/V2 方法注入为实例方法 |
| `qe/user/trading.py` | V1 母单、子单、TCA、listenKey |
| `qe/user/trading_v2.py` | V2 母单、子单、TCA、动作接口、listenKey |
| `qe/user/exchange_v2.py` | V2 交易所 API Key 列表 |
| `qe/user/exchange_balance.py` | 交易所余额、账户、持仓代理接口 |
| `qe/pub/trading.py` | V1/V2 公共交易对 |
| `qe/lib/trading_enums.py` | 交易、市场、交易所枚举 |
| `qe/lib/trading_v2_types.py` | V2 dataclass、状态枚举、字段转换 |
| `qe/ws/client.py` | WebSocket 客户端、重连、消息分发 |
| `qe/ws/types.py` | WebSocket 消息类型和 handler dataclass |
| `tests/` | Bitget、枚举、V2 签名、分页、WS 测试 |
| `examples/` | 用户接口、公共接口、WS 示例 |
| `Makefile` | `make build`、`make upload` |
| `tox.ini` | 多 Python 版本测试配置 |

仓库中已有 `build/`、`dist/`、`qe_connector.egg-info/` 等历史产物。日常改 SDK 源码和文档时不要顺手重建或删除这些产物；只有正式发版时再按发布流程处理。

## 4. API 基类、签名与响应解析

`API.__init__` 会创建 `requests.Session`，并设置：

- `Content-Type: application/json;charset=utf-8`
- `User-Agent: qe-connector-python/{__version__}`
- `X-MBX-APIKEY: {api_key}`
- HTTP/HTTPS adapter：`pool_connections=32`、`pool_maxsize=32`

普通签名请求走 `sign_request`：

1. payload 中加入 `timestamp=get_timestamp()`。
2. 用 `_prepare_params` 编码 query string。
3. HMAC-SHA256 生成 `signature`。
4. 通过 `send_request` 发送，payload 放 `params=`。

带业务 JSON body 的 V2 写接口走 `sign_json_request`；没有业务 body 的接口，例如 `create_listen_key_v2()`，当前仍走普通 `sign_request`。

1. 清理 body/query 中值为 `None` 的字段。
2. query 中加入 `timestamp`。
3. 签名参数为 query 字段 + JSON body 顶层字段。
4. 标量按后端规则转字符串，数组/对象用紧凑 JSON 字符串。
5. 实际请求只把 `timestamp`、`recvWindow`、`signature` 放 query，业务字段放 JSON body。

响应解析在 `_parse_response`：

- HTTP status `>= 400` 先进入 `_handle_exception`。
- 响应 JSON 中如果有 `code` 且 `code != 200`，抛 `APIError`。
- `code == 200` 时返回 `message` 字段。
- 没有 `code` wrapper 的响应保持原样返回。

签名算法：

- 默认使用 HMAC-SHA256。
- `private_key` 存在时会尝试 Ed25519 / RSA 签名，这属于历史 Binance 风格能力；当前 QE Strategy API 主线使用 HMAC。

## 5. User 与 Strategy API V2

`User` 默认 `base_url="https://api.quantumexecute.com"`。V1 方法保持原名，V2 方法统一以 `_v2` 结尾。

当前 V2 方法：

| 方法 | Method / Path |
| --- | --- |
| `list_exchange_apis_v2()` | `GET /user/exchange/v2/exchange-apis` |
| `create_master_order_v2()` | `POST /user/trading/v2/master-orders` |
| `list_master_orders_v2()` | `GET /user/trading/v2/master-orders` |
| `get_master_order_v2(masterOrderId)` | `GET /user/trading/v2/master-orders/{masterOrderId}` |
| `get_master_order_by_client_order_id_v2(clientOrderId)` | `GET /user/trading/v2/master-orders/by-client-order-id/{clientOrderId}` |
| `list_order_fills_v2()` | `GET /user/trading/v2/order-fills` |
| `get_tca_analysis_v2()` | `GET /user/trading/v2/tca-analysis` |
| `create_listen_key_v2()` | `POST /user/trading/v2/listen-key` |
| `cancel_master_order_v2()` | `PUT /user/trading/v2/master-orders/{masterOrderId}/cancel` |
| `pause_master_order_v2()` | `PUT /user/trading/v2/master-orders/{masterOrderId}/pause` |
| `resume_master_order_v2()` | `PUT /user/trading/v2/master-orders/{masterOrderId}/resume` |
| `update_master_order_v2()` | `PUT /user/trading/v2/master-orders/{masterOrderId}/update` |
| `batch_cancel_master_orders_v2()` | `PUT /user/trading/v2/master-orders/batch-cancel` |

`create_master_order_v2` 支持两种调用方式：

- 传 `CreateMasterOrderV2Request` dataclass。
- 直接传 kwargs。

核心校验：

- 必填：`apiKeyId`、`exchange`、`marketType`、`symbol`、`side`、`algorithm`、`executionDurationSeconds`。
- `executionDurationSeconds` 必须大于 10。
- `totalQuantity` 与 `orderNotional` 必须二选一。
- `isTargetPosition=True` 时必须传 `totalQuantity`，且禁止 `orderNotional`。
- `startTimeMs` 必须是 epoch milliseconds。
- V2 不支持 `limitPrice` / `limitPriceString`，应使用 `worstPrice`。
- `povLimit` 默认值由当前代码决定：`POV -> "0.05"`，其它算法 -> `"1"`。
- `povLimit` 必须在 `[0, 1]`。

V2 查询注意：

- 分页参数既接受 `pageSize`，也接受 Python 风格 `page_size`，最终会转成 `pageSize`。
- `pageSize` 最大 100。
- `apiKeyUuid` 作为兼容 alias，会转成 `apiKeyId`。
- 母单列表状态过滤建议只传 `MasterOrderStatusV2.NEW` 或 `MasterOrderStatusV2.COMPLETED` 两个聚合值。

## 6. V2 类型层

V2 dataclass 在 `qe/lib/trading_v2_types.py`。它们故意使用 lowerCamelCase 属性名，因为这和后端 JSON 字段一一对应；Python 方法名本身仍保持 snake_case。

常用类型：

| 类型 | 说明 |
| --- | --- |
| `CreateMasterOrderV2Request` | 创建母单请求体 |
| `UpdateMasterOrderV2Request` | 修改母单请求体 |
| `CreateMasterOrderV2Reply` | 创建母单响应 |
| `MasterOrderV2Info` | 母单列表/详情记录 |
| `OrderFillV2Info` | 子单/成交记录 |
| `ExchangeApiV2Info` | 交易所 API Key 绑定记录 |
| `MasterOrderActionV2Reply` | 取消/暂停/恢复/修改动作响应 |
| `BatchCancelV2Reply`、`BatchCancelV2FailedItem` | 批量取消响应 |
| `MasterOrderStatusV2` | V2 母单状态全集 |

字段转换规则：

- Decimal 类字段接受 `str | int | float | Decimal`，序列化时统一转为非科学计数法字符串。
- `to_payload()` 会丢弃值为 `None` 的字段。
- `from_dict()` 方法用于把后端 dict 转成 dataclass。
- `ExchangeApiV2Info.from_dict()` 会把 `apiKeyId`、`apiKeyUuid`、`id` 互相回填，照顾旧调用方。
- `OrderFillV2Info.from_dict()` 会兼容后端把 Decimal 字段返回成 number 或 string。

新增字段时优先扩展 dataclass 和 `from_dict()`，不要只改 README 示例。

## 7. 公共数据与已接入交易所

公共交易对入口在 `qe/pub/trading.py`：

| 方法 | Path | 说明 |
| --- | --- | --- |
| `Pub.trading_pairs()` | `GET /pub/trading-pairs` | V1 公共交易对，保留兼容 |
| `Pub.trading_pairs_v2()` | `GET /pub/v2/trading-pairs` | V2 公共交易对，支持 `exchange`、`marketType`、`isCoin` |

交易所枚举在 `qe/lib/trading_enums.py`：

| 交易所 | 枚举 | 当前 SDK 覆盖 |
| --- | --- | --- |
| Binance | `Exchange.BINANCE` | V1/V2 母单、公共交易对、spot/futures/PAPI/PV1/UM/CM/DAPI/cross margin 余额与账户、position side |
| OKX | `Exchange.OKX` | V1/V2 母单、公共交易对、账户余额、持仓、最大可下单量 |
| LTP | `Exchange.LTP` | V1/V2 母单、公共交易对、账户、组合资产、持仓 |
| Deribit | `Exchange.DERIBIT` | V1/V2 母单、公共交易对、账户、持仓 |
| Hyperliquid | `Exchange.HYPERLIQUID` | V1/V2 母单、公共交易对、spot balance、perp positions |
| Bybit | `Exchange.BYBIT` | V2 交易所校验、母单、公共交易对；目标仓位模式遵循 V2 数量规则 |
| Bitget | `Exchange.BITGET` | V1/V2 母单、公共交易对；币本位 symbol 形如 `BTCUSD_CM` |

余额/账户/持仓接口在 `qe/user/exchange_balance.py`，本质是平台后端代理交易所请求，SDK 只对 QE 平台签名。

| 分类 | 方法 |
| --- | --- |
| Binance 余额 | `get_account_balance`、`get_margin_balance`、`get_pv1_balance` |
| Binance 账户 | `get_um_account`、`get_cm_account`、`get_pv1_account`、`get_dapi_account`、`get_fapi_account`、`get_cross_margin_account_detail` |
| Binance 持仓设置 | `get_fapi_position_side_dial`、`get_papi_um_position_side_dual` |
| OKX | `get_okx_account_balance`、`get_okx_account_positions`、`get_okx_account_max_size` |
| LTP | `get_ltp_account`、`get_ltp_portfolio_asset`、`get_ltp_position` |
| Deribit | `get_deribit_account`、`get_deribit_position` |
| Hyperliquid | `get_hyperliquid_spot_balance`、`get_hyperliquid_positions` |

新增交易所时：

1. 在 `Exchange` 枚举和 V2 `_EXCHANGES` 白名单中增加值。
2. 如果影响创建母单，补充 `validate_exchange`、特殊数量/notional 规则和测试。
3. 如果有公共交易对，确认 `_normalize_trading_pair_filters` 能正确序列化。
4. 如果有余额/账户/持仓代理接口，在 `exchange_balance.py` 增加方法。
5. 同步 Go SDK、QE-API-Key 文档站和 README 示例。

## 8. WebSocket

Python WebSocket 入口在 `qe/ws/client.py`：

```python
from qe.ws.client import WebSocketService
from qe.ws.types import WebSocketEventHandlers

ws = WebSocketService(client, base_url="wss://www.quantumexecute.com", version="v2")
ws.set_handlers(WebSocketEventHandlers(
    on_connected=lambda: None,
    on_master_order=lambda order: None,
    on_order=lambda order: None,
))
ws.connect(listen_key)
```

默认行为：

- `base_url` 默认是 `wss://test.quantumexecute.com`，这点和 HTTP `User` 默认生产域名不同。
- `version="v2"` 时路径是 `/api/ws/v2?listen_key=...`。
- 非 V2 版本路径是 `/api/ws?listen_key=...`。
- 使用 `websockets`，在后台线程中运行 asyncio event loop。
- 重连延迟 `5s`，ping interval `1s`，pong timeout `10s`。

消息分发：

- envelope 先解析为 `ClientPushMessage`。
- `status` 走 `on_status`。
- `error` 走 `on_error`。
- `master_data` 会解析成母单消息并走 `on_master_order`。
- `order_data` 会解析成子单/成交消息并走 `on_order`。
- `data` 既兼容 JSON string，也兼容 dict。

转发注意：

- 浏览器或平台前端通常通过 `/api/ws/v2` 转发；SDK 直接连接时传 `wss://...` host。
- listenKey 来自 `create_listen_key_v2()` 或历史 `create_listen_key()`。
- 如果本地联调走 Nginx/gin，确认转发保留 `Upgrade`、`Connection`、query string 和超时时间。

## 9. 测试与质量门槛

文档或小范围 SDK 改动至少跑：

```bash
python -m pytest
git diff --check
```

针对性测试：

| 场景 | 建议命令 |
| --- | --- |
| V2 JSON body 签名 | `python -m pytest tests/test_v2_json_signing.py` |
| V2 pageSize、alias | `python -m pytest tests/test_v2_pagination.py` |
| WebSocket V2 | `python -m pytest tests/test_ws_v2.py` |
| 交易所枚举 | `python -m pytest tests/test_exchange_enums.py` |
| Bitget | `python -m pytest tests/test_bitget_support.py` |

新增测试建议：

- 使用 monkeypatch/mock 拦截 `requests.Session`，断言 URL query、JSON body、header 和签名。
- 不依赖真实网络、真实 API Key 或真实 listenKey。
- Go/Python 对同一 endpoint 的测试口径尽量保持一致。

## 10. 新增接口维护 Runbook

新增 GET endpoint：

1. 在对应 `qe/user/*.py` 或 `qe/pub/*.py` 中增加函数。
2. 对 signed 接口调用 `self.sign_request(method, path, payload)`。
3. 在 `qe/user/__init__.py` 或 `qe/pub/__init__.py` 把函数导入到类中。
4. 若有类型需求，在 `qe/lib/*_types.py` 增加 dataclass 和 `from_dict()`。
5. 补测试覆盖 query 参数、签名、Kratos wrapper 拆包和错误响应。

新增带 JSON body 的 V2 POST/PUT endpoint：

1. 业务字段放 JSON body，认证字段放 query，调用 `self.sign_json_request(...)`。
2. `recvWindow` 通过 `_split_v2_body_query` 从 body 拆到 query。
3. body 字段保持 lowerCamelCase。
4. Decimal 字段通过 `to_decimal_str()` 或 dataclass `to_payload()` 转为 string。
5. 数组/对象字段必须测试紧凑 JSON 签名。
6. 同步 Go SDK、QE-API-Key 文档站和后端契约文档。

新增字段：

- 入参字段要同时支持 kwargs 与 dataclass。
- 回包字段要更新 dataclass、`from_dict()` 和 README/文档站示例。
- 如果是替代旧字段，旧字段先保留 alias 或明确抛出友好错误，不要静默忽略。

## 11. 构建与发布

当前 `Makefile`：

```bash
make build
make upload
```

等价于：

```bash
python setup.py sdist bdist_wheel
twine upload dist/* --verbose
```

推荐发版流程：

1. 更新 `qe/__version__.py`。
2. 更新 `CHANGELOG.md`，把 `Unreleased` 内容归档到新版本。
3. 同步 README、examples 和 QE-API-Key 文档站示例。
4. 跑 `python -m pytest`，必要时跑 `tox`。
5. 正式构建前清理旧产物，避免把历史版本一起上传。
6. 执行 `make build`。
7. 上传前检查 `dist/` 中只包含本次版本。
8. 执行 `make upload` 或 CI 发布。

注意：本仓库当前已经存在历史 `dist` 文件。只有在明确进入发版流程时才清理或重建，普通交接文档/代码小改不要动产物。

## 12. 常见风险点

- HTTP 默认生产域名，WebSocket 默认测试域名；联调时很容易混用。
- baseURL 与 `/strategy-api` 前缀重复或缺失，会导致 404 或签名验证失败。
- `apiKeyId` 和 Strategy API Key 容易混淆；下单 body 里传的是交易所绑定 ID。
- V2 写接口不要走 `sign_request`，否则业务字段会进 query，而不是 JSON body。
- Decimal 字段不要用 Python float 作为示例首选，文档示例优先写字符串。
- `pageSize > 100` 会在 SDK 侧被拒绝。
- 列表 status 过滤只推荐 `NEW` / `COMPLETED` 聚合值；细分状态主要用于详情和 WS 推送。
- 修改 Python SDK 时要同步 Go SDK，因为外部文档站通常同时展示两种语言示例。
