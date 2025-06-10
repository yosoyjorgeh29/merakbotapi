import random
import time
import dotenv
from pocketoptionapi_async import AsyncPocketOptionClient
import logging
import os
logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(message)s')

dotenv.load_dotenv()

ssid = (r'42["auth",{"session":"n1p5ah5u8t9438rbunpgrq0hlq","isDemo":1,"uid":72645361,"platform":1,"isFastHistory":true}]') #os.getenv("SSID")
print(ssid)
api = AsyncPocketOptionClient(ssid=ssid, is_demo=True)
