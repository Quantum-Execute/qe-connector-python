# 更新日志（Changelog）

本文件记录 `qe-connector`（Python SDK）的用户可见变更。

## Unreleased

## 1.0.18 - 2025-12-15

### 新增
- **Deribit 支持**：`Exchange` 枚举新增 `DERIBIT = "Deribit"`。

### 变更
- **Deribit(BTCUSD/ETHUSD) 下单限制**：当 `exchange=Deribit` 且 `symbol` 为 `BTCUSD` 或 `ETHUSD` 时：
  - 仅允许使用 `totalQuantity`（单位：USD）
  - 禁止使用 `orderNotional`

### 文档
- README：`exchange` 可选值补充 `Deribit`，并补充 Deribit BTCUSD/ETHUSD 的数量字段说明。


