import httpx
import asyncio
import logging
from config import Config
from dotenv import load_dotenv  # إضافة لتحميل .env

# تحميل المتغيرات من .env
load_dotenv()

class PriceFetcher:
    _cache: dict = {}
    _expiry: float = 0
    _ttl: int = 300  # ثواني

    def __init__(self, cfg: Config):
        self.url = cfg.COINGECKO_URL

    async def fetch(self) -> dict:
        now = asyncio.get_event_loop().time()
        if PriceFetcher._cache and now < PriceFetcher._expiry:
            return PriceFetcher._cache
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.url)
            data = resp.json() if resp.status_code == 200 else {}
        PriceFetcher._cache = data
        PriceFetcher._expiry = now + self._ttl
        logging.info("Fetched prices from CoinGecko")
        return data