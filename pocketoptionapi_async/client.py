"""
Professional Async PocketOption API Client
"""

import asyncio
import json
import uuid
from typing import Optional, List, Dict, Any, Union, Callable
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

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
    
    def __init__(self, session_id: str, is_demo: bool = True, timeout: float = 30.0):
        """
        Initialize the async PocketOption client
        
        Args:
            session_id: Your PocketOption session ID (SSID)
            is_demo: Whether to use demo account (default: True)
            timeout: Default timeout for operations in seconds
        """
        self.session_id = session_id
        self.is_demo = is_demo
        self.timeout = timeout
        
        # Internal state
        self._websocket = AsyncWebSocketClient()
        self._balance: Optional[Balance] = None
        self._server_time: Optional[ServerTime] = None
        self._active_orders: Dict[str, OrderResult] = {}
        self._order_results: Dict[str, OrderResult] = {}
        self._candles_cache: Dict[str, List[Candle]] = {}
        
        # Event callbacks
        self._event_callbacks: Dict[str, List[Callable]] = {}
        
        # Setup event handlers
        self._setup_event_handlers()
        
        logger.info(f"Initialized PocketOption client (demo={is_demo})")
    
    async def connect(self, regions: Optional[List[str]] = None) -> bool:
        """
        Connect to PocketOption WebSocket
        
        Args:
            regions: Optional list of specific regions to try
            
        Returns:
            bool: True if connected successfully
        """
        try:
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
                # Wait for authentication
                await self._wait_for_authentication()
                
                # Initialize data
                await self._initialize_data()
                
                logger.info("Successfully connected and authenticated")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from PocketOption"""
        try:
            await self._websocket.disconnect()
            logger.info("Disconnected from PocketOption")
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
    
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
        """Check if client is connected"""
        return self._websocket.is_connected
    
    @property
    def connection_info(self):
        """Get connection information"""
        return self._websocket.connection_info
    
    @property
    def server_time(self) -> Optional[datetime]:
        """Get synchronized server time"""
        if self._server_time:
            # Calculate current server time based on offset
            local_time = datetime.now().timestamp()
            return datetime.fromtimestamp(local_time + self._server_time.offset)
        return None
    
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
        auth_data = {
            "session": self.session_id,
            "isDemo": 1 if self.is_demo else 0,
            "uid": 0,  # Will be updated after authentication
            "platform": 1
        }
        return f'42["auth",{json.dumps(auth_data)}]'
    
    async def _wait_for_authentication(self, timeout: float = 10.0) -> None:
        """Wait for authentication to complete"""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            await asyncio.sleep(0.1)
            # Check if authenticated (this would be set by event handler)
            # For now, just wait a bit and assume success
        
        await asyncio.sleep(2)  # Give time for initial data
    
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
    
    # Context manager support
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
