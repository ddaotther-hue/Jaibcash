from flask import Flask, request, jsonify
import sqlite3
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "jaibcash.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_tables():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, language TEXT DEFAULT "ar", approved_tasks INTEGER DEFAULT 0, level INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, trust_score INTEGER DEFAULT 50, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS balances (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, total_earned INTEGER DEFAULT 0, total_withdrawn INTEGER DEFAULT 0, referral_earnings INTEGER DEFAULT 0)')
        cursor.execute('CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, amount INTEGER, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor.execute('CREATE TABLE IF NOT EXISTS advertiser_wallets (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, frozen_balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0)')
        conn.commit()
        conn.close()
        logger.info("✅ الجداول جاهزة")
        return True
    except Exception as e:
        logger.error(f"❌ فشل إنشاء الجداول: {e}")
        return False

def execute_with_retry(operations, max_retries=5):
    for attempt in range(max_retries):
        try:
            conn = get_db()
            cursor = conn.cursor()
            for op in operations:
                cursor.execute(op['sql'], op['params'])
            conn.commit()
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.5
                logger.warning(f"⚠️ قفل، إعادة المحاولة {attempt+1}/{max_retries} بعد {wait_time} ثانية...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"❌ فشل: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ خطأ: {e}")
            return False
    return False

def add_points(user_id, points):
    operations = [
        {'sql': 'INSERT OR IGNORE INTO users (user_id) VALUES (?)', 'params': (user_id,)},
        {'sql': 'INSERT OR IGNORE INTO balances (user_id, points, total_earned) VALUES (?, ?, ?)', 'params': (user_id, 0, 0)},
        {'sql': 'INSERT OR IGNORE INTO advertiser_wallets (user_id, balance, frozen_balance) VALUES (?, ?, ?)', 'params': (user_id, 0.0, 0.0)},
        {'sql': 'UPDATE balances SET points = points + ?, total_earned = total_earned + ? WHERE user_id = ?', 'params': (points, points, user_id)},
        {'sql': 'INSERT INTO transactions (user_id, type, amount, description) VALUES (?, "ad", ?, "مشاهدة إعلان (AdsGram)")', 'params': (user_id, points)}
    ]
    if execute_with_retry(operations):
        logger.info(f"✅ تم إضافة {points} نقطة للمستخدم {user_id}")
        return True
    return False

@app.route('/reward', methods=['GET', 'POST'])
def reward():
    user_id = request.args.get('userId')
    if not user_id:
        return jsonify({"error": "Missing userId"}), 400
    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "Invalid userId"}), 400
    if add_points(user_id, 1000):
        return jsonify({"status": "success", "points": 1000}), 200
    return jsonify({"error": "Database error"}), 500

@app.route('/health', methods=['GET'])
def health():
    try:
        conn = get_db()
        conn.close()
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 500

if __name__ == '__main__':
    ensure_tables()
    logger.info("🚀 تشغيل سيرفر المكافآت على المنفذ 8001")
    app.run(host='0.0.0.0', port=8002, debug=False)
