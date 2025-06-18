import os
import logging
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import random

# إعدادات السجل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AIFilter:
    model = None  # نموذج الذكاء الاصطناعي المدرب

    @staticmethod
    def init_client(cfg=None):
        """
        تهيئة عميل الذكاء الاصطناعي باستخدام الإعدادات.
        :param cfg: إعدادات التكوين
        """
        model_path = "ai_model.joblib"

        if os.path.exists(model_path):
            try:
                # إذا كان النموذج موجودًا، قم بتحميله
                AIFilter.model = joblib.load(model_path)
                logging.info(f"AI Model loaded from {model_path}")
            except Exception as e:
                logging.error(f"Failed to load AI model: {e}")
        else:
            logging.info("No existing model found. Training a new model...")
            AIFilter.train_and_save_model()  # إذا لم يكن النموذج موجودًا، قم بتدريبه وحفظه

    @staticmethod
    def train_and_save_model():
        """
        تدريب النموذج وحفظه.
        """
        wallet_data = AIFilter.generate_fake_wallets(500)  # توليد 500 محفظة وهمية للتدريب
        if wallet_data:
            model = AIFilter.train_model(wallet_data)  # تدريب النموذج
            AIFilter.save_model(model)  # حفظ النموذج المدرب
        else:
            logging.error("No data to train the model.")

    @staticmethod
    def train_model(wallet_data):
        """
        تدريب نموذج الذكاء الاصطناعي باستخدام بيانات المحافظ.
        :param wallet_data: بيانات المحافظ
        :return: النموذج المدرب
        """
        X = []
        y = []

        for wallet in wallet_data:
            features = [
                wallet["total_usdt"],
                wallet["num_tokens"],
                wallet["avg_token_value"],
                wallet["max_token_value"],
                wallet.get("last_transaction_value", 0),
                wallet.get("transaction_frequency", 0)
            ]
            X.append(features)

            if wallet["total_usdt"] >= 50000:
                y.append(2)  # VIP
            elif wallet["total_usdt"] >= 10000:
                y.append(1)  # Active
            else:
                y.append(0)  # Low

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        return model

    @staticmethod
    def save_model(model, model_path="ai_model.joblib"):
        """
        حفظ النموذج المدرب إلى ملف.
        :param model: النموذج المدرب
        :param model_path: المسار الذي سيتم حفظ النموذج فيه
        """
        try:
            joblib.dump(model, model_path)
            logging.info(f"Model saved to {model_path}")
        except Exception as e:
            logging.error(f"Error saving model: {e}")

    @staticmethod
    def generate_fake_wallets(num_wallets=100):
        """
        توليد بيانات وهمية للمحافظ.
        :param num_wallets: عدد المحافظ التي سيتم توليدها
        :return: قائمة من البيانات الوهمية للمحافظ
        """
        wallets = []
        for _ in range(num_wallets):
            wallet = {
                "total_usdt": random.randint(0, 100000),
                "num_tokens": random.randint(1, 50),
                "avg_token_value": round(random.uniform(0.1, 100), 2),
                "max_token_value": round(random.uniform(0.1, 500), 2),
                "last_transaction_value": round(random.uniform(1, 1000), 2),
                "transaction_frequency": random.randint(1, 100)
            }
            wallets.append(wallet)
        return wallets