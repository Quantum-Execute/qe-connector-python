# 更新日志（Changelog）

本文件记录 `qe-connector`（Python SDK）的用户可见变更。

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


