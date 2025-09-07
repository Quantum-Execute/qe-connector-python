# WebSocket推送消息处理功能

本目录包含了QE Connector Python SDK的WebSocket功能使用示例。

## 功能特性

- ✅ 自动重连机制
- ✅ 心跳检测
- ✅ 消息类型自动分发
- ✅ 事件回调处理
- ✅ 错误处理
- ✅ 线程安全

## 支持的消息类型

### 客户端消息类型
- `data`: 数据消息
- `status`: 状态消息
- `error`: 错误消息
- `master_data`: 主订单数据
- `order_data`: 订单数据

### 第三方消息类型
- `master_order`: 主订单消息
- `order`: 订单消息
- `fill`: 成交消息

## 快速开始

### 1. 基本使用

```python
from qe import API, WebSocketService, WebSocketEventHandlers

# 创建API客户端
api = API(
    api_key="your_api_key",
    api_secret="your_api_secret",
    base_url="https://test.quantumexecute.com"
)

# 创建事件处理器
def on_connected():
    print("WebSocket连接成功")

def on_master_order(message):
    print(f"收到主订单: {message.master_order_id}")

handlers = WebSocketEventHandlers(
    on_connected=on_connected,
    on_master_order=on_master_order
)

# 创建WebSocket服务
ws_service = WebSocketService(api)
ws_service.set_handlers(handlers)

# 连接WebSocket
ws_service.connect("your_listen_key")
```

### 2. 高级使用

```python
from qe import API, WebSocketService, WebSocketEventHandlers, MasterOrderMessage, OrderMessage, FillMessage

class TradingDataProcessor:
    def __init__(self):
        self.orders = {}
        self.fills = []
    
    def process_master_order(self, message: MasterOrderMessage):
        self.orders[message.master_order_id] = message
        print(f"主订单状态: {message.status}")
    
    def process_order(self, message: OrderMessage):
        print(f"订单状态: {message.status}")
    
    def process_fill(self, message: FillMessage):
        self.fills.append(message)
        print(f"成交: {message.symbol} {message.filled_qty}@{message.fill_price}")

# 创建处理器
processor = TradingDataProcessor()

# 设置事件处理器
handlers = WebSocketEventHandlers(
    on_master_order=processor.process_master_order,
    on_order=processor.process_order,
    on_fill=processor.process_fill
)

# 创建WebSocket服务
ws_service = WebSocketService(api)
ws_service.set_handlers(handlers)

# 设置连接参数
ws_service.set_reconnect_delay(5.0)  # 重连延迟5秒
ws_service.set_ping_interval(30.0)   # 心跳间隔30秒
ws_service.set_pong_timeout(10.0)    # Pong超时10秒

# 连接WebSocket
ws_service.connect("your_listen_key")
```

## 事件处理器

### WebSocketEventHandlers

所有的事件处理器都是可选的，你可以只实现需要的事件处理器：

```python
handlers = WebSocketEventHandlers(
    on_connected=None,           # 连接成功回调
    on_disconnected=None,        # 断开连接回调
    on_error=None,              # 错误回调
    on_status=None,             # 状态消息回调
    on_master_order=None,       # 主订单消息回调
    on_order=None,              # 订单消息回调
    on_fill=None,               # 成交消息回调
    on_raw_message=None         # 原始消息回调
)
```

### 消息类型

#### MasterOrderMessage (主订单消息)
```python
@dataclass
class MasterOrderMessage:
    type: str
    master_order_id: str
    client_id: str
    strategy: str
    symbol: str
    side: str
    qty: float
    duration_secs: float
    category: str
    action: str
    reduce_only: bool
    status: str
    date: float
    ticktime_int: int
    ticktime_ms: int
    reason: str
    timestamp: int
```

#### OrderMessage (订单消息)
```python
@dataclass
class OrderMessage:
    type: str
    master_order_id: str
    order_id: str
    symbol: str
    category: str
    side: str
    price: float
    quantity: float
    status: str
    created_time: int
    fill_qty: float
    fill_price: float
    cum_filled_qty: float
    quantity_remaining: float
    ack_time: int
    last_fill_time: int
    cancel_time: int
    price_type: str
    reason: str
    timestamp: int
```

#### FillMessage (成交消息)
```python
@dataclass
class FillMessage:
    type: str
    master_order_id: str
    order_id: str
    symbol: str
    category: str
    side: str
    fill_price: float
    filled_qty: float
    fill_time: int
    timestamp: int
```

## 配置选项

### 连接参数
- `set_reconnect_delay(delay)`: 设置重连延迟（秒）
- `set_ping_interval(interval)`: 设置心跳间隔（秒）
- `set_pong_timeout(timeout)`: 设置Pong超时时间（秒）

### 日志配置
```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.INFO)

# 为WebSocket设置专门的日志记录器
ws_service.set_logger(logging.getLogger("websocket"))
```

## 错误处理

WebSocket客户端会自动处理以下错误：
- 连接断开自动重连
- 网络错误重试
- 消息解析错误
- 心跳超时处理

所有错误都会通过 `on_error` 回调函数通知用户。

## 示例文件

- `websocket_example.py`: 基本使用示例
- `advanced_websocket_example.py`: 高级使用示例，包含数据处理器和统计功能

## 注意事项

1. 确保在连接WebSocket之前已经获取了有效的 `listen_key`
2. 在生产环境中建议设置适当的日志级别
3. 根据网络环境调整重连和心跳参数
4. 在程序退出时记得调用 `close()` 方法关闭连接
