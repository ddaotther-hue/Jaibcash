from .core import get_db
from datetime import datetime
from .referrals import process_referral_earnings

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
    # ✅ معالجة أرباح الإحالة
    process_referral_earnings(user_id, points, "تسجيل يومي")
    return {'success': True, 'points': points, 'day': new_streak}
