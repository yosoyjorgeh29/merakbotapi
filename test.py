import random
import time
import dotenv
from pocketoptionapi_async import AsyncPocketOptionClient
import logging
import os
import time

dotenv.load_dotenv()

ssid = (r'42["auth",{"session":"t04ppgptp3404h0lajp4bo7smh","isDemo":1,"uid":101884312,"platform":2,"isFastHistory":true}]') #os.getenv("SSID")
print(ssid)
api = AsyncPocketOptionClient(ssid=ssid, is_demo=True)
async def main():
    await api.connect()

    await asyncio.sleep(5)  # Wait for connection to establish

    balance = await api.get_balance()
    print(f"Balance: {balance}")

    # order_Data = await api.place_order(
    #     asset="EURUSD_otc",
    #     amount=1,
    #     direction="call",
    #     duration=5
    # )
    # print(f"OrderData: {order_Data}")
    # order_info = await api.check_order_result(order_Data.order_id)
    # print(f"OrderInfo: {order_info}")

    candles = await api.get_candles(
        asset="EURUSD_otc",
        period=5,
        count=100
    )
    print(candles)

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Closing connection...")