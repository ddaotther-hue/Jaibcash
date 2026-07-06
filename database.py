# database.py - واجهة موحدة تستورد كل الدوال من مجلد db
from db import *
from db.core import init_db

__all__ = [
    'get_db', 'init_db',
    'create_user', 'get_user', 'set_language', 'get_language',
    'update_approved_tasks', 'get_level', 'set_level',
    'is_banned', 'ban_user', 'unban_user',
    'get_balance', 'update_balance',
    'get_transactions',
    'get_transactions',
    'add_withdrawal', 'get_withdrawals', 'get_leaderboard',
    'add_referral', 'get_referral_stats',
    'process_referral_earnings',
    'check_in',
    'get_advertiser_balance', 'get_advertiser_frozen_balance',
    'get_advertiser_total_balance', 'freeze_advertiser_balance',
    'release_frozen_balance', 'add_advertiser_balance',
    'deduct_advertiser_balance', 'update_advertiser_total_spent',
    'save_charge_request', 'get_charge_request', 'update_charge_request_status',
    'save_task', 'get_task_by_id', 'get_task_owner', 'increment_task_completed',
    'save_task_submission', 'get_task_submission', 'update_task_submission_status',
    'unlock_achievement', 'get_achievements'
]

# ===== دوال تتبع الإعلانات =====

def save_user_ad(user_id: int, ad_id: str, ad_source: str):
    """حفظ إعلان شاهدته المستخدم"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_ad_history (user_id, ad_id, ad_source)
        VALUES (?, ?, ?)
    ''', (user_id, ad_id, ad_source))
    conn.commit()
    conn.close()

def get_user_recent_ads(user_id: int, hours: int = 24) -> list:
    """جلب الإعلانات التي شاهدها المستخدم خلال الساعات المحددة"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ad_id, ad_source FROM user_ad_history
        WHERE user_id = ? AND watched_at > datetime('now', '-' || ? || ' hours')
        ORDER BY watched_at DESC
    ''', (user_id, hours))
    results = cursor.fetchall()
    conn.close()
    return [{'ad_id': r['ad_id'], 'ad_source': r['ad_source']} for r in results]

def get_last_ad_time(user_id: int):
    """جلب وقت آخر إعلان شاهدته المستخدم"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT last_ad_time FROM user_ad_cooldown WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['last_ad_time'] if row else None

def update_last_ad_time(user_id: int):
    """تحديث وقت آخر إعلان للمستخدم"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_ad_cooldown (user_id, last_ad_time)
        VALUES (?, CURRENT_TIMESTAMP)
    ''', (user_id,))
    conn.commit()
    conn.close()

def is_ad_seen_recently(user_id: int, ad_id: str, ad_source: str, hours: int = 24) -> bool:
    """التحقق مما إذا كان المستخدم قد شاهد هذا الإعلان خلال الساعات المحددة"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM user_ad_history
        WHERE user_id = ? AND ad_id = ? AND ad_source = ?
        AND watched_at > datetime('now', '-' || ? || ' hours')
    ''', (user_id, ad_id, ad_source, hours))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0
