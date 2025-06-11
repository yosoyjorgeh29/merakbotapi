"""
Connection Keep-Alive Manager for PocketOption API
"""

import asyncio
import time
import json
from collections import defaultdict
from typing import Dict, List, Callable, Any, Optional
from loguru import logger

class ConnectionKeepAlive:
    """
    Handles persistent connection with automatic keep-alive and reconnection
    """
    
    def __init__(self, ssid: str, is_demo: bool = True):
        """
        Initialize connection keep-alive manager
        
        Args:
            ssid: Session ID for authentication
            is_demo: Whether this is a demo account (default: True)
        """
        self.ssid = ssid
        self.is_demo = is_demo
        self.is_connected = False
        self._websocket = None  # Will store reference to websocket client
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._ping_task = None
        self._reconnect_task = None
        self._connection_stats = {
            'last_ping_time': None,
            'total_reconnections': 0,
            'messages_sent': 0,
            'messages_received': 0
        }
        
        # Importing inside the class to avoid circular imports
        try:
            from .websocket_client import AsyncWebSocketClient
            self._websocket_client_class = AsyncWebSocketClient
        except ImportError:
            logger.error("Failed to import AsyncWebSocketClient")
            raise ImportError("AsyncWebSocketClient module not available")
    
    def add_event_handler(self, event: str, handler: Callable):
        """Add event handler function"""
        self._event_handlers[event].append(handler)
    
    async def _trigger_event_async(self, event: str, *args, **kwargs):
        """Trigger event handlers asynchronously"""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    # Call async handlers directly
                    await handler(*args, **kwargs)
                else:
                    # Call sync handlers directly
                    handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {event} handler: {e}")
    
    def _trigger_event(self, event: str, *args, **kwargs):
        """Trigger event handlers"""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    # Create task for async handlers
                    asyncio.create_task(self._handle_async_callback(handler, args, kwargs))
                else:
                    # Call sync handlers directly
                    handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {event} handler: {e}")
                
    async def _handle_async_callback(self, callback, args, kwargs):
        """Helper to handle async callbacks in tasks"""
        try:
            await callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in async callback: {e}")
    
    # Event forwarding methods
    async def _forward_balance_data(self, data):
        """Forward balance_data event from WebSocket to keep-alive handlers"""
        await self._trigger_event_async('balance_data', data)
    
    async def _forward_balance_updated(self, data):
        """Forward balance_updated event from WebSocket to keep-alive handlers"""  
        await self._trigger_event_async('balance_updated', data)
    
    async def _forward_authenticated(self, data):
        """Forward authenticated event from WebSocket to keep-alive handlers"""
        await self._trigger_event_async('authenticated', data)
    
    async def _forward_order_opened(self, data):
        """Forward order_opened event from WebSocket to keep-alive handlers"""
        await self._trigger_event_async('order_opened', data)
    
    async def _forward_order_closed(self, data):
        """Forward order_closed event from WebSocket to keep-alive handlers"""
        await self._trigger_event_async('order_closed', data)
    
    async def _forward_stream_update(self, data):
        """Forward stream_update event from WebSocket to keep-alive handlers"""
        await self._trigger_event_async('stream_update', data)
    
    async def _forward_json_data(self, data):
        """Forward json_data event from WebSocket to keep-alive handlers"""
        await self._trigger_event_async('json_data', data)

    async def connect_with_keep_alive(self, regions: Optional[List[str]] = None) -> bool:
        """
        Connect with automatic keep-alive and reconnection
        
        Args:
            regions: List of region names to try (optional)
            
        Returns:
            bool: Success status
        """
        # Create websocket client if needed
        if not self._websocket:
            self._websocket = self._websocket_client_class()
            
            # Forward WebSocket events to keep-alive events
            self._websocket.add_event_handler('balance_data', self._forward_balance_data)
            self._websocket.add_event_handler('balance_updated', self._forward_balance_updated)
            self._websocket.add_event_handler('authenticated', self._forward_authenticated)
            self._websocket.add_event_handler('order_opened', self._forward_order_opened)
            self._websocket.add_event_handler('order_closed', self._forward_order_closed)
            self._websocket.add_event_handler('stream_update', self._forward_stream_update)
            self._websocket.add_event_handler('json_data', self._forward_json_data)
            
        # Format auth message
        if self.ssid.startswith('42["auth",'):
            ssid_message = self.ssid
        else:
            # Create basic auth message from raw session ID
            ssid_message = f'42["auth", {{"ssid": "{self.ssid}", "is_demo": {str(self.is_demo).lower()}}}]'
        
        # Connect to WebSocket
        from .constants import REGIONS
        if not regions:
            # Use appropriate regions based on demo mode
            if self.is_demo:
                all_regions = REGIONS.get_all_regions()
                demo_urls = REGIONS.get_demo_regions()
                regions = []
                for name, url in all_regions.items():
                    if url in demo_urls:
                        regions.append(name)
            else:
                # For live mode, use all regions except demo
                all_regions = REGIONS.get_all_regions()
                regions = [name for name, url in all_regions.items() if "DEMO" not in name.upper()]
        
        # Try to connect
        for region_name in regions:
            region_url = REGIONS.get_region(region_name)
            if not region_url:
                continue
                
            try:
                urls = [region_url]
                logger.info(f"Trying to connect to {region_name} ({region_url})")
                success = await self._websocket.connect(urls, ssid_message)
                
                if success:
                    logger.info(f"Connected to {region_name}")
                    self.is_connected = True
                    
                    # Start keep-alive
                    self._start_keep_alive_tasks()
                    
                    # Notify connection (async-aware)
                    await self._trigger_event_async('connected')
                    return True
            except Exception as e:
                logger.warning(f"Failed to connect to {region_name}: {e}")
        
        return False

    def _start_keep_alive_tasks(self):
        """Start keep-alive tasks"""
        logger.info("Starting keep-alive tasks")
        
        # Start ping task
        if self._ping_task:
            self._ping_task.cancel()
        self._ping_task = asyncio.create_task(self._ping_loop())
        
        # Start reconnection monitor
        if self._reconnect_task:
            self._reconnect_task.cancel()
        self._reconnect_task = asyncio.create_task(self._reconnection_monitor())
    
    async def _ping_loop(self):
        """Send periodic pings to keep connection alive"""
        while self.is_connected and self._websocket:
            try:
                await self._websocket.send_message('42["ps"]')
                self._connection_stats['last_ping_time'] = time.time()
                self._connection_stats['messages_sent'] += 1
                await asyncio.sleep(20)  # Ping every 20 seconds
            except Exception as e:
                logger.warning(f"Ping failed: {e}")
                self.is_connected = False
    
    async def _reconnection_monitor(self):
        """Monitor and reconnect if connection is lost"""
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            if not self.is_connected or not self._websocket or not self._websocket.is_connected:
                logger.info("Connection lost, reconnecting...")
                self.is_connected = False
                
                # Try to reconnect
                success = await self.connect_with_keep_alive()
                
                if success:
                    self._connection_stats['total_reconnections'] += 1
                    logger.info("Reconnection successful")
                    await self._trigger_event_async('reconnected')
                else:
                    logger.error("Reconnection failed")
                    await asyncio.sleep(10)  # Wait before next attempt
    
    async def disconnect(self):
        """Disconnect and clean up resources"""
        logger.info("Disconnecting...")
        
        # Cancel tasks
        if self._ping_task:
            self._ping_task.cancel()
        if self._reconnect_task:
            self._reconnect_task.cancel()
        
        # Disconnect websocket
        if self._websocket:
            await self._websocket.disconnect()
        
        self.is_connected = False
        logger.info("Disconnected")
        await self._trigger_event_async('disconnected')
    
    async def send_message(self, message):
        """Send WebSocket message"""
        if not self.is_connected or not self._websocket:
            raise ConnectionError("Not connected")
            
        await self._websocket.send_message(message)
        self._connection_stats['messages_sent'] += 1
    
    async def on_message(self, message):
        """Handle WebSocket message"""
        self._connection_stats['messages_received'] += 1
        await self._trigger_event_async('message_received', message)
