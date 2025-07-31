import streamlit as st
import os
import time
import json
import threading
from datetime import datetime
from typing import List
import random
import hashlib
import pandas as pd

st.set_page_config(
    page_title="Wallet Scanner Pro",
    layout="wide"
)

RESULTS_FILE = "results.json"

class WalletResult:
    def __init__(self, address, private_key, chain, balance_usdt, timestamp, risk_score):
        self.address = address
        self.private_key = private_key
        self.chain = chain
        self.balance_usdt = balance_usdt
        self.timestamp = timestamp
        self.risk_score = risk_score

    def to_dict(self):
        return {
            "address": self.address,
            "private_key": self.private_key,
            "chain": self.chain,
            "balance_usdt": self.balance_usdt,
            "timestamp": self.timestamp.isoformat(),
            "risk_score": self.risk_score
        }

    @staticmethod
    def from_dict(d):
        return WalletResult(
            d["address"], d["private_key"], d["chain"],
            d["balance_usdt"], datetime.fromisoformat(d["timestamp"]),
            d["risk_score"]
        )

class WalletScanner:
    def __init__(self):
        self.running = False
        self.results: List[WalletResult] = []
        self.total_scanned = 0
        self.thread = None
        self.min_usdt = 0
        self.scan_rate = 10

    def generate_wallet(self):
        if random.random() < 0.5:
            priv = os.urandom(32).hex()
            addr = "0x" + hashlib.sha256(priv.encode()).hexdigest()[:40]
            chain = "Ethereum"
            price = 2600
        else:
            priv = os.urandom(32).hex()
            addr = "1" + hashlib.sha256(priv.encode()).hexdigest()[:33]
            chain = "Bitcoin"
            price = 43000

        if random.random() < 0.0001:
            balance = round(random.uniform(0.1, 5), 4)
            usd_value = balance * price
        else:
            balance = 0
            usd_value = 0

        return addr, priv, chain, usd_value

    def scan(self):
        while self.running:
            for _ in range(self.scan_rate):
                addr, priv, chain, balance = self.generate_wallet()
                self.total_scanned += 1
                if balance >= self.min_usdt:
                    result = WalletResult(
                        addr, priv, chain, round(balance, 2),
                        datetime.now(), random.randint(1, 10)
                    )
                    self.results.append(result)
                    self.save_results()

            time.sleep(1)

    def start(self, min_usdt, scan_rate):
        if not self.running:
            self.min_usdt = min_usdt
            self.scan_rate = scan_rate
            self.running = True
            self.thread = threading.Thread(target=self.scan, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False

    def save_results(self):
        data = [r.to_dict() for r in self.results]
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_results(self):
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    self.results = [WalletResult.from_dict(d) for d in data]
                except:
                    self.results = []

scanner = WalletScanner()
scanner.load_results()

st.title("🔍 Wallet Scanner Pro")

# Sidebar
with st.sidebar:
    st.header("⚙️ الإعدادات")
    min_usdt = st.number_input("الحد الأدنى للرصيد (USDT)", 0.1, 100000.0, 10.0)
    scan_rate = st.slider("معدل المسح (محافظ/ثانية)", 1, 50, 10)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ بدء المسح"):
            scanner.start(min_usdt, scan_rate)
            st.success("تم بدء المسح!")
    with col2:
        if st.button("⏹️ إيقاف المسح"):
            scanner.stop()
            st.info("تم الإيقاف.")

# Main dashboard
tab1, tab2 = st.tabs(["📊 لوحة المراقبة", "💰 النتائج"])

with tab1:
    st.metric("الحالة", "نشط ✅" if scanner.running else "متوقف ❌")
    st.metric("إجمالي المسح", f"{scanner.total_scanned:,}")
    st.metric("عدد النتائج", f"{len(scanner.results)}")

    if scanner.running:
        st.markdown("⏳ يتم تحديث النتائج...")
        time.sleep(2)
        st.experimental_rerun()

with tab2:
    if scanner.results:
        df = pd.DataFrame([r.to_dict() for r in scanner.results])
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(df)

        csv = df.to_csv(index=False)
        st.download_button("⬇️ تحميل النتائج CSV", data=csv, file_name="results.csv", mime="text/csv")
    else:
        st.info("لا توجد نتائج بعد.")