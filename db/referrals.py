import logging
from .core import get_db

logger = logging.getLogger(__name__)

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
    """جلب معرف المحيل من خلال معرف المُحال"""
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

    logger.info(f"✅ إحالة: {referrer_id} ← {user_id} | مكافأة: {bonus} نقطة (5%) من {source}")

def activate_referral(user_id: int):
    """تفعيل الإحالة (جعلها active)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE referrals SET status = "active" WHERE referred_id = ?', (user_id,))
    conn.commit()
    conn.close()
