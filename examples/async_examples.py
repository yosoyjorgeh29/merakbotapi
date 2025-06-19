"""
Example usage of the Professional Async PocketOption API
"""

import asyncio
import os
from loguru import logger

# Configure logging
logger.add("pocketoption.log", rotation="1 day", retention="7 days", level="INFO")

from pocketoptionapi_async import (
    AsyncPocketOptionClient,
    OrderDirection,
    PocketOptionError,
    ConnectionError,
    OrderError,
)
from pocketoptionapi_async.utils import fetch_ssid


async def basic_example():
    """Basic example of using the async API"""

    # Replace with your actual session ID
    session_id = os.getenv("POCKET_OPTION_SSID", "your_session_id_here")

    # Create client
    client = AsyncPocketOptionClient(
        session_id=session_id,
        is_demo=True,  # Use demo account
        timeout=30.0,
    )

    try:
        # Connect to PocketOption
        logger.info("Connecting to PocketOption...")
        await client.connect()

        # Get account balance
        balance = await client.get_balance()
        logger.info(f"Current balance: ${balance.balance:.2f} ({balance.currency})")

        # Get historical data
        logger.info("Fetching candle data...")
        candles = await client.get_candles(
            asset="EURUSD_otc", timeframe="1m", count=100
        )
        logger.info(f"Retrieved {len(candles)} candles")

        # Get data as DataFrame
        df = await client.get_candles_dataframe(
            asset="EURUSD_otc", timeframe="5m", count=50
        )
        logger.info(f"DataFrame shape: {df.shape}")

        # Place a demo order
        if balance.balance > 10:  # Ensure sufficient balance
            logger.info("Placing demo order...")

            order_result = await client.place_order(
                asset="EURUSD_otc",
                amount=1.0,  # $1 minimum
                direction=OrderDirection.CALL,
                duration=60,  # 60 seconds
            )

            logger.info(f"Order placed: {order_result.order_id}")
            logger.info(f"Order status: {order_result.status}")

            # Wait for order to complete (in real trading, use callbacks)
            logger.info("Waiting for order to complete...")
            await asyncio.sleep(65)  # Wait slightly longer than duration

            # Check order result
            result = await client.check_order_result(order_result.order_id)
            if result:
                logger.info(f"Order completed: {result.status}")
                if result.profit:
                    logger.info(f"Profit/Loss: ${result.profit:.2f}")

    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
    except OrderError as e:
        logger.error(f"Order failed: {e}")
    except PocketOptionError as e:
        logger.error(f"API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Always disconnect
        await client.disconnect()
        logger.info("Disconnected from PocketOption")


async def context_manager_example():
    """Example using async context manager"""

    session_id = os.getenv("POCKET_OPTION_SSID", "your_session_id_here")

    try:
        # Use async context manager (automatically connects and disconnects)
        async with AsyncPocketOptionClient(session_id, is_demo=True) as client:
            # Add event callbacks
            def on_balance_updated(balance):
                logger.info(f"Balance updated: ${balance.balance:.2f}")

            def on_order_closed(order_result):
                logger.info(
                    f"Order {order_result.order_id} closed with profit: ${order_result.profit:.2f}"
                )

            client.add_event_callback("balance_updated", on_balance_updated)
            client.add_event_callback("order_closed", on_order_closed)

            # Get balance
            balance = await client.get_balance()
            logger.info(f"Account balance: ${balance.balance:.2f}")

            # Get historical data for multiple assets
            assets = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc"]

            for asset in assets:
                try:
                    candles = await client.get_candles(asset, "1m", 50)
                    logger.info(f"{asset}: {len(candles)} candles retrieved")

                    if candles:
                        last_price = candles[-1].close
                        logger.info(f"{asset} last price: {last_price}")

                except Exception as e:
                    logger.error(f"Error getting candles for {asset}: {e}")

    except Exception as e:
        logger.error(f"Error in context manager example: {e}")


async def multiple_orders_example():
    """Example of managing multiple orders"""

    session_id = os.getenv("POCKET_OPTION_SSID", "your_session_id_here")

    async with AsyncPocketOptionClient(session_id, is_demo=True) as client:
        balance = await client.get_balance()
        logger.info(f"Starting balance: ${balance.balance:.2f}")

        if balance.balance < 10:
            logger.warning("Insufficient balance for multiple orders")
            return

        # Place multiple orders
        orders = []
        assets = ["EURUSD_otc", "GBPUSD_otc"]

        for asset in assets:
            try:
                # Alternate between CALL and PUT
                direction = (
                    OrderDirection.CALL if len(orders) % 2 == 0 else OrderDirection.PUT
                )

                order_result = await client.place_order(
                    asset=asset,
                    amount=1.0,
                    direction=direction,
                    duration=120,  # 2 minutes
                )

                orders.append(order_result)
                logger.info(
                    f"Placed {direction.value} order for {asset}: {order_result.order_id}"
                )

            except Exception as e:
                logger.error(f"Failed to place order for {asset}: {e}")

        # Monitor active orders
        while True:
            active_orders = await client.get_active_orders()

            if not active_orders:
                logger.info("All orders completed")
                break

            logger.info(f"Active orders: {len(active_orders)}")
            await asyncio.sleep(5)  # Check every 5 seconds

        # Check all order results
        total_profit = 0
        for order in orders:
            result = await client.check_order_result(order.order_id)
            if result and result.profit is not None:
                total_profit += result.profit
                logger.info(
                    f"Order {order.order_id}: {result.status} - Profit: ${result.profit:.2f}"
                )

        logger.info(f"Total profit/loss: ${total_profit:.2f}")


async def real_time_monitoring_example():
    """Example of real-time monitoring and automated trading"""

    session_id = os.getenv("POCKET_OPTION_SSID", "your_session_id_here")

    async with AsyncPocketOptionClient(session_id, is_demo=True) as client:
        # Track price movements
        asset = "EURUSD_otc"
        last_price = None
        price_history = []

        # Simple trading strategy: buy when price moves significantly
        async def simple_strategy():
            nonlocal last_price, price_history

            try:
                # Get recent candles
                candles = await client.get_candles(asset, "1m", 5)

                if not candles:
                    return

                current_price = candles[-1].close
                price_history.append(current_price)

                # Keep only last 10 prices
                if len(price_history) > 10:
                    price_history.pop(0)

                logger.info(f"{asset} current price: {current_price}")

                # Simple strategy: if price moved more than 0.01% in last 5 minutes
                if len(price_history) >= 5:
                    price_change = (
                        (current_price - price_history[0]) / price_history[0]
                    ) * 100

                    logger.info(f"Price change: {price_change:.3f}%")

                    # Only trade if change is significant and we have sufficient balance
                    if abs(price_change) > 0.01:  # 0.01% threshold
                        balance = await client.get_balance()

                        if balance.balance > 5:
                            direction = (
                                OrderDirection.CALL
                                if price_change > 0
                                else OrderDirection.PUT
                            )

                            try:
                                order = await client.place_order(
                                    asset=asset,
                                    amount=1.0,
                                    direction=direction,
                                    duration=60,
                                )

                                logger.info(
                                    f"Strategy triggered: {direction.value} order placed: {order.order_id}"
                                )

                            except Exception as e:
                                logger.error(f"Failed to place strategy order: {e}")

                last_price = current_price

            except Exception as e:
                logger.error(f"Error in strategy: {e}")

        # Run strategy every 30 seconds for 5 minutes
        logger.info("Starting real-time monitoring...")

        for i in range(10):  # 10 iterations = 5 minutes
            await simple_strategy()
            await asyncio.sleep(30)

        logger.info("Real-time monitoring completed")


if __name__ == "__main__":
    # Set your session ID in environment variable or directly here
    # export POCKET_OPTION_SSID="your_actual_session_id"

    print("Choose an example to run:")
    print("1. Basic example")
    print("2. Context manager example")
    print("3. Multiple orders example")
    print("4. Real-time monitoring example")

    choice = input("Enter choice (1-4): ").strip()

    if choice == "1":
        asyncio.run(basic_example())
    elif choice == "2":
        asyncio.run(context_manager_example())
    elif choice == "3":
        asyncio.run(multiple_orders_example())
    elif choice == "4":
        asyncio.run(real_time_monitoring_example())
    else:
        print("Invalid choice. Running basic example...")
        asyncio.run(basic_example())
