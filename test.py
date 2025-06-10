import random
import time
import dotenv
from pocketoptionapi_async import AsyncPocketOptionClient
import logging
import os
import time

dotenv.load_dotenv()

ssid = (r'42["auth",{"session":"n1p5ah5u8t9438rbunpgrq0hlq","isDemo":1,"uid":72645361,"platform":1,"isFastHistory":true}]') #os.getenv("SSID")
print(ssid)
api = AsyncPocketOptionClient(ssid=ssid, is_demo=True)
async def main():
    await api.connect()

    await asyncio.sleep(5)  # Wait for connection to establish

    balance = await api.get_balance()
    print(f"Balance: {balance}")

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