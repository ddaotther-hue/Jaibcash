import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import (
    get_db, save_task_submission, get_task_submission, update_task_submission_status,
    get_task_by_id, get_task_owner, get_user, update_balance,
    release_frozen_balance, increment_task_completed, process_referral_earnings
)
from i18n import t
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# حالات المحادثة
ASKING_PROOF_TEXT, ASKING_PROOF_IMAGE = range(2)

async def browse_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المهام النشطة"""
    user_id = update.effective_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, type, link, description, points_per_person, target_count, completed_count
        FROM tasks WHERE status = 'active' ORDER BY created_at DESC LIMIT 10
    ''')
    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        await update.effective_message.reply_text("📭 لا توجد مهام متاحة حالياً.")
        return

    for task in tasks:
        task_id = task['id']
        task_type = task['type']
        link = task['link'] if task['link'] is not None else ''
        description = task['description']
        points = task['points_per_person']
        total = task['target_count']
        completed = task['completed_count']
        remaining = total - completed

        type_labels = {
            "telegram": "📱 Telegram",
            "youtube": "🎥 YouTube",
            "social": "🌐 تواصل اجتماعي",
            "website": "🌐 موقع ويب",
            "app": "📲 تطبيق"
        }
        type_label = type_labels.get(task_type, task_type)

        message_text = (
            f"📌 **{type_label}**\n"
            f"🔗 **الرابط:** {link}\n"
            f"📝 {description}\n"
            f"💰 المكافأة: **{points:,} نقطة**\n"
            f"👥 المتبقي: {remaining} من {total}\n"
        )
        keyboard = [[InlineKeyboardButton("🚀 تنفيذ المهمة", callback_data=f"execute_task_{task_id}")]]
        await update.effective_message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def start_task_execution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء تنفيذ المهمة: التحقق من عدم التكرار (موافقة سابقة)"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    task_id = int(query.data.replace("execute_task_", ""))

    # التحقق من المهمة
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, type, proof_type, target_count, completed_count, status, link, description, points_per_person
        FROM tasks WHERE id = ? AND status = 'active'
    ''', (task_id,))
    task = cursor.fetchone()
    conn.close()

    if not task:
        await query.message.reply_text("⚠️ هذه المهمة غير متاحة.")
        return
    if task['completed_count'] >= task['target_count']:
        await query.message.reply_text("⚠️ هذه المهمة اكتملت.")
        return

    # التحقق من وجود إثبات مقبول مسبقاً
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM task_submissions WHERE task_id = ? AND user_id = ? AND status = "approved"', (task_id, user_id))
    approved_count = cursor.fetchone()[0]
    conn.close()
    if approved_count > 0:
        await query.message.reply_text(
            "⚠️ **لقد تمت الموافقة على إنجازك لهذه المهمة مسبقاً.**\n\n"
            "لا يمكنك تنفيذ نفس المهمة أكثر من مرة."
        )
        return

    # التحقق من وجود طلب قيد المراجعة
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM task_submissions WHERE task_id = ? AND user_id = ? AND status = "pending"', (task_id, user_id))
    pending_count = cursor.fetchone()[0]
    conn.close()
    if pending_count > 0:
        await query.message.reply_text(
            "⏳ **لديك طلب إنجاز لهذه المهمة قيد المراجعة.**\n\n"
            "يرجى الانتظار حتى يتم البت في طلبك."
        )
        return

    # تخزين بيانات المهمة في السياق
    context.user_data['executing_task_id'] = task_id
    context.user_data['task_points'] = task['points_per_person']

    # إذا كان نوع الإثبات تلقائياً (تيليجرام)
    if task['proof_type'] == "auto_telegram_membership":
        await query.message.reply_text("✅ هذه المهمة تتحقق تلقائياً...")
        await complete_task_execution(update, context, task_id, auto=True)
        return

    # طلب اسم المستخدم
    await query.message.reply_text(
        f"🚀 **تنفيذ المهمة**\n\n"
        f"📋 رقم المهمة: #{task_id}\n"
        f"🔗 **الرابط:** {task['link'] or 'غير متوفر'}\n"
        f"📝 **الوصف:** {task['description']}\n\n"
        f"✍️ أرسل **اسم المستخدم** الخاص بك (أو أي بيانات مطلوبة) لإثبات التنفيذ."
    )
    return ASKING_PROOF_TEXT

async def receive_proof_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال اسم المستخدم (النص)"""
    proof_text = update.message.text.strip()
    if not proof_text:
        await update.message.reply_text("⚠️ لا يمكن أن يكون فارغاً. أرسل اسم المستخدم.")
        return ASKING_PROOF_TEXT

    context.user_data['proof_text'] = proof_text

    await update.message.reply_text(
        "✅ تم استلام اسم المستخدم.\n\n"
        "📸 الآن أرسل **صورة إثبات** (Screenshot) تثبت تنفيذك للمهمة.\n"
        "تأكد من وضوح الصورة وأنها تحتوي على اسم المستخدم الذي أرسلته."
    )
    return ASKING_PROOF_IMAGE

async def receive_proof_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال صورة الإثبات وإرسالها للمعلن"""
    user_id = update.effective_user.id
    task_id = context.user_data.get('executing_task_id')
    proof_text = context.user_data.get('proof_text', '')
    points = context.user_data.get('task_points', 0)

    if not task_id:
        await update.message.reply_text("⚠️ لا توجد مهمة قيد التنفيذ. ابدأ من جديد.")
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text("⚠️ يرجى إرسال صورة.")
        return ASKING_PROOF_IMAGE

    photo = update.message.photo[-1]
    file_id = photo.file_id

    # حفظ الإثبات في قاعدة البيانات
    submission_id = await save_task_submission(task_id, user_id, proof_text, file_id)

    await update.message.reply_text(
        f"✅ تم استلام إثباتك بنجاح!\n\n"
        f"📋 رقم الطلب: #{submission_id}\n"
        f"💰 المكافأة المنتظرة: {points:,} نقطة\n\n"
        f"⏳ سيتم مراجعة إثباتك من قبل صاحب المهمة في أقرب وقت ممكن.\n"
        f"ستصلك رسالة عند الموافقة أو الرفض."
    )

    # إرسال إشعار للمعلن (صاحب المهمة)
    owner_id = await get_task_owner(task_id)
    if owner_id:
        try:
            user = get_user(user_id)
            username = user['username'] if user else "غير متوفر"
            first_name = user['first_name'] if user else "مستخدم"

            owner_message = (
                f"🔔 **طلب مراجعة إثبات**\n\n"
                f"📋 رقم الطلب: #{submission_id}\n"
                f"👤 المستخدم: {first_name} (@{username})\n"
                f"🆔 المعرف: `{user_id}`\n"
                f"📝 البيانات: {proof_text}\n"
                f"💰 المكافأة: {points:,} نقطة\n"
                f"📎 الصورة مرفقة أدناه."
            )

            keyboard = [
                [
                    InlineKeyboardButton("✅ موافقة", callback_data=f"task_approve_{submission_id}"),
                    InlineKeyboardButton("❌ رفض", callback_data=f"task_reject_{submission_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_photo(
                chat_id=owner_id,
                photo=file_id,
                caption=owner_message,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            logger.info(f"✅ تم إرسال طلب المراجعة #{submission_id} لصاحب المهمة {owner_id}")
        except Exception as e:
            logger.error(f"❌ فشل إرسال الإشعار لصاحب المهمة: {e}")
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"⚠️ فشل إرسال الإشعار لصاحب المهمة. الطلب #{submission_id}",
                    )
                except:
                    pass

    # تنظيف السياق
    context.user_data.pop('executing_task_id', None)
    context.user_data.pop('proof_text', None)
    context.user_data.pop('task_points', None)

    return ConversationHandler.END

async def complete_task_execution(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int, auto: bool = False):
    """تنفيذ فوري للمهام التلقائية (دون مراجعة)"""
    user_id = update.effective_user.id
    points = context.user_data.get('task_points', 0)

    update_balance(user_id, points, 'task', f'تنفيذ مهمة #{task_id} (تلقائي)')
    
    # ✅ معالجة أرباح الإحالة
    process_referral_earnings(user_id, points, f"مهمة #{task_id} (تلقائي)")
    
    await increment_task_completed(task_id)

    await update.effective_message.reply_text(
        f"✅ **تم تنفيذ المهمة بنجاح!**\n\n"
        f"📋 رقم المهمة: #{task_id}\n"
        f"💰 حصلت على {points:,} نقطة."
    )

    context.user_data.pop('executing_task_id', None)
    context.user_data.pop('task_points', None)

async def handle_task_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج موافقة أو رفض المعلن على الإثبات"""
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id

    data = query.data
    parts = data.split('_')
    action = parts[1]  # approve أو reject
    submission_id = int(parts[2])

    # جلب الإثبات
    submission = await get_task_submission(submission_id)
    if not submission:
        await query.message.reply_text("⚠️ الإثبات غير موجود.")
        return

    if submission['status'] != 'pending':
        await query.message.reply_text(f"⚠️ هذا الإثبات تمت مراجعته مسبقاً (الحالة: {submission['status']}).")
        return

    task_id = submission['task_id']
    user_id = submission['user_id']
    task = await get_task_by_id(task_id)
    if not task:
        await query.message.reply_text("⚠️ المهمة غير موجودة.")
        return

    points = task['points_per_person']
    owner_id = await get_task_owner(task_id)

    if action == 'approve':
        # منع الموافقة إذا اكتملت المهمة
        if task['completed_count'] >= task['target_count']:
            await query.message.reply_text("⚠️ هذه المهمة اكتملت بالفعل.")
            return

        # إضافة النقاط للمستخدم المنفذ
        update_balance(user_id, points, 'task', f'تنفيذ مهمة #{task_id} (مراجعة)')
        
        # ✅ معالجة أرباح الإحالة
        process_referral_earnings(user_id, points, f"مهمة #{task_id} (مراجعة)")

        # زيادة عداد المنفذين في المهمة
        await increment_task_completed(task_id)

        # تحرير الرصيد المجمد للمعلن
        if owner_id:
            price_per_person = task['price_per_person']
            await release_frozen_balance(owner_id, price_per_person, to_spent=True)
            logger.info(f"✅ تم تحرير {price_per_person}$ من المجمد للمعلن {owner_id}")

        # تحديث حالة الإثبات
        await update_task_submission_status(submission_id, 'approved', admin_id, points)

        # إرسال رسالة للمستخدم
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ **تمت الموافقة على إثباتك!**\n\n"
                     f"📋 رقم الطلب: #{submission_id}\n"
                     f"💰 حصلت على {points:,} نقطة.\n"
                     f"🎉 شكراً لك!"
            )
        except Exception as e:
            logger.error(f"فشل إرسال رسالة للمستخدم {user_id}: {e}")

        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n✅ **تمت الموافقة بواسطة المعلن**",
            parse_mode="Markdown",
            reply_markup=None
        )
        await query.message.reply_text("✅ تمت الموافقة وإضافة النقاط للمستخدم.")

    else:  # reject
        # تحديث حالة الإثبات
        await update_task_submission_status(submission_id, 'rejected', admin_id)

        # إرسال رسالة للمستخدم
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ **تم رفض إثباتك**\n\n"
                     f"📋 رقم الطلب: #{submission_id}\n"
                     f"يمكنك إعادة تنفيذ المهمة من جديد."
            )
        except Exception as e:
            logger.error(f"فشل إرسال رسالة للمستخدم {user_id}: {e}")

        await query.edit_message_caption(
            caption=f"{query.message.caption}\n\n❌ **تم الرفض بواسطة المعلن**",
            parse_mode="Markdown",
            reply_markup=None
        )
        await query.message.reply_text("❌ تم رفض الإثبات.")

async def cancel_execution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء تنفيذ المهمة"""
    user_id = update.effective_user.id
    context.user_data.pop('executing_task_id', None)
    context.user_data.pop('proof_text', None)
    context.user_data.pop('task_points', None)
    await update.message.reply_text("❌ تم إلغاء تنفيذ المهمة.")
    return ConversationHandler.END

def get_task_execution_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_task_execution, pattern="^execute_task_"),
        ],
        states={
            ASKING_PROOF_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_proof_text),
            ],
            ASKING_PROOF_IMAGE: [
                MessageHandler(filters.PHOTO, receive_proof_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: u.message.reply_text("⚠️ أرسل صورة وليس نصاً.")),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_execution),
        ],
    )
