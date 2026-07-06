# db/referrals.py - دوال الإحالات (مع total, active, earnings) - نسخة مستقرة
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
    """
    تعيد إحصائيات الإحالات:
    - total: عدد الإحالات الكلي (بما فيها المعلقة والنشطة)
    - active: عدد الإحالات النشطة فقط
    - earnings: إجمالي أرباح الإحالات النشطة
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # إجمالي الإحالات
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (referrer_id,))
    total = cursor.fetchone()[0]
    
    # الإحالات النشطة
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND status = "active"', (referrer_id,))
    active = cursor.fetchone()[0]
    
    # مجموع أرباح الإحالات النشطة
    cursor.execute('SELECT COALESCE(SUM(total_earned), 0) FROM referrals WHERE referrer_id = ? AND status = "active"', (referrer_id,))
    earnings = cursor.fetchone()[0]
    
    conn.close()
    return {
        'total': total,
        'active': active,
        'earnings': earnings
    }

# ===== معالجة أرباح الإحالة =====
def process_referral_earnings(user_id: int, points: int, source: str = ""):
    """
    تُستدعى كلما أضيفت نقاط للمستخدم.
    - تبحث عن إحالة معلقة (pending) لهذا المستخدم.
    - تحسب 5% من النقاط وتضيفها للمحيل.
    - ترفّع حالة الإحالة إلى active (في أول مرة فقط).
    """
    if points <= 0:
        return
    
    conn = get_db()
    cursor = conn.cursor()
    
    # البحث عن إحالة معلقة لهذا المستخدم
    cursor.execute('''
        SELECT id, referrer_id, status FROM referrals
        WHERE referred_id = ? AND status = 'pending'
        ORDER BY id ASC LIMIT 1
    ''', (user_id,))
    referral = cursor.fetchone()
    
    if not referral:
        conn.close()
        return
    
    referrer_id = referral['referrer_id']
    bonus = int(points * 0.05)  # 5%
    
    if bonus <= 0:
        conn.close()
        return
    
    # تحديث رصيد المحيل (إضافة النقاط)
    cursor.execute('''
        UPDATE balances
        SET points = points + ?,
            referral_earnings = referral_earnings + ?
        WHERE user_id = ?
    ''', (bonus, bonus, referrer_id))
    
    # تسجيل المعاملة للمحيل
    cursor.execute('''
        INSERT INTO transactions (user_id, type, amount, description)
        VALUES (?, 'referral', ?, ?)
    ''', (referrer_id, bonus, f'أرباح إحالة: {source}'))
    
    # تحديث إجمالي أرباح الإحالة في جدول referrals وترقية الحالة
    cursor.execute('''
        UPDATE referrals
        SET total_earned = total_earned + ?,
            status = 'active'
        WHERE referred_id = ?
    ''', (bonus, user_id))
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ إحالة: {referrer_id} ← {user_id} | مكافأة: {bonus} نقطة (5%) من {source}")
