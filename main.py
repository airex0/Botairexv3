import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
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
            # تحويل البيانات إلى DataFrame
            df = pd.json_normalize(results, record_path=["tokens"],
                                   meta=["address", "chain", "total_usdt", "private_key", "score"])

            # التحقق من أن "score" موجود في البيانات
            if 'score' in df.columns:
                unique_scores = df["score"].dropna().unique().tolist()
                selected_scores = st.multiselect("فلترة حسب التصنيف:", unique_scores, default=unique_scores)
                df = df[df["score"].isin(selected_scores)]
            else:
                st.warning("العمود 'score' غير موجود في البيانات.")
                unique_scores = []  # أو يمكنك تخصيص تصنيف آخر أو تعيينه إلى قيمة أخرى

            st.markdown("### النتائج:")
            st.dataframe(df, use_container_width=True)

            # تنزيل النتائج كـ CSV
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

            st.markdown("### توزيع المحافظ حسب التصنيف:")
            fig, ax = plt.subplots()
            df["score"].value_counts().plot(kind="bar", ax=ax)
            ax.set_ylabel("عدد المحافظ")
            ax.set_xlabel("تصنيف AI")
            st.pyplot(fig)

            # إرسال إشعار عبر Telegram
            asyncio.run(notifier.send_telegram(f"🟢 تم العثور على {len(results)} محفظة ≥ {min_usdt} USDT"))
        else:
            st.warning("❌ لا توجد محافظ مطابقة.")

        await asyncio.sleep(3)  # الانتظار 3 ثوانٍ قبل البدء بالبحث مرة أخرى

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
    except Exception as e:
        st.warning("لا توجد بيانات محفوظة بعد.")
        all_data = []

    if all_data:
        timestamps = [entry["timestamp"] for entry in all_data]
        counts = [len(entry["results"]) for entry in all_data]
        total_usdt = [sum(w["total_usdt"] for w in entry["results"]) for entry in all_data]

        st.markdown("### 📉 عدد المحافظ عبر الزمن")
        fig, ax = plt.subplots()
        ax.plot(timestamps, counts, marker="o", color="b", label="عدد المحافظ")
        ax.set_xlabel("التاريخ")
        ax.set_ylabel("عدد المحافظ")
        ax.set_title("توزيع المحافظ عبر الوقت")
        st.pyplot(fig)

        st.markdown("### 📊 الرصيد الإجمالي عبر الزمن")
        fig, ax = plt.subplots()
        ax.plot(timestamps, total_usdt, marker="o", color="g", label="الرصيد الإجمالي (USDT)")
        ax.set_xlabel("التاريخ")
        ax.set_ylabel("الرصيد الإجمالي")
        ax.set_title("توزيع الرصيد الإجمالي عبر الوقت")
        st.pyplot(fig)

        network_counts = {}
        for entry in all_data:
            for wallet in entry["results"]:
                chain = wallet["chain"]
                if chain not in network_counts:
                    network_counts[chain] = 0
                network_counts[chain] += 1

        st.markdown("### 🌐 توزيع المحافظ حسب الشبكة")
        fig, ax = plt.subplots()
        ax.bar(network_counts.keys(), network_counts.values(), color="purple")
        ax.set_xlabel("الشبكة")
        ax.set_ylabel("عدد المحافظ")
        ax.set_title("توزيع المحافظ حسب الشبكة")
        st.pyplot(fig)

        selected_date = st.selectbox("اختر تاريخ الفحص:", timestamps)
        selected_data = next(item for item in all_data if item["timestamp"] == selected_date)

        # تحقق من وجود العمود "score" في البيانات
        df = pd.DataFrame(selected_data["results"])
        if 'score' in df.columns:
            unique_scores = df["score"].unique()
            selected_scores = st.multiselect("فلترة حسب التصنيف:", unique_scores, default=unique_scores)
            filtered_results = [w for w in selected_data["results"] if w["score"] in selected_scores]
        else:
            st.warning("العمود 'score' غير موجود في البيانات.")
            filtered_results = selected_data["results"]  # عرض كل النتائج إذا لم يكن "score" موجودًا

        st.markdown(f"### نتائج الفحص بتاريخ `{selected_date}`")
        df_filtered = pd.json_normalize(filtered_results, record_path=["tokens"],
                                        meta=["address", "chain", "total_usdt", "private_key", "score"])
        st.dataframe(df_filtered, use_container_width=True)

        for wallet in filtered_results:
            if wallet["total_usdt"] >= threshold:
                message = f"🟢 تم العثور على محفظة تحتوي على {wallet['total_usdt']} USDT! \nمحفظة: {wallet['address']}"
                asyncio.run(notifier.send_telegram(message))

    else:
        st.info("لا توجد نتائج محفوظة.")

with tabs[5]:
    st.markdown("## ⚙️ إعدادات النظام")
    st.write("تم تحميل المفاتيح من `env.api`. لا تنس استخدام `FERNET_KEY` إذا كانت مشفرة.")
    st.write("المفاتيح تشمل: Alchemy، Covalent، OpenRouter، Telegram.")