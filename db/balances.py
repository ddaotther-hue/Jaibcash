from .core import get_db

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

async def get_transactions(user_id: int, limit: int = 20):
    """جلب آخر المعاملات المالية للمستخدم (جميع الأنواع)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, type, amount, description, created_at
        FROM transactions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

async def get_transactions(user_id: int, limit: int = 20):
    """جلب آخر المعاملات المالية للمستخدم (جميع الأنواع)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, type, amount, description, created_at
        FROM transactions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

async def get_transactions(user_id: int, limit: int = 20):
    """جلب آخر المعاملات المالية للمستخدم (جميع الأنواع)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, type, amount, description, created_at
        FROM transactions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows
