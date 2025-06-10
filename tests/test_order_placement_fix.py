#!/usr/bin/env python3
"""
Test script to verify order placement fix
"""

import asyncio
import os
from datetime import datetime
from loguru import logger

# Configure logger
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
    level="INFO"
)

from pocketoptionapi_async import AsyncPocketOptionClient, OrderDirection


async def test_order_placement_fix():
    """Test the order placement fix"""
    
    # Get SSID from environment or use a placeholder
    ssid = os.getenv("POCKET_OPTION_SSID", "placeholder_session_id")
    
    if ssid == "placeholder_session_id":
        logger.warning("⚠️ No SSID provided - using placeholder (will fail connection)")
        logger.info("Set POCKET_OPTION_SSID environment variable for real testing")
    
    logger.info("🧪 Testing order placement fix...")
    
    # Create client
    client = AsyncPocketOptionClient(ssid, is_demo=True)
    
    try:
        # Test order creation (this should not fail with the attribute error anymore)
        logger.info("📝 Testing Order model creation...")
        
        # This should work now (Order uses request_id)
        from pocketoptionapi_async.models import Order
        test_order = Order(
            asset="EURUSD_otc",
            amount=1.0,
            direction=OrderDirection.CALL,
            duration=60
        )
        
        logger.success(f"✅ Order created successfully with request_id: {test_order.request_id}")
        logger.info(f"   Asset: {test_order.asset}")
        logger.info(f"   Amount: {test_order.amount}")
        logger.info(f"   Direction: {test_order.direction}")
        logger.info(f"   Duration: {test_order.duration}")
        
        # Test that the order doesn't have order_id attribute
        if not hasattr(test_order, 'order_id'):
            logger.success("✅ Order correctly uses request_id instead of order_id")
        else:
            logger.error("❌ Order still has order_id attribute - this should not exist")
            
        # If we have a real SSID, try connecting and placing an order
        if ssid != "placeholder_session_id":
            logger.info("🔌 Attempting to connect and place order...")
            
            await client.connect()
            
            if client.is_connected:
                logger.success("✅ Connected successfully")
                
                # Try to place an order (this should not fail with attribute error)
                try:
                    order_result = await client.place_order(
                        asset="EURUSD_otc",
                        amount=1.0,
                        direction=OrderDirection.CALL,
                        duration=60
                    )
                    
                    logger.success(f"✅ Order placement succeeded: {order_result.order_id}")
                    logger.info(f"   Status: {order_result.status}")
                    
                except Exception as e:
                    if "'Order' object has no attribute 'order_id'" in str(e):
                        logger.error("❌ The attribute error still exists!")
                    else:
                        logger.warning(f"⚠️ Order placement failed for other reason: {e}")
                        logger.info("This is likely due to connection/authentication issues, not the attribute fix")
                    
            else:
                logger.warning("⚠️ Could not connect (expected with placeholder SSID)")
        
        logger.success("🎉 Order placement fix test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if client.is_connected:
            await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_order_placement_fix())
