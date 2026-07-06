"""
أمر اختبار مؤقت: /testref
===========================
يحاكي بالضبط نفس منطق استقبال إحالة حقيقية (نفس الكود الموجود بـ start()،
بس بدون الحاجة لحساب Telegram جديد كلياً أو رابط ?start= فعلي).

⚠️ هذا أمر اختباري فقط للمطور/المشرف — لازم تشيله أو تقيّده بشكل صارم
قبل إطلاق البوت للجمهور، لأنه لو ضل مفتوح لأي مستخدم، ممكن يُستغل
لتسجيل إحالات وهمية بدون أي تحقق حقيقي.

طريقة الاستخدام من Telegram:
    /testref REFERRER_ID REFERRED_ID

مثال:
    /testref 1488610580 1091815563
    (يعني: 1488610580 هو المحيل، 1091815563 هو المُحال)
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import add_referral, create_user

logger = logging.getLogger(__name__)

# ⚠️ عدّل هذا لآيدي حسابك الشخصي فقط — الأمر يشتغل معك أنت بس
ADMIN_IDS = [1488610580]  # استبدل برقم الـ Telegram ID تبعك


async def testref_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "الاستخدام: /testref REFERRER_ID REFERRED_ID\n"
            "مثال: /testref 1488610580 1091815563"
        )
        return

    try:
        referrer_id = int(context.args[0])
        referred_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text("⚠️ لازم تكتب أرقام صحيحة (Telegram User IDs).")
        return

    if referrer_id == referred_id:
        await update.message.reply_text("⚠️ لا يمكن أن يكون المحيل والمُحال نفس الشخص.")
        return

    # نفس منطق start() بالضبط: تأكد المُحال موجود بقاعدة البيانات، وسجّل الإحالة
    create_user(referred_id, username=f"test_{referred_id}", first_name="Test User", lang="ar")
    add_referral(referrer_id, referred_id)

    logger.info(f"✅ [TEST] إحالة تجريبية: {referrer_id} → {referred_id}")
    await update.message.reply_text(
        f"✅ تم تسجيل إحالة تجريبية:\n"
        f"المحيل: {referrer_id}\n"
        f"المُحال: {referred_id}\n\n"
        f"روح افحص '👥 الإحالة' بحساب المحيل ({referrer_id}) وشوف هل زاد العداد."
    )
