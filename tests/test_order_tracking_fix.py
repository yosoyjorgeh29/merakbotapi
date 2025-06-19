#!/usr/bin/env python3
"""
Test Order Tracking Fix
Test to verify that order tracking and result checking works properly
"""

import asyncio
import os
from datetime import datetime
from loguru import logger

from pocketoptionapi_async import AsyncPocketOptionClient, OrderDirection


async def test_order_tracking():
    """Test order tracking functionality"""

    # Get SSID from environment or use placeholder
    ssid = os.getenv("POCKET_OPTION_SSID", "your_session_id_here")

    if ssid == "your_session_id_here":
        print("❌ Please set POCKET_OPTION_SSID environment variable")
        return

    print("🚀 Testing Order Tracking Fix...")

    # Create client
    client = AsyncPocketOptionClient(ssid, is_demo=True)

    try:
        # Connect
        print("📡 Connecting...")
        await client.connect()

        if not client.is_connected:
            print("❌ Failed to connect")
            return

        print("✅ Connected successfully")

        # Wait for initialization
        await asyncio.sleep(3)

        # Get balance
        balance = await client.get_balance()
        if balance:
            print(f"💰 Balance: ${balance.balance:.2f} (Demo: {balance.is_demo})")
        else:
            print("⚠️ No balance received")

        # Place a test order
        print("\n🎯 Placing test order...")
        order_result = await client.place_order(
            asset="EURUSD_otc", amount=1.0, direction=OrderDirection.CALL, duration=60
        )

        print(f"📈 Order placed: {order_result.order_id}")
        print(f"   Status: {order_result.status}")
        print(f"   Asset: {order_result.asset}")
        print(f"   Amount: ${order_result.amount}")
        print(f"   Direction: {order_result.direction}")
        print(f"   Duration: {order_result.duration}s")

        # Test order result checking - should return the active order immediately
        print("\n🔍 Checking order result immediately...")
        immediate_result = await client.check_order_result(order_result.order_id)

        if immediate_result:
            print("✅ Order found in tracking system:")
            print(f"   Order ID: {immediate_result.order_id}")
            print(f"   Status: {immediate_result.status}")
            print(f"   Placed at: {immediate_result.placed_at}")
            print(f"   Expires at: {immediate_result.expires_at}")
        else:
            print("❌ Order NOT found in tracking system")
            return

        # Check active orders
        print("\n📊 Checking active orders...")
        active_orders = await client.get_active_orders()
        print(f"Active orders count: {len(active_orders)}")

        for order in active_orders:
            print(f"   - {order.order_id}: {order.status} ({order.asset})")

        # Test tracking over time
        print("\n⏱️ Monitoring order for 30 seconds...")
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < 30:
            result = await client.check_order_result(order_result.order_id)

            if result:
                status_emoji = (
                    "🟢"
                    if result.status == "active"
                    else "🔴"
                    if result.status in ["win", "lose"]
                    else "🟡"
                )
                print(f"   {status_emoji} Order {result.order_id}: {result.status}")

                # If order completed, show result
                if result.profit is not None:
                    win_lose = "WIN" if result.profit > 0 else "LOSE"
                    print(
                        f"   🎯 Final result: {win_lose} - Profit: ${result.profit:.2f}"
                    )
                    break
            else:
                print("   ❌ Order not found in tracking")
                break

            await asyncio.sleep(5)  # Check every 5 seconds

        # Final status
        final_result = await client.check_order_result(order_result.order_id)
        if final_result:
            print(f"\n📋 Final order status: {final_result.status}")
            if final_result.profit is not None:
                print(f"💰 Profit/Loss: ${final_result.profit:.2f}")
            else:
                print("💰 Profit/Loss: Not yet determined")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Disconnect
        print("\n🔌 Disconnecting...")
        await client.disconnect()
        print("✅ Test completed")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<level>{level}</level> | {message}",
        level="INFO",
    )

    asyncio.run(test_order_tracking())
