from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DB_PATH = os.getenv("DB_PATH", "data/jaibcash.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ===== Healthcheck =====
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

# ===== API: جلب بيانات المستخدم =====
@app.route('/api/profile', methods=['GET'])
def profile():
    user_id = request.args.get('user_id', 1488610580)
    try:
        user_id = int(user_id)
    except:
        return jsonify({"error": "Invalid user_id"}), 400

    conn = get_db()
    cursor = conn.cursor()

    # الرصيد
    cursor.execute('SELECT points FROM balances WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    balance = row['points'] if row else 0

    # الإحالات
    cursor.execute('SELECT COUNT(*) as count, COALESCE(SUM(total_earned), 0) as earnings FROM referrals WHERE referrer_id = ? AND status = "active"', (user_id,))
    ref = cursor.fetchone()
    referrals = ref['count'] if ref else 0
    referral_earnings = ref['earnings'] if ref else 0

    conn.close()

    return jsonify({
        "balance": balance,
        "referrals": referrals,
        "referral_earnings": referral_earnings,
        "advertiser_balance": 0
    })

# ===== API: مشاهدة إعلان =====
@app.route('/api/watch-ad', methods=['POST'])
def watch_ad():
    data = request.get_json()
    user_id = data.get('user_id', 1488610580)
    try:
        user_id = int(user_id)
    except:
        return jsonify({"error": "Invalid user_id"}), 400

    points = 1000
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('UPDATE balances SET points = points + ?, total_earned = total_earned + ? WHERE user_id = ?', (points, points, user_id))
    cursor.execute('INSERT INTO transactions (user_id, type, amount, description) VALUES (?, "ad", ?, "مشاهدة إعلان")', (user_id, points))

    cursor.execute('SELECT points FROM balances WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    new_balance = row['points'] if row else 0

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "points": points,
        "balance": new_balance
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=False)

# ===== API: جلب بيانات المستخدم =====
@app.route('/api/profile', methods=['GET'])
def profile():
    user_id = request.args.get('user_id', 1488610580)
    try:
        user_id = int(user_id)
    except:
        return jsonify({"error": "Invalid user_id"}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT points FROM balances WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    balance = row['points'] if row else 0

    cursor.execute('SELECT COUNT(*) as count, COALESCE(SUM(total_earned), 0) as earnings FROM referrals WHERE referrer_id = ? AND status = "active"', (user_id,))
    ref = cursor.fetchone()
    referrals = ref['count'] if ref else 0
    referral_earnings = ref['earnings'] if ref else 0

    conn.close()

    return jsonify({
        "balance": balance,
        "referrals": referrals,
        "referral_earnings": referral_earnings,
        "advertiser_balance": 0
    })

# ===== API: مشاهدة إعلان =====
@app.route('/api/watch-ad', methods=['POST'])
def watch_ad():
    data = request.get_json()
    user_id = data.get('user_id', 1488610580)
    try:
        user_id = int(user_id)
    except:
        return jsonify({"error": "Invalid user_id"}), 400

    points = 1000
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('UPDATE balances SET points = points + ?, total_earned = total_earned + ? WHERE user_id = ?', (points, points, user_id))
    cursor.execute('INSERT INTO transactions (user_id, type, amount, description) VALUES (?, "ad", ?, "مشاهدة إعلان")', (user_id, points))

    cursor.execute('SELECT points FROM balances WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    new_balance = row['points'] if row else 0

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "points": points,
        "balance": new_balance
    })

# ===== API: جلب المهام =====
@app.route('/api/tasks', methods=['GET'])
def tasks():
    user_id = request.args.get('user_id', 1488610580)
    try:
        user_id = int(user_id)
    except:
        return jsonify({"error": "Invalid user_id"}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, description, points_per_person, target_count, completed_count, status
        FROM tasks WHERE status = "active" ORDER BY created_at DESC LIMIT 10
    ''')
    rows = cursor.fetchall()
    conn.close()

    tasks_list = []
    for row in rows:
        status_map = {
            'active': 'pending',
            'completed': 'done'
        }
        tasks_list.append({
            "id": row['id'],
            "name": row['description'],
            "reward": row['points_per_person'],
            "status": status_map.get(row['status'], 'pending'),
            "progress": f"{row['completed_count']}/{row['target_count']}"
        })

    return jsonify(tasks_list)
