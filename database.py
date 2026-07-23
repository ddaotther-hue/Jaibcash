import os
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ===== اتصال قاعدة البيانات =====
DB_PATH = os.getenv("DB_PATH", "data/jaibcash.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, language TEXT DEFAULT 'ar', approved_tasks INTEGER DEFAULT 0, level INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, trust_score INTEGER DEFAULT 50, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS balances (user_id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0, total_earned INTEGER DEFAULT 0, total_withdrawn INTEGER DEFAULT 0, referral_earnings INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, amount INTEGER, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, wallet_address TEXT, status TEXT DEFAULT 'pending', tx_hash TEXT, requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, processed_at TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS referrals (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, referred_id INTEGER UNIQUE, status TEXT DEFAULT 'pending', total_earned INTEGER DEFAULT 0, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS daily_checkins (user_id INTEGER PRIMARY KEY, streak INTEGER DEFAULT 1, last_checkin DATE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS achievements (user_id INTEGER, achievement_id TEXT, unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, achievement_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS advertiser_wallets (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, frozen_balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS charge_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, screenshot_file_id TEXT, status TEXT DEFAULT 'pending', requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reviewed_at TIMESTAMP, reviewer_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, advertiser_id INTEGER, type TEXT, link TEXT, description TEXT, image_file_id TEXT, proof_type TEXT, target_count INTEGER, price_per_person REAL, total_cost REAL, commission REAL, points_per_person INTEGER, total_points_charged INTEGER, completed_count INTEGER DEFAULT 0, status TEXT DEFAULT 'active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS task_submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER, user_id INTEGER, proof_text TEXT, proof_image_file_id TEXT, status TEXT DEFAULT 'pending', submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reviewed_at TIMESTAMP, reviewer_id INTEGER, points_awarded INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_ad_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ad_id TEXT, ad_source TEXT, watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_ad_cooldown (user_id INTEGER PRIMARY KEY, last_ad_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()
    logger.info("✅ تم إنشاء جميع الجداول")

def create_user(user_id, username=None, first_name=None, lang='ar'):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, language) VALUES (?, ?, ?, ?)', (user_id, username, first_name, lang))
    cursor.execute('INSERT OR IGNORE INTO balances (user_id, points) VALUES (?, 0)', (user_id,))
    cursor.execute('INSERT OR IGNORE INTO advertiser_wallets (user_id, balance, frozen_balance) VALUES (?, 0.0, 0.0)', (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def is_banned(user_id):
    user = get_user(user_id)
    return user['is_banned'] == 1 if user else False

def ban_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT points FROM balances WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result['points'] if result else 0

def update_balance(user_id, amount, transaction_type, description=''):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE balances SET points = points + ?, total_earned = total_earned + ? WHERE user_id = ?', (amount, max(amount, 0), user_id))
    cursor.execute('INSERT INTO transactions (user_id, type, amount, description) VALUES (?, ?, ?, ?)', (user_id, transaction_type, amount, description))
    conn.commit()
    conn.close()

def update_approved_tasks(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET approved_tasks = approved_tasks + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def set_level(user_id, level):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET level = ? WHERE user_id = ?', (level, user_id))
    conn.commit()
    conn.close()

def add_referral(referrer_id, referred_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO referrals (referrer_id, referred_id, status) VALUES (?, ?, "pending")', (referrer_id, referred_id))
    conn.commit()
    conn.close()

def get_referral_stats(referrer_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (referrer_id,))
    total = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND status = "active"', (referrer_id,))
    active = cursor.fetchone()[0]
    cursor.execute('SELECT COALESCE(SUM(total_earned), 0) FROM referrals WHERE referrer_id = ? AND status = "active"', (referrer_id,))
    earnings = cursor.fetchone()[0]
    conn.close()
    return {'total': total, 'active': active, 'earnings': earnings}

def get_referrer_by_referred(referred_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT referrer_id FROM referrals WHERE referred_id = ?', (referred_id,))
    row = cursor.fetchone()
    conn.close()
    return row['referrer_id'] if row else None

def process_referral_earnings(user_id: int, points: int, source: str = ""):
    if points <= 0:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, referrer_id, status FROM referrals WHERE referred_id = ? AND status = "pending" ORDER BY id ASC LIMIT 1', (user_id,))
    referral = cursor.fetchone()
    if not referral:
        conn.close()
        return
    referrer_id = referral['referrer_id']
    bonus = int(points * 0.05)
    if bonus <= 0:
        conn.close()
        return
    cursor.execute('UPDATE balances SET points = points + ?, referral_earnings = referral_earnings + ? WHERE user_id = ?', (bonus, bonus, referrer_id))
    cursor.execute('INSERT INTO transactions (user_id, type, amount, description) VALUES (?, "referral", ?, ?)', (referrer_id, bonus, f'أرباح إحالة: {source}'))
    cursor.execute('UPDATE referrals SET total_earned = total_earned + ?, status = "active" WHERE referred_id = ?', (bonus, user_id))
    conn.commit()
    conn.close()

def check_in(user_id):
    conn = get_db()
    cursor = conn.cursor()
    today = datetime.now().date()
    cursor.execute('SELECT streak, last_checkin FROM daily_checkins WHERE user_id = ?', (user_id,))
    record = cursor.fetchone()
    if record:
        last_date = datetime.strptime(record['last_checkin'], '%Y-%m-%d').date()
        diff = (today - last_date).days
        if diff == 0:
            conn.close()
            return {'success': False, 'points': 0, 'day': 0}
        new_streak = record['streak'] + 1 if diff == 1 else 1
    else:
        new_streak = 1
    points = min(new_streak, 7) * 500
    cursor.execute('INSERT OR REPLACE INTO daily_checkins (user_id, streak, last_checkin) VALUES (?, ?, ?)', (user_id, new_streak, today))
    cursor.execute('UPDATE balances SET points = points + ?, total_earned = total_earned + ? WHERE user_id = ?', (points, points, user_id))
    cursor.execute('INSERT INTO transactions (user_id, type, amount, description) VALUES (?, "checkin", ?, "تسجيل يومي")', (user_id, points))
    conn.commit()
    conn.close()
    return {'success': True, 'points': points, 'day': new_streak}

def add_withdrawal(user_id, amount_points, wallet_address):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO withdrawals (user_id, amount, wallet_address, status) VALUES (?, ?, ?, "pending")', (user_id, amount_points, wallet_address))
    conn.commit()
    conn.close()

def get_withdrawals(user_id, limit=10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM withdrawals WHERE user_id = ? ORDER BY requested_at DESC LIMIT ?', (user_id, limit))
    results = cursor.fetchall()
    conn.close()
    return results

def get_leaderboard(limit=10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT u.user_id, u.username, u.first_name, b.points FROM balances b JOIN users u ON u.user_id = b.user_id WHERE u.is_banned = 0 ORDER BY b.points DESC LIMIT ?', (limit,))
    results = cursor.fetchall()
    conn.close()
    return results

async def get_advertiser_balance(user_id: int) -> float:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM advertiser_wallets WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['balance'] if row else 0.0

async def get_advertiser_frozen_balance(user_id: int) -> float:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT frozen_balance FROM advertiser_wallets WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['frozen_balance'] if row else 0.0

async def get_advertiser_total_balance(user_id: int) -> float:
    return await get_advertiser_balance(user_id) + await get_advertiser_frozen_balance(user_id)

async def deduct_advertiser_balance(user_id: int, amount: float) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM advertiser_wallets WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row or row['balance'] < amount:
        conn.close()
        return False
    cursor.execute('UPDATE advertiser_wallets SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ?', (amount, amount, user_id))
    conn.commit()
    conn.close()
    return True

async def save_charge_request(user_id: int, amount: float, file_id: str) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO charge_requests (user_id, amount, screenshot_file_id, status) VALUES (?, ?, ?, "pending")', (user_id, amount, file_id))
    conn.commit()
    request_id = cursor.lastrowid
    conn.close()
    return request_id

async def get_charge_request(request_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM charge_requests WHERE id = ?', (request_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

async def update_charge_request_status(request_id: int, status: str, reviewer_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE charge_requests SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewer_id = ? WHERE id = ?', (status, reviewer_id, request_id))
    conn.commit()
    conn.close()

async def save_task(task_dict: dict) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (advertiser_id, type, link, description, image_file_id, proof_type, target_count, price_per_person, total_cost, commission, points_per_person, total_points_charged) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (task_dict['advertiser_id'], task_dict['type'], task_dict.get('link', ''), task_dict.get('description', ''), task_dict.get('image_file_id', None), task_dict.get('proof_type', 'photo_username'), task_dict['target_count'], task_dict['price_per_person'], task_dict['total_cost'], task_dict['commission'], task_dict['points_per_person'], task_dict['total_points_charged']))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id

async def get_task_by_id(task_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

async def get_task_owner(task_id: int) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT advertiser_id FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    return row['advertiser_id'] if row else None

async def increment_task_completed(task_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET completed_count = completed_count + 1, status = CASE WHEN completed_count + 1 >= target_count THEN "completed" ELSE "active" END WHERE id = ? AND status != "completed"', (task_id,))
    conn.commit()
    conn.close()

async def save_task_submission(task_id: int, user_id: int, proof_text: str = None, proof_image_id: str = None) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO task_submissions (task_id, user_id, proof_text, proof_image_file_id, status) VALUES (?, ?, ?, ?, "pending")', (task_id, user_id, proof_text, proof_image_id))
    conn.commit()
    submission_id = cursor.lastrowid
    conn.close()
    return submission_id

async def get_task_submission(submission_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM task_submissions WHERE id = ?', (submission_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

async def update_task_submission_status(submission_id: int, status: str, reviewer_id: int, points: int = None):
    conn = get_db()
    cursor = conn.cursor()
    if points is not None:
        cursor.execute('UPDATE task_submissions SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewer_id = ?, points_awarded = ? WHERE id = ?', (status, reviewer_id, points, submission_id))
    else:
        cursor.execute('UPDATE task_submissions SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewer_id = ? WHERE id = ?', (status, reviewer_id, submission_id))
    conn.commit()
    conn.close()

def unlock_achievement(user_id, achievement_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO achievements (user_id, achievement_id) VALUES (?, ?)', (user_id, achievement_id))
    conn.commit()
    conn.close()

def get_achievements(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT achievement_id FROM achievements WHERE user_id = ?', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return [r['achievement_id'] for r in results]

async def get_transactions(user_id: int, limit: int = 20):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

def save_user_ad(user_id: int, ad_id: str, ad_source: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO user_ad_history (user_id, ad_id, ad_source) VALUES (?, ?, ?)', (user_id, ad_id, ad_source))
    conn.commit()
    conn.close()

def get_user_recent_ads(user_id: int, hours: int = 24) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT ad_id, ad_source FROM user_ad_history WHERE user_id = ? AND watched_at > datetime("now", "-" || ? || " hours") ORDER BY watched_at DESC', (user_id, hours))
    results = cursor.fetchall()
    conn.close()
    return [{'ad_id': r['ad_id'], 'ad_source': r['ad_source']} for r in results]

def get_last_ad_time(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT last_ad_time FROM user_ad_cooldown WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['last_ad_time'] if row else None

def update_last_ad_time(user_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO user_ad_cooldown (user_id, last_ad_time) VALUES (?, CURRENT_TIMESTAMP)', (user_id,))
    conn.commit()
    conn.close()

def is_ad_seen_recently(user_id: int, ad_id: str, ad_source: str, hours: int = 24) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM user_ad_history WHERE user_id = ? AND ad_id = ? AND ad_source = ? AND watched_at > datetime("now", "-" || ? || " hours")', (user_id, ad_id, ad_source, hours))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def set_language(user_id, lang):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN language TEXT DEFAULT "ar"')
    except:
        pass
    cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang, user_id))
    conn.commit()
    conn.close()

def get_language(user_id):
    user = get_user(user_id)
    return user['language'] if user else 'ar'

# ===== دوال محفظة المعلن (المفقودة) =====

async def add_advertiser_balance(user_id: int, amount: float):
    """إضافة رصيد لمحفظة المعلن"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO advertiser_wallets (user_id, balance, frozen_balance)
        VALUES (?, ?, 0.0)
        ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
    ''', (user_id, amount, amount))
    conn.commit()
    conn.close()

async def freeze_advertiser_balance(user_id: int, amount: float) -> bool:
    """تجميد رصيد المعلن"""
    if amount <= 0:
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM advertiser_wallets WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row or row['balance'] < amount:
        conn.close()
        return False
    cursor.execute('''
        UPDATE advertiser_wallets
        SET balance = balance - ?,
            frozen_balance = frozen_balance + ?
        WHERE user_id = ?
    ''', (amount, amount, user_id))
    conn.commit()
    conn.close()
    return True

async def release_frozen_balance(user_id: int, amount: float, to_spent: bool = True):
    """تحرير الرصيد المجمد"""
    if amount <= 0:
        return
    conn = get_db()
    cursor = conn.cursor()
    if to_spent:
        cursor.execute('''
            UPDATE advertiser_wallets
            SET frozen_balance = frozen_balance - ?,
                total_spent = total_spent + ?
            WHERE user_id = ?
        ''', (amount, amount, user_id))
    else:
        cursor.execute('''
            UPDATE advertiser_wallets
            SET frozen_balance = frozen_balance - ?,
                balance = balance + ?
            WHERE user_id = ?
        ''', (amount, amount, user_id))
    conn.commit()
    conn.close()

async def update_advertiser_total_spent(user_id: int, amount: float):
    """تحديث إجمالي ما أنفقه المعلن"""
    if amount <= 0:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE advertiser_wallets
        SET total_spent = total_spent + ?
        WHERE user_id = ?
    ''', (amount, user_id))
    conn.commit()
    conn.close()


def get_users_count():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_referrals(limit=20):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.referrer_id, r.referred_id, r.status, r.joined_at,
               ru.username AS referrer_username, ru.first_name AS referrer_name,
               du.username AS referred_username, du.first_name AS referred_name
        FROM referrals r
        LEFT JOIN users ru ON ru.user_id = r.referrer_id
        LEFT JOIN users du ON du.user_id = r.referred_id
        ORDER BY r.joined_at DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_advertiser_tasks(advertiser_id, limit=15):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE advertiser_id = ? ORDER BY created_at DESC LIMIT ?', (advertiser_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_task_submission_counts(task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT status, COUNT(*) as cnt FROM task_submissions WHERE task_id = ? GROUP BY status', (task_id,))
    rows = cursor.fetchall()
    conn.close()
    counts = {'pending': 0, 'approved': 0, 'rejected': 0}
    for r in rows:
        counts[r['status']] = r['cnt']
    return counts

# ===== دوال API الإضافية للميني آب =====

def get_leaderboard_api(limit=10):
    """الحصول على قائمة المتصدرين (نسخة API)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.user_id, u.username, u.first_name, b.points as balance, u.level
        FROM balances b 
        JOIN users u ON u.user_id = b.user_id 
        WHERE u.is_banned = 0 
        ORDER BY b.points DESC 
        LIMIT ?
    ''', (limit,))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_transactions_api(user_id, limit=20):
    """الحصول على سجل المعاملات (نسخة API)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM transactions 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (user_id, limit))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def add_points_to_user(user_id, points, reason):
    """إضافة نقاط للمستخدم مع تسجيل المعاملة"""
    if points <= 0:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE balances SET points = points + ?, total_earned = total_earned + ? 
        WHERE user_id = ?
    ''', (points, points, user_id))
    cursor.execute('''
        INSERT INTO transactions (user_id, type, amount, description) 
        VALUES (?, 'earn', ?, ?)
    ''', (user_id, points, reason))
    conn.commit()
    conn.close()

def claim_reward(user_id):
    """سحب النقاط اليومي"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT last_claim FROM users WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    
    from datetime import datetime, timedelta
    now = datetime.now()
    
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN last_claim TIMESTAMP')
        conn.commit()
    except:
        pass
    
    if row and row[0]:
        last_claim = datetime.fromisoformat(row[0])
        if (now - last_claim).total_seconds() < 86400:
            conn.close()
            raise Exception("تم السحب اليومي مسبقاً")
    
    points = 15
    cursor.execute('''
        UPDATE users SET last_claim = ? WHERE user_id = ?
    ''', (now.isoformat(), user_id))
    cursor.execute('''
        UPDATE balances SET points = points + ?, total_earned = total_earned + ? 
        WHERE user_id = ?
    ''', (points, points, user_id))
    cursor.execute('''
        INSERT INTO transactions (user_id, type, amount, description) 
        VALUES (?, 'earn', ?, 'سحب يومي')
    ''', (user_id, points))
    conn.commit()
    conn.close()
    return {"points": points, "message": "تم السحب اليومي"}

def withdraw_points(user_id, amount):
    """طلب سحب النقود"""
    balance = get_balance(user_id)
    if balance < amount:
        raise Exception("الرصيد غير كافٍ")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE balances SET points = points - ?, total_withdrawn = total_withdrawn + ? 
        WHERE user_id = ?
    ''', (amount, amount, user_id))
    cursor.execute('''
        INSERT INTO transactions (user_id, type, amount, description) 
        VALUES (?, 'withdraw', ?, 'طلب سحب')
    ''', (user_id, amount))
    conn.commit()
    conn.close()
    return {"amount": amount, "status": "pending"}

def get_checkin_status(user_id):
    """التحقق من حالة التسجيل اليومي"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT streak, last_checkin FROM daily_checkins WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"can_checkin": True, "last_checkin": None, "streak": 0}
    
    from datetime import datetime, timedelta
    last_checkin = row['last_checkin']
    streak = row['streak'] or 1
    
    if last_checkin:
        last = datetime.fromisoformat(last_checkin)
        now = datetime.now()
        diff = (now - last).total_seconds()
        
        if diff < 86400:
            return {"can_checkin": False, "last_checkin": last_checkin, "streak": streak}
        elif diff < 172800:
            streak += 1
        else:
            streak = 1
    else:
        streak = 1
    
    return {"can_checkin": True, "last_checkin": last_checkin, "streak": streak}

def do_checkin(user_id):
    """تنفيذ التسجيل اليومي"""
    status = get_checkin_status(user_id)
    if not status.get('can_checkin'):
        raise Exception("لا يمكن التسجيل اليومي الآن")
    
    from datetime import datetime
    points = 10 + status.get('streak', 1) * 2
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO daily_checkins (user_id, streak, last_checkin) 
        VALUES (?, ?, ?)
    ''', (user_id, status.get('streak', 1), datetime.now().isoformat()))
    cursor.execute('''
        UPDATE balances SET points = points + ?, total_earned = total_earned + ? 
        WHERE user_id = ?
    ''', (points, points, user_id))
    cursor.execute('''
        INSERT INTO transactions (user_id, type, amount, description) 
        VALUES (?, 'earn', ?, 'تسجيل يومي')
    ''', (user_id, points))
    conn.commit()
    conn.close()
    return {"points": points, "streak": status.get('streak', 1)}

def get_referrals_list(user_id):
    """الحصول على قائمة الإحالات"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.user_id, u.username, u.first_name, u.joined_at, b.points as balance
        FROM referrals r
        JOIN users u ON u.user_id = r.referred_id
        LEFT JOIN balances b ON b.user_id = u.user_id
        WHERE r.referrer_id = ?
        ORDER BY r.joined_at DESC
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_available_tasks(user_id):
    """المهام المتاحة للمستخدم"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM tasks 
        WHERE status = 'active'
        AND id NOT IN (
            SELECT task_id FROM task_submissions 
            WHERE user_id = ? AND status IN ('pending', 'approved')
        )
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_user_tasks(user_id):
    """مهام المستخدم الحالية"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, ts.status as submission_status, ts.submitted_at, ts.points_awarded
        FROM task_submissions ts
        JOIN tasks t ON ts.task_id = t.id
        WHERE ts.user_id = ?
        ORDER BY ts.submitted_at DESC
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_user_level(user_id):
    """مستوى المستخدم"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT level FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['level'] if row else 0

def get_user_stats(user_id):
    """إحصائيات المستخدم"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT ts.task_id) as total_tasks,
            COALESCE(SUM(ts.points_awarded), 0) as total_earned,
            (SELECT COUNT(*) FROM referrals WHERE referrer_id = ?) as total_referrals
        FROM task_submissions ts
        WHERE ts.user_id = ? AND ts.status = 'approved'
    ''', (user_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

def get_user_achievements(user_id):
    """إنجازات المستخدم"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT achievement_id, unlocked_at FROM achievements 
        WHERE user_id = ?
        ORDER BY unlocked_at DESC
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_referral_link(user_id):
    """رابط الإحالة للمستخدم"""
    return f"https://t.me/JaibCashBot?start=ref_{user_id}"
