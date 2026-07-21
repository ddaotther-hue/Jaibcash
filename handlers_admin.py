# ============================================================
# JaibCash Bot - handlers_admin.py (أوامر المشرفين)
# ============================================================

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import update_balance, ban_user, unban_user, is_banned, get_users_count, get_all_referrals, get_user, get_balance, get_referral_stats, get_achievements, get_referrer_by_referred
from utils import is_admin
from i18n import t
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

async def add_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, 'admin_only'))
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        update_balance(target_id, amount, 'admin', f'إضافة من المشرف: {amount}')
        await update.message.reply_text(t(user_id, 'points_added', points=amount, user=target_id))
    except (IndexError, ValueError):
        await update.message.reply_text("الاستخدام: /addpoints <user_id> <amount>")

async def deduct_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, 'admin_only'))
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        update_balance(target_id, -amount, 'admin', f'خصم من المشرف: {amount}')
        await update.message.reply_text(t(user_id, 'points_deducted', points=amount, user=target_id))
    except (IndexError, ValueError):
        await update.message.reply_text("الاستخدام: /deductpoints <user_id> <amount>")

async def ban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, 'admin_only'))
        return
    try:
        target_id = int(context.args[0])
        ban_user(target_id)
        await update.message.reply_text(t(user_id, 'user_banned', user=target_id))
    except (IndexError, ValueError):
        await update.message.reply_text("الاستخدام: /ban <user_id>")

async def unban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, 'admin_only'))
        return
    try:
        target_id = int(context.args[0])
        unban_user(target_id)
        await update.message.reply_text(t(user_id, 'user_unbanned', user=target_id))
    except (IndexError, ValueError):
        await update.message.reply_text("الاستخدام: /unban <user_id>")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, 'admin_only'))
        return
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 عدد المستخدمين", callback_data="admin_usercount")],
        [InlineKeyboardButton("🔗 آخر الإحالات", callback_data="admin_referrals")],
    ])
    await update.message.reply_text(
        "🛠️ لوحة تحكم الأدمن\n\nللبحث عن بيانات مستخدم معين استخدم:\n/userinfo <user_id>",
        reply_markup=keyboard
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("🚫 هذا الأمر للمشرفين فقط.", show_alert=True)
        return
    await query.answer()

    if query.data == "admin_usercount":
        count = get_users_count()
        await query.message.reply_text(f"👥 عدد المستخدمين الكلي: {count}")

    elif query.data == "admin_referrals":
        rows = get_all_referrals(limit=20)
        if not rows:
            await query.message.reply_text("لا توجد إحالات مسجلة بعد.")
            return
        lines = ["🔗 آخر 20 إحالة:\n"]
        for r in rows:
            referrer_name = r['referrer_name'] or r['referrer_username'] or str(r['referrer_id'])
            referred_name = r['referred_name'] or r['referred_username'] or str(r['referred_id'])
            lines.append(
                f"👤 {referrer_name} (`{r['referrer_id']}`) ⬅️ {referred_name} (`{r['referred_id']}`)\n"
                f"الحالة: {r['status']} | {r['joined_at']}"
            )
        text = "\n\n".join(lines)
        if len(text) > 4000:
            text = text[:4000] + "\n\n... (تم الاقتصار على أول النتائج)"
        await query.message.reply_text(text, parse_mode="Markdown")

async def user_info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, 'admin_only'))
        return
    try:
        target_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("الاستخدام: /userinfo <user_id>")
        return

    u = get_user(target_id)
    if not u:
        await update.message.reply_text("⚠️ لا يوجد مستخدم بهذا المعرف.")
        return

    balance = get_balance(target_id)
    stats = get_referral_stats(target_id)
    achievements = get_achievements(target_id)
    referrer_id = get_referrer_by_referred(target_id)

    username_line = f"@{u['username']}" if u['username'] else "غير محدد"
    referrer_line = f"`{referrer_id}`" if referrer_id else "لا يوجد (مستخدم مباشر)"

    text = (
        f"👤 معلومات المستخدم\n\n"
        f"🆔 المعرف: `{u['user_id']}`\n"
        f"الاسم: {u['first_name'] or 'غير محدد'}\n"
        f"اليوزر: {username_line}\n"
        f"محظور: {'نعم 🚫' if u['is_banned'] else 'لا ✅'}\n"
        f"تاريخ الانضمام: {u['joined_at']}\n"
        f"المستوى: {u['level']}\n"
        f"المهام المقبولة: {u['approved_tasks']}\n\n"
        f"💰 الرصيد: {balance} نقطة\n\n"
        f"🔗 من دعاه: {referrer_line}\n"
        f"👥 عدد إحالاته: {stats['total']} (نشطة: {stats['active']})\n"
        f"🎁 أرباح إحالاته: {stats['earnings']} نقطة\n\n"
        f"🏆 عدد إنجازاته: {len(achievements)}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
