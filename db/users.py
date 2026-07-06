from .core import get_db
import sqlite3

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

def set_language(user_id, lang):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN language TEXT DEFAULT "ar"')
    except sqlite3.OperationalError:
        pass
    cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang, user_id))
    conn.commit()
    conn.close()

def get_language(user_id):
    user = get_user(user_id)
    return user['language'] if user else 'ar'

def update_approved_tasks(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET approved_tasks = approved_tasks + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_level(user_id):
    user = get_user(user_id)
    return user['level'] if user else 0

def set_level(user_id, level):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET level = ? WHERE user_id = ?', (level, user_id))
    conn.commit()
    conn.close()

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
