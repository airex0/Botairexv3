# main.py

import streamlit as st
import pandas as pd
import time
import logging
import asyncio
from datetime import datetime
from threading import Thread

from utils.notifications import Notifier
from utils.checker import WalletChecker
from utils.pricing import PriceFetcher
from config import Config

st.set_page_config(page_title="Wallet Scanner Pro", layout="wide")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# تهيئة المكونات
cfg = Config()
price_fetcher = PriceFetcher(cfg)
checker = WalletChecker(cfg, price_fetcher)
notifier = Notifier(cfg)

# حالة التطبيق في الجلسة
session = st.session_state
session.setdefault('scanner_running', False)
session.setdefault('wallets_found', [])     # قائمة النتائج
session.setdefault('total_scanned', 0)      # عدد المحافظ المُولدة فحصياً
session.setdefault('scan_start_time', None)
session.setdefault('notified', False)

# إعداد الشريط الجانبي
with st.sidebar:
    st.header("⚙️ إعدادات الفحص")
    min_usdt = st.number_input("الحد الأدنى (USDT)", value=100.0, step=0.1)
    scan_rate = st.number_input("🚀 معدل الفحص (حتى 20000)", value=500, step=100)
    send_alert = st.checkbox("🔔 إرسال إشعار Telegram", value=False)
    alert_threshold = st.number_input("📣 إشعار عند رصيد ≥", value=1000.0, step=0.1)

    if st.button("▶️ بدء الفحص"):
        if not session.scanner_running:
            session.scanner_running = True
            session.scan_start_time = datetime.now()
            session.notified = False

            def runner():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(checker.gen_and_check(min_usdt=min_usdt, concurrency=scan_rate))
                session.total_scanned += scan_rate
                for w in results:
                    session.wallets_found.append(w)
                    if send_alert and w["total_usdt"] >= alert_threshold and not session.notified:
                        msg = (
                            f"🎯 محفظة قوية: {w['address']} على {w['chain']}\n"
                            f"💰 {w['total_usdt']} USDT"
                        )
                        try:
                            loop.run_until_complete(notifier.send_telegram(msg))
                            session.notified = True
                        except Exception as e:
                            logging.warning(f"Telegram failed: {e}")
                session.scanner_running = False

            Thread(target=runner, daemon=True).start()

    if st.button("⏹️ إيقاف"):
        session.scanner_running = False

# تبويبات الواجهة
tab1, tab2, tab3 = st.tabs(["📊 لوحة النتائج", "📈 الرسوم البيانية & تحليل", "⬇️ تصدير البيانات"])

# تبويب النتائج
with tab1:
    st.header("📋 المحافظ المكتشفة")
    st.write(f"- إجمالي المحافظ المفحوصة: **{session.total_scanned:,}**")
    st.write(f"- عدد المحافظ المكتشفة: **{len(session.wallets_found)}'")
    if session.wallets_found:
        df = pd.DataFrame([{
            "العنوان": w["address"],
            "🌐 الشبكة": w["chain"],
            "الرصيد (USDT)": w["total_usdt"],
            "AI التصنيف": w.get("score", ""),
            "📅 الوقت": w["timestamp"]
        } for w in session.wallets_found])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد نتائج حتى الآن.")

# تبويب التحليل
with tab2:
    st.header("📈 تحليل مباشر & رسوم بيانية")
    if session.scan_start_time:
        duration = datetime.now() - session.scan_start_time
        st.metric("⏱️ مدة التشغيل", str(duration).split('.')[0])
        st.metric("📦 عدد التحولات الكلي", session.total_scanned)
    if session.wallets_found:
        # توزيع الشبكات:
        st.subheader("🧬 توزيع حسب الشبكة")
        chain_counts = pd.Series([w["chain"] for w in session.wallets_found]).value_counts()
        st.bar_chart(chain_counts)

        # توزيع التصنيفات AI:
        st.subheader("🎯 توزيع التصنيف AI")
        score_counts = pd.Series([w.get("score", "") for w in session.wallets_found]).value_counts()
        st.bar_chart(score_counts)
    else:
        st.info("ابدأ الفحص لعرض التحليلات")

# تبويب التصدير
with tab3:
    st.header("⬇️ تصدير البيانات")
    if session.wallets_found:
        export_df = pd.DataFrame(session.wallets_found)
        st.download_button(
            label="📤 تحميل CSV",
            data=export_df.to_csv(index=False),
            file_name="wallets_results.csv",
            mime="text/csv"
        )
        st.download_button(
            label="📤 تحميل JSON",
            data=export_df.to_json(orient="records", force_ascii=False),
            file_name="wallets_results.json",
            mime="application/json"
        )
    else:
        st.warning("لا توجد بيانات للتصدير")

# تحديث تلقائي إذا المسح شغّال
if session.scanner_running:
    time.sleep(3)
    st.rerun()