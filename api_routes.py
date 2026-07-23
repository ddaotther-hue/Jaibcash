"""
مسارات API مستقلة لتطبيق JaibCash Mini App.
هذا الملف منفصل عن main.py بالكامل - يتم ربطه بسطرين فقط بدون لمس منطق البوت.
"""

import asyncio
import logging
from flask import Blueprint, jsonify, request

from database import get_user, get_balance, get_referral_stats, get_advertiser_balance

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')


def run_async(coro):
    """تشغيل دالة async من داخل route متزامن (Flask)."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@api_bp.route('/profile')
def profile():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    try:
        user = get_user(user_id)
        if not user:
            return jsonify({"error": "user not found"}), 404

        balance = get_balance(user_id)
        referral_stats = get_referral_stats(user_id)

        try:
            adv_balance = run_async(get_advertiser_balance(user_id))
        except Exception as e:
            logger.warning(f"advertiser balance fetch failed for {user_id}: {e}")
            adv_balance = 0

        # sqlite3.Row يتحول لـ dict عادي عشان يصير قابل للتحويل لـ JSON
        user_dict = dict(user) if user is not None else {}

        return jsonify({
            "user_id": user_id,
            "balance": balance,
            "level": user_dict.get("level"),
            "username": user_dict.get("username"),
            "first_name": user_dict.get("first_name"),
            "user_raw": user_dict,
            "referral_stats": referral_stats if isinstance(referral_stats, dict) else dict(referral_stats),
            "advertiser_balance": adv_balance,
        }), 200

    except Exception as e:
        logger.exception(f"profile endpoint failed for user_id={user_id}")
        return jsonify({"error": "internal error", "detail": str(e)}), 500
