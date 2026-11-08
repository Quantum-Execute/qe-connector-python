# Deribit 期权接入（V2）

期权使用现有 V2 接口，支持已发布 CSV 内的 **USDC 线性期权**和 **BTC/ETH 币本位期权**。本指南对应包含期权支持的 SDK 源码；旧版 1.3.3 尚无完整支持，安装旧发行版不能直接运行以下新增用法。

- 创建母单：`POST /user/trading/v2/master-orders`，`exchange=Deribit`、`marketType=OPTION`。
- `symbol` 必须是发布列表中的完整合约名，不能使用标的 pair。`SOL_USDC-25DEC26-100-C` 仅说明格式，不保证当前可交易。
- 后端将算法类别设为 `option`。调用方不提交 `Category` 或 `optionMetadata`。
- 默认 API 地址为 `https://api.quantumexecute.com`。若自行部署的网关需要 `/strategy-api` 前缀，将其放入 base URL；不要重复拼接。
- SDK 使用平台 Strategy API Key/Secret 签名；请求的 `apiKeyId` 是绑定的 Deribit 交易账户 ID，不是 Strategy API Key，也不是交易所密钥文本。

## 1. 查询合约与完整规则

先查询 `GET /pub/v2/trading-pairs?exchange=Deribit&marketType=OPTION`；选定后增加完整 `symbol` 再查一次。SDK 负责 URL 编码。

列表可能包含 `status=EXPIRED` 的过期项，且 `rulesReady` 可能为 false/省略。**带 symbol 查询当前有效合约后，确认 `rulesReady=true`，再使用价格规则。** `tickSizeSteps` 未返回不等于没有分段步长。未发布的交易所合约不能绕过 CSV 范围下单。

| 字段 | 含义 |
| --- | --- |
| `baseAsset` / `quoteAsset` | 标的币 / 权利金计价币 |
| `contractType` | `linear`（USDC）或 `reversed`（BTC/ETH） |
| `optionType` / `strike` | `call` 或 `put` / 行权价；与 buy/sell 无关 |
| `expirationTimestamp` | UTC epoch 毫秒；显示时转换时区，不硬编码某个整点 |
| `contractSize` | 每张对应的标的币数量 |
| `minOrderQty` / `stepSize` | 标的币单位的最小下单量 / 数量步长 |
| `tickSize` / `tickSizeSteps` | 基础权利金步长 / 分段价格步长 |
| `underlyingIndex` | 标的指数名称，不是实时指数价 |

分段规则采用**最高已达到的门槛**：当价格 `>= abovePrice` 时使用对应 `tickSize`；未达到任何门槛时使用基础 `tickSize`。验证限价是最终有效步长的整数倍，使用十进制运算，不用二进制浮点取模。

`isCoin` 用于永续合约筛选，不用于选择期权结算币种。

## 2. 数量与权利金

| 类型 | `totalQuantity` | `worstPrice`、成交价和累计权利金币种 |
| --- | --- | --- |
| USDC 期权 | 标的币，如 SOL / AVAX | USDC |
| BTC 币本位期权 | BTC | BTC |
| ETH 币本位期权 | ETH | ETH |

- **张数 × contractSize = totalQuantity**，调用 SDK 前只换算一次。若乘数是 10，1 张传 `"10"`，不是 `"1"`；SDK 不再乘乘数。BTC/ETH 乘数为 1 也可按合约规则使用小数数量。
- 普通模式数量必须正数且满足最小量和步长；目标模式可为零，仍需满足步长，实际差额也由后端校验。
- `worstPrice` 是**必填的正数权利金限价**：实际买入的最高价格 / 实际卖出的最低价格。不可留空或传 0、-1 表示不限价。按合约有效价格步长校验。
- API/SDK 不会自动查询买一卖一或预填限价。调用方选择价格；行情不可用时仍可提交手填有效限价，服务端会检查合约规则。
- 不传 `orderNotional`（包括 0），不使用 `isMargin=true`。普通数量模式支持 `reduceOnly`。
- 数量和价格使用十进制字符串；限价/数量最多 20 位整数、10 位小数，不用科学记数法。服务端验证动态规则，SDK 的静态校验不替代服务端。
- 权利金估算为标的币数量 × 权利金单价；名义价值估算为标的币数量 × 指数价。不能把 BTC/ETH 权利金直接标成 USD；估算不等于保证金，也不含手续费。

## 3. 默认值、触发与到期

- 支持 TWAP、VWAP、POV。
- OPTION 的 `executionDurationSeconds` 省略或传 0 时默认 **1800 秒**；显式时长必须 >10 秒。SPOT/PERP 的原有时长要求不变。
- `mustComplete`、`tailOrderProtection` 的期权服务端默认值均为 false；建议显式传 false。
- `triggerPrice` / `triggerPrice1` 使用期权权利金口径，不是标的指数。留空或 0 禁用对应项；任一启用时 `maxTriggerWaitSecs` 必须为有限正数。
- 触发价兼容首尾空白、小数及科学计数法；展开后按非负 `DECIMAL(30,10)` 校验，最多 20 位整数和 10 位有效小数。不接受下划线、分数、负数（含 `-0`）、NaN 或 Infinity；`worstPrice` 仍须为正数普通十进制，兼容首尾空白。
- `maxTriggerWaitTimeoutAction` 沿用 0～10 的整数，0=超时终止；其余编号使用前确认算法版本支持。
- 创建时必须满足：

```text
max(服务端当前时间, startTimeMs)
  + (有效触发等待秒数 + executionDurationSeconds) × 1000
  <= expirationTimestamp - 60000
```

未启用触发价时等待计为零。超出边界拒绝提交，不会自动缩短执行时长。

## 4. 目标仓位

1. 用现有 Deribit 持仓接口读取绑定账户：`GET /user/exchange-apis/deribit-position?bindingId=…`。`bindingId` 与下单 `apiKeyId` 对应同一账户。
2. 按完整 `instrumentName`、`kind=option` 匹配。用 `size`（标的币数量），`direction=buy` 为正、sell 为负；不要套用永续的 `sizeCurrency`。仅完整成功响应缺少对应持仓时按零；读取失败不可按零。
3. 计算 `差额=有符号目标-有符号当前持仓`。请求 `side` 表示目标方向，`totalQuantity` 为目标绝对量，`isTargetPosition=true`；额外传 `expectedExecutionSide` 表示差额的实际 buy/sell。限价按实际执行方向选取。

例如当前 +20 SOL，目标 +10 SOL：

```json
{
  "apiKeyId": "YOUR_EXCHANGE_API_KEY_ID",
  "exchange": "Deribit",
  "marketType": "OPTION",
  "symbol": "YOUR_PUBLISHED_OPTION_SYMBOL",
  "side": "buy",
  "totalQuantity": "10",
  "isTargetPosition": true,
  "expectedExecutionSide": "sell",
  "worstPrice": "0.125",
  "algorithm": "TWAP",
  "executionDurationSeconds": 1800,
  "mustComplete": false,
  "tailOrderProtection": false
}
```

以上为示意值。目标量 `"0"` 可用于平仓，但仍需预览实际方向。提交时后端重查持仓：差额数量变化但方向不变时继续；方向反转返回 `code=409 / reason=OPTION_DIRECTION_CHANGED`，此次不创建母单。刷新持仓、重算差额及限价并重新确认后才能重提，**不要自动盲重试**。

已达到目标返回 `OPTION_INVALID`，不会创建零数量单。后端将目标模式 `reduceOnly` 置为 false。目标只在提交时计算一次，执行期间不持续追踪目标；响应数量、方向是实际委托量和方向。

## 5. 查询、改单与 WebSocket

期权复用现有 V2 母单列表、详情、子单列表及撤单/暂停/恢复/改单接口。订单 `category=option`。按完整 `symbol` 或 `masterOrderId` 查询，不能把标的 pair 当作期权合约。

- 母单和子单 REST 响应可包含 `optionMetadata`；子单复用母单静态资料。
- 六个字段：`optionType`、`strike`、`expirationTimestamp`、`contractSize`、`contractType`、`underlyingIndex`。该对象由后端验证保存，不接受客户端提交，不包含 IV、Delta、行情或目标仓位快照。
- 沿用 listenKey / V2 WebSocket，SDK 解析可选 metadata。不是每种推送都保证携带它；缺失时用母单 ID 补查 REST 详情。非期权或旧记录缺失时为 nil/None。
- 改限价仍必须为有效正数权利金并符合步长；不能改成按名义金额下单。改数量需满足最小量/步长且不小于已成交量。
- 改执行时长会重新验证到期边界；已到期或距到期不足一分钟不能修改/恢复。改单作用于已生成的委托，不重新设置目标仓位。
- 通常 `code=400 / reason=OPTION_INVALID` 表示合约、规则、数量、限价、到期或持仓读取等校验失败，具体看 message。HTTP 200 不等于业务成功；SDK 会抛出/返回 API 错误，保留 reason。

## 6. Python 用法

```python
from qe.pub import Pub
from qe.lib.trading_enums import Exchange, MarketType

public = Pub()
try:
    pairs = public.trading_pairs_v2(exchange=Exchange.DERIBIT, marketType=MarketType.OPTION)
    # 从 pairs["items"] 中选取有效 symbol 后，再查询完整规则。
    rules = public.trading_pairs_v2(
        exchange=Exchange.DERIBIT, marketType=MarketType.OPTION, symbol=symbol,
    )
finally:
    public.session.close()
```

目标模式向 `CreateMasterOrderV2Request` 或 `User.create_master_order_v2()` 传入 `isTargetPosition=True, expectedExecutionSide="sell"`；方向来自实际差额预览。持仓入口为 `client.get_deribit_position(binding_id)`。

公开交易对返回原始 dict，包含所有期权规则。`MasterOrderV2Info.from_dict()`、`OrderFillV2Info.from_dict()` 将 `optionMetadata` 转成 `OptionMetadata`，`expirationTimestamp` 转成 Python int。REST 类型通过 `from qe import OptionMetadata` 或 `from qe.lib import OptionMetadata` 导入；WS `MasterOrderMessage` / `OrderMessage` 的对应字段名为 `option_metadata`。

完整可运行程序见 [examples/user/v2/options_v2.py](../examples/user/v2/options_v2.py)。在仓库根目录、虚拟环境中运行：

```bash
python -m pip install -e .
python examples/user/v2/options_v2.py --symbol 'YOUR_PUBLISHED_OPTION_SYMBOL' \
  --quantity '10' --premium-limit '0.125'
```

默认只读查询规则并打印请求预览。需要提交真实订单时先设置 `QE_API_KEY`、`QE_API_SECRET`、`QE_EXCHANGE_API_KEY_ID`，再显式添加 `--submit`；价格与数量必须自行按所选合约调整。可通过 `QE_BASE_URL` 指定环境。

## 7. 验证与发布

离线回归：`python -m pytest tests`。期权测试 mock HTTP 请求，覆盖签名、USDC/BTC/ETH 数量和币种、静态校验、目标方向冲突、REST / WS metadata；不会创建真实订单。

本次源码更新不等于 PyPI 已发布。当前可使用上面的 editable install 验证；下游需安装包含这些修改的后续发行版。
