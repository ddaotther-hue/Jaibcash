# config.py - قراءة المتغيرات من ملف .env مشفر باستخدام AES-GCM

import os
import base64
import io
from Crypto.Cipher import AES
from dotenv import load_dotenv

ENCRYPTED_ENV_FILE = ".env.enc"
KEY_FILE = ".env.key"

def decrypt_env():
    """فك تشفير ملف .env.enc وإرجاع قاموس المتغيرات"""
    if not os.path.exists(ENCRYPTED_ENV_FILE):
        raise FileNotFoundError(f"❌ الملف المشفر {ENCRYPTED_ENV_FILE} غير موجود!")

    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError(f"❌ ملف المفتاح {KEY_FILE} غير موجود!")

    with open(KEY_FILE, 'r') as f:
        key = base64.b64decode(f.read().strip())

    with open(ENCRYPTED_ENV_FILE, 'rb') as f:
        encrypted_data = f.read()

    # استخراج nonce (12 بايت), tag (16 بايت), ciphertext (الباقي)
    nonce = encrypted_data[:12]
    tag = encrypted_data[12:28]
    ciphertext = encrypted_data[28:]

    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    try:
        decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError as e:
        raise ValueError("❌ فشل فك التشفير: المفتاح أو الملف تالف.") from e

    env_content = decrypted_data.decode('utf-8')

    # تحميل المتغيرات إلى os.environ
    env_file_like = io.StringIO(env_content)
    load_dotenv(stream=env_file_like)

# فك التشفير عند تحميل config
try:
    decrypt_env()
except Exception as e:
    print(f"⚠️ فشل فك التشفير: {e}")
    print("⚠️ تأكد من وجود .env.enc و .env.key")
    if os.path.exists(".env"):
        from dotenv import load_dotenv
        load_dotenv()

# ---------- التوكنات والمعرفات ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADSGRAM_API_KEY = os.getenv("ADSGRAM_API_KEY")
ADSGRAM_PLATFORM_ID = os.getenv("ADSGRAM_PLATFORM_ID", "34824")
ADSGRAM_BLOCK_ID = os.getenv("ADSGRAM_BLOCK_ID", "37415")
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@JaibCashChannel")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "1488610580").split(',')))

# ---------- الثوابت المالية ----------
REFERRAL_PERCENT = 0.05
LEVEL_BONUS = 1000
MIN_WITHDRAWAL = 2.0
POINTS_PER_DOLLAR = 1_000_000

# ---------- نظام المستويات ----------
LEVEL_THRESHOLDS = [0, 20, 50, 90, 140, 200, 270]
LEVEL_NAMES = {
    0: "🥉 برونز",
    1: "🥈 فضي",
    2: "🥇 ذهبي",
    3: "💎 بلاتيني",
    4: "👑 ألماسي",
    5: "🚀 ماستر",
    6: "🔥 أسطوري"
}

# ---------- قاعدة البيانات ----------
DB_PATH = os.getenv("DB_PATH", "data/jaibcash.db")

# ---------- اللغة الافتراضية ----------
DEFAULT_LANG = "ar"

# ---------- Cloudflare Turnstile ----------
TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "")
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")

# التحقق من وجود التوكنات الأساسية
if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN غير موجود. تأكد من ملف .env المشفر.")

# ---------- RichAds ----------
RICHADS_API_KEY = os.getenv("RICHADS_API_KEY", "")
RICHADS_WIDGET_ID = os.getenv("RICHADS_WIDGET_ID", "123875")

# ---------- RichAds ----------
RICHADS_PUBLISHER_ID = os.getenv("RICHADS_PUBLISHER_ID", "")
RICHADS_WIDGET_ID = os.getenv("RICHADS_WIDGET_ID", "123875")
RICHADS_API_KEY = os.getenv("RICHADS_API_KEY", "")

# ---------- RichAds Endpoint ----------
RICHADS_ENDPOINT = os.getenv("RICHADS_ENDPOINT", "http://15068.xml.adx1.com/telegram-mb")
