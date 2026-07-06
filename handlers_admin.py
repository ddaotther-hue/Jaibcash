# ============================================================
# JaibCash Bot - handlers_admin.py (أوامر المشرفين)
# ============================================================

import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import update_balance, ban_user, unban_user, is_banned
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
