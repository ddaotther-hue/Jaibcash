import logging
import time
import threading
from flask import Flask, jsonify
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from config import BOT_TOKEN, POINTS_PER_DOLLAR
from database import init_db, get_advertiser_balance, deduct_advertiser_balance, save_task
from handlers_start import start
from handlers_user import (
    balance, watch_ad, claim, referral, withdraw, account,
    leaderboard, rewards, checkin, advertiser_balance,
    show_my_level, show_my_stats, show_my_achievements,
    transaction_history, withdraw_advertiser_balance
)
from handlers_admin import add_points, deduct_points, ban_user_cmd, unban_user_cmd
from handlers_callback import handle_callback, handle_message
from task_creation import get_task_creation_handler, init_task_creation
from handlers_tasks import get_task_execution_handler

# تهيئة قاعدة البيانات
init_db()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== خادم ويب صغير لـ Healthcheck =====
web_app = Flask(__name__)

@web_app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

@web_app.route('/')
def index():
    return jsonify({"status": "running", "service": "JaibCash Bot"}), 200

def run_web_server():
    """تشغيل خادم الويب في خيط منفصل"""
    try:
        web_app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"⚠️ فشل تشغيل خادم الويب: {e}")

def main():
    # تشغيل خادم الويب في الخلفية
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("🌐 خادم الويب يعمل على المنفذ 8000")

    application = Application.builder().token(BOT_TOKEN).build()

    # ----- تهيئة نظام إنشاء المهام -----
    init_task_creation(
        get_advertiser_balance=get_advertiser_balance,
        deduct_advertiser_balance=deduct_advertiser_balance,
        save_task=save_task,
        points_per_dollar=POINTS_PER_DOLLAR,
        commission_rate=0.10,
    )

    application.add_handler(get_task_creation_handler())
    application.add_handler(get_task_execution_handler())

    # ----- أوامر المستخدم -----
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("watch", watch_ad))
    application.add_handler(CommandHandler("claim", claim))
    application.add_handler(CommandHandler("referral", referral))
    application.add_handler(CommandHandler("withdraw", withdraw))
    application.add_handler(CommandHandler("account", account))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("rewards", rewards))
    application.add_handler(CommandHandler("checkin", checkin))

    # ----- أوامر المشرفين -----
    application.add_handler(CommandHandler("addpoints", add_points))
    application.add_handler(CommandHandler("deductpoints", deduct_points))
    application.add_handler(CommandHandler("ban", ban_user_cmd))
    application.add_handler(CommandHandler("unban", unban_user_cmd))

    # ----- معالج الأزرار والرسائل -----
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ JaibCash Bot يعمل الآن مع دعم كامل للإحالات والمهام...")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
