from .core import get_db

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
