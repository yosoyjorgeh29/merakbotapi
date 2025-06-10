"""
Migration script to convert old PocketOption API usage to new async API
"""

import asyncio
import time
from datetime import datetime
from typing import Optional

# Import the old API for comparison
try:
    from pocketoptionapi.stable_api import PocketOption as OldPocketOption
except ImportError:
    print("Old API not found, continuing with migration guide only")
    OldPocketOption = None

# Import the new async API
from pocketoptionapi_async import (
    AsyncPocketOptionClient,
    OrderDirection,
    OrderStatus,
    PocketOptionError
)


class PocketOptionMigrationWrapper:
    """
    Wrapper class to help migrate from old sync API to new async API
    Provides similar interface to old API but with async implementation
    """
    
    def __init__(self, ssid: str, demo: bool = True):
        """
        Initialize migration wrapper
        
        Args:
            ssid: Session ID
            demo: Whether to use demo account
        """
        self.ssid = ssid
        self.demo = demo
        self.client = AsyncPocketOptionClient(
            session_id=ssid,
            is_demo=demo
        )
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to PocketOption (async version of old connect())"""
        try:
            await self.client.connect()
            self._connected = True
            print("✅ Connected successfully")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from PocketOption"""
        if self._connected:
            await self.client.disconnect()
            self._connected = False
            print("✅ Disconnected successfully")
    
    def check_connect(self) -> bool:
        """Check if connected (similar to old API)"""
        return self.client.is_connected
    
    async def get_balance(self) -> Optional[float]:
        """Get balance (async version)"""
        try:
            balance = await self.client.get_balance()
            return balance.balance
        except Exception as e:
            print(f"❌ Failed to get balance: {e}")
            return None
    
    async def buy(self, amount: float, active: str, action: str, 
                  expirations: int) -> tuple[bool, Optional[str]]:
        """
        Place order (async version of old buy method)
        
        Returns:
            tuple: (success, order_id)
        """
        try:
            # Convert action to OrderDirection
            direction = OrderDirection.CALL if action.lower() == "call" else OrderDirection.PUT
            
            # Place order
            result = await self.client.place_order(
                asset=active,
                amount=amount,
                direction=direction,
                duration=expirations
            )
            
            return True, result.order_id
            
        except Exception as e:
            print(f"❌ Order failed: {e}")
            return False, None
    
    async def check_win(self, order_id: str) -> tuple[Optional[float], str]:
        """
        Check order result (async version)
        
        Returns:
            tuple: (profit, status)
        """
        try:
            # Wait for order completion
            max_wait = 300  # 5 minutes
            wait_time = 0
            
            while wait_time < max_wait:
                result = await self.client.check_order_result(order_id)
                
                if result and result.status in [OrderStatus.WIN, OrderStatus.LOSE]:
                    status = "win" if result.status == OrderStatus.WIN else "lose"
                    return result.profit, status
                
                await asyncio.sleep(1)
                wait_time += 1
            
            return None, "timeout"
            
        except Exception as e:
            print(f"❌ Failed to check order result: {e}")
            return None, "error"
    
    async def get_candles(self, active: str, period: int, count: int = 100) -> list:
        """
        Get candles data (async version)
        
        Args:
            active: Asset symbol
            period: Period in seconds
            count: Number of candles
            
        Returns:
            list: Candle data
        """
        try:
            candles = await self.client.get_candles(
                asset=active,
                timeframe=period,
                count=count
            )
            
            # Convert to old format for compatibility
            result = []
            for candle in candles:
                result.append({
                    'time': int(candle.timestamp.timestamp()),
                    'open': candle.open,
                    'high': candle.high,
                    'low': candle.low,
                    'close': candle.close,
                    'asset': candle.asset
                })
            
            return result
            
        except Exception as e:
            print(f"❌ Failed to get candles: {e}")
            return []
    
    # Context manager support
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


async def migration_example_old_style():
    """
    Example showing how to migrate old-style code to new async API
    This maintains similar interface to old API
    """
    
    ssid = "your_session_id_here"
    
    # Old style with new async implementation
    async with PocketOptionMigrationWrapper(ssid, demo=True) as api:
        
        print("=== Old-Style API with Async Implementation ===")
        
        # Check connection (similar to old API)
        if api.check_connect():
            print("✅ Connected successfully")
        
        # Get balance (similar to old API)
        balance = await api.get_balance()
        if balance:
            print(f"💰 Balance: ${balance:.2f}")
        
        # Place order (similar to old API)
        success, order_id = await api.buy(
            amount=1.0,
            active="EURUSD_otc",
            action="call",
            expirations=60
        )
        
        if success and order_id:
            print(f"📈 Order placed: {order_id}")
            
            # Check result (similar to old API)
            profit, status = await api.check_win(order_id)
            if profit is not None:
                print(f"💰 Result: {status} - Profit: ${profit:.2f}")
        
        # Get candles (similar to old API)
        candles = await api.get_candles("EURUSD_otc", 60, 10)
        if candles:
            print(f"📊 Retrieved {len(candles)} candles")
            print(f"    Last price: {candles[-1]['close']}")


async def migration_example_new_style():
    """
    Example showing the recommended new async API usage
    """
    
    ssid = "your_session_id_here"
    
    print("\n=== New Modern Async API ===")
    
    # Modern async approach
    async with AsyncPocketOptionClient(ssid, is_demo=True) as client:
        
        # Add event callbacks for real-time updates
        def on_balance_updated(balance):
            print(f"💰 Balance updated: ${balance.balance:.2f}")
        
        def on_order_closed(order_result):
            status = "WIN" if order_result.status == OrderStatus.WIN else "LOSE"
            print(f"📊 Order {order_result.order_id}: {status} - Profit: ${order_result.profit:.2f}")
        
        client.add_event_callback('balance_updated', on_balance_updated)
        client.add_event_callback('order_closed', on_order_closed)
        
        # Get balance with proper error handling
        try:
            balance = await client.get_balance()
            print(f"💰 Current balance: ${balance.balance:.2f}")
            
            # Get candles with DataFrame support
            df = await client.get_candles_dataframe(
                asset="EURUSD_otc",
                timeframe="1m",
                count=50
            )
            print(f"📊 Retrieved DataFrame with {len(df)} rows")
            
            # Place order with modern error handling
            order_result = await client.place_order(
                asset="EURUSD_otc",
                amount=1.0,
                direction=OrderDirection.CALL,
                duration=60
            )
            
            print(f"📈 Order placed: {order_result.order_id}")
            print(f"    Status: {order_result.status}")
            print(f"    Expires at: {order_result.expires_at}")
            
        except PocketOptionError as e:
            print(f"❌ API Error: {e.message}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


async def side_by_side_comparison():
    """Show side-by-side comparison of old vs new API"""
    
    print("\n" + "="*60)
    print("MIGRATION COMPARISON")
    print("="*60)
    
    print("\n📝 OLD SYNCHRONOUS API:")
    print("""
    from pocketoptionapi.stable_api import PocketOption
    
    # Initialize
    api = PocketOption(ssid, demo=True)
    api.connect()
    
    # Get balance
    balance = api.get_balance()
    
    # Place order
    success, order_id = api.buy(1.0, "EURUSD_otc", "call", 60)
    
    # Check result
    profit, status = api.check_win(order_id)
    
    # Get candles
    candles = api.get_candles("EURUSD_otc", 60, 100)
    
    # Cleanup
    api.disconnect()
    """)
    
    print("\n🚀 NEW ASYNC API:")
    print("""
    from pocketoptionapi_async import AsyncPocketOptionClient, OrderDirection
    
    async def main():
        # Context manager handles connection/cleanup
        async with AsyncPocketOptionClient(ssid, is_demo=True) as client:
            
            # Get balance
            balance = await client.get_balance()
            
            # Place order
            order_result = await client.place_order(
                asset="EURUSD_otc",
                amount=1.0,
                direction=OrderDirection.CALL,
                duration=60
            )
            
            # Get candles (with DataFrame support)
            df = await client.get_candles_dataframe(
                asset="EURUSD_otc",
                timeframe="1m",
                count=100
            )
            
            # Event-driven order monitoring
            def on_order_closed(result):
                print(f"Order closed: {result.profit}")
            
            client.add_event_callback('order_closed', on_order_closed)
    
    asyncio.run(main())
    """)
    
    print("\n✅ KEY IMPROVEMENTS:")
    print("- 100% async/await support")
    print("- Type safety with Pydantic models")
    print("- Automatic connection management")
    print("- Event-driven architecture")
    print("- pandas DataFrame integration")
    print("- Professional error handling")
    print("- Built-in rate limiting")
    print("- Comprehensive testing")


def print_migration_checklist():
    """Print migration checklist"""
    
    print("\n" + "="*60)
    print("MIGRATION CHECKLIST")
    print("="*60)
    
    checklist = [
        "✅ Install new dependencies (pip install -r requirements.txt)",
        "✅ Update imports to use pocketoptionapi_async",
        "✅ Convert functions to async/await",
        "✅ Use context managers for connection management",
        "✅ Replace string directions with OrderDirection enum",
        "✅ Update error handling to use custom exceptions",
        "✅ Consider using event callbacks for real-time updates",
        "✅ Migrate to DataFrame for candle data analysis",
        "✅ Update test cases for async functionality",
        "✅ Review and update logging configuration"
    ]
    
    for item in checklist:
        print(f"  {item}")
    
    print("\n💡 TIPS:")
    print("- Start by wrapping existing code with migration wrapper")
    print("- Gradually refactor to use modern async patterns")
    print("- Use type hints for better code quality")
    print("- Implement proper error handling strategies")
    print("- Test thoroughly with demo account first")


async def main():
    """Main migration demonstration"""
    
    print("🔄 POCKETOPTION API MIGRATION GUIDE")
    print("="*50)
    
    # Show side-by-side comparison
    side_by_side_comparison()
    
    # Print migration checklist
    print_migration_checklist()
    
    print("\n🚀 RUNNING MIGRATION EXAMPLES...")
    
    # Note: Replace with actual session ID for testing
    print("\n⚠️  To run live examples, set your session ID in the code")
    print("   Examples will show structure without making actual API calls")
    
    # You can uncomment these to test with real session ID
    # await migration_example_old_style()
    # await migration_example_new_style()
    
    print("\n✅ Migration guide completed!")
    print("📖 Check README_ASYNC.md for comprehensive documentation")


if __name__ == "__main__":
    asyncio.run(main())
