from .core import get_db

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
