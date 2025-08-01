import asyncio
import os
import json
import time
import logging
from datetime import datetime
from threading import Thread

from utils.checker import WalletChecker
from utils.pricing import PriceFetcher
from config import Config

# ملف التخزين المشترك للنتائج والحالة
STATUS_FILE = "scanner_status.json"

class ScannerServer:
    def __init__(self):
        self.cfg = Config()
        self.checker = WalletChecker(self.cfg, PriceFetcher(self.cfg))
        self.running = False
        self.thread = None

        # إنشاء ملف الحالة إذا لم يكن موجوداً
        if not os.path.exists(STATUS_FILE):
            self._write_status({
                "running": False,
                "last_run": None,
                "total_scanned": 0,
                "wallets": []
            })

    def _write_status(self, data):
        try:
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logging.error(f"Failed to write status: {e}")

    def _read_status(self):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def _append_wallets(self, new_wallets):
        status = self._read_status()
        existing = status.get("wallets", [])
        status["wallets"] = existing + new_wallets
        status["total_scanned"] += len(new_wallets)
        status["last_run"] = datetime.utcnow().isoformat()
        self._write_status(status)

    def start(self, min_usdt: float, rate: int):
        if not self.running:
            self.running = True
            self._write_status({**self._read_status(), "running": True})
            self.thread = Thread(target=self._worker, args=(min_usdt, rate), daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        status = self._read_status()
        status["running"] = False
        self._write_status(status)

    def _worker(self, min_usdt, rate):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logging.info("📡 Background scanner started.")
        while self.running:
            try:
                wallets = loop.run_until_complete(self.checker.gen_and_check(min_usdt=min_usdt, concurrency=rate))
                self._append_wallets([w.__dict__ for w in wallets])
            except Exception as e:
                logging.warning(f"Background scan failed: {e}")
            time.sleep(5)  # انتظار قبل الجولة التالية
        logging.info("🛑 Scanner stopped.")

if __name__ == "__main__":
    server = ScannerServer()
    server.start(min_usdt=100.0, rate=10000)