import logging
from sklearn.externals import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# إعدادات السجل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AIFilter:
    model = None  # نموذج الذكاء الاصطناعي المدرب سيتم تخزينه هنا

    @staticmethod
    def init_client(cfg):
        """
        تهيئة عميل الذكاء الاصطناعي باستخدام الإعدادات.
        :param cfg: إعدادات التكوين
        """
        try:
            # تحميل النموذج المدرب من الملف
            model_path = "ai_model.joblib"
            AIFilter.model = joblib.load(model_path)
            logging.info(f"AI Model loaded from {model_path}")
        except Exception as e:
            logging.error(f"Failed to initialize AI client: {e}")
            raise

    @staticmethod
    def analyze_wallet(wallet):
        """
        تحليل المحفظة باستخدام الذكاء الاصطناعي وتقديم التنبؤ بالتصنيف.
        :param wallet: بيانات المحفظة
        :return: تصنيف المحفظة
        """
        features = [
            wallet["total_usdt"],           # إجمالي الرصيد بالـ USDT
            wallet["num_tokens"],           # عدد الرموز في المحفظة
            wallet["avg_token_value"],      # متوسط قيمة الرموز
            wallet["max_token_value"],      # أقصى قيمة للرمز
            wallet.get("last_transaction_value", 0),  # قيمة آخر معاملة
            wallet.get("transaction_frequency", 0)    # تكرار المعاملات
        ]

        try:
            # التنبؤ بتصنيف المحفظة باستخدام النموذج المدرب
            prediction = AIFilter.model.predict([features])
            category = ["Low", "Active", "VIP"][prediction[0]]
            return category
        except Exception as e:
            logging.error(f"Error during wallet analysis: {e}")
            return "Unknown"

    @staticmethod
    def classify_wallet(wallet):
        """
        تصنيف المحفظة باستخدام الذكاء الاصطناعي بناءً على القيم المميزة.
        :param wallet: بيانات المحفظة
        :return: التصنيف
        """
        category = AIFilter.analyze_wallet(wallet)
        logging.info(f"Wallet classified as: {category}")
        return category

    @staticmethod
    def filter(wallet):
        """
        فلترة المحفظة بناءً على تصنيف الذكاء الاصطناعي.
        :param wallet: بيانات المحفظة
        :return: True إذا كانت المحفظة تطابق الفلاتر، False خلاف ذلك
        """
        # مثال لفلترة المحفظة التي تحتوي على "VIP" فقط
        category = AIFilter.classify_wallet(wallet)
        if category == "VIP":
            return True
        return False

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

            # تصنيف المحفظة بناءً على قيمة total_usdt
            if wallet["total_usdt"] >= 50000:
                y.append(2)  # VIP
            elif wallet["total_usdt"] >= 10000:
                y.append(1)  # Active
            else:
                y.append(0)  # Low

        # تدريب النموذج باستخدام RandomForestClassifier
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        return model

    @staticmethod
    def evaluate_model(model, X_test, y_test):
        """
        تقييم النموذج باستخدام بيانات الاختبار.
        :param model: النموذج المدرب
        :param X_test: بيانات الاختبار
        :param y_test: التصنيفات الحقيقية
        :return: تقرير التقييم
        """
        from sklearn.metrics import classification_report
        predictions = model.predict(X_test)
        report = classification_report(y_test, predictions)
        logging.info("Model Evaluation:")
        logging.info(report)
        return report

    @staticmethod
    def retrain_model(wallet_data, model_path="ai_model.joblib"):
        """
        إعادة تدريب النموذج باستخدام بيانات جديدة.
        :param wallet_data: بيانات المحافظ الجديدة
        :param model_path: مسار حفظ النموذج المدرب
        """
        model = AIFilter.train_model(wallet_data)
        AIFilter.save_model(model, model_path)
        logging.info("Model retrained and saved successfully.")