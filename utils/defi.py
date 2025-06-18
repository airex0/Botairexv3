import httpx
import logging
from config import Config
from dotenv import load_dotenv  # إضافة لتحميل .env

# تحميل المتغيرات من .env
load_dotenv()

class DeFiFetcher:
    def __init__(self, cfg: Config):
        self.url_template = cfg.COVALENT_DEFI_URL

    async def fetch_positions(self, address: str, chain_id: int):
        url = self.url_template.format(chain_id=chain_id, address=address)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url)
            data = r.json().get("data",{}).get("items",[])
            logging.info(f"DeFi positions fetched for {address} on {chain_id}")
            return data
        except Exception as e:
            logging.warning(f"DeFi fetch failed: {e}")
            return []