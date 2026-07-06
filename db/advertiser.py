import logging
from .core import get_db
logger = logging.getLogger(__name__)

async def get_advertiser_balance(user_id: int) -> float:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM advertiser_wallets WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['balance'] if row else 0.0

async def get_advertiser_frozen_balance(user_id: int) -> float:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT frozen_balance FROM advertiser_wallets WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['frozen_balance'] if row else 0.0

async def get_advertiser_total_balance(user_id: int) -> float:
    available = await get_advertiser_balance(user_id)
    frozen = await get_advertiser_frozen_balance(user_id)
    return available + frozen

async def freeze_advertiser_balance(user_id: int, amount: float) -> bool:
    if amount <= 0:
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM advertiser_wallets WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row or row['balance'] < amount:
        conn.close()
        logger.warning(f"❌ رصيد غير كافٍ لتجميد {amount:.2f}$ للمستخدم {user_id}")
        return False
    cursor.execute('UPDATE advertiser_wallets SET balance = balance - ?, frozen_balance = frozen_balance + ? WHERE user_id = ?', (amount, amount, user_id))
    conn.commit()
    conn.close()
    logger.info(f"✅ تم تجميد {amount:.2f}$ للمستخدم {user_id}")
    return True

async def release_frozen_balance(user_id: int, amount: float, to_spent: bool = True):
    if amount <= 0:
        return
    conn = get_db()
    cursor = conn.cursor()
    if to_spent:
        cursor.execute('UPDATE advertiser_wallets SET frozen_balance = frozen_balance - ?, total_spent = total_spent + ? WHERE user_id = ?', (amount, amount, user_id))
    else:
        cursor.execute('UPDATE advertiser_wallets SET frozen_balance = frozen_balance - ?, balance = balance + ? WHERE user_id = ?', (amount, amount, user_id))
    conn.commit()
    conn.close()
    logger.info(f"✅ تم تحرير {amount:.2f}$ من المجمد للمستخدم {user_id} (to_spent={to_spent})")

async def add_advertiser_balance(user_id: int, amount: float):
    if amount <= 0:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO advertiser_wallets (user_id, balance, frozen_balance) VALUES (?, ?, 0.0) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?', (user_id, amount, amount))
    conn.commit()
    conn.close()
    logger.info(f"✅ تم إيداع {amount:.2f}$ للمستخدم {user_id}")

async def deduct_advertiser_balance(user_id: int, amount: float) -> bool:
    if amount <= 0:
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM advertiser_wallets WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if not row or row['balance'] < amount:
        conn.close()
        return False
    cursor.execute('UPDATE advertiser_wallets SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ?', (amount, amount, user_id))
    conn.commit()
    conn.close()
    return True

async def update_advertiser_total_spent(user_id: int, amount: float):
    if amount <= 0:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE advertiser_wallets SET total_spent = total_spent + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()
