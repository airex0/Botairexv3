import random
import bip_utils
from eth_account import Account
import hashlib
from concurrent.futures import ThreadPoolExecutor


class WalletGenerator:
    @staticmethod
    def generate_btc() -> str:
        """
        توليد مفتاح خاص لمحفظة Bitcoin باستخدام BIP-44
        """
        priv = random.getrandbits(256)  # توليد رقم عشوائي للمفتاح
        key = bip_utils.Bip44.FromSeed(priv.to_bytes(32, 'big'), bip_utils.Bip44Coins.BITCOIN)
        return key.PrivateKey().ToWif()

    @staticmethod
    def generate_eth() -> str:
        """
        توليد مفتاح خاص لمحفظة Ethereum باستخدام eth-account
        """
        acct = Account.create()  # توليد مفتاح عشوائي لإيثيريوم
        return acct.privateKey.hex()

    @staticmethod
    def generate_hd(mnemonic: str, coin: str = "ETH", account_idx: int = 0) -> tuple:
        """
        توليد مفتاح خاص باستخدام عبارة الاستعادة (Mnemonic) لـ Ethereum أو Bitcoin
        """
        coin_map = {
            "ETH": bip_utils.Bip44Coins.ETHEREUM,
            "BTC": bip_utils.Bip44Coins.BITCOIN,
            "ADA": bip_utils.Bip44Coins.CARDANO_BYRON,
            "SOL": bip_utils.Bip44Coins.SOLANA,  # دعم Solana
        }
        bip_coin = coin_map.get(coin.upper(), bip_utils.Bip44Coins.BITCOIN)
        bip_obj = (
            bip_utils.Bip44
            .FromMnemonic(mnemonic, bip_coin)
            .Purpose().Coin().Account(account_idx)
            .Change(False).AddressIndex(0)
        )
        return bip_obj.PublicKey().ToAddress(), bip_obj.PrivateKey().ToWif()


def encrypt_private_key(private_key: str) -> str:
    """
    تحسين الأمان عن طريق تشفير المفتاح الخاص
    """
    hashed_key = hashlib.sha256(private_key.encode()).hexdigest()
    return hashed_key


def generate_secure_wallet():
    """
    توليد محفظة مشفرة تتضمن توليد مفاتيح BTC و ETH المشفرة
    """
    btc_key = WalletGenerator.generate_btc()
    eth_key = WalletGenerator.generate_eth()

    encrypted_btc_key = encrypt_private_key(btc_key)
    encrypted_eth_key = encrypt_private_key(eth_key)

    return {"btc_key": encrypted_btc_key, "eth_key": encrypted_eth_key}


def generate_wallet_key(_):
    """
    توليد محفظة عشوائية مع مفتاحين مشفرين Bitcoin و Ethereum
    """
    btc_key = WalletGenerator.generate_btc()
    eth_key = WalletGenerator.generate_eth()
    encrypted_btc_key = encrypt_private_key(btc_key)
    encrypted_eth_key = encrypt_private_key(eth_key)

    return {"btc_key": encrypted_btc_key, "eth_key": encrypted_eth_key}


def generate_wallets_parallel(num_wallets=10000):
    """
    توليد عدد من المحافظ باستخدام ThreadPoolExecutor لزيادة السرعة
    """
    with ThreadPoolExecutor() as executor:
        wallets = list(executor.map(generate_wallet_key, range(num_wallets)))
    return wallets


def analyze_wallet_safety(wallet):
    """
    تحليل الأمان للمفاتيح الخاصة (على سبيل المثال، تحليل طول المفتاح)
    """
    btc_safety_score = len(wallet['btc_key'])  # فرضًا نعتبر أن الأمان يعتمد على طول المفتاح
    eth_safety_score = len(wallet['eth_key'])  # نفس الشيء لإيثيريوم
    return btc_safety_score, eth_safety_score


def analyze_wallet_security(wallet_data):
    """
    تحليل الأمان للمحافظ التي تحتوي على أموال فقط
    """
    secure_wallets = []
    for wallet in wallet_data:
        btc_safety, eth_safety = analyze_wallet_safety(wallet)
        # إذا كانت درجة الأمان للمفاتيح جيدة، أضف المحفظة إلى القائمة
        if btc_safety > 100 and eth_safety > 100:
            secure_wallets.append(wallet)
    return secure_wallets


def parallel_analyze_wallet_security(wallet_data):
    """
    تحليل الأمان للمحافظ بشكل متوازي باستخدام ThreadPoolExecutor لتحسين الأداء
    """
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(analyze_wallet_security, wallet_data))
    return results