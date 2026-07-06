import sqlite3
import os
import logging
from config import DB_PATH
logger = logging.getLogger(__name__)

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, language TEXT DEFAULT "ar", approved_tasks INTEGER DEFAULT 0, level INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, trust_score INTEGER DEFAULT 50, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute('CREATE TABLE IF NOT EXISTS balances (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, total_earned INTEGER DEFAULT 0, total_withdrawn INTEGER DEFAULT 0, referral_earnings INTEGER DEFAULT 0, FOREIGN KEY (user_id) REFERENCES users(user_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, amount INTEGER, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(user_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, wallet_address TEXT, status TEXT DEFAULT "pending", tx_hash TEXT, requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, processed_at TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(user_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS referrals (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, referred_id INTEGER UNIQUE, status TEXT DEFAULT "pending", total_earned INTEGER DEFAULT 0, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (referrer_id) REFERENCES users(user_id), FOREIGN KEY (referred_id) REFERENCES users(user_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS daily_checkins (user_id INTEGER PRIMARY KEY, streak INTEGER DEFAULT 1, last_checkin DATE, FOREIGN KEY (user_id) REFERENCES users(user_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS achievements (user_id INTEGER, achievement_id TEXT, unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, achievement_id), FOREIGN KEY (user_id) REFERENCES users(user_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS advertiser_wallets (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, frozen_balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, FOREIGN KEY (user_id) REFERENCES users(user_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS charge_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, screenshot_file_id TEXT, status TEXT DEFAULT "pending", requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reviewed_at TIMESTAMP, reviewer_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(user_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, advertiser_id INTEGER, type TEXT, link TEXT, description TEXT, image_file_id TEXT, proof_type TEXT, target_count INTEGER, price_per_person REAL, total_cost REAL, commission REAL, points_per_person INTEGER, total_points_charged INTEGER, completed_count INTEGER DEFAULT 0, status TEXT DEFAULT "active", created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (advertiser_id) REFERENCES users(user_id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS task_submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER, user_id INTEGER, proof_text TEXT, proof_image_file_id TEXT, status TEXT DEFAULT "pending", submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reviewed_at TIMESTAMP, reviewer_id INTEGER, points_awarded INTEGER, FOREIGN KEY (task_id) REFERENCES tasks(id), FOREIGN KEY (user_id) REFERENCES users(user_id))')
    conn.commit()
    conn.close()
    logger.info("✅ تم إنشاء جميع جداول قاعدة البيانات بنجاح")
