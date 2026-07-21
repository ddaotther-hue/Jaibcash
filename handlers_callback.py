import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import is_banned, save_charge_request, get_charge_request, update_charge_request_status, add_advertiser_balance, get_user
from i18n import t
from keyboards import get_reply_keyboard, get_wallet_menu, get_tasks_menu, get_account_menu, get_referral_menu, get_leaderboard_menu
from handlers_user import (
    balance, watch_ad, claim, referral, withdraw, account,
    leaderboard, rewards, checkin, advertiser_balance,
    show_my_level, show_my_stats, show_my_achievements,
    transaction_history, withdraw_advertiser_balance,
    privacy_policy, support
)
from handlers_start import handle_language_selection
from handlers_tasks import browse_tasks, handle_task_admin_action, my_posted_tasks, my_posted_tasks
from config import ADMIN_IDS

logger = logging.getLogger(__name__)
WALLET_ADDRESS = "TDwFwBpvCfPXnj7An82ETMARzTtyesPQZ6"
ADMIN_ID = 1488610580

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # استثناءات ConversationHandler
    if data == "create_task" or data.startswith("execute_task_"):
        return

    # أزرار مراجعة الإثباتات
    if data.startswith('task_approve_') or data.startswith('task_reject_'):
        await handle_task_admin_action(update, context)
        return

    # اختيار اللغة
    if data.startswith('lang_'):
        await handle_language_selection(update, context)
        return

    # زر إعلان
    if data == 'ad_watched':
        await claim(update, context)
        return

    # ===== شحن الرصيد =====
    if data == 'wallet_charge':
        msg = (
            f"💳 **{t(user_id, 'wallet_charge_title')}**\n\n"
            f"📌 **{t(user_id, 'wallet_address_label')} (TRC-20):**\n"
            f"`{WALLET_ADDRESS}`\n\n"
            f"1️⃣ {t(user_id, 'wallet_charge_step1')}\n"
            f"2️⃣ {t(user_id, 'wallet_charge_step2')}\n"
            f"{t(user_id, 'wallet_charge_example')}\n\n"
            f"⚠️ {t(user_id, 'wallet_charge_min')}: **5$**\n"
            f"⚠️ {t(user_id, 'wallet_charge_max')}: **1000$**"
        )
        await query.message.reply_text(msg, parse_mode="Markdown")
        context.user_data['awaiting_charge_amount'] = True
        return

    # ===== أزرار الأدمن (شحن) =====
    if data.startswith('charge_approve_') or data.startswith('charge_reject_'):
        await handle_charge_admin_action(update, context)
        return

    # ===== تصفح المهام =====
    if data == 'tasks_browse':
        await browse_tasks(update, context)
        return

    # ===== أزرار المحفظة =====
    if data == 'wallet_withdraw':
        await withdraw(update, context)
        return
    elif data == 'wallet_history':
        await transaction_history(update, context)
        return
    elif data == 'wallet_back':
        await query.edit_message_text(t(user_id, 'main_menu'), reply_markup=get_reply_keyboard(user_id))
        return
    elif data == 'wallet_advertiser_withdraw':
        await withdraw_advertiser_balance(update, context)
        return

    # ===== أزرار المهام =====
    elif data == 'tasks_achievements':
        await query.edit_message_text(t(user_id, 'tasks_achievements_msg'), reply_markup=get_tasks_menu(user_id))
        return
    elif data == "tasks_my_posts":
        await my_posted_tasks(update, context)
        return
    elif data == 'tasks_back':
        await query.edit_message_text(t(user_id, 'main_menu'), reply_markup=get_reply_keyboard(user_id))
        return

    # ===== أزرار الحساب =====
    elif data == 'account_profile':
        await account(update, context)
        return
    elif data == 'account_level':
        await show_my_level(update, context)
        return
    elif data == 'account_stats':
        await show_my_stats(update, context)
        return
    elif data == 'account_achievements':
        await show_my_achievements(update, context)
        return
    elif data == 'account_back':
        await query.edit_message_text(t(user_id, 'main_menu'), reply_markup=get_reply_keyboard(user_id))
        return

    # ===== أزرار الإحالة =====
    elif data == 'referral_share':
        await referral(update, context)
        return
    elif data == 'referral_stats':
        await referral(update, context)
        return
    elif data == 'referral_back':
        await query.edit_message_text(t(user_id, 'main_menu'), reply_markup=get_reply_keyboard(user_id))
        return

    # ===== أزرار التصنيف =====
    elif data == 'leaderboard_weekly':
        await leaderboard(update, context)
        return
    elif data == 'leaderboard_monthly':
        await query.edit_message_text(t(user_id, 'leaderboard_monthly_msg'), reply_markup=get_leaderboard_menu(user_id))
        return
    elif data == 'leaderboard_back':
        await query.edit_message_text(t(user_id, 'main_menu'), reply_markup=get_reply_keyboard(user_id))
        return

    # ===== أزرار القائمة الرئيسية =====
    elif data == 'menu_balance':
        await balance(update, context)
    elif data == 'menu_watch':
        await watch_ad(update, context)
    elif data == 'menu_referral':
        await referral(update, context)
    elif data == 'menu_withdraw':
        await withdraw(update, context)
    elif data == 'menu_account':
        await account(update, context)
    elif data == 'menu_leaderboard':
        await leaderboard(update, context)
    elif data == 'menu_rewards':
        await rewards(update, context)
    elif data == 'menu_checkin':
        await checkin(update, context)
    elif data == 'menu_privacy':
        await privacy_policy(update, context)
        return
    elif data == 'menu_support':
        await support(update, context)
        return

    else:
        logger.warning(f"⚠️ زر غير معروف: {data}")

async def handle_charge_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin_id = query.from_user.id

    if admin_id != ADMIN_ID and admin_id not in ADMIN_IDS:
        await query.message.reply_text("⛔ هذا الزر للمشرفين فقط.")
        return

    data = query.data
    parts = data.split('_')
    if len(parts) < 3:
        await query.message.reply_text("⚠️ بيانات الطلب غير صحيحة.")
        return

    action = parts[1]
    try:
        request_id = int(parts[2])
    except ValueError:
        await query.message.reply_text("⚠️ رقم الطلب غير صحيح.")
        return

    request = await get_charge_request(request_id)
    if not request or request['status'] != 'pending':
        await query.message.reply_text("⚠️ الطلب غير موجود أو تمت مراجعته.")
        return

    user_id = request['user_id']
    amount = request['amount']

    if action == 'approve':
        await add_advertiser_balance(user_id, amount)
        await update_charge_request_status(request_id, 'approved', admin_id)
        await context.bot.send_message(chat_id=user_id, text=f"✅ تمت الموافقة على شحن {amount:.2f}$")
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ تمت الموافقة", reply_markup=None)
        await query.message.reply_text("✅ تمت الموافقة.")
    else:
        await update_charge_request_status(request_id, 'rejected', admin_id)
        await context.bot.send_message(chat_id=user_id, text=f"❌ تم رفض طلب الشحن.")
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ تم الرفض", reply_markup=None)
        await query.message.reply_text("❌ تم الرفض.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text if update.message.text else None
    photo = update.message.photo[-1] if update.message.photo else None

    if is_banned(user_id):
        await update.message.reply_text("🚫 Banned.")
        return

    # ----- استقبال المبلغ للشحن -----
    if context.user_data.get('awaiting_charge_amount', False):
        if not text:
            await update.message.reply_text("⚠️ أرسل المبلغ كنص.")
            return
        try:
            amount = float(text.strip().replace("$", ""))
            if amount < 5 or amount > 1000:
                await update.message.reply_text("⚠️ المبلغ بين 5 و 1000 دولار.")
                return
        except ValueError:
            await update.message.reply_text("⚠️ أرسل رقماً صحيحاً.")
            return
        context.user_data['charge_amount'] = amount
        context.user_data['awaiting_charge_amount'] = False
        context.user_data['awaiting_charge_screenshot'] = True
        await update.message.reply_text(f"✅ {t(user_id, 'wallet_charge_amount_confirmed', amount=amount)}\n\n{t(user_id, 'wallet_charge_screenshot_instruction')}")
        return

    # ----- استقبال صورة الشحن -----
    if context.user_data.get('awaiting_charge_screenshot', False):
        if not photo:
            await update.message.reply_text("⚠️ أرسل صورة.")
            return
        file_id = photo.file_id
        amount = context.user_data.get('charge_amount', 0)
        request_id = await save_charge_request(user_id, amount, file_id)
        await update.message.reply_text(f"✅ {t(user_id, 'wallet_charge_request_submitted', request_id=request_id)}")
        admin_message = f"🔔 {t(ADMIN_ID, 'wallet_charge_admin_notification')}\n{t(ADMIN_ID, 'user_label')}: {user_id}\n{t(ADMIN_ID, 'amount_label')}: {amount:.2f}$"
        keyboard = [[InlineKeyboardButton(f"✅ {t(ADMIN_ID, 'approve_btn')}", callback_data=f"charge_approve_{request_id}"), InlineKeyboardButton(f"❌ {t(ADMIN_ID, 'reject_btn')}", callback_data=f"charge_reject_{request_id}")]]
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=admin_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        context.user_data.pop('charge_amount', None)
        context.user_data.pop('awaiting_charge_screenshot', None)
        return

    # ----- استقبال عنوان المحفظة لسحب رصيد المعلن -----
    if context.user_data.get('awaiting_advertiser_withdraw', False):
        from handlers_user import handle_advertiser_withdraw_address
        await handle_advertiser_withdraw_address(update, context)
        return

    # ----- الأزرار الثابتة -----
    if text == t(user_id, 'btn_balance'):
        await balance(update, context)
    elif text == t(user_id, 'btn_watch'):
        await watch_ad(update, context)
    elif text == t(user_id, 'btn_tasks'):
        await update.message.reply_text(t(user_id, 'tasks_center'), reply_markup=get_tasks_menu(user_id))
    elif text == t(user_id, 'btn_referral'):
        await referral(update, context)
    elif text == t(user_id, 'btn_checkin'):
        await checkin(update, context)
    elif text == t(user_id, 'btn_rank'):
        await update.message.reply_text(t(user_id, 'leaderboard_title'), reply_markup=get_leaderboard_menu(user_id))
    elif text == t(user_id, 'btn_withdraw'):
        await withdraw(update, context)
    elif text == t(user_id, 'btn_account'):
        await update.message.reply_text(t(user_id, 'account_title'), reply_markup=get_account_menu(user_id))
    elif text == t(user_id, 'btn_rewards'):
        await rewards(update, context)
    elif text == t(user_id, 'btn_advertiser_wallet'):
        await advertiser_balance(update, context)
    elif text == t(user_id, 'btn_privacy'):
        await privacy_policy(update, context)
    elif text == t(user_id, 'btn_support'):
        await support(update, context)
    else:
        await update.message.reply_text(t(user_id, 'unknown_command'))
