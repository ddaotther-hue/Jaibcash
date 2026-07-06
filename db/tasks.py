import logging
from .core import get_db
logger = logging.getLogger(__name__)

async def save_task(task_dict: dict) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (
            advertiser_id, type, link, description, image_file_id,
            proof_type, target_count, price_per_person,
            total_cost, commission, points_per_person, total_points_charged
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        task_dict['advertiser_id'],
        task_dict['type'],
        task_dict.get('link', ''),
        task_dict.get('description', ''),
        task_dict.get('image_file_id', None),
        task_dict.get('proof_type', 'photo_username'),
        task_dict['target_count'],
        task_dict['price_per_person'],
        task_dict['total_cost'],
        task_dict['commission'],
        task_dict['points_per_person'],
        task_dict['total_points_charged'],
    ))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    logger.info(f"✅ تم حفظ المهمة #{task_id}")
    return task_id

async def get_task_by_id(task_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

async def get_task_owner(task_id: int) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT advertiser_id FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    return row['advertiser_id'] if row else None

async def increment_task_completed(task_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET completed_count = completed_count + 1, status = CASE WHEN completed_count + 1 >= target_count THEN "completed" ELSE "active" END WHERE id = ? AND status != "completed"', (task_id,))
    conn.commit()
    conn.close()
