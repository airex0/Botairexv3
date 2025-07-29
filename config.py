import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import logging.handlers

# تحميل المتغيرات من .env (لبيئة التطوير المحلي)
load_dotenv()

class Config:
    def __init__(self,
                 env_path: str = ".env",
                 log_dir: str = "logs",
                 log_level: str = "INFO"):
        load_dotenv(dotenv_path=env_path)

        # تحميل المفاتيح البيئية
        self.ALCHEMY_KEY      = os.getenv("ALCHEMY_KEY", "")
        self.COVALENT_KEY     = os.getenv("COVALENT_KEY", "")
        self.OPENROUTER_KEY   = os.getenv("OPENROUTER_KEY", "")
        self.TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
        self.FERNET_KEY       = os.getenv("FERNET_KEY", "")

        self.NETWORKS = self._build_networks()

        self.COINGECKO_URL     = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,binancecoin,polygon,fantom,avalanche-2,arbitrum-one,optimism,solana,litecoin&vs_currencies=usd"
        self.COVALENT_TX_URL   = "https://api.covalenthq.com/v1/{chain_id}/address/{address}/transactions_v2/?key=" + self.COVALENT_KEY
        self.COVALENT_DEFI_URL = "https://api.covalenthq.com/v1/{chain_id}/address/{address}/portfolio_v2/?key=" + self.COVALENT_KEY

        self._setup_logging(log_dir, log_level)

    def _build_networks(self) -> dict:
        k = self.ALCHEMY_KEY
        return {
            "Ethereum":  {"rpc": f"https://eth-mainnet.g.alchemy.com/v2/{k}", "chain_id": 1},
            "BSC":       {"rpc": f"https://bsc-mainnet.g.alchemy.com/v2/{k}", "chain_id": 56},
            "Polygon":   {"rpc": f"https://polygon-mainnet.g.alchemy.com/v2/{k}", "chain_id": 137},
            "Fantom":    {"rpc": f"https://fantom-mainnet.g.alchemy.com/v2/{k}", "chain_id": 250},
            "Avalanche": {"rpc": f"https://avalanche-mainnet.g.alchemy.com/v2/{k}", "chain_id": 43114},
            "Arbitrum":  {"rpc": f"https://arb-mainnet.g.alchemy.com/v2/{k}", "chain_id": 42161},
            "Optimism":  {"rpc": f"https://opt-mainnet.g.alchemy.com/v2/{k}", "chain_id": 10},
            "Bitcoin":   {"api": "https://api.blockcypher.com/v1/btc/main/addrs", "chain_id": None},
            "Litecoin":  {"api": "https://api.blockcypher.com/v1/ltc/main/addrs", "chain_id": None},
            "Solana":    {"api": "https://api.mainnet-beta.solana.com", "chain_id": None},
        }

    def _setup_logging(self, log_dir: str, level: str):
        Path(log_dir).mkdir(exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            f"{log_dir}/app.log", maxBytes=5 * 1024 * 1024, backupCount=5
        )
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        handler.setFormatter(fmt)
        root = logging.getLogger()
        root.setLevel(getattr(logging, level.upper(), logging.INFO))
        if not root.handlers:
            root.addHandler(handler)