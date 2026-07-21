import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import create_user, set_language, add_referral, is_banned, get_user, get_referral_stats
from utils import check_channel_membership, extract_referrer_id
from i18n import t, reload_locale
from keyboards import get_reply_keyboard, get_language_selection
from config import REQUIRED_CHANNEL

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if is_banned(user_id):
        await update.message.reply_text("🚫 تم حظر حسابك. تواصل مع الإدارة.")
        return

    if not await check_channel_membership(update, context):
        channel_link = REQUIRED_CHANNEL if REQUIRED_CHANNEL.startswith('@') else f"https://t.me/{REQUIRED_CHANNEL}"
        await update.message.reply_text(t(user_id, 'not_subscribed', channel=channel_link))
        return

    create_user(user_id, user.username, user.first_name, 'ar')

    # ===== معالجة الإحالة =====
    if context.args:
        ref_id = extract_referrer_id(context.args[0])
        if ref_id and ref_id != user_id:
            add_referral(ref_id, user_id)
            logger.info(f"✅ إحالة جديدة: {ref_id} → {user_id}")

            # ===== إرسال إشعار للمحيل =====
            try:
                new_user = get_user(user_id)
                stats = get_referral_stats(ref_id)
                referrer = get_user(ref_id)

                await context.bot.send_message(
                    chat_id=ref_id,
                    text=f"🔔 **إحالة جديدة!**\n\n"
                         f"👤 {new_user['first_name'] or 'مستخدم جديد'} دخل عبر رابط إحالتك.\n"
                         f"🆔 المعرف: `{user_id}`\n"
                         f"📊 عدد الإحالات حتى الآن: {stats['total']}\n\n"
                         f"💡 سيحصل على مكافأة عند إكمال أول مهمة."
                )
            except Exception as e:
                logger.error(f"❌ فشل إرسال إشعار للمحيل {ref_id}: {e}")

    keyboard = get_language_selection()
    await update.message.reply_text(
        t(user_id, 'welcome'),
        reply_markup=keyboard
    )

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
