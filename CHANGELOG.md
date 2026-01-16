# 更新日志（Changelog）

本文件记录 `qe-connector`（Python SDK）的用户可见变更。

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


