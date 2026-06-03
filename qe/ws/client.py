"""
WebSocket客户端实现
"""
import asyncio
import json
import logging
import threading
import time
from concurrent.futures import TimeoutError
from typing import Optional, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from .types import (
    WebSocketEventHandlers,
    ClientPushMessage,
    MasterOrderMessage,
    OrderMessage,
    FillMessage,
    BaseThirdPartyMessage,
    ClientMessageType,
    ThirdPartyMessageType
)
from ..error import WebsocketClientError


class WebSocketService:
    """WebSocket服务"""
    
    def __init__(self, client, base_url: str = "wss://test.quantumexecute.com", version: str = "v2"):
        self.client = client
        self.base_url = base_url
        self.version = version
        self.listen_key: Optional[str] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.handlers = WebSocketEventHandlers()
        self._is_connected = False
        self._lock = threading.RLock()
        self._reconnect_delay = 5.0
        self._ping_interval = 1.0
        self._pong_timeout = 10.0
        self._stop_event = threading.Event()
        self._threads = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._logger = logging.getLogger(__name__)
    
    def set_handlers(self, handlers: WebSocketEventHandlers) -> 'WebSocketService':
        """设置事件处理器"""
        self.handlers = handlers
        return self
    
    def connect(self, listen_key: str) -> None:
        """连接WebSocket"""
        with self._lock:
            self.listen_key = listen_key
            self._stop_event.clear()
        
        # 在单独线程中运行异步连接
        thread = threading.Thread(target=self._run_async_connect, daemon=True)
        thread.start()
        self._threads.append(thread)
    
    def _run_async_connect(self):
        """运行异步连接"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with self._lock:
            self._loop = loop
        try:
            loop.run_until_complete(self._async_connect())
        finally:
            with self._lock:
                if self._loop is loop:
                    self._loop = None
            loop.close()
    
    async def _async_connect(self):
        """异步连接WebSocket"""
        with self._lock:
            if self._is_connected:
                return
        
        ws_url = self._get_websocket_url()
        self._logger.debug(f"Connecting to WebSocket: {ws_url}")
        
        try:
            async with websockets.connect(
                ws_url,
                ping_interval=self._ping_interval,
                ping_timeout=self._pong_timeout,
                close_timeout=10
            ) as websocket:
                self.websocket = websocket
                with self._lock:
                    self._is_connected = True
                
                # 调用连接成功回调
                if self.handlers.on_connected:
                    try:
                        self.handlers.on_connected()
                    except Exception as e:
                        self._logger.error(f"OnConnected handler error: {e}")
                
                # 启动消息读取任务
                await self._read_messages()
                
        except Exception as e:
            self._logger.error(f"WebSocket connection error: {e}")
            if self.handlers.on_error:
                try:
                    self.handlers.on_error(WebsocketClientError(f"Connection failed: {e}"))
                except Exception as handler_error:
                    self._logger.error(f"Error handler error: {handler_error}")
            
            # 尝试重连
            if not self._stop_event.is_set():
                await self._reconnect()
    
    def _get_websocket_url(self) -> str:
        """获取WebSocket URL"""
        path = "/api/ws/v2" if self.version == "v2" else "/api/ws"
        return f"{self.base_url}{path}?listen_key={self.listen_key}"
    
    async def _read_messages(self):
        """读取消息"""
        try:
            async for message in self.websocket:
                if self._stop_event.is_set():
                    break
                
                self._logger.debug(f"Received message: {message}")
                
                # 处理pong消息
                if message == "pong":
                    continue
                
                # 处理消息
                await self._handle_message(message)
                
        except ConnectionClosed:
            self._logger.info("WebSocket connection closed")
        except WebSocketException as e:
            self._logger.error(f"WebSocket error: {e}")
        except Exception as e:
            self._logger.error(f"Unexpected error in read_messages: {e}")
        finally:
            self._handle_disconnect()
    
    async def _handle_message(self, message: str):
        """处理消息"""
        try:
            # 解析客户端推送消息
            data = json.loads(message)
            client_msg = ClientPushMessage(
                type=data.get("type", ""),
                messageId=data.get("messageId", ""),
                userId=data.get("userId", ""),
                data=data.get("data", "")
            )
            
            # 调用原始消息处理器
            if self.handlers.on_raw_message:
                try:
                    self.handlers.on_raw_message(client_msg)
                except Exception as e:
                    self._logger.error(f"Raw message handler error: {e}")
            
            # 根据消息类型处理
            await self._dispatch_message(client_msg)
            
        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse message as JSON: {e}")
            if self.handlers.on_error:
                try:
                    self.handlers.on_error(WebsocketClientError(f"JSON decode error: {e}"))
                except Exception as handler_error:
                    self._logger.error(f"Error handler error: {handler_error}")
        except Exception as e:
            self._logger.error(f"Error handling message: {e}")
            if self.handlers.on_error:
                try:
                    self.handlers.on_error(e)
                except Exception as handler_error:
                    self._logger.error(f"Error handler error: {handler_error}")
    
    async def _dispatch_message(self, client_msg: ClientPushMessage):
        """分发消息到相应的处理器"""
        try:
            if client_msg.type == ClientMessageType.STATUS.value:
                # 状态消息 - 根据extra中的message_type判断具体类型
                message_type = client_msg.data  # 直接使用data作为状态类型
                if self.handlers.on_status:
                    self.handlers.on_status(message_type)
            
            elif client_msg.type == ClientMessageType.ERROR.value:
                if self.handlers.on_error:
                    self.handlers.on_error(WebsocketClientError(f"Server error: {client_msg.data}"))
            
            elif client_msg.type == ClientMessageType.MASTER_DATA.value:
                # 母单详细数据 - 解析JSON数据
                try:
                    master_order_data = self._parse_payload_data(client_msg.data)
                    if self.handlers.on_master_order:
                        master_order = self._build_master_order_message(master_order_data)
                        self.handlers.on_master_order(master_order)
                
                except json.JSONDecodeError as e:
                    self._logger.error(f"Failed to parse master data message: {e}")
                    if self.handlers.on_error:
                        self.handlers.on_error(WebsocketClientError(f"Master data parse error: {e}"))
                except Exception as e:
                    self._logger.error(f"Error processing master data message: {e}")
                    if self.handlers.on_error:
                        self.handlers.on_error(e)
            
            elif client_msg.type == ClientMessageType.ORDER_DATA.value:
                # 订单详细数据 - 解析JSON数据
                try:
                    order_data = self._parse_payload_data(client_msg.data)
                    if self.handlers.on_order:
                        order = self._build_order_message(order_data)
                        self.handlers.on_order(order)
                
                except json.JSONDecodeError as e:
                    self._logger.error(f"Failed to parse order data message: {e}")
                    if self.handlers.on_error:
                        self.handlers.on_error(WebsocketClientError(f"Order data parse error: {e}"))
                except Exception as e:
                    self._logger.error(f"Error processing order data message: {e}")
                    if self.handlers.on_error:
                        self.handlers.on_error(e)
        
        except Exception as e:
            self._logger.error(f"Error in message dispatch: {e}")
            if self.handlers.on_error:
                try:
                    self.handlers.on_error(e)
                except Exception as handler_error:
                    self._logger.error(f"Error handler error: {handler_error}")

    @staticmethod
    def _parse_payload_data(payload: Any) -> Dict[str, Any]:
        """Parse the envelope data field, accepting either a JSON string or dict."""
        if isinstance(payload, dict):
            return payload
        if payload in (None, ""):
            return {}
        return json.loads(payload)

    @staticmethod
    def _get_any(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        for key in keys:
            value = data.get(key)
            if value is not None:
                return value
        return default

    @classmethod
    def _to_float(cls, value: Any, default: float = 0.0) -> float:
        if value in (None, ""):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _to_int(cls, value: Any, default: int = 0) -> int:
        if value in (None, ""):
            return default
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return bool(value)

    @classmethod
    def _build_master_order_message(cls, data: Dict[str, Any]) -> MasterOrderMessage:
        return MasterOrderMessage(
            type=cls._get_any(data, "type", default="master_order"),
            master_order_id=cls._get_any(data, "master_order_id", "masterOrderId", default=""),
            client_id=cls._get_any(data, "client_id", "clientId", "clientOrderId", default=""),
            strategy=cls._get_any(data, "strategy", "algorithm", default=""),
            symbol=cls._get_any(data, "symbol", default=""),
            side=cls._get_any(data, "side", default=""),
            qty=cls._to_float(cls._get_any(data, "qty", "totalQuantity", default=0.0)),
            duration_secs=cls._to_float(
                cls._get_any(data, "duration_secs", "durationSecs", "executionDurationSeconds", default=0.0)
            ),
            category=cls._get_any(data, "category", "marketType", default=""),
            action=cls._get_any(data, "action", default=""),
            reduce_only=cls._to_bool(cls._get_any(data, "reduce_only", "reduceOnly", default=False)),
            status=cls._get_any(data, "status", default=""),
            date=cls._to_float(cls._get_any(data, "date", default=0.0)),
            ticktime_int=cls._to_int(cls._get_any(data, "ticktime_int", "ticktimeInt", default=0)),
            ticktime_ms=cls._to_int(cls._get_any(data, "ticktime_ms", "ticktimeMs", default=0)),
            reason=cls._get_any(data, "reason", "rejectReason", default=""),
            timestamp=cls._to_int(cls._get_any(data, "timestamp", default=0)),
        )

    @classmethod
    def _build_order_message(cls, data: Dict[str, Any]) -> OrderMessage:
        filled_quantity = cls._get_any(data, "fill_qty", "fillQty", "filledQuantity", "filledQty", default=0.0)
        average_price = cls._get_any(data, "fill_price", "fillPrice", "averagePrice", "avgPrice", default=0.0)

        return OrderMessage(
            type=cls._get_any(data, "type", default="order"),
            master_order_id=cls._get_any(data, "master_order_id", "masterOrderId", default=""),
            order_id=cls._get_any(data, "order_id", "orderId", "id", default=""),
            symbol=cls._get_any(data, "symbol", default=""),
            category=cls._get_any(data, "category", "marketType", default=""),
            side=cls._get_any(data, "side", default=""),
            price=cls._to_float(cls._get_any(data, "price", default=0.0)),
            quantity=cls._to_float(cls._get_any(data, "quantity", default=0.0)),
            status=cls._get_any(data, "status", default=""),
            created_time=cls._to_int(cls._get_any(data, "created_time", "createdTime", "orderCreatedTime", default=0)),
            fill_qty=cls._to_float(filled_quantity),
            fill_price=cls._to_float(average_price),
            cum_filled_qty=cls._to_float(cls._get_any(data, "cum_filled_qty", "cumFilledQty", default=filled_quantity)),
            quantity_remaining=cls._to_float(
                cls._get_any(data, "quantity_remaining", "quantityRemaining", default=0.0)
            ),
            ack_time=cls._to_int(cls._get_any(data, "ack_time", "ackTime", default=0)),
            last_fill_time=cls._to_int(cls._get_any(data, "last_fill_time", "lastFillTime", "fillTime", default=0)),
            cancel_time=cls._to_int(cls._get_any(data, "cancel_time", "cancelTime", default=0)),
            price_type=cls._get_any(data, "price_type", "priceType", "orderType", default=""),
            reason=cls._get_any(data, "reason", "rejectReason", default=""),
            timestamp=cls._to_int(cls._get_any(data, "timestamp", default=0)),
        )
    
    def _handle_disconnect(self):
        """处理断开连接"""
        with self._lock:
            if not self._is_connected:
                return
            
            self._is_connected = False
            self.websocket = None
        
        # 调用断开连接回调
        if self.handlers.on_disconnected:
            try:
                self.handlers.on_disconnected()
            except Exception as e:
                self._logger.error(f"OnDisconnected handler error: {e}")
    
    async def _reconnect(self):
        """重连"""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._reconnect_delay)
                self._logger.info("Attempting to reconnect...")
                await self._async_connect()
                self._logger.info("Reconnected successfully")
                return
            except Exception as e:
                self._logger.error(f"Reconnect failed: {e}")
                continue
    
    def close(self):
        """关闭连接"""
        self._stop_event.set()

        websocket = None
        loop = None
        with self._lock:
            websocket = self.websocket
            loop = self._loop or getattr(websocket, "_loop", None) or getattr(websocket, "loop", None)
            self._is_connected = False

        if websocket and hasattr(websocket, "close") and not getattr(websocket, "closed", False):
            self._close_websocket_on_loop(websocket, loop)

        with self._lock:
            if self.websocket is websocket:
                self.websocket = None

        # 等待所有线程结束
        current_thread = threading.current_thread()
        for thread in self._threads:
            if thread is not current_thread and thread.is_alive():
                thread.join(timeout=5)
        self._threads.clear()

    def _close_websocket_on_loop(self, websocket: Any, loop: Optional[asyncio.AbstractEventLoop]) -> None:
        """Schedule websocket.close() on the loop that owns the connection."""
        if loop and loop.is_running():
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            try:
                if running_loop is loop:
                    loop.create_task(websocket.close())
                else:
                    future = asyncio.run_coroutine_threadsafe(websocket.close(), loop)
                    future.result(timeout=5)
            except TimeoutError:
                self._logger.warning("Timed out closing websocket")
            except Exception as e:
                self._logger.warning(f"Error closing websocket: {e}")
            return

        self._logger.debug("WebSocket event loop is not running; skipping async close")
    
    def is_connected(self) -> bool:
        """是否已连接"""
        with self._lock:
            return self._is_connected
    
    def set_reconnect_delay(self, delay: float) -> 'WebSocketService':
        """设置重连延迟"""
        self._reconnect_delay = delay
        return self
    
    def set_ping_interval(self, interval: float) -> 'WebSocketService':
        """设置心跳间隔"""
        self._ping_interval = interval
        return self
    
    def set_pong_timeout(self, timeout: float) -> 'WebSocketService':
        """设置Pong超时时间"""
        self._pong_timeout = timeout
        return self
    
    def set_logger(self, logger: logging.Logger) -> 'WebSocketService':
        """设置日志记录器"""
        self._logger = logger
        return self
