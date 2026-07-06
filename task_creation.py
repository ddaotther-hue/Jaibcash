# ============================================================
# task_creation.py — إنشاء مهمة مع تجميد الرصيد
# ============================================================

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from database import freeze_advertiser_balance  # ✅ دالة تجميد الرصيد

logger = logging.getLogger(__name__)

# ---------- حالات المحادثة ----------
(
    CHOOSING_TYPE,
    ENTERING_LINK,
    CHECKING_BOT_MEMBERSHIP,
    ENTERING_DESCRIPTION,
    ASKING_IMAGE,
    CHOOSING_PROOF_TYPE,
    ENTERING_TARGET_COUNT,
    ENTERING_PRICE,
    REVIEWING_SUMMARY,
) = range(9)

# ---------- الإعدادات العامة ----------
_config = {
    "get_advertiser_balance": None,
    "deduct_advertiser_balance": None,
    "save_task": None,
    "points_per_dollar": 1_000_000,
    "commission_rate": 0.10,
}

# مخزن بيانات المهمة المؤقتة لكل معلن (حتى التأكيد)
_drafts = {}

# ---------- أنواع المهام وأنواع الإثبات ----------
TASK_TYPES = {
    "telegram": "📱 Telegram",
    "youtube": "🎥 YouTube",
    "social": "🌐 تواصل اجتماعي",
    "website": "🌐 موقع ويب",
    "app": "📲 تطبيق",
}

PROOF_TYPES = {
    "photo_username": "📸 صورة إثبات + اسم مستخدم",
    "username_only": "✍️ اسم مستخدم فقط",
    "none": "✅ لا تحتاج شيء",
}

# ---------- تهيئة الوحدة (تُستدعى من main.py) ----------
def init_task_creation(
    get_advertiser_balance,
    deduct_advertiser_balance,
    save_task,
    points_per_dollar=1_000_000,
    commission_rate=0.10,
):
    _config.update(
        {
            "get_advertiser_balance": get_advertiser_balance,
            "deduct_advertiser_balance": deduct_advertiser_balance,
            "save_task": save_task,
            "points_per_dollar": points_per_dollar,
            "commission_rate": commission_rate,
        }
    )
    logger.info("✅ تم تهيئة نظام إنشاء المهام")


# ---------- دوال مساعدة ----------
async def _check_bot_membership(context, link: str) -> bool:
    """التحقق من عضوية البوت في قناة/جروب تيليجرام"""
    try:
        chat_username = link.rstrip("/").split("/")[-1]
        chat_id = f"@{chat_username}" if not chat_username.startswith("@") else chat_username
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=context.bot.id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"فشل التحقق من العضوية: {e}")
        return False


# ---------- نقطة الدخول ----------
async def start_task_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يُستدعى عند الضغط على زر 'إنشاء مهمة'"""
    user_id = update.effective_user.id

    # التحقق من تهيئة الوحدة
    if _config["get_advertiser_balance"] is None:
        await update.effective_message.reply_text("⚠️ نظام إنشاء المهام غير مفعّل.")
        return ConversationHandler.END

    # جلب الرصيد المتاح (وليس الإجمالي)
    balance = await _config["get_advertiser_balance"](user_id)
    if balance <= 0:
        keyboard = [[InlineKeyboardButton("💳 شحن الرصيد", callback_data="wallet_charge")]]
        await update.effective_message.reply_text(
            "💰 رصيد محفظة المعلن: 0$\n\nلازم تشحن رصيد أول.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ConversationHandler.END

    # بدء مخزن مؤقت لهذا المعلن
    _drafts[user_id] = {"advertiser_id": user_id}

    # عرض أزرار أنواع المهام
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"tasktype_{key}")]
        for key, label in TASK_TYPES.items()
    ]
    await update.effective_message.reply_text(
        f"💰 رصيدك المتاح: {balance:.2f}$\n\n"
        "1️⃣ اختر نوع المهمة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_TYPE


# ---------- اختيار نوع المهمة ----------
async def choose_task_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    task_type = query.data.replace("tasktype_", "")

    if task_type not in TASK_TYPES:
        await query.message.reply_text("⚠️ نوع غير معروف. اختر من الأزرار.")
        return CHOOSING_TYPE

    _drafts[user_id]["type"] = task_type
    logger.info(f"✅ المستخدم {user_id} اختار نوع المهمة: {task_type}")

    if task_type == "telegram":
        await query.message.reply_text(
            "2️⃣ أرسل رابط القناة أو الجروب (يجب إضافة @JaibCashBot كعضو)."
        )
    else:
        await query.message.reply_text(
            "2️⃣ أرسل رابط المهمة (الفيديو / الحساب / الموقع / التطبيق):"
        )
    return ENTERING_LINK


# ---------- إدخال الرابط ----------
async def enter_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = update.message.text.strip()
    _drafts[user_id]["link"] = link

    # إذا كان النوع Telegram، نتحقق من عضوية البوت
    if _drafts[user_id]["type"] == "telegram":
        if not await _check_bot_membership(context, link):
            keyboard = [[InlineKeyboardButton("🔄 أعد الفحص", callback_data="recheck_membership")]]
            await update.message.reply_text(
                "❌ البوت ليس عضواً بالقناة/الجروب. تأكد ثم أعد الفحص.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return CHECKING_BOT_MEMBERSHIP
        _drafts[user_id]["proof_type"] = "auto_telegram_membership"
        await update.message.reply_text("✅ تم التحقق! البوت عضو.")

    # الانتقال لطلب الوصف
    await _ask_description(update.message, context)
    return ENTERING_DESCRIPTION


# ---------- إعادة فحص العضوية (عند الضغط على زر أعد الفحص) ----------
async def recheck_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    link = _drafts[user_id].get("link", "")
    if not await _check_bot_membership(context, link):
        await query.message.reply_text("❌ لسا البوت مش عضو. تأكد وأعد المحاولة.")
        return CHECKING_BOT_MEMBERSHIP

    _drafts[user_id]["proof_type"] = "auto_telegram_membership"
    await query.message.reply_text("✅ تم التحقق! البوت عضو.")
    await _ask_description(query.message, context)
    return ENTERING_DESCRIPTION


# ---------- طلب الوصف ----------
async def _ask_description(message, context=None):
    await message.reply_text("3️⃣ اكتب وصف المهمة (شو المطلوب بالضبط من المنفذ):")


async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _drafts[user_id]["description"] = update.message.text.strip()

    keyboard = [
        [InlineKeyboardButton("📎 إرفاق صورة توضيحية", callback_data="add_reference_image")],
        [InlineKeyboardButton("⏭️ تخطي", callback_data="skip_reference_image")],
    ]
    await update.message.reply_text(
        "هل تريد إرفاق صورة مرجعية توضح شكل المهمة؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASKING_IMAGE


# ---------- التعامل مع الصورة التوضيحية ----------
async def skip_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    _drafts[user_id]["image_file_id"] = None
    return await _proceed_to_proof_type(query.message, user_id, context)


async def request_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("أرسل الصورة الآن:")
    return ASKING_IMAGE


async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.photo:
        await update.message.reply_text("⚠️ يرجى إرسال صورة.")
        return ASKING_IMAGE
    _drafts[user_id]["image_file_id"] = update.message.photo[-1].file_id
    await update.message.reply_text("✅ تم حفظ الصورة.")
    return await _proceed_to_proof_type(update.message, user_id, context)


# ---------- اختيار نوع الإثبات (لغير Telegram) ----------
async def _proceed_to_proof_type(message, user_id, context):
    if _drafts[user_id]["type"] == "telegram":
        # مهام Telegram تتحقق تلقائياً، لا حاجة لسؤال الإثبات
        await _ask_target_count(message)
        return ENTERING_TARGET_COUNT

    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"proof_{key}")]
        for key, label in PROOF_TYPES.items()
    ]
    await message.reply_text(
        "4️⃣ ما نوع الإثبات المطلوب من المنفذ؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_PROOF_TYPE


async def choose_proof_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    proof_type = query.data.replace("proof_", "")
    _drafts[user_id]["proof_type"] = proof_type
    await _ask_target_count(query.message)
    return ENTERING_TARGET_COUNT


# ---------- عدد المنفذين ----------
async def _ask_target_count(message):
    await message.reply_text("5️⃣ كم شخص تريد أن ينجز هذه المهمة؟ (أرسل رقماً، مثال: 100)")


async def enter_target_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("⚠️ أرسل رقماً صحيحاً أكبر من صفر.")
        return ENTERING_TARGET_COUNT
    _drafts[user_id]["target_count"] = int(text)
    await update.message.reply_text(
        "6️⃣ كم تدفع لكل شخص ينجز المهمة؟ (بالدولار، مثال: 0.10)"
    )
    return ENTERING_PRICE


# ---------- السعر لكل شخص ----------
async def enter_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().replace("$", "")
    try:
        price = float(text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ أرسل قيمة صحيحة أكبر من صفر (مثال: 0.10).")
        return ENTERING_PRICE

    _drafts[user_id]["price_per_person"] = price
    return await _show_summary(update.message, user_id, context)


# ---------- شاشة المراجعة النهائية ----------
async def _show_summary(message, user_id, context):
    draft = _drafts[user_id]
    total_cost = draft["target_count"] * draft["price_per_person"]
    commission = total_cost * _config["commission_rate"]
    points_per_person = int(
        ((total_cost - commission) / draft["target_count"]) * _config["points_per_dollar"]
    )
    draft["total_cost"] = total_cost
    draft["commission"] = commission
    draft["points_per_person"] = points_per_person
    draft["total_points_charged"] = int(total_cost * _config["points_per_dollar"])

    text = (
        "📊 ملخص المهمة:\n────────────────\n"
        f"النوع: {TASK_TYPES[draft['type']]}\n"
        f"الرابط: {draft.get('link', '—')}\n"
        f"الوصف: {draft['description']}\n────────────────\n"
        f"عدد المنفذين: {draft['target_count']}\n"
        f"السعر لكل شخص: {draft['price_per_person']:.2f}$\n────────────────\n"
        f"الإجمالي: {total_cost:.2f}$\n"
        f"عمولة المنصة ({int(_config['commission_rate']*100)}%): {commission:.2f}$\n────────────────\n"
        f"💰 المخصوم: {total_cost:.2f}$ ({draft['total_points_charged']:,} نقطة)\n"
        f"✅ كل منفذ سيحصل على: {points_per_person:,} نقطة\n\n"
        "⚠️ لا يمكن التراجع أو استرداد المبلغ بعد النشر."
    )

    keyboard = [
        [InlineKeyboardButton("✅ تأكيد ونشر المهمة", callback_data="confirm_task")],
        [InlineKeyboardButton("❌ إلغاء والتعديل", callback_data="cancel_task")],
    ]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return REVIEWING_SUMMARY


# ---------- تأكيد النشر (مع تجميد الرصيد) ----------
async def confirm_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    draft = _drafts.get(user_id)

    if not draft:
        await query.message.reply_text("⚠️ لم يتم العثور على بيانات المهمة. ابدأ من جديد.")
        return ConversationHandler.END

    # ✅ تجميد الرصيد بدلاً من الخصم المباشر
    amount_to_freeze = draft["total_cost"]
    logger.info(f"💰 محاولة تجميد {amount_to_freeze:.2f}$ للمستخدم {user_id}")
    success = await freeze_advertiser_balance(user_id, amount_to_freeze)

    if not success:
        await query.message.reply_text(
            "❌ فشل تجميد الرصيد (رصيد غير كافٍ). تأكد من رصيدك المتاح."
        )
        _drafts.pop(user_id, None)
        return ConversationHandler.END

    # حفظ المهمة في قاعدة البيانات
    task_id = await _config["save_task"](draft)
    await query.message.reply_text(
        f"🎉 تم نشر المهمة بنجاح! رقم المهمة: #{task_id}\n"
        f"💰 تم تجميد {amount_to_freeze:.2f}$ من رصيدك المتاح."
    )

    # تنظيف المخزن المؤقت
    _drafts.pop(user_id, None)
    return ConversationHandler.END


# ---------- إلغاء النشر (بدون خصم) ----------
async def cancel_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    _drafts.pop(user_id, None)
    await query.message.reply_text("تم الإلغاء، لم يُخصم أي مبلغ.")
    return ConversationHandler.END


# ---------- أمر الإلغاء العام ----------
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _drafts.pop(user_id, None)
    await update.message.reply_text("تم إلغاء إنشاء المهمة.")
    return ConversationHandler.END


# ---------- بناء معالج المحادثة ----------
def get_task_creation_handler() -> ConversationHandler:
    """إرجاع معالج المحادثة الخاص بإنشاء المهام لاستخدامه في main.py"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_task_creation, pattern="^create_task$"),
        ],
        states={
            CHOOSING_TYPE: [
                CallbackQueryHandler(choose_task_type, pattern="^tasktype_"),
            ],
            ENTERING_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_link),
            ],
            CHECKING_BOT_MEMBERSHIP: [
                CallbackQueryHandler(recheck_membership, pattern="^recheck_membership$"),
            ],
            ENTERING_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description),
            ],
            ASKING_IMAGE: [
                CallbackQueryHandler(request_image, pattern="^add_reference_image$"),
                CallbackQueryHandler(skip_image, pattern="^skip_reference_image$"),
                MessageHandler(filters.PHOTO, receive_image),
            ],
            CHOOSING_PROOF_TYPE: [
                CallbackQueryHandler(choose_proof_type, pattern="^proof_"),
            ],
            ENTERING_TARGET_COUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_target_count),
            ],
            ENTERING_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_price),
            ],
            REVIEWING_SUMMARY: [
                CallbackQueryHandler(confirm_task, pattern="^confirm_task$"),
                CallbackQueryHandler(cancel_task, pattern="^cancel_task$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
        ],
    )
