# Professional Async PocketOption API

A complete rewrite of the PocketOption API with 100% async support and professional Python practices.

## 🚀 Features

- **100% Async/Await Support**: Built from ground up with asyncio
- **Type Safety**: Full type hints with Pydantic models
- **Professional Code Quality**: Following Python best practices
- **Comprehensive Error Handling**: Custom exceptions with detailed error information
- **Real-time WebSocket**: Efficient async WebSocket client with automatic reconnection
- **Rate Limiting**: Built-in rate limiting to prevent API abuse
- **Context Manager Support**: Easy resource management with async context managers
- **Extensive Testing**: Comprehensive test suite with pytest
- **Rich Logging**: Structured logging with loguru
- **Modern Python**: Requires Python 3.8+

## 📦 Installation

```bash
# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements.txt pytest pytest-asyncio
```

## 🔧 Quick Start

### Basic Usage

```python
import asyncio
from pocketoptionapi_async import AsyncPocketOptionClient, OrderDirection

async def main():
    # Initialize client
    client = AsyncPocketOptionClient(
        session_id="your_session_id_here",
        is_demo=True  # Use demo account
    )
    
    try:
        # Connect to PocketOption
        await client.connect()
        
        # Get account balance
        balance = await client.get_balance()
        print(f"Balance: ${balance.balance:.2f}")
        
        # Get historical data
        candles = await client.get_candles(
            asset="EURUSD_otc",
            timeframe="1m",
            count=100
        )
        print(f"Retrieved {len(candles)} candles")
        
        # Place an order
        order_result = await client.place_order(
            asset="EURUSD_otc",
            amount=1.0,
            direction=OrderDirection.CALL,
            duration=60
        )
        print(f"Order placed: {order_result.order_id}")
        
    finally:
        await client.disconnect()

# Run the example
asyncio.run(main())
```

### Using Context Manager

```python
async def context_example():
    session_id = "your_session_id_here"
    
    # Automatic connection and cleanup
    async with AsyncPocketOptionClient(session_id, is_demo=True) as client:
        
        # Add event callbacks
        def on_order_closed(order_result):
            print(f"Order closed with profit: ${order_result.profit:.2f}")
        
        client.add_event_callback('order_closed', on_order_closed)
        
        # Your trading logic here
        balance = await client.get_balance()
        print(f"Balance: ${balance.balance:.2f}")

asyncio.run(context_example())
```

### Advanced Example with DataFrame

```python
import pandas as pd

async def dataframe_example():
    async with AsyncPocketOptionClient("your_session_id", is_demo=True) as client:
        
        # Get data as pandas DataFrame
        df = await client.get_candles_dataframe(
            asset="EURUSD_otc",
            timeframe="5m",
            count=200
        )
        
        # Technical analysis
        df['sma_20'] = df['close'].rolling(20).mean()
        df['rsi'] = calculate_rsi(df['close'])  # Your TA function
        
        # Simple trading signal
        if df['close'].iloc[-1] > df['sma_20'].iloc[-1]:
            order = await client.place_order(
                asset="EURUSD_otc",
                amount=1.0,
                direction=OrderDirection.CALL,
                duration=300
            )
            print(f"Signal: BUY - Order: {order.order_id}")

asyncio.run(dataframe_example())
```

## 📊 Available Assets

The API supports 100+ assets including:

- **Forex**: EURUSD, GBPUSD, USDJPY, etc.
- **Cryptocurrencies**: BTCUSD, ETHUSD, etc.
- **Commodities**: Gold (XAUUSD), Silver (XAGUSD), Oil, etc.
- **Indices**: SP500, NASDAQ, DAX, etc.
- **Stocks**: Apple, Microsoft, Tesla, etc.

See `constants.py` for the complete list.

## 🔧 Configuration

### Environment Variables

```bash
# Set your session ID
export POCKET_OPTION_SSID="your_actual_session_id"

# Optional: Set log level
export LOG_LEVEL="INFO"
```

### Session ID

To get your session ID:
1. Login to PocketOption in your browser
2. Open Developer Tools (F12)
3. Go to Network tab
4. Look for WebSocket connections
5. Find the auth message containing your session ID

## 🎯 API Reference

### AsyncPocketOptionClient

#### Constructor
```python
client = AsyncPocketOptionClient(
    session_id: str,          # Your PocketOption session ID
    is_demo: bool = True,     # Use demo account
    timeout: float = 30.0     # Default timeout for operations
)
```

#### Connection Methods
```python
await client.connect(regions: List[str] = None)  # Connect to WebSocket
await client.disconnect()                        # Disconnect
client.is_connected -> bool                      # Check connection status
```

#### Trading Methods
```python
# Get balance
balance = await client.get_balance()

# Place order
order_result = await client.place_order(
    asset: str,                    # Asset symbol
    amount: float,                 # Order amount
    direction: OrderDirection,     # CALL or PUT
    duration: int                  # Duration in seconds
)

# Check order result
result = await client.check_order_result(order_id: str)

# Get active orders
active_orders = await client.get_active_orders()
```

#### Data Methods
```python
# Get candles
candles = await client.get_candles(
    asset: str,                    # Asset symbol
    timeframe: Union[str, int],    # '1m', '5m', '1h' or seconds
    count: int = 100,              # Number of candles
    end_time: datetime = None      # End time (default: now)
)

# Get candles as DataFrame
df = await client.get_candles_dataframe(
    asset: str,
    timeframe: Union[str, int],
    count: int = 100,
    end_time: datetime = None
)
```

#### Event Callbacks
```python
# Add event callback
client.add_event_callback(event: str, callback: Callable)

# Remove event callback
client.remove_event_callback(event: str, callback: Callable)
```

### Available Events

- `authenticated`: Authentication successful
- `balance_updated`: Balance changed
- `order_opened`: Order placed successfully
- `order_closed`: Order completed
- `disconnected`: WebSocket disconnected

### Models

#### Balance
```python
balance = Balance(
    balance: float,               # Account balance
    currency: str = "USD",        # Currency
    is_demo: bool = True,         # Demo account flag
    last_updated: datetime        # Last update time
)
```

#### Order
```python
order = Order(
    asset: str,                   # Asset symbol
    amount: float,                # Order amount
    direction: OrderDirection,    # CALL or PUT
    duration: int,                # Duration in seconds
    request_id: str = None        # Auto-generated if None
)
```

#### OrderResult
```python
result = OrderResult(
    order_id: str,                # Order ID
    asset: str,                   # Asset symbol
    amount: float,                # Order amount
    direction: OrderDirection,    # CALL or PUT
    duration: int,                # Duration in seconds
    status: OrderStatus,          # Order status
    placed_at: datetime,          # Placement time
    expires_at: datetime,         # Expiration time
    profit: float = None,         # Profit/loss
    payout: float = None          # Payout amount
)
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=pocketoptionapi_async --cov-report=html

# Run specific test
python -m pytest tests/test_async_api.py::TestAsyncPocketOptionClient::test_connect_success -v
```

## 📝 Examples

Check the `examples/` directory for comprehensive examples:

- `async_examples.py`: Basic usage examples
- Advanced trading strategies
- Real-time monitoring
- Multiple order management

## 🔒 Error Handling

The API uses custom exceptions for better error handling:

```python
from pocketoptionapi_async import (
    PocketOptionError,      # Base exception
    ConnectionError,        # Connection issues
    AuthenticationError,    # Auth failures
    OrderError,            # Order problems
    TimeoutError,          # Operation timeouts
    InvalidParameterError  # Invalid parameters
)

try:
    await client.place_order(...)
except OrderError as e:
    print(f"Order failed: {e.message}")
except ConnectionError as e:
    print(f"Connection issue: {e.message}")
```

## 🚨 Rate Limiting

The API includes built-in rate limiting:

```python
from pocketoptionapi_async.utils import RateLimiter

# Create rate limiter (100 calls per minute)
limiter = RateLimiter(max_calls=100, time_window=60)

# Use before API calls
await limiter.acquire()
await client.place_order(...)
```

## 🔧 Utilities

### Retry Decorator
```python
from pocketoptionapi_async.utils import retry_async

@retry_async(max_attempts=3, delay=1.0, backoff_factor=2.0)
async def unreliable_operation():
    # Your code here
    pass
```

### Performance Monitor
```python
from pocketoptionapi_async.utils import performance_monitor

@performance_monitor
async def monitored_function():
    # Execution time will be logged
    pass
```

## 📈 Migration from Old API

### Old Synchronous Code
```python
# Old way
from pocketoptionapi.stable_api import PocketOption

api = PocketOption(ssid)
api.connect()
balance = api.get_balance()
result, order_id = api.buy(1.0, "EURUSD_otc", "call", 60)
```

### New Async Code
```python
# New way
from pocketoptionapi_async import AsyncPocketOptionClient, OrderDirection

async def main():
    async with AsyncPocketOptionClient(ssid, is_demo=True) as client:
        balance = await client.get_balance()
        result = await client.place_order(
            asset="EURUSD_otc",
            amount=1.0,
            direction=OrderDirection.CALL,
            duration=60
        )

asyncio.run(main())
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational purposes only. Trading binary options involves significant risk. Always use demo accounts for testing and never trade with money you cannot afford to lose.

## 📞 Support

- Create an issue on GitHub
- Check the examples directory
- Read the comprehensive documentation
- Join our Discord community

## 🙏 Acknowledgments

- Original PocketOption API developers
- Python asyncio community
- Contributors and testers

---

**Happy Trading! 🚀**
