"""
Professional Async PocketOption API Client
"""

import asyncio
import json
import time
import uuid
from typing import Optional, List, Dict, Any, Union, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
from loguru import logger

from .monitoring import error_monitor, health_checker, ErrorCategory, ErrorSeverity
from .websocket_client import AsyncWebSocketClient
from .models import (
    Balance, Candle, Order, OrderResult, OrderStatus, OrderDirection,
    Asset, ConnectionStatus, ServerTime
)
from .constants import ASSETS, REGIONS, TIMEFRAMES, API_LIMITS
from .exceptions import (
    PocketOptionError, ConnectionError, AuthenticationError,
    OrderError, TimeoutError, InvalidParameterError
)


class AsyncPocketOptionClient:
    """
    Professional async PocketOption API client with modern Python practices
    """
    
    def __init__(self, ssid: str, is_demo: bool = True, region: Optional[str] = None, 
                 uid: int = 0, platform: int = 1, is_fast_history: bool = True,
                 persistent_connection: bool = False, auto_reconnect: bool = True):
        """
        Initialize async PocketOption client with enhanced monitoring
        
        Args:
            ssid: Complete SSID string or raw session ID for authentication
            is_demo: Whether to use demo account
            region: Preferred region for connection
            uid: User ID (if providing raw session)
            platform: Platform identifier (1=web, 3=mobile)
            is_fast_history: Enable fast history loading
            persistent_connection: Enable persistent connection with keep-alive (like old API)
            auto_reconnect: Enable automatic reconnection on disconnection
        """
        self.raw_ssid = ssid
        self.is_demo = is_demo
        self.preferred_region = region
        self.uid = uid
        self.platform = platform
        self.is_fast_history = is_fast_history
        self.persistent_connection = persistent_connection
        self.auto_reconnect = auto_reconnect
        
        # Parse SSID if it's a complete auth message
        if ssid.startswith('42["auth",'):
            self._parse_complete_ssid(ssid)
        else:
            # Treat as raw session ID
            self.session_id = ssid
            self._complete_ssid = None
        
        # Core components
        self._websocket = AsyncWebSocketClient()
        self._balance: Optional[Balance] = None
        self._orders: Dict[str, OrderResult] = {}
        self._server_time: Optional[ServerTime] = None
        self._event_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Enhanced monitoring and error handling
        self._error_monitor = error_monitor
        self._health_checker = health_checker
        self._connection_health_checks()
        
        # Performance tracking
        self._operation_metrics: Dict[str, List[float]] = defaultdict(list)
        self._last_health_check = time.time()
        
        # Keep-alive functionality (based on old API patterns)
        self._keep_alive_manager = None
        self._ping_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._is_persistent = False
        
        # Connection statistics (like old API)
        self._connection_stats = {
            'total_connections': 0,
            'successful_connections': 0,
            'total_reconnects': 0,
            'last_ping_time': None,
            'messages_sent': 0,
            'messages_received': 0,
            'connection_start_time': None
        }
        
        logger.info(f"Initialized PocketOption client (demo={is_demo}, uid={self.uid}, persistent={persistent_connection}) with enhanced monitoring")
    
    async def connect(self, regions: Optional[List[str]] = None, persistent: bool = None) -> bool:
        """
        Connect to PocketOption WebSocket with optional persistent keep-alive
        
        Args:
            regions: Optional list of specific regions to try
            persistent: Override persistent connection setting for this connection
            
        Returns:
            bool: True if connected successfully
        """
        try:
            # Use persistent setting from init or override
            use_persistent = persistent if persistent is not None else self.persistent_connection
            
            if use_persistent:
                return await self._start_persistent_connection(regions)
            else:
                return await self._start_regular_connection(regions)
                
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect: {e}")
    
    async def _start_persistent_connection(self, regions: Optional[List[str]] = None) -> bool:
        """Start persistent connection with keep-alive (like old API)"""
        logger.info("🚀 Starting persistent connection with automatic keep-alive...")
        
        # Import the keep-alive manager
        import sys
        sys.path.append('/Users/vigowalker/PocketOptionAPI-3')
        from connection_keep_alive import ConnectionKeepAlive
        
        # Create keep-alive manager
        complete_ssid = self.raw_ssid
        self._keep_alive_manager = ConnectionKeepAlive(complete_ssid, self.is_demo)
        
        # Add event handlers
        self._keep_alive_manager.add_event_handler('connected', self._on_keep_alive_connected)
        self._keep_alive_manager.add_event_handler('reconnected', self._on_keep_alive_reconnected)
        self._keep_alive_manager.add_event_handler('message_received', self._on_keep_alive_message)
        self._keep_alive_manager.add_event_handler('authenticated', self._on_keep_alive_authenticated)
        
        # Start persistent connection
        success = await self._keep_alive_manager.start_persistent_connection()
        
        if success:
            self._is_persistent = True
            self._connection_stats['connection_start_time'] = datetime.now()
            self._connection_stats['successful_connections'] += 1
            
            # Initialize data
            await self._initialize_data()
            
            logger.success("✅ Persistent connection established with keep-alive active")
            return True
        else:
            logger.error("❌ Failed to establish persistent connection")
            return False
    
    async def _start_regular_connection(self, regions: Optional[List[str]] = None) -> bool:
        """Start regular connection (existing behavior)"""
        # Get URLs to try
        if regions:
            urls = [REGIONS.get_region(region) for region in regions if REGIONS.get_region(region)]
        else:
            urls = REGIONS.get_demo_regions() if self.is_demo else REGIONS.get_all()
        
        if not urls:
            raise ConnectionError("No valid WebSocket URLs available")
        
        # Format session message
        ssid_message = self._format_session_message()
        
        # Connect to WebSocket
        success = await self._websocket.connect(urls, ssid_message)
        
        if success:
            self._connection_stats['successful_connections'] += 1
            
            # Start keep-alive for regular connection too (if auto_reconnect enabled)
            if self.auto_reconnect:
                await self._start_keep_alive_tasks()
            
            # Wait for authentication
            await self._wait_for_authentication()
            
            # Initialize data
            await self._initialize_data()
            
            logger.info("Successfully connected and authenticated")
            return True
        
        return False
    
    async def _start_keep_alive_tasks(self):
        """Start keep-alive tasks for regular connection"""
        logger.info("🔄 Starting keep-alive tasks for regular connection...")
        
        # Start ping task (like old API)
        self._ping_task = asyncio.create_task(self._ping_loop())
        
        # Start reconnection monitor if auto_reconnect is enabled
        if self.auto_reconnect:
            self._reconnect_task = asyncio.create_task(self._reconnection_monitor())
    
    async def _ping_loop(self):
        """Ping loop for regular connections (like old API)"""
        while self.is_connected:
            try:
                await asyncio.sleep(20)  # 20 seconds like old API
                
                if self.is_connected:
                    await self._websocket.send_message('42["ps"]')
                    self._connection_stats['last_ping_time'] = datetime.now()
                    self._connection_stats['messages_sent'] += 1
                    logger.debug("🏓 Ping sent")
                    
            except Exception as e:
                logger.error(f"❌ Ping failed: {e}")
                break
    
    async def _reconnection_monitor(self):
        """Monitor and handle reconnections for regular connections"""
        while self.auto_reconnect:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                if not self.is_connected and self.auto_reconnect:
                    logger.warning("🔄 Connection lost, attempting reconnection...")
                    
                    self._connection_stats['total_reconnects'] += 1
                    
                    # Try to reconnect
                    try:
                        success = await self._start_regular_connection()
                        if success:
                            logger.success("✅ Reconnection successful!")
                            await self._emit_event('reconnected', {})
                        else:
                            await asyncio.sleep(5)  # Wait before next attempt
                    except Exception as e:
                        logger.error(f"❌ Reconnection failed: {e}")
                        await asyncio.sleep(5)
                        
            except Exception as e:
                logger.error(f"❌ Reconnection monitor error: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from PocketOption and cleanup all resources"""
        try:
            logger.info("🛑 Disconnecting from PocketOption...")
            
            # Stop auto-reconnect
            self.auto_reconnect = False
            
            # Stop keep-alive manager if running
            if self._keep_alive_manager:
                await self._keep_alive_manager.stop_persistent_connection()
                self._keep_alive_manager = None
                self._is_persistent = False
            
            # Cancel background tasks
            if self._ping_task and not self._ping_task.done():
                self._ping_task.cancel()
                try:
                    await self._ping_task
                except asyncio.CancelledError:
                    pass
            
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
                try:
                    await self._reconnect_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect regular websocket
            await self._websocket.disconnect()
            
            logger.info("✅ Disconnected from PocketOption")
            
        except Exception as e:
            logger.error(f"❌ Disconnect error: {e}")
    
    async def get_balance(self) -> Balance:
        """
        Get current account balance
        
        Returns:
            Balance: Current balance information
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to PocketOption")
        
        # Request balance update if needed
        if not self._balance or (datetime.now() - self._balance.last_updated).seconds > 60:
            await self._request_balance_update()
        
        return self._balance
    
    async def place_order(self, asset: str, amount: float, direction: OrderDirection, 
                         duration: int) -> OrderResult:
        """
        Place a binary options order
        
        Args:
            asset: Asset symbol (e.g., 'EURUSD_otc')
            amount: Order amount in USD
            direction: Order direction (CALL or PUT)
            duration: Duration in seconds
            
        Returns:
            OrderResult: Order execution result
        """
        # Validate parameters
        self._validate_order_parameters(asset, amount, direction, duration)
        
        if not self.is_connected:
            raise ConnectionError("Not connected to PocketOption")
        
        # Create order
        order = Order(
            asset=asset,
            amount=amount,
            direction=direction,
            duration=duration
        )
        
        try:
            # Send order
            await self._send_order(order)
            
            # Wait for order result
            result = await self._wait_for_order_result(order.request_id)
            
            # Store active order
            if result.status == OrderStatus.ACTIVE:
                self._active_orders[result.order_id] = result
            
            logger.info(f"Order placed: {result.order_id} - {result.status}")
            return result
            
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            raise OrderError(f"Failed to place order: {e}")
    
    async def get_candles(self, asset: str, timeframe: Union[str, int], 
                         count: int = 100, end_time: Optional[datetime] = None) -> List[Candle]:
        """
        Get historical candle data
        
        Args:
            asset: Asset symbol
            timeframe: Timeframe (e.g., '1m', '5m' or seconds)
            count: Number of candles to retrieve
            end_time: End time for historical data (default: now)
            
        Returns:
            List[Candle]: Historical candle data
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to PocketOption")
        
        # Convert timeframe
        if isinstance(timeframe, str):
            timeframe_seconds = TIMEFRAMES.get(timeframe)
            if not timeframe_seconds:
                raise InvalidParameterError(f"Invalid timeframe: {timeframe}")
        else:
            timeframe_seconds = timeframe
        
        # Validate asset
        if asset not in ASSETS:
            raise InvalidParameterError(f"Invalid asset: {asset}")
        
        # Set default end time
        if not end_time:
            end_time = datetime.now()
        
        try:
            # Request candle data
            candles = await self._request_candles(asset, timeframe_seconds, count, end_time)
            
            # Cache results
            cache_key = f"{asset}_{timeframe_seconds}"
            self._candles_cache[cache_key] = candles
            
            logger.info(f"Retrieved {len(candles)} candles for {asset}")
            return candles
            
        except Exception as e:
            logger.error(f"Failed to get candles: {e}")
            raise PocketOptionError(f"Failed to get candles: {e}")
    
    async def get_candles_dataframe(self, asset: str, timeframe: Union[str, int], 
                                   count: int = 100, end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Get historical candle data as pandas DataFrame
        
        Args:
            asset: Asset symbol
            timeframe: Timeframe (e.g., '1m', '5m' or seconds)
            count: Number of candles to retrieve
            end_time: End time for historical data
            
        Returns:
            pd.DataFrame: Historical candle data
        """
        candles = await self.get_candles(asset, timeframe, count, end_time)
        
        # Convert to DataFrame
        data = []
        for candle in candles:
            data.append({
                'timestamp': candle.timestamp,
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.volume
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
        
        return df
    
    async def check_order_result(self, order_id: str) -> Optional[OrderResult]:
        """
        Check the result of a specific order
        
        Args:
            order_id: Order ID to check
            
        Returns:
            OrderResult: Order result or None if not found
        """
        return self._order_results.get(order_id)
    
    async def get_active_orders(self) -> List[OrderResult]:
        """
        Get all active orders
        
        Returns:
            List[OrderResult]: Active orders
        """
        return list(self._active_orders.values())
    
    def add_event_callback(self, event: str, callback: Callable) -> None:
        """
        Add event callback
        
        Args:
            event: Event name (e.g., 'order_closed', 'balance_updated')
            callback: Callback function
        """
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)
    
    def remove_event_callback(self, event: str, callback: Callable) -> None:
        """
        Remove event callback
        
        Args:
            event: Event name
            callback: Callback function to remove
        """
        if event in self._event_callbacks:
            try:
                self._event_callbacks[event].remove(callback)
            except ValueError:
                pass
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected (including persistent connections)"""
        if self._is_persistent and self._keep_alive_manager:
            return self._keep_alive_manager.is_connected
        else:
            return self._websocket.is_connected
    
    @property
    def connection_info(self):
        """Get connection information (including persistent connections)"""
        if self._is_persistent and self._keep_alive_manager:
            return self._keep_alive_manager.connection_info
        else:
            return self._websocket.connection_info
    
    async def send_message(self, message: str) -> bool:
        """Send message through active connection"""
        try:
            if self._is_persistent and self._keep_alive_manager:
                success = await self._keep_alive_manager.send_message(message)
                if success:
                    self._connection_stats['messages_sent'] += 1
                return success
            else:
                await self._websocket.send_message(message)
                self._connection_stats['messages_sent'] += 1
                return True
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            return False
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics"""
        stats = dict(self._connection_stats)
        
        if self._is_persistent and self._keep_alive_manager:
            keep_alive_stats = self._keep_alive_manager.get_connection_stats()
            stats.update(keep_alive_stats)
        
        # Add uptime calculation
        if stats.get('connection_start_time'):
            stats['uptime'] = datetime.now() - stats['connection_start_time']
        
        stats.update({
            'is_connected': self.is_connected,
            'is_persistent': self._is_persistent,
            'auto_reconnect': self.auto_reconnect,
            'current_region': self.connection_info.region if self.connection_info else None
        })
        
        return stats
    
    # Private methods
    
    def _setup_event_handlers(self):
        """Setup WebSocket event handlers"""
        self._websocket.add_event_handler('authenticated', self._on_authenticated)
        self._websocket.add_event_handler('balance_updated', self._on_balance_updated)
        self._websocket.add_event_handler('order_opened', self._on_order_opened)
        self._websocket.add_event_handler('order_closed', self._on_order_closed)
        self._websocket.add_event_handler('stream_update', self._on_stream_update)
        self._websocket.add_event_handler('candles_received', self._on_candles_received)
        self._websocket.add_event_handler('disconnected', self._on_disconnected)
    
    def _format_session_message(self) -> str:
        """Format session authentication message"""
        
        # If we already have a parsed complete SSID, return it
        if hasattr(self, '_complete_ssid') and self._complete_ssid:
            logger.debug("Using parsed complete SSID")
            return self._complete_ssid
        
        # Otherwise, format from components
        auth_data = self.raw_ssid
        
        # Add optional parameters
        if self.is_fast_history:
            auth_data["isFastHistory"] = True
        
        formatted_ssid = f'42["auth",{json.dumps(auth_data)}]'
        logger.debug("Formatted SSID from components")
        return formatted_ssid
    
    def _parse_complete_ssid(self, ssid: str) -> None:
        """Parse complete SSID auth message to extract components"""
        try:
            # Extract JSON part from message like: 42["auth",{...}]
            if ssid.startswith('42["auth",') and ssid.endswith(']'):
                json_part = ssid[10:-1]  # Remove '42["auth",' and ']'
                auth_data = json.loads(json_part)
                
                # Extract components
                self.session_id = auth_data.get("session", "")
                self.is_demo = bool(auth_data.get("isDemo", 1))
                self.uid = auth_data.get("uid", 0)
                self.platform = auth_data.get("platform", 1)
                self.is_fast_history = auth_data.get("isFastHistory", True)
                
                # Store complete SSID for direct use
                self._complete_ssid = ssid
                
                logger.info(f"Parsed SSID: session={self.session_id[:10]}..., uid={self.uid}, demo={self.is_demo}")
                
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse complete SSID, treating as raw session: {e}")
            self.session_id = ssid
            self._complete_ssid = None
    
    async def _wait_for_authentication(self, timeout: float = 10.0) -> None:
        """Wait for authentication to complete (like old API)"""
        logger.debug("Waiting for authentication...")
        
        # Create an event to wait for authentication
        auth_event = asyncio.Event()
        auth_error = None
        
        def on_authenticated(data):
            logger.success("✅ Authentication successful")
            auth_event.set()
        
        def on_auth_error(data):
            nonlocal auth_error
            auth_error = data.get('message', 'Authentication failed')
            logger.error(f"❌ Authentication failed: {auth_error}")
            auth_event.set()
        
        # Add event handlers
        self._websocket.add_event_handler('authenticated', on_authenticated)
        self._websocket.add_event_handler('auth_error', on_auth_error)
        
        try:
            # Wait for authentication with timeout
            await asyncio.wait_for(auth_event.wait(), timeout=timeout)
            
            if auth_error:
                raise AuthenticationError(auth_error)
                
        except asyncio.TimeoutError:
            raise AuthenticationError("Authentication timeout - no response from server")
        finally:
            # Clean up event handlers
            self._websocket.remove_event_handler('authenticated', on_authenticated)
            self._websocket.remove_event_handler('auth_error', on_auth_error)
    
    async def _initialize_data(self) -> None:
        """Initialize client data after connection"""
        # Request initial balance
        await self._request_balance_update()
        
        # Setup time synchronization
        await self._setup_time_sync()
    
    async def _request_balance_update(self) -> None:
        """Request balance update from server"""
        message = '42["getBalance"]'
        await self._websocket.send_message(message)
    
    async def _setup_time_sync(self) -> None:
        """Setup server time synchronization"""
        # This would typically involve getting server timestamp
        # For now, create a basic time sync object
        local_time = datetime.now().timestamp()
        self._server_time = ServerTime(
            server_timestamp=local_time,
            local_timestamp=local_time,
            offset=0.0
        )
    
    def _validate_order_parameters(self, asset: str, amount: float, 
                                  direction: OrderDirection, duration: int) -> None:
        """Validate order parameters"""
        if asset not in ASSETS:
            raise InvalidParameterError(f"Invalid asset: {asset}")
        
        if amount < API_LIMITS['min_order_amount'] or amount > API_LIMITS['max_order_amount']:
            raise InvalidParameterError(
                f"Amount must be between {API_LIMITS['min_order_amount']} and {API_LIMITS['max_order_amount']}"
            )
        
        if duration < API_LIMITS['min_duration'] or duration > API_LIMITS['max_duration']:
            raise InvalidParameterError(
                f"Duration must be between {API_LIMITS['min_duration']} and {API_LIMITS['max_duration']} seconds"
            )
    
    async def _send_order(self, order: Order) -> None:
        """Send order to server"""
        order_data = {
            "asset": order.asset,
            "amount": order.amount,
            "action": order.direction.value,
            "isDemo": 1 if self.is_demo else 0,
            "requestId": order.request_id,
            "optionType": 100,
            "time": order.duration
        }
        
        message = f'42["openOrder",{json.dumps(order_data)}]'
        await self._websocket.send_message(message)
    
    async def _wait_for_order_result(self, request_id: str, timeout: float = 10.0) -> OrderResult:
        """Wait for order execution result"""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if request_id in self._order_results:
                return self._order_results[request_id]
            await asyncio.sleep(0.1)
        
        raise TimeoutError(f"Order result timeout for request {request_id}")
    
    async def _request_candles(self, asset: str, timeframe: int, count: int, 
                              end_time: datetime) -> List[Candle]:
        """Request candle data from server"""
        # Convert end_time to timestamp
        end_timestamp = int(end_time.timestamp())
        
        candle_data = {
            "asset": asset,
            "index": end_timestamp,
            "time": end_timestamp,
            "offset": count,
            "period": timeframe
        }
        
        message = f'42["loadHistoryPeriod",{json.dumps(candle_data)}]'
        await self._websocket.send_message(message)
        
        # Wait for candles (this would be implemented with proper event handling)
        await asyncio.sleep(2)  # Placeholder
        
        # For now, return empty list (would be populated by event handler)
        return []
    
    async def _emit_event(self, event: str, data: Any) -> None:
        """Emit event to registered callbacks"""
        if event in self._event_callbacks:
            for callback in self._event_callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in event callback for {event}: {e}")
    
    # Event handlers
    
    async def _on_authenticated(self, data: Dict[str, Any]) -> None:
        """Handle authentication success"""
        logger.info("Authentication successful")
        await self._emit_event('authenticated', data)
    
    async def _on_balance_updated(self, data: Dict[str, Any]) -> None:
        """Handle balance update"""
        if 'balance' in data:
            self._balance = Balance(
                balance=float(data['balance']),
                currency=data.get('currency', 'USD'),
                is_demo=self.is_demo
            )
            logger.info(f"Balance updated: {self._balance.balance}")
            await self._emit_event('balance_updated', self._balance)
    
    async def _on_order_opened(self, data: Dict[str, Any]) -> None:
        """Handle order opened event"""
        logger.info(f"Order opened: {data}")
        await self._emit_event('order_opened', data)
    
    async def _on_order_closed(self, data: Dict[str, Any]) -> None:
        """Handle order closed event"""
        logger.info(f"Order closed: {data}")
        
        # Update order result
        if 'id' in data:
            order_id = str(data['id'])
            if order_id in self._active_orders:
                # Update order with result
                active_order = self._active_orders[order_id]
                profit = data.get('profit', 0)
                
                result = OrderResult(
                    order_id=active_order.order_id,
                    asset=active_order.asset,
                    amount=active_order.amount,
                    direction=active_order.direction,
                    duration=active_order.duration,
                    status=OrderStatus.WIN if profit > 0 else OrderStatus.LOSE,
                    placed_at=active_order.placed_at,
                    expires_at=active_order.expires_at,
                    profit=profit,
                    payout=data.get('payout')
                )
                
                self._order_results[order_id] = result
                del self._active_orders[order_id]
                
                await self._emit_event('order_closed', result)
    
    async def _on_stream_update(self, data: Dict[str, Any]) -> None:
        """Handle stream update (time sync, etc.)"""
        if isinstance(data, list) and len(data) > 0:
            # Update server time
            server_timestamp = data[0].get('timestamp') if isinstance(data[0], dict) else data[0]
            if server_timestamp:
                local_timestamp = datetime.now().timestamp()
                offset = server_timestamp - local_timestamp
                
                self._server_time = ServerTime(
                    server_timestamp=server_timestamp,
                    local_timestamp=local_timestamp,
                    offset=offset
                )
    
    async def _on_candles_received(self, data: Dict[str, Any]) -> None:
        """Handle candles data"""
        logger.info("Candles data received")
        await self._emit_event('candles_received', data)
    
    async def _on_disconnected(self, data: Dict[str, Any]) -> None:
        """Handle disconnection"""
        logger.warning("WebSocket disconnected")
        await self._emit_event('disconnected', data)
        
        # Attempt to reconnect if enabled
        if self.auto_reconnect:
            logger.info("Attempting to reconnect...")
            await self.connect()
    
    def _connection_health_checks(self):
        """Setup connection health checks"""
        async def check_websocket_health():
            """Check WebSocket connection health"""
            try:
                if not self.is_connected:
                    return {'status': 'disconnected', 'healthy': False}
                
                # Check ping response time
                start_time = time.time()
                await self._websocket.send_message('42["ps"]')
                ping_time = time.time() - start_time
                
                return {
                    'status': 'connected',
                    'healthy': ping_time < 5.0,  # Healthy if ping < 5s
                    'ping_time': ping_time,
                    'connection_info': self.connection_info
                }
            except Exception as e:
                return {'status': 'error', 'healthy': False, 'error': str(e)}
        
        async def check_balance_availability():
            """Check if balance data is available and recent"""
            try:
                if not self._balance:
                    return {'status': 'no_balance', 'healthy': False}
                
                time_since_update = (datetime.now() - self._balance.last_updated).total_seconds()
                is_recent = time_since_update < 300  # 5 minutes
                
                return {
                    'status': 'available',
                    'healthy': is_recent,
                    'last_update': time_since_update,
                    'balance': self._balance.balance
                }
            except Exception as e:
                return {'status': 'error', 'healthy': False, 'error': str(e)}
        
        # Register health checks
        self._health_checker.register_health_check('websocket', check_websocket_health)
        self._health_checker.register_health_check('balance', check_balance_availability)
    
    async def execute_with_monitoring(self, operation_name: str, func: Callable, *args, **kwargs):
        """Execute operation with comprehensive monitoring"""
        return await self._error_monitor.execute_with_monitoring(
            func=func,
            operation_name=operation_name,
            category=ErrorCategory.TRADING,
            use_circuit_breaker=True,
            use_retry=True,
            *args, **kwargs
        )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        # Run health checks if enough time has passed
        current_time = time.time()
        if current_time - self._last_health_check > 30:  # Check every 30 seconds
            await self._health_checker.start_monitoring()
            self._last_health_check = current_time
        
        return self._health_checker.get_health_report()
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'operation_metrics': dict(self._operation_metrics),
            'error_summary': self._error_monitor.get_error_summary(),
            'health_status': await self.get_health_status()
        }
    
    # Context manager support
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    # Keep-alive and reconnect functionality
    
    def _start_keep_alive_task(self):
        """Start the keep-alive task"""
        if self._ping_task is not None:
            return  # Task already running
        
        async def keep_alive():
            """Send periodic ping messages to keep the connection alive"""
            while self._is_persistent:
                try:
                    await self._websocket.send_message('42["ps"]')
                    logger.debug("Ping sent")
                except Exception as e:
                    logger.warning(f"Ping failed: {e}")
                    self._is_persistent = False
                    break
                
                await asyncio.sleep(10)  # Ping interval (10 seconds)
        
        self._ping_task = asyncio.create_task(keep_alive())
        logger.info("Keep-alive task started")
    
    def _stop_keep_alive_task(self):
        """Stop the keep-alive task"""
        if self._ping_task is not None:
            self._ping_task.cancel()
            self._ping_task = None
            logger.info("Keep-alive task stopped")
    
    async def _reconnect(self):
        """Reconnect to the WebSocket"""
        self._stop_keep_alive_task()
        
        try:
            logger.info("Reconnecting to PocketOption...")
            await self.disconnect()
            await asyncio.sleep(2)  # Wait before reconnecting
            await self.connect()
            logger.info("Reconnected successfully")
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            # Schedule next reconnect attempt
            await asyncio.sleep(5)
            await self._reconnect()
    
    async def _handle_disconnection(self):
        """Handle disconnection and attempt to reconnect if enabled"""
        logger.warning("WebSocket disconnected")
        await self._emit_event('disconnected', {})
        
        if self.auto_reconnect:
            logger.info("Auto-reconnect enabled, attempting to reconnect...")
            await self._reconnect()
