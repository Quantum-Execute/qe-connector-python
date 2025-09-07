"""
WebSocket客户端实现
"""
import asyncio
import json
import logging
import threading
import time
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
    
    def __init__(self, client, base_url: str = "wss://test.quantumexecute.com"):
        self.client = client
        self.base_url = base_url
        self.listen_key: Optional[str] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.handlers = WebSocketEventHandlers()
        self.is_connected = False
        self._lock = threading.RLock()
        self._reconnect_delay = 5.0
        self._ping_interval = 1.0
        self._pong_timeout = 10.0
        self._stop_event = threading.Event()
        self._threads = []
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
        try:
            loop.run_until_complete(self._async_connect())
        finally:
            loop.close()
    
    async def _async_connect(self):
        """异步连接WebSocket"""
        with self._lock:
            if self.is_connected:
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
                    self.is_connected = True
                
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
        return f"{self.base_url}/api/ws?listen_key={self.listen_key}"
    
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
                if self.handlers.on_status:
                    self.handlers.on_status(client_msg.data)
            
            elif client_msg.type == ClientMessageType.ERROR.value:
                if self.handlers.on_error:
                    self.handlers.on_error(WebsocketClientError(f"Server error: {client_msg.data}"))
            
            elif client_msg.type in [ClientMessageType.MASTER_DATA.value, ClientMessageType.ORDER_DATA.value]:
                # 解析第三方消息类型
                try:
                    base_data = json.loads(client_msg.data)
                    base_msg = BaseThirdPartyMessage(type=base_data.get("type", ""))
                    
                    # 根据第三方消息类型分发
                    if base_msg.type == ThirdPartyMessageType.MASTER_ORDER.value:
                        if self.handlers.on_master_order:
                            master_order = MasterOrderMessage(**base_data)
                            self.handlers.on_master_order(master_order)
                    
                    elif base_msg.type == ThirdPartyMessageType.ORDER.value:
                        if self.handlers.on_order:
                            order = OrderMessage(**base_data)
                            self.handlers.on_order(order)
                    
                    elif base_msg.type == ThirdPartyMessageType.FILL.value:
                        if self.handlers.on_fill:
                            fill = FillMessage(**base_data)
                            self.handlers.on_fill(fill)
                
                except json.JSONDecodeError as e:
                    self._logger.error(f"Failed to parse third party message: {e}")
                    if self.handlers.on_error:
                        self.handlers.on_error(WebsocketClientError(f"Third party message parse error: {e}"))
                except Exception as e:
                    self._logger.error(f"Error processing third party message: {e}")
                    if self.handlers.on_error:
                        self.handlers.on_error(e)
        
        except Exception as e:
            self._logger.error(f"Error in message dispatch: {e}")
            if self.handlers.on_error:
                try:
                    self.handlers.on_error(e)
                except Exception as handler_error:
                    self._logger.error(f"Error handler error: {handler_error}")
    
    def _handle_disconnect(self):
        """处理断开连接"""
        with self._lock:
            if not self.is_connected:
                return
            
            self.is_connected = False
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
        
        with self._lock:
            if self.websocket:
                # 在事件循环中关闭连接
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.websocket.close())
                finally:
                    loop.close()
                self.websocket = None
            self.is_connected = False
        
        # 等待所有线程结束
        for thread in self._threads:
            if thread.is_alive():
                thread.join(timeout=5)
        self._threads.clear()
    
    def is_connected(self) -> bool:
        """是否已连接"""
        with self._lock:
            return self.is_connected
    
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
