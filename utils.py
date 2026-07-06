# ============================================================
# JaibCash Bot - utils.py (مع تفعيل التحقق من القناة)
# ============================================================

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import REQUIRED_CHANNEL, ADMIN_IDS, LEVEL_THRESHOLDS, POINTS_PER_DOLLAR
import re
import aiohttp

logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ============================================================
# 1. التحقق من الاشتراك في القناة (مفعل الآن)
# ============================================================
async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        logger.error(f"خطأ في التحقق من القناة: {e}")
        return False

# ============================================================
# 2. Cloudflare Turnstile (مكافحة البوتات)
# ============================================================
TURNSTILE_SECRET_KEY = "YOUR_TURNSTILE_SECRET_KEY"  # ضع المفتاح من Cloudflare

async def verify_turnstile(token: str) -> bool:
    """التحقق من صحة توكن Turnstile"""
    if not token:
        return False
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    data = {
        "secret": TURNSTILE_SECRET_KEY,
        "response": token
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                result = await response.json()
                return result.get("success", False)
    except Exception as e:
        logger.error(f"خطأ في Turnstile: {e}")
        return False

# ============================================================
# باقي الدوال المساعدة
# ============================================================
def calculate_level(approved_tasks: int) -> int:
    level = 0
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if approved_tasks >= threshold:
            level = i
        else:
            break
    return level

def get_level_name(level: int, lang: str = 'ar') -> str:
    if lang == 'ar':
        names = {0: "🥉 برونز", 1: "🥈 فضي", 2: "🥇 ذهبي", 3: "💎 بلاتيني", 4: "👑 ألماسي", 5: "🚀 ماستر", 6: "🔥 أسطوري"}
    else:
        names = {0: "🥉 Bronze", 1: "🥈 Silver", 2: "🥇 Gold", 3: "💎 Platinum", 4: "👑 Diamond", 5: "🚀 Master", 6: "🔥 Legend"}
    return names.get(level, "🥉 برونز")

def get_level_tasks_required(level: int) -> int:
    if level >= len(LEVEL_THRESHOLDS) - 1:
        return None
    return LEVEL_THRESHOLDS[level + 1]

def get_next_level_tasks(approved_tasks: int) -> dict:
    current = calculate_level(approved_tasks)
    next_level = current + 1
    if next_level >= len(LEVEL_THRESHOLDS):
        return {'current_level': current, 'next_level': None, 'tasks_needed': 0, 'progress_percent': 100, 'is_max': True}
    current_threshold = LEVEL_THRESHOLDS[current]
    next_threshold = LEVEL_THRESHOLDS[next_level]
    tasks_needed = next_threshold - approved_tasks
    total_needed = next_threshold - current_threshold
    progress = approved_tasks - current_threshold
    percent = min(100, int((progress / total_needed) * 100))
    return {'current_level': current, 'next_level': next_level, 'tasks_needed': max(0, tasks_needed), 'progress_percent': percent, 'is_max': False}

def format_points(points: int) -> str:
    return f"{points:,}"

def points_to_usd(points: int) -> float:
    return points / POINTS_PER_DOLLAR

def usd_to_points(usd: float) -> int:
    return int(usd * POINTS_PER_DOLLAR)

def is_suspicious_activity(activity_log: list) -> bool:
    return False

def get_referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

def extract_referrer_id(text: str) -> int:
    match = re.search(r'ref_(\d+)', text)
    if match:
        return int(match.group(1))
    return None

def is_valid_trc20_address(address: str) -> bool:
    if not address:
        return False
    if not address.startswith('T'):
        return False
    if len(address) != 34:
        return False
    return True
