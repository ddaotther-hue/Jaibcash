# ============================================================
# JaibCash Bot - handlers_charge.py (نظام الشحن مع عنوان المحفظة)
# ============================================================

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
from database import save_charge_request, get_charge_request, update_charge_request_status, add_advertiser_balance, get_user
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

ENTERING_AMOUNT, ENTERING_SCREENSHOT = range(2)
ADMIN_ID = 1488610580

# عنوان المحفظة الخاص بالمنصة (ضع عنوانك الحقيقي)
WALLET_ADDRESS = "TDwFwBpvCfPXnj7An82ETMARzTtyesPQZ6"

async def start_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        f"💳 **شحن رصيد المحفظة**\n\n"
        f"📌 **عنوان المحفظة (TRC-20):**\n"
        f"`{WALLET_ADDRESS}`\n\n"
        f"1️⃣ قم بتحويل المبلغ المطلوب إلى العنوان أعلاه عبر شبكة **TRC-20**.\n"
        f"2️⃣ أرسل المبلغ الذي قمت بتحويله (بالدولار).\n"
        f"مثال: `10` أو `25.50`\n\n"
        f"⚠️ الحد الأدنى للشحن: **5$**\n"
        f"⚠️ الحد الأقصى للشحن: **1000$**"
    )
    return ENTERING_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().replace("$", "")

    try:
        amount = float(text)
        if amount < 5:
            await update.message.reply_text("⚠️ الحد الأدنى للشحن هو 5$. أرسل مبلغاً أكبر.")
            return ENTERING_AMOUNT
        if amount > 1000:
            await update.message.reply_text("⚠️ الحد الأقصى للشحن هو 1000$. أرسل مبلغاً أقل.")
            return ENTERING_AMOUNT
    except ValueError:
        await update.message.reply_text("⚠️ أرسل رقماً صحيحاً (مثال: 10 أو 25.50).")
        return ENTERING_AMOUNT

    context.user_data['charge_amount'] = amount
    await update.message.reply_text(
        f"✅ المبلغ: **{amount:.2f}$**\n\n"
        f"2️⃣ الآن أرسل **صورة إشعار التحويل** (Screenshot) من محفظتك التي أرسلت منها الأموال إلى:\n"
        f"`{WALLET_ADDRESS}`\n\n"
        f"تأكد من وضوح المبلغ وعنوان المحفظة المرسَل منها."
    )
    return ENTERING_SCREENSHOT

async def enter_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount = context.user_data.get('charge_amount', 0)

    if not update.message.photo:
        await update.message.reply_text("⚠️ يرجى إرسال صورة وليس ملفاً آخر.")
        return ENTERING_SCREENSHOT

    photo = update.message.photo[-1]
    file_id = photo.file_id

    request_id = await save_charge_request(user_id, amount, file_id)

    await update.message.reply_text(
        f"✅ تم استلام طلب الشحن بنجاح!\n\n"
        f"📋 رقم الطلب: `#{request_id}`\n"
        f"💰 المبلغ: {amount:.2f}$\n\n"
        "⏳ سيتم مراجعة طلبك من قبل الأدمن في أقرب وقت ممكن.\n"
        "ستصلك رسالة عند الموافقة أو الرفض."
    )

    # إرسال إشعار للأدمن
    user = get_user(user_id)
    username = user['username'] if user else "غير متوفر"
    first_name = user['first_name'] if user else "مستخدم"

    admin_message = (
        f"🔔 **طلب شحن جديد**\n\n"
        f"👤 المستخدم: {first_name} (@{username})\n"
        f"🆔 المعرف: `{user_id}`\n"
        f"💰 المبلغ: **{amount:.2f}$**\n"
        f"📋 رقم الطلب: `#{request_id}`\n"
        f"📅 الوقت: {update.message.date.strftime('%Y-%m-%d %H:%M')}\n"
        f"📌 عنوان المحفظة المستخدم: `{WALLET_ADDRESS}`\n\n"
        "📎 الصورة مرفقة أدناه."
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ موافقة", callback_data=f"charge_approve_{request_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"charge_reject_{request_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=admin_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        logger.info(f"✅ تم إرسال طلب الشحن #{request_id} للأدمن")
    except Exception as e:
        logger.error(f"❌ فشل إرسال الإشعار للأدمن: {e}")
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ فشل إرسال صورة الطلب #{request_id}\n{admin_message}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    context.user_data.pop('charge_amount', None)
    return ConversationHandler.END

async def charge_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.pop('charge_amount', None)
    await update.message.reply_text("❌ تم إلغاء عملية الشحن.")
    return ConversationHandler.END

async def handle_charge_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id

    if admin_id != ADMIN_ID and admin_id not in ADMIN_IDS:
        await query.message.reply_text("⛔ هذا الزر للمشرفين فقط.")
        return

    data = query.data
    parts = data.split('_')
    action = parts[1]
    request_id = int(parts[2])

    request = await get_charge_request(request_id)
    if not request:
        await query.message.reply_text("⚠️ الطلب غير موجود.")
        return

    if request['status'] != 'pending':
        await query.message.reply_text(f"⚠️ هذا الطلب تمت مراجعته مسبقاً (الحالة: {request['status']}).")
        return

    user_id = request['user_id']
    amount = request['amount']

    if action == 'approve':
        await add_advertiser_balance(user_id, amount)
        await update_charge_request_status(request_id, 'approved', admin_id)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ **تمت الموافقة على طلب الشحن!**\n\n"
                     f"📋 رقم الطلب: `#{request_id}`\n"
                     f"💰 المبلغ: **{amount:.2f}$**\n"
                     f"✅ تمت إضافته إلى رصيد محفظتك.\n\n"
                     f"شكراً لاستخدامك JaibCash! 🎉"
            )
        except Exception as e:
            logger.error(f"فشل إرسال رسالة للمستخدم {user_id}: {e}")

        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n✅ **تمت الموافقة على الطلب بواسطة المشرف**",
            parse_mode="Markdown",
            reply_markup=None
        )
        await query.message.reply_text("✅ تمت الموافقة وإضافة الرصيد للمستخدم.")

    elif action == 'reject':
        await update_charge_request_status(request_id, 'rejected', admin_id)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ **تم رفض طلب الشحن**\n\n"
                     f"📋 رقم الطلب: `#{request_id}`\n"
                     f"💰 المبلغ: **{amount:.2f}$**\n\n"
                     f"قد يكون السبب صورة غير واضحة أو عدم تطابق المبلغ.\n"
                     f"يمكنك إعادة المحاولة من جديد."
            )
        except Exception as e:
            logger.error(f"فشل إرسال رسالة للمستخدم {user_id}: {e}")

        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n❌ **تم رفض الطلب بواسطة المشرف**",
            parse_mode="Markdown",
            reply_markup=None
        )
        await query.message.reply_text("❌ تم رفض الطلب.")

def get_charge_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_charge, pattern="^wallet_charge$"),
        ],
        states={
            ENTERING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount),
            ],
            ENTERING_SCREENSHOT: [
                MessageHandler(filters.PHOTO, enter_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: u.message.reply_text("⚠️ أرسل صورة وليس نصاً.")),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", charge_cancel),
        ],
    )
