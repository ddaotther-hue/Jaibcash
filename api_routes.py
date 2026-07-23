"""
مسارات API مستقلة لتطبيق JaibCash Mini App.
هذا الملف منفصل عن main.py بالكامل - يتم ربطه بسطرين فقط بدون لمس منطق البوت.
"""

import asyncio
import logging
from flask import Blueprint, jsonify, request
from database import (
    get_user, get_balance, get_referral_stats, get_advertiser_balance,
    get_leaderboard, get_transactions, add_points_to_user,
    claim_reward, withdraw_points, get_checkin_status, do_checkin,
    get_available_tasks, get_user_tasks, get_user_level, 
    get_user_stats, get_user_achievements, get_referrals_list
)

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

# ========== المسار الرئيسي ==========
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
        
        user_dict = dict(user) if user is not None else {}
        
        return jsonify({
            "user_id": user_id,
            "balance": balance,
            "level": user_dict.get("level", 0),
            "username": user_dict.get("username"),
            "first_name": user_dict.get("first_name"),
            "user_raw": user_dict,
            "referral_stats": referral_stats if isinstance(referral_stats, dict) else dict(referral_stats),
            "advertiser_balance": adv_balance,
        }), 200
        
    except Exception as e:
        logger.exception(f"profile endpoint failed for user_id={user_id}")
        return jsonify({"error": "internal error", "detail": str(e)}), 500

# ========== المسارات الجديدة ==========

@api_bp.route('/balance', methods=['GET'])
def get_balance_api():
    """الحصول على رصيد المستخدم"""
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    try:
        balance = get_balance(user_id)
        return jsonify({
            "user_id": user_id,
            "balance": balance
        }), 200
    except Exception as e:
        logger.exception(f"balance endpoint failed for user_id={user_id}")
        return jsonify({"error": "internal error"}), 500

@api_bp.route('/leaderboard', methods=['GET'])
def leaderboard_api():
    """لوحة المتصدرين"""
    limit = request.args.get('limit', 10, type=int)
    if limit > 100:
        limit = 100
    
    try:
        data = get_leaderboard(limit)
        result = []
        for item in data:
            if isinstance(item, dict):
                result.append(item)
            else:
                result.append(dict(item))
        
        return jsonify({
            "leaderboard": result,
            "count": len(result)
        }), 200
    except Exception as e:
        logger.exception(f"leaderboard endpoint failed")
        return jsonify({"error": "internal error"}), 500

@api_bp.route('/transactions', methods=['GET'])
def transactions_api():
    """سجل المعاملات"""
    user_id = request.args.get('user_id', type=int)
    limit = request.args.get('limit', 20, type=int)
    
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    try:
        data = get_transactions(user_id, limit)
        result = []
        for item in data:
            if isinstance(item, dict):
                result.append(item)
            else:
                result.append(dict(item))
        
        return jsonify({
            "user_id": user_id,
            "transactions": result,
            "count": len(result)
        }), 200
    except Exception as e:
        logger.exception(f"transactions endpoint failed for user_id={user_id}")
        return jsonify({"error": "internal error"}), 500

@api_bp.route('/watch_ad', methods=['POST'])
def watch_ad_api():
    """مشاهدة إعلان"""
    data = request.json
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    try:
        points_earned = 10
        add_points_to_user(user_id, points_earned, "مشاهدة إعلان")
        
        return jsonify({
            "success": True,
            "points": points_earned,
            "message": "تم مشاهدة الإعلان بنجاح"
        }), 200
    except Exception as e:
        logger.exception(f"watch_ad endpoint failed for user_id={user_id}")
        return jsonify({"error": "internal error"}), 500

@api_bp.route('/claim', methods=['POST'])
def claim_api():
    """سحب النقاط اليومي"""
    data = request.json
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    try:
        result = claim_reward(user_id)
        return jsonify({
            "success": True,
            "message": "تم السحب بنجاح",
            "points": result.get('points', 0)
        }), 200
    except Exception as e:
        logger.exception(f"claim endpoint failed for user_id={user_id}")
        return jsonify({"error": str(e)}), 400

@api_bp.route('/withdraw', methods=['POST'])
def withdraw_api():
    """طلب سحب الأموال"""
    data = request.json
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    
    user_id = data.get('user_id')
    amount = data.get('amount')
    
    if not user_id or not amount:
        return jsonify({"error": "user_id and amount are required"}), 400
    
    try:
        result = withdraw_points(user_id, amount)
        return jsonify({
            "success": True,
            "message": f"تم طلب سحب {amount} نقطة",
            "details": result
        }), 200
    except Exception as e:
        logger.exception(f"withdraw endpoint failed for user_id={user_id}")
        return jsonify({"error": str(e)}), 400

@api_bp.route('/referral', methods=['GET'])
def referral_api():
    """بيانات الإحالات"""
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    try:
        stats = get_referral_stats(user_id)
        referrals = get_referrals_list(user_id)
        
        return jsonify({
            "user_id": user_id,
            "stats": stats if isinstance(stats, dict) else dict(stats),
            "referrals": [dict(r) if not isinstance(r, dict) else r for r in referrals],
            "referral_link": f"https://t.me/JaibCashBot?start=ref_{user_id}"
        }), 200
    except Exception as e:
        logger.exception(f"referral endpoint failed for user_id={user_id}")
        return jsonify({"error": "internal error"}), 500

@api_bp.route('/checkin', methods=['GET', 'POST'])
def checkin_api():
    """التسجيل اليومي"""
    if request.method == 'GET':
        user_id = request.args.get('user_id', type=int)
    else:
        data = request.json
        user_id = data.get('user_id') if data else None
    
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    try:
        if request.method == 'GET':
            status = get_checkin_status(user_id)
            return jsonify({
                "user_id": user_id,
                "can_checkin": status.get('can_checkin', True),
                "last_checkin": status.get('last_checkin'),
                "streak": status.get('streak', 0)
            }), 200
        else:
            result = do_checkin(user_id)
            return jsonify({
                "success": True,
                "message": "تم التسجيل اليومي بنجاح",
                "points_earned": result.get('points', 10),
                "streak": result.get('streak', 1)
            }), 200
    except Exception as e:
        logger.exception(f"checkin endpoint failed for user_id={user_id}")
        return jsonify({"error": str(e)}), 400

@api_bp.route('/tasks', methods=['GET'])
def tasks_api():
    """قائمة المهام المتاحة"""
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    try:
        available = get_available_tasks(user_id)
        my_tasks = get_user_tasks(user_id)
        
        return jsonify({
            "user_id": user_id,
            "available": [dict(t) if not isinstance(t, dict) else t for t in available],
            "my_tasks": [dict(t) if not isinstance(t, dict) else t for t in my_tasks]
        }), 200
    except Exception as e:
        logger.exception(f"tasks endpoint failed for user_id={user_id}")
        return jsonify({"error": "internal error"}), 500

@api_bp.route('/stats', methods=['GET'])
def stats_api():
    """إحصائيات المستخدم"""
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    try:
        level = get_user_level(user_id)
        stats = get_user_stats(user_id)
        achievements = get_user_achievements(user_id)
        
        return jsonify({
            "user_id": user_id,
            "level": level,
            "stats": stats if isinstance(stats, dict) else dict(stats),
            "achievements": [dict(a) if not isinstance(a, dict) else a for a in achievements]
        }), 200
    except Exception as e:
        logger.exception(f"stats endpoint failed for user_id={user_id}")
        return jsonify({"error": "internal error"}), 500

@api_bp.route('/health', methods=['GET'])
def health_api():
    """فحص صحة الخادم"""
    return jsonify({
        "status": "ok",
        "service": "JaibCash Mini App API",
        "version": "1.0.0"
    }), 200

@api_bp.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@api_bp.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500
