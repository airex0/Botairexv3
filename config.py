import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import logging.handlers

# تحميل المتغيرات من .env
load_dotenv()

class Config:
    def __init__(self,
                 env_path: str = ".env",  # استخدام .env
                 decrypt_key: str = None,  # مفتاح لفك التشفير
                 log_dir: str = "logs",  # إعدادات الدليل لتسجيل السجلات
                 log_level: str = "INFO"):  # إعداد مستوى السجلات
        load_dotenv(dotenv_path=env_path)  # تحميل المتغيرات البيئية من .env
        self._decryptor = Fernet(decrypt_key) if (Fernet and decrypt_key) else None

        # تحميل المفاتيح البيئية
        self.ALCHEMY_KEY      = self._get("ALCHEMY_KEY")
        self.COVALENT_KEY     = self._get("COVALENT_KEY")
        self.OPENROUTER_KEY   = self._get("OPENROUTER_KEY")
        self.TELEGRAM_TOKEN   = self._get("TELEGRAM_TOKEN")
        self.TELEGRAM_CHAT_ID = self._get("TELEGRAM_CHAT_ID")
        self.FERNET_KEY       = self._get("FERNET_KEY")  # مفتاح فِرنِت لفك التشفير

        # إعدادات الشبكات
        self.NETWORKS = self._build_networks()

        # إعدادات APIs
        self.COINGECKO_URL     = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,binancecoin,polygon,fantom,avalanche-2,arbitrum-one,optimism,solana,litecoin&vs_currencies=usd"
        self.COVALENT_TX_URL   = "https://api.covalenthq.com/v1/{chain_id}/address/{address}/transactions_v2/?key=" + self.COVALENT_KEY
        self.COVALENT_DEFI_URL = "https://api.covalenthq.com/v1/{chain_id}/address/{address}/portfolio_v2/?key=" + self.COVALENT_KEY

        self._setup_logging(log_dir, log_level)  # إعداد السجلات الاحترافية

    def _get(self, key: str) -> str:
        """
        الحصول على المتغير البيئي، مع دعم فك التشفير إذا كان مفعلًا.
        :param key: اسم المتغير البيئي
        :return: القيمة المقابلة للمتغير البيئي
        """
        raw = os.getenv(key, "")
        if self._decryptor:
            try:
                return self._decryptor.decrypt(raw.encode()).decode()  # فك التشفير إذا كان هناك مفتاح
            except Exception as e:
                logging.warning(f"Failed to decrypt {key}: {e}")
        return raw

    def _build_networks(self) -> dict:
        """
        بناء إعدادات الشبكات التي ستتصل بها الأداة.
        :return: معجم يحتوي على إعدادات الشبكات.
        """
        k = self.ALCHEMY_KEY  # مفتاح Alchemy
        return {
            "Ethereum":  {"rpc": f"https://eth-mainnet.g.alchemy.com/v2/{k}", "chain_id": 1},  # شبكة Ethereum
            "BSC":       {"rpc": f"https://bsc-mainnet.g.alchemy.com/v2/{k}", "chain_id": 56},  # شبكة BSC
            "Polygon":   {"rpc": f"https://polygon-mainnet.g.alchemy.com/v2/{k}", "chain_id": 137},  # شبكة Polygon
            "Fantom":    {"rpc": f"https://fantom-mainnet.g.alchemy.com/v2/{k}", "chain_id": 250},  # شبكة Fantom
            "Avalanche": {"rpc": f"https://avalanche-mainnet.g.alchemy.com/v2/{k}", "chain_id": 43114},  # شبكة Avalanche
            "Arbitrum":  {"rpc": f"https://arb-mainnet.g.alchemy.com/v2/{k}", "chain_id": 42161},  # شبكة Arbitrum
            "Optimism":  {"rpc": f"https://opt-mainnet.g.alchemy.com/v2/{k}", "chain_id": 10},  # شبكة Optimism
            "Bitcoin":   {"api": "https://api.blockcypher.com/v1/btc/main/addrs", "chain_id": None},  # شبكة Bitcoin
            "Litecoin":  {"api": "https://api.blockcypher.com/v1/ltc/main/addrs", "chain_id": None},  # شبكة Litecoin
            "Solana":    {"api": "https://api.mainnet-beta.solana.com", "chain_id": None},  # شبكة Solana
        }

    def _setup_logging(self, log_dir: str, level: str):
        """
        إعداد السجلات لكتابة السجلات في ملف مع التحكم في الحجم وعدد النسخ الاحتياطية.
        :param log_dir: المجلد الذي سيتم تخزين السجلات فيه
        :param level: مستوى السجلات (INFO, DEBUG, ERROR, ...)
        """
        Path(log_dir).mkdir(exist_ok=True)  # إنشاء المجلد إذا لم يكن موجودًا
        handler = logging.handlers.RotatingFileHandler(
            f"{log_dir}/app.log", maxBytes=5*1024*1024, backupCount=5  # التحكم في حجم الملف
        )
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        handler.setFormatter(fmt)
        root = logging.getLogger()
        root.setLevel(getattr(logging, level.upper(), logging.INFO))  # إعداد مستوى السجلات
        if not root.handlers:
            root.addHandler(handler)