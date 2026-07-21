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
        await update.message.reply_text(" 🚫 تم حظر حسابك. تواصل مع الإدارة.")
        return

    # ===== حفظ معرف الإحالة قبل أي شيء حتى لا يضيع =====
    if context.args:
        candidate_ref = extract_referrer_id(context.args[0])
        if candidate_ref and candidate_ref != user_id:
            context.user_data['pending_ref'] = candidate_ref

    # ===== اختيار اللغة أول خطوة فور الضغط على /start =====
    keyboard = get_language_selection()
    await update.message.reply_text(
        "🌐 اختر لغتك المفضلة / Please choose your language:",
        reply_markup=keyboard
    )


async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.replace('lang_', '')

    set_language(user_id, lang)
    reload_locale(lang)

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.reply_text(t(user_id, 'lang_selected'))

    if is_banned(user_id):
        await query.message.reply_text("🚫 " + t(user_id, 'banned'))
        return

    if not await check_channel_membership(update, context):
        channel_link = REQUIRED_CHANNEL if REQUIRED_CHANNEL.startswith('@') else f"https://t.me/{REQUIRED_CHANNEL}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(t(user_id, 'btn_check_sub'), callback_data="check_sub")]])
        await query.message.reply_text(t(user_id, 'not_subscribed', channel=channel_link), reply_markup=keyboard)
        return

    await _finish_start(update, context, user_id, query.from_user)


async def _finish_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, user):
    create_user(user_id, user.username, user.first_name, 'ar')

    # ===== معالجة الإحالة =====
    ref_id = context.user_data.pop('pending_ref', None)
    if not ref_id and context.args:
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

    reply_keyboard = get_reply_keyboard(user_id)
    target_message = update.message if update.message else update.callback_query.message
    await target_message.reply_text(
        t(user_id, 'welcome_main'),
        reply_markup=reply_keyboard
    )


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id

    if not await check_channel_membership(update, context):
        await query.answer("⚠️ لسا ما اشتركت بالقناة، اشترك أول وبعدين اضغط الزر.", show_alert=True)
        return

    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass

    await _finish_start(update, context, user_id, user)
