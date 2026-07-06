from .core import get_db

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
