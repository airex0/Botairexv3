import os
import httpx
import logging
from config import Config
from dotenv import load_dotenv  # إضافة لتحميل .env

# تحميل المتغيرات من .env
load_dotenv()

class RiskScanner:
    def __init__(self, cfg: Config):
        self.networks = cfg.NETWORKS

    async def fetch_approvals(self, address: str, chain_key: str):
        api_url = {
            "Ethereum": "https://api.etherscan.io/api",
            "BSC":      "https://api.bscscan.com/api",
        }.get(chain_key)
        if not api_url:
            return []
        params = {"module":"account","action":"tokentx","address":address,"sort":"desc"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(api_url, params=params)
            return r.json().get("result",[])
        except Exception as e:
            logging.warning(f"Risk scan failed: {e}")
            return []