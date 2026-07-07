import os
from dotenv import load_dotenv

load_dotenv()

# ---------- التوكنات والمعرفات ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADSGRAM_API_KEY = os.getenv("ADSGRAM_API_KEY")
ADSGRAM_PLATFORM_ID = os.getenv("ADSGRAM_PLATFORM_ID", "34824")
ADSGRAM_BLOCK_ID = os.getenv("ADSGRAM_BLOCK_ID", "37415")
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@jaib_cash")
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

# ---------- RichAds ----------
RICHADS_PUBLISHER_ID = os.getenv("RICHADS_PUBLISHER_ID", "409986")
RICHADS_WIDGET_ID = os.getenv("RICHADS_WIDGET_ID", "123875")
RICHADS_API_KEY = os.getenv("RICHADS_API_KEY", "")

# ---------- Cloudflare Turnstile (اختياري) ----------
TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "")
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")

# التحقق من وجود التوكنات الأساسية
if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN غير موجود. تأكد من ملف .env المشفر.")
