"""
Async WebSocket client for PocketOption API
"""

import asyncio
import json
import ssl
import time
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from loguru import logger

from .models import ConnectionInfo, ConnectionStatus, ServerTime
from .constants import CONNECTION_SETTINGS, DEFAULT_HEADERS
from .exceptions import WebSocketError, ConnectionError


class AsyncWebSocketClient:
    """
    Professional async WebSocket client for PocketOption
    """
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connection_info: Optional[ConnectionInfo] = None
        self.server_time: Optional[ServerTime] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = CONNECTION_SETTINGS['max_reconnect_attempts']
        
    async def connect(self, urls: List[str], ssid: str) -> bool:
        """
        Connect to PocketOption WebSocket with fallback URLs
        
        Args:
            urls: List of WebSocket URLs to try
            ssid: Session ID for authentication
            
        Returns:
            bool: True if connected successfully
        """
        for url in urls:
            try:
                logger.info(f"Attempting to connect to {url}")
                
                # SSL context setup
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # Connect with timeout
                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        url,
                        ssl=ssl_context,
                        extra_headers=DEFAULT_HEADERS,
                        ping_interval=CONNECTION_SETTINGS['ping_interval'],
                        ping_timeout=CONNECTION_SETTINGS['ping_timeout'],
                        close_timeout=CONNECTION_SETTINGS['close_timeout']
                    ),
                    timeout=10.0
                )
                
                # Update connection info
                region = self._extract_region_from_url(url)
                self.connection_info = ConnectionInfo(
                    url=url,
                    region=region,
                    status=ConnectionStatus.CONNECTED,
                    connected_at=datetime.now(),
                    reconnect_attempts=self._reconnect_attempts
                )
                
                logger.info(f"Connected to {region} region successfully")
                
                # Start message handling
                self._running = True
                
                # Send initial handshake
                await self._send_handshake(ssid)
                
                # Start background tasks
                await self._start_background_tasks()
                
                self._reconnect_attempts = 0
                return True
                
            except Exception as e:
                logger.warning(f"Failed to connect to {url}: {e}")
                if self.websocket:
                    await self.websocket.close()
                    self.websocket = None
                continue
                
        raise ConnectionError("Failed to connect to any WebSocket endpoint")
    
    async def disconnect(self):
        """Gracefully disconnect from WebSocket"""
        logger.info("Disconnecting from WebSocket")
        
        self._running = False
        
        # Cancel background tasks
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket connection
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            
        # Update connection status
        if self.connection_info:
            self.connection_info = ConnectionInfo(
                url=self.connection_info.url,
                region=self.connection_info.region,
                status=ConnectionStatus.DISCONNECTED,
                connected_at=self.connection_info.connected_at,
                reconnect_attempts=self.connection_info.reconnect_attempts
            )
    
    async def send_message(self, message: str) -> None:
        """
        Send message to WebSocket
        
        Args:
            message: Message to send
        """
        if not self.websocket or self.websocket.closed:
            raise WebSocketError("WebSocket is not connected")
            
        try:
            await self.websocket.send(message)
            logger.debug(f"Sent message: {message}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise WebSocketError(f"Failed to send message: {e}")
    
    async def receive_messages(self) -> None:
        """
        Continuously receive and process messages
        """
        try:
            while self._running and self.websocket:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=CONNECTION_SETTINGS['message_timeout']
                    )
                    await self._process_message(message)
                    
                except asyncio.TimeoutError:
                    logger.warning("Message receive timeout")
                    continue
                except ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    await self._handle_disconnect()
                    break
                    
        except Exception as e:
            logger.error(f"Error in message receiving: {e}")
            await self._handle_disconnect()
    
    def add_event_handler(self, event: str, handler: Callable) -> None:
        """
        Add event handler
        
        Args:
            event: Event name
            handler: Handler function
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    def remove_event_handler(self, event: str, handler: Callable) -> None:
        """
        Remove event handler
        
        Args:
            event: Event name
            handler: Handler function to remove
        """
        if event in self._event_handlers:
            try:
                self._event_handlers[event].remove(handler)
            except ValueError:
                pass
    
    async def _send_handshake(self, ssid: str) -> None:
        """Send initial handshake messages"""
        # Wait for initial connection message
        await asyncio.sleep(0.5)
        
        # Send handshake sequence
        await self.send_message("40")
        await asyncio.sleep(0.1)
        await self.send_message(ssid)
        
        logger.debug("Handshake completed")
    
    async def _start_background_tasks(self) -> None:
        """Start background tasks"""
        # Start ping task
        self._ping_task = asyncio.create_task(self._ping_loop())
        
        # Start message receiving task
        asyncio.create_task(self.receive_messages())
    
    async def _ping_loop(self) -> None:
        """Send periodic ping messages"""
        while self._running and self.websocket:
            try:
                await asyncio.sleep(CONNECTION_SETTINGS['ping_interval'])
                
                if self.websocket and not self.websocket.closed:
                    await self.send_message('42["ps"]')
                    
                    # Update last ping time
                    if self.connection_info:
                        self.connection_info = ConnectionInfo(
                            url=self.connection_info.url,
                            region=self.connection_info.region,
                            status=self.connection_info.status,
                            connected_at=self.connection_info.connected_at,
                            last_ping=datetime.now(),
                            reconnect_attempts=self.connection_info.reconnect_attempts
                        )
                        
            except Exception as e:
                logger.error(f"Ping failed: {e}")
                break
    
    async def _process_message(self, message: str) -> None:
        """
        Process incoming WebSocket message
        
        Args:
            message: Raw message from WebSocket
        """
        try:
            logger.debug(f"Received message: {message}")
            
            # Handle different message types
            if message.startswith('0') and 'sid' in message:
                await self.send_message("40")
                
            elif message == "2":
                await self.send_message("3")
                
            elif message.startswith('40') and 'sid' in message:
                # Connection established
                await self._emit_event('connected', {})
                
            elif message.startswith('451-['):
                # Parse JSON message
                json_part = message.split("-", 1)[1]
                data = json.loads(json_part)
                await self._handle_json_message(data)
                
            elif message.startswith('42') and 'NotAuthorized' in message:
                logger.error("Authentication failed: Invalid SSID")
                await self._emit_event('auth_error', {'message': 'Invalid SSID'})
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _handle_json_message(self, data: List[Any]) -> None:
        """
        Handle JSON formatted messages
        
        Args:
            data: Parsed JSON data
        """
        if not data or len(data) < 1:
            return
            
        event_type = data[0]
        event_data = data[1] if len(data) > 1 else {}
        
        # Handle specific events
        if event_type == "successauth":
            await self._emit_event('authenticated', event_data)
            
        elif event_type == "successupdateBalance":
            await self._emit_event('balance_updated', event_data)
            
        elif event_type == "successopenOrder":
            await self._emit_event('order_opened', event_data)
            
        elif event_type == "successcloseOrder":
            await self._emit_event('order_closed', event_data)
            
        elif event_type == "updateStream":
            await self._emit_event('stream_update', event_data)
            
        elif event_type == "loadHistoryPeriod":
            await self._emit_event('candles_received', event_data)
            
        elif event_type == "updateHistoryNew":
            await self._emit_event('history_update', event_data)
            
        else:
            await self._emit_event('unknown_event', {'type': event_type, 'data': event_data})
    
    async def _emit_event(self, event: str, data: Dict[str, Any]) -> None:
        """
        Emit event to registered handlers
        
        Args:
            event: Event name
            data: Event data
        """
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event}: {e}")
    
    async def _handle_disconnect(self) -> None:
        """Handle WebSocket disconnection"""
        if self.connection_info:
            self.connection_info = ConnectionInfo(
                url=self.connection_info.url,
                region=self.connection_info.region,
                status=ConnectionStatus.DISCONNECTED,
                connected_at=self.connection_info.connected_at,
                last_ping=self.connection_info.last_ping,
                reconnect_attempts=self.connection_info.reconnect_attempts
            )
        
        await self._emit_event('disconnected', {})
        
        # Attempt reconnection if enabled
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            logger.info(f"Attempting reconnection {self._reconnect_attempts}/{self._max_reconnect_attempts}")
            await asyncio.sleep(CONNECTION_SETTINGS['reconnect_delay'])
            # Note: Reconnection logic would be handled by the main client
    
    def _extract_region_from_url(self, url: str) -> str:
        """Extract region name from URL"""
        try:
            # Extract from URLs like "wss://api-eu.po.market/..."
            parts = url.split('//')[1].split('.')[0]
            if 'api-' in parts:
                return parts.replace('api-', '').upper()
            elif 'demo' in parts:
                return 'DEMO'
            else:
                return 'UNKNOWN'
        except:
            return 'UNKNOWN'
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return (self.websocket is not None and 
                not self.websocket.closed and 
                self.connection_info and 
                self.connection_info.status == ConnectionStatus.CONNECTED)
