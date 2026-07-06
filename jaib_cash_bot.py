"""
JaibCash Bot - بوت مكافآت بسيط مع إعلانات RichAds
================================================

قبل التشغيل، لازم تحط التوكنات كمتغيرات بيئة (Environment Variables)

طريقة التشغيل على Termux:
    export TELEGRAM_BOT_TOKEN="التوكن_تبع_البوت"
    export RICHADS_PUBLISHER_ID="409986"
    export RICHADS_WIDGET_ID="123875"
    python jaib_cash_bot.py
"""

import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------- الإعدادات (من متغيرات البيئة) ----------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
RICHADS_PUBLISHER_ID = os.environ.get("RICHADS_PUBLISHER_ID", "409986")
RICHADS_WIDGET_ID = os.environ.get("RICHADS_WIDGET_ID", "123875")
RICHADS_ENDPOINT = "http://15068.xml.adx1.com/telegram-mb"
POINTS_PER_AD = 1000
POINTS_TO_DOLLAR = 1_000_000

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- قاعدة بيانات مؤقتة بالذاكرة ----------
user_balances: dict[int, int] = {}

def get_balance(user_id: int) -> int:
    return user_balances.get(user_id, 0)

def add_points(user_id: int, points: int) -> int:
    user_balances[user_id] = get_balance(user_id) + points
    return user_balances[user_id]

# ---------- أوامر البوت ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = get_balance(user_id)
    keyboard = [
        [InlineKeyboardButton("🎥 شاهد إعلان واربح نقاط", callback_data="watch_ad")],
        [InlineKeyboardButton("💰 رصيدي", callback_data="check_balance")],
    ]
    await update.message.reply_text(
        f"أهلاً فيك بـ JaibCash! 👋\n\n"
        f"رصيدك الحالي: {balance:,} نقطة\n"
        f"({balance / POINTS_TO_DOLLAR:.4f}$)\n\n"
        f"شاهد إعلانات واربح نقاط تقدر تحولها لفلوس لاحقاً.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = get_balance(user_id)
    await update.message.reply_text(
        f"💰 رصيدك: {balance:,} نقطة\n"
        f"= {balance / POINTS_TO_DOLLAR:.4f}$"
    )

async def claim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pending = getattr(send_ad, "_pending", {})

    if pending.get(user_id):
        new_balance = add_points(user_id, POINTS_PER_AD)
        pending[user_id] = False
        await update.message.reply_text(
            f"✅ أخذت {POINTS_PER_AD:,} نقطة!\n"
            f"رصيدك الجديد: {new_balance:,} نقطة"
        )
    else:
        await update.message.reply_text(
            "ما في إعلان بانتظار التأكيد. دوس 'شاهد إعلان' الأول."
        )

# ---------- دالة عرض الإعلان ----------
async def send_ad(query, user_id: int):
    payload = {
        "language_code": "ar",
        "publisher_id": RICHADS_PUBLISHER_ID,
        "widget_id": RICHADS_WIDGET_ID,
        "telegram_id": str(user_id),
        "production": True,
    }

    try:
        response = requests.post(RICHADS_ENDPOINT, json=payload, timeout=10)
        response.raise_for_status()
        ads = response.json()

        if not ads:
            await query.message.reply_text("⚠️ ما في إعلانات متاحة هلأ، جرب بعد شوي.")
            return

        ad = ads[0]
        title = ad.get("title", "")
        message = ad.get("message", "")
        image = ad.get("image", "")
        link = ad.get("link", "")
        button_text = ad.get("button", "شاهد العرض")
        notification_url = ad.get("notification_url", "")

        caption = f"{title}\n\n{message}" if title else message
        keyboard = [[InlineKeyboardButton(button_text, url=link)]]

        pending = getattr(send_ad, "_pending", {})
        pending[user_id] = True
        send_ad._pending = pending

        if image:
            await query.message.reply_photo(
                photo=image,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                protect_content=True,
            )
        else:
            await query.message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                protect_content=True,
            )

        if notification_url:
            try:
                requests.get(notification_url, timeout=5)
            except Exception as e:
                logger.warning(f"RichAds notification failed: {e}")

    except requests.exceptions.RequestException as e:
        logger.error(f"RichAds API error: {e}")
        await query.message.reply_text("⚠️ ما في إعلانات متاحة هلأ، جرب بعد شوي.")

# ---------- معالج الأزرار ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "watch_ad":
        await send_ad(query, user_id)
    elif query.data == "check_balance":
        balance = get_balance(user_id)
        await query.message.reply_text(
            f"💰 رصيدك: {balance:,} نقطة\n"
            f"= {balance / POINTS_TO_DOLLAR:.4f}$"
        )

# ---------- تشغيل البوت ----------
def main():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("❌ TELEGRAM_BOT_TOKEN غير موجود. حطه كمتغير بيئة.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("claim", claim_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🚀 JaibCash Bot (RichAds) شغال...")
    app.run_polling()

if __name__ == "__main__":
    main()
