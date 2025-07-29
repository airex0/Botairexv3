import os
import streamlit as st
import pandas as pd
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from config import Config
from utils.wallets import WalletGenerator
from utils.pricing import PriceFetcher
from utils.checker import WalletChecker
from utils.defi import DeFiFetcher
from utils.ai import AIFilter
from utils.risk import RiskScanner
from utils.notifications import Notifier

import plotly.express as px
import plotly.graph_objects as go

# إعدادات التكوين
cfg = Config(env_path="env.api", decrypt_key=os.getenv("FERNET_KEY"))
AIFilter.init_client(cfg)
price_fetcher = PriceFetcher(cfg)
checker = WalletChecker(cfg, price_fetcher)
defi = DeFiFetcher(cfg)
risk = RiskScanner(cfg)
notifier = Notifier(cfg)

# إعدادات Streamlit
st.set_page_config(page_title="🔍 فاحص المحافظ الشامل", layout="wide")
st.title("🔍 فاحص المحافظ الشامل مع AI, DeFi & Risk")

# المدخلات
min_usdt = st.sidebar.number_input("الحد الأدنى للقيمة (USDT):", 0.0, 1e6, 1.0, 0.5)
concurrency = st.sidebar.number_input("عدد العمال (حتى 20000):", 1, 20000, 1000, 1)
threshold = st.sidebar.number_input("حدد الحد الأدنى لإرسال الإشعار (USDT):", min_value=0.0, value=1000.0, step=0.1)

# إنشاء التبويبات في Streamlit
tabs = st.tabs(["🔎 البحث", "📊 DeFi", "💡 AI", "⚠️ المخاطر", "📂 المحفوظات", "⚙️ الإعدادات"])

async def run_search(min_usdt, concurrency):
    while True:
        results = await checker.gen_and_check(min_usdt, concurrency)

        if results:
            df = pd.json_normalize(results, record_path=["tokens"],
                                   meta=["address", "chain", "total_usdt", "private_key", "score"])

            if 'score' in df.columns:
                unique_scores = df["score"].dropna().unique().tolist()
                selected_scores = st.multiselect("فلترة حسب التصنيف:", unique_scores, default=unique_scores)
                df = df[df["score"].isin(selected_scores)]
            else:
                st.warning("العمود 'score' غير موجود في البيانات.")
                unique_scores = []

            st.markdown("### النتائج:")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ تحميل النتائج كـ CSV", csv, "wallets.csv", "text/csv")

            st.markdown("### عرض كبطاقات:")
            for _, row in df.head(10).iterrows():
                st.markdown(f"""
                **عنوان:** `{row['address']}`  
                **شبكة:** {row['chain']}  
                **الرصيد الكلي:** ${row['total_usdt']}  
                **تصنيف AI:** `{row['score']}`  
                **رمز خاص:** `{row['private_key']}`  
                **التوكنز:** {row['symbol']} (${row['value_usd']})  
                """)
                st.markdown("---")

            # توزيع المحافظ حسب التصنيف
            score_counts = df["score"].value_counts().reset_index()
            score_counts.columns = ["score", "count"]
            fig_score = px.bar(score_counts, x="score", y="count",
                               labels={"score": "تصنيف AI", "count": "عدد المحافظ"},
                               title="توزيع المحافظ حسب التصنيف")
            st.plotly_chart(fig_score, use_container_width=True)

            asyncio.run(notifier.send_telegram(f"🟢 تم العثور على {len(results)} محفظة ≥ {min_usdt} USDT"))
        else:
            st.warning("❌ لا توجد محافظ مطابقة.")

        await asyncio.sleep(3)

with tabs[0]:
    st.markdown("## 🚀 البحث عن محافظ")
    if st.button("ابدأ الفحص", key="start_search_btn"):
        asyncio.run(run_search(min_usdt, concurrency))

with tabs[1]:
    st.markdown("## 📊 DeFi Positions")
    addr = st.text_input("أدخل عنوان المحفظة:", key="defi_address")
    chain = st.selectbox("اختر الشبكة:", list(cfg.NETWORKS.keys()), key="defi_chain")
    if st.button("تحميل البيانات", key="load_defi_btn"):
        items = asyncio.run(defi.fetch_positions(addr, cfg.NETWORKS[chain]["chain_id"]))
        st.json(items)

with tabs[2]:
    st.markdown("## 💡 تحليل NFT")
    if st.button("تحليل فحص جديد (10 محافظ فقط)", key="analyze_nft_btn"):
        results = asyncio.run(checker.gen_and_check(min_usdt, 10))
        for w in results:
            st.markdown(f"### {w['address']} على {w['chain']}")
            st.write(AIFilter.analyze_nft(w))

with tabs[3]:
    st.markdown("## ⚠️ فحص الصلاحيات")
    addr2 = st.text_input("أدخل عنوان الفحص:", key="risk_address")
    chain2 = st.selectbox("اختر الشبكة:", list(cfg.NETWORKS.keys()), key="risk_chain")
    if st.button("بدء الفحص", key="scan_risk_btn"):
        ap = asyncio.run(risk.fetch_approvals(addr2, chain2))
        st.json(ap)

with tabs[4]:
    st.markdown("## 🕒 محفوظات الفحوصات السابقة")
    try:
        with open("results.json", "r", encoding="utf-8") as f:
            all_data = json.load(f)
    except Exception:
        st.warning("لا توجد بيانات محفوظة بعد.")
        all_data = []

    if all_data:
        timestamps = [entry["timestamp"] for entry in all_data]
        counts = [len(entry["results"]) for entry in all_data]
        total_usdt = [sum(w["total_usdt"] for w in entry["results"]) for entry in all_data]

        # عدد المحافظ عبر الزمن
        fig1 = px.line(x=timestamps, y=counts, markers=True,
                       labels={"x": "التاريخ", "y": "عدد المحافظ"},
                       title="توزيع المحافظ عبر الوقت")
        st.plotly_chart(fig1, use_container_width=True)

        # الرصيد الإجمالي عبر الزمن
        fig2 = px.line(x=timestamps, y=total_usdt, markers=True,
                       labels={"x": "التاريخ", "y": "الرصيد الإجمالي"},
                       title="توزيع الرصيد الإجمالي عبر الوقت")
        st.plotly_chart(fig2, use_container_width=True)

        network_counts = {}
        for entry in all_data:
            for wallet in entry["results"]:
                chain = wallet["chain"]
                network_counts[chain] = network_counts.get(chain, 0) + 1

        network_df = pd.DataFrame(list(network_counts.items()), columns=["network", "count"])
        fig3 = px.bar(network_df, x="network", y="count",
                      labels={"network": "الشبكة", "count": "عدد المحافظ"},
                      title="توزيع المحافظ حسب الشبكة")
        st.plotly_chart(fig3, use_container_width=True)

        selected_date = st.selectbox("اختر تاريخ الفحص:", timestamps)
        selected_data = next(item for item in all_data if item["timestamp"] == selected_date)

        df_filtered = pd.DataFrame(selected_data["results"])
        if 'score' in df_filtered.columns:
            unique_scores = df_filtered["score"].unique()
            selected_scores = st.multiselect("فلترة حسب التصنيف:", unique_scores, default=unique_scores)
            filtered_results = [w for w in selected_data["results"] if w["score"] in selected_scores]
        else:
            st.warning("العمود 'score' غير موجود.")
            filtered_results = selected_data["results"]

        df_norm = pd.json_normalize(filtered_results, record_path=["tokens"],
                                     meta=["address", "chain", "total_usdt", "private_key", "score"])
        st.dataframe(df_norm, use_container_width=True)

        for wallet in filtered_results:
            if wallet["total_usdt"] >= threshold:
                message = (
                    f"🟢 تم العثور على محفظة تحتوي على {wallet['total_usdt']} USDT! "
                    f"\nمحفظة: {wallet['address']}"
                )
                asyncio.run(notifier.send_telegram(message))
    else:
        st.info("لا توجد نتائج محفوظة.")

with tabs[5]:
    st.markdown("## ⚙️ إعدادات النظام")
    st.write("تم تحميل المفاتيح من `env.api`. لا تنس استخدام `FERNET_KEY` إذا كانت مشفرة.")
    st.write("المفاتيح تشمل: Alchemy، Covalent، OpenRouter، Telegram.")