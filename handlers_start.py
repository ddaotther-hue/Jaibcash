# الإصلاح المطلوب بملف handlers_start.py
# المشكلة: فحص القناة الإجبارية كان يوقف الكود (return) قبل ما توصل معالجة الإحالة
# الحل: نستخرج وين نخزن الإحالة "معلقة" فوراً بغض النظر عن حالة الاشتراك بالقناة،
#       وبعدين نكمل فحص القناة كالمعتاد

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import create_user, set_language, add_referral, is_banned
from utils import check_channel_membership, extract_referrer_id
from i18n import t, reload_locale
from keyboards import get_reply_keyboard, get_language_selection
from config import REQUIRED_CHANNEL

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج /start العام (يشمل الإحالات)"""
    user = update.effective_user
    user_id = user.id

    # التحقق من الحظر
    if is_banned(user_id):
        await update.message.reply_text("🚫 تم حظر حسابك. تواصل مع الإدارة.")
        return

    # ----- إنشاء المستخدم ومعالجة الإحالة أولاً، قبل أي فحص قد يوقف التنفيذ -----
    # هذا يضمن أن الإحالة تُسجَّل حتى لو المستخدم لم يشترك بالقناة بعد
    create_user(user_id, user.username, user.first_name, 'ar')

    if context.args:
        payload = context.args[0]
        ref_id = extract_referrer_id(payload)
        if ref_id and ref_id != user_id:
            add_referral(ref_id, user_id)
            logger.info(f"✅ إحالة جديدة: {ref_id} → {user_id}")

    # ----- التحقق من القناة الإجبارية (بعد تسجيل الإحالة) -----
    if not await check_channel_membership(update, context):
        channel_link = REQUIRED_CHANNEL if REQUIRED_CHANNEL.startswith('@') else f"https://t.me/{REQUIRED_CHANNEL}"
        await update.message.reply_text(t(user_id, 'not_subscribed', channel=channel_link))
        return

    # عرض اختيار اللغة
    keyboard = get_language_selection()
    await update.message.reply_text(
        t(user_id, 'welcome'),
        reply_markup=keyboard
    )


# ---------- معالج اختيار اللغة (بدون تغيير) ----------
async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.replace('lang_', '')

    set_language(user_id, lang)
    reload_locale(lang)

    await query.message.delete()

    reply_keyboard = get_reply_keyboard(user_id)
    await query.message.reply_text(
        t(user_id, 'lang_selected'),
        reply_markup=reply_keyboard
    )
    await query.message.reply_text(
        t(user_id, 'main_menu'),
        reply_markup=reply_keyboard
    )
