import logging
import time
import random
import aiohttp
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import REQUIRED_CHANNEL, LEVEL_BONUS, MIN_WITHDRAWAL, RICHADS_PUBLISHER_ID, RICHADS_WIDGET_ID, ADSGRAM_BLOCK_ID, ADSGRAM_API_KEY
from database import *
from utils import *
from i18n import t, get_level_name as get_level_name_i18n
from keyboards import get_reply_keyboard, get_wallet_menu, get_account_menu, get_referral_menu, get_leaderboard_menu

logger = logging.getLogger(__name__)

MIN_AD_WATCH_TIME = 15
AD_COOLDOWN_MINUTES = 1
AD_REPEAT_HOURS = 24

def get_reply_and_edit_methods(update):
    if update.callback_query:
        q = update.callback_query
        return q.message.reply_text, q.edit_message_text, q.from_user.id, q.message.chat.id
    return update.message.reply_text, None, update.effective_user.id, update.effective_chat.id

def get_ad_watch_buttons(uid, click_url, button_name):
    keyboard = [
        [InlineKeyboardButton(button_name, url=click_url)],
        [InlineKeyboardButton(t(uid, 'btn_watched'), callback_data="ad_watched")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def check_ad_cooldown(uid):
    last_time = get_last_ad_time(uid)
    if last_time:
        try:
            last_dt = datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')
            elapsed = (datetime.utcnow() - last_dt).total_seconds()
            if elapsed < AD_COOLDOWN_MINUTES * 60:
                remaining = int(AD_COOLDOWN_MINUTES * 60 - elapsed)
                return remaining
        except:
            pass
    return 0

async def balance(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    p = get_balance(uid)
    u = get_user(uid)
    lvl = u['level'] if u else 0
    lname = get_level_name_i18n(uid, lvl)
    stats = get_referral_stats(uid)
    avail = await get_advertiser_balance(uid)
    frozen = await get_advertiser_frozen_balance(uid)
    total = await get_advertiser_total_balance(uid)
    msg = f"💰 **{t(uid, 'wallet_title')}**\n\n🟢 **{t(uid, 'points_balance')}:** {format_points(p)} {t(uid, 'points_unit')} (≈ ${points_to_usd(p):.2f})\n📊 {t(uid, 'current_level', level_name=lname, tasks=u['approved_tasks'] if u else 0, progress=0)}\n👥 {t(uid, 'referral_stats_full', total=stats['total'], active=stats['active'], earnings=format_points(stats['earnings']))}\n\n━━━━━━━━━━━━━━━━━━\n💼 **{t(uid, 'advertiser_wallet_title')}:**\n🟢 {t(uid, 'advertiser_available')}: {avail:.2f}$\n🔒 {t(uid, 'advertiser_frozen')}: {frozen:.2f}$\n📊 {t(uid, 'advertiser_total')}: {total:.2f}$\n\n🔹 {t(uid, 'advertiser_available_desc')}\n🔹 {t(uid, 'advertiser_frozen_desc')}"
    if edit: await edit(msg, reply_markup=get_wallet_menu(uid), parse_mode="Markdown")
    else: await reply(msg, reply_markup=get_wallet_menu(uid), parse_mode="Markdown")

async def watch_ad(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))

    cooldown = await check_ad_cooldown(uid)
    if cooldown > 0:
        await reply(t(uid, 'ad_cooldown', seconds=cooldown))
        return

    ads = []

    # AdsGram
    try:
        ad_url = "https://api.adsgram.ai/advbot"
        params = {
            "tgid": uid,
            "blockid": ADSGRAM_BLOCK_ID,
            "language": "ar",
            "token": ADSGRAM_API_KEY,
            "rnd": int(time.time() * 1000)
        }
        response = requests.get(ad_url, params=params, timeout=10)
        logger.info(f"AdsGram status={response.status_code} body={response.text[:200]!r}")
        ad_data = None
        if response.status_code == 200 and response.text.strip():
            try:
                ad_data = response.json()
            except ValueError:
                logger.info("AdsGram: لا يوجد إعلان متاح حالياً (رد غير JSON)")
        if ad_data is not None:
            if ad_data and isinstance(ad_data, dict):
                ad_id = ad_data.get("id") or ad_data.get("block_id") or f"adsgram_{int(time.time())}"
                if not is_ad_seen_recently(uid, ad_id, 'adsgram', AD_REPEAT_HOURS):
                    ads.append({
                        'source': 'adsgram',
                        'id': ad_id,
                        'text_html': ad_data.get("text_html", ""),
                        'image_url': ad_data.get("image_url"),
                        'click_url': ad_data.get("click_url", ""),
                        'button_name': ad_data.get("button_name", "شاهد الإعلان"),
                    })
    except Exception as e:
        logger.error(f"AdsGram error: {e}")

    # RichAds
    try:
        url = "http://15068.xml.adx1.com/telegram-mb"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        pub_id = RICHADS_PUBLISHER_ID or "409986"
        widget_id = RICHADS_WIDGET_ID or "123875"
        payload = {
            "language_code": "ar",
            "publisher_id": str(pub_id),
            "widget_id": str(widget_id),
            "telegram_id": str(uid),
            "production": True,
            "rnd": int(time.time() * 1000)
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=15) as response:
                if response.status == 200:
                    import json
                    try:
                        ad_data = json.loads(await response.text())
                        if ad_data and isinstance(ad_data, list) and len(ad_data) > 0:
                            ad = ad_data[0]
                            ad_id = ad.get('id') or ad.get('link', '').split('/')[-1] or f"richads_{int(time.time())}"
                            if not is_ad_seen_recently(uid, ad_id, 'richads', AD_REPEAT_HOURS):
                                ads.append({
                                    'source': 'richads',
                                    'id': ad_id,
                                    'title': ad.get('title', ''),
                                    'message': ad.get('message', ''),
                                    'image_url': ad.get('image', ''),
                                    'click_url': ad.get('link', ''),
                                    'button_name': ad.get('button', 'شاهد العرض'),
                                    'brand': ad.get('brand', ''),
                                    'bid_price': ad.get('bid_price', 0),
                                })
                    except:
                        pass
    except Exception as e:
        logger.error(f"RichAds error: {e}")

    if not ads:
        await reply(t(uid, "no_ads_available"))
        return

    random.shuffle(ads)
    ad = ads[0]

    context.user_data['pending_ad'] = True
    context.user_data['ad_start_time'] = time.time()
    context.user_data['ad_points'] = 1000
    context.user_data['ad_source'] = ad['source']
    context.user_data['ad_id'] = ad['id']

    instructions = t(uid, 'ad_watch_instructions')
    if ad['source'] == 'adsgram':
        keyboard = get_ad_watch_buttons(uid, ad['click_url'], ad['button_name'])
        full_text = f"{instructions}\n\n{ad['text_html']}"
        if ad['image_url']:
            await reply(full_text, reply_markup=keyboard, parse_mode=ParseMode.HTML, protect_content=True)
        else:
            await reply(full_text, reply_markup=keyboard, parse_mode=ParseMode.HTML, protect_content=True)
    else:
        caption = f"{instructions}\n\n📢 {ad['title']}\n\n{ad['message']}"
        if ad.get('bid_price'):
            caption += f"\n\n💰 السعر: ${ad['bid_price']:.2f}"
        if ad.get('brand'):
            caption += f"\n🏷️ {ad['brand']}"
        keyboard = get_ad_watch_buttons(uid, ad['click_url'], ad['button_name'])
        if ad['image_url']:
            await reply(caption, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            await reply(caption, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    logger.info(f"✅ تم عرض إعلان من {ad['source']} للمستخدم {uid} (ID: {ad['id']})")

async def handle_ad_watched(update, context):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if not context.user_data.get('pending_ad', False):
        await query.edit_message_text("⚠️ " + t(uid, 'claim_already'))
        return

    elapsed = time.time() - context.user_data.get('ad_start_time', 0)
    if elapsed < MIN_AD_WATCH_TIME:
        remaining = int(MIN_AD_WATCH_TIME - elapsed)
        await query.edit_message_text(
            t(uid, 'ad_watch_wait', remaining=remaining, elapsed=int(elapsed), total=MIN_AD_WATCH_TIME)
        )
        return

    pts = context.user_data.get('ad_points', 1000)
    ad_source = context.user_data.get('ad_source', 'unknown')
    ad_id = context.user_data.get('ad_id', str(int(time.time())))

    save_user_ad(uid, ad_id, ad_source)
    update_last_ad_time(uid)

    update_balance(uid, pts, 'ad', f'مشاهدة إعلان ({ad_source})')
    process_referral_earnings(uid, pts, "مشاهدة إعلان")
    update_approved_tasks(uid)

    # ===== إشعار للمحيل عند أول مهمة =====
    try:
        user = get_user(uid)
        if user and user['approved_tasks'] == 1:
            from db.referrals import get_referrer_by_referred
            referrer_id = get_referrer_by_referred(uid)
            if referrer_id:
                bonus = int(pts * 0.05)
                stats = get_referral_stats(referrer_id)
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 **أول مهمة للمُحال!**\n\n"
                         f"👤 المستخدم الذي دعوته أكمل أول مهمة.\n"
                         f"💰 ربحت 5% من نقاطه: **{bonus:,} نقطة**\n"
                         f"📊 رصيدك من الإحالات الآن: {format_points(stats['earnings'])} نقطة"
                )
    except Exception as e:
        logger.error(f"❌ فشل إرسال إشعار للمحيل: {e}")

    u = get_user(uid)
    new_lvl = calculate_level(u['approved_tasks'] if u else 0)
    old_lvl = u['level'] if u else 0
    if new_lvl > old_lvl:
        set_level(uid, new_lvl)
        update_balance(uid, LEVEL_BONUS, 'levelup', f'ترقية إلى مستوى {new_lvl}')
        process_referral_earnings(uid, LEVEL_BONUS, f"ترقية مستوى {new_lvl}")
        await query.message.reply_text(
            t(uid, 'level_up', level_name=get_level_name_i18n(uid, new_lvl), bonus=format_points(LEVEL_BONUS))
        )

    new_balance = get_balance(uid)
    keyboard = [[InlineKeyboardButton("💰 تفقد رصيدك", callback_data="menu_balance")]]

    await query.edit_message_text(
        f"✅ **تهانينا!**\n\n"
        f"🎉 لقد حصلت على **{pts:,} نقطة** من مشاهدة الإعلان!\n"
        f"📊 رصيدك الحالي: **{format_points(new_balance)} نقطة**\n"
        f"💵 ≈ ${points_to_usd(new_balance):.2f}\n\n"
        f"🔹 استمر في مشاهدة الإعلانات لكسب المزيد!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    context.user_data['pending_ad'] = False
    context.user_data.pop('ad_start_time', None)
    context.user_data.pop('ad_points', None)
    context.user_data.pop('ad_source', None)
    context.user_data.pop('ad_id', None)

async def claim(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not context.user_data.get('pending_ad', False):
        return await reply("⚠️ " + t(uid, 'claim_already'))
    await handle_ad_watched(update, context)

# ============================================================
# باقي الدوال (referral, checkin, account, ...) كما هي
# ============================================================

async def referral(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    bot_username = (await context.bot.get_me()).username
    link = get_referral_link(bot_username, uid)
    stats = get_referral_stats(uid)
    msg = f"{t(uid, 'referral_link', link=link)}\n\n{t(uid, 'referral_stats_full', total=stats['total'], active=stats['active'], earnings=format_points(stats['earnings']))}"
    if edit: await edit(msg, reply_markup=get_referral_menu(uid), parse_mode=ParseMode.HTML)
    else: await reply(msg, reply_markup=get_referral_menu(uid), parse_mode=ParseMode.HTML)

async def checkin(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    r = check_in(uid)
    if r['success']: await reply(t(uid, 'checkin_success', points=format_points(r['points']), day=r['day']))
    else: await reply(t(uid, 'already_checked'))

async def account(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    u = get_user(uid)
    if not u: return await reply(t(uid, 'please_start'))
    pts = get_balance(uid)
    lname = get_level_name_i18n(uid, u['level'])
    stats = get_referral_stats(uid)
    ach = get_achievements(uid)
    from utils import get_next_level_tasks
    prog = get_next_level_tasks(u['approved_tasks'])
    joined = u['joined_at'][:10] if u['joined_at'] else t(uid, 'not_specified')
    msg = f"👤 **{t(uid, 'account_title')}**\n━━━━━━━━━━━━━━━━━━\n🆔 **{t(uid, 'user_id_label')}:** `{uid}`\n📛 **{t(uid, 'name_label')}:** {u['first_name'] or t(uid, 'not_specified')}\n📅 **{t(uid, 'joined_date_label')}:** {joined}\n━━━━━━━━━━━━━━━━━━\n🏅 **{t(uid, 'level_label')}:** {lname}\n📊 **{t(uid, 'tasks_label')}:** {u['approved_tasks']}\n"
    if not prog['is_max']: msg += f"📈 **{t(uid, 'progress_label')}:** {prog['progress_percent']}%\n⏳ **{t(uid, 'tasks_remaining_label')}:** {prog['tasks_needed']}\n"
    else: msg += f"🔥 **{t(uid, 'max_level_label')}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n💰 **{t(uid, 'balance_label')}:** {format_points(pts)} {t(uid, 'points_unit')}\n💵 ≈ **${points_to_usd(pts):.2f}**\n━━━━━━━━━━━━━━━━━━\n👥 **{t(uid, 'referral_total_label')}:** {stats['total']}\n✅ **{t(uid, 'referral_active_label')}:** {stats['active']}\n🎁 **{t(uid, 'referral_earnings_label')}:** {format_points(stats['earnings'])} {t(uid, 'points_unit')}\n🎖️ **{t(uid, 'achievements_label')}:** {len(ach)}/10\n"
    if edit: await edit(msg, reply_markup=get_account_menu(uid), parse_mode="Markdown")
    else: await reply(msg, reply_markup=get_account_menu(uid), parse_mode="Markdown")

async def show_my_level(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    u = get_user(uid)
    if not u: return await reply(t(uid, 'please_start'))
    lvl = u['level']
    lname = get_level_name_i18n(uid, lvl)
    tasks = u['approved_tasks']
    from utils import get_next_level_tasks
    prog = get_next_level_tasks(tasks)
    bar_len = 20
    filled = int((prog['progress_percent'] / 100) * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    msg = f"🏅 **{t(uid, 'my_level_title')}**\n━━━━━━━━━━━━━━━━━━\n📌 **{t(uid, 'current_level_full')}:** {lname}\n📊 **{t(uid, 'approved_tasks_label')}:** {tasks}\n━━━━━━━━━━━━━━━━━━\n"
    if not prog['is_max']: msg += f"📈 **{t(uid, 'progress_to_next')}:**\n`{bar}` {prog['progress_percent']}%\n⏳ **{t(uid, 'tasks_remaining_label')}:** {prog['tasks_needed']}\n"
    else: msg += f"🔥 **{t(uid, 'max_level_label')}**\n"
    from config import LEVEL_THRESHOLDS, LEVEL_NAMES
    msg += "\n━━━━━━━━━━━━━━━━━━\n📋 **{t(uid, 'all_levels_label')}:**\n"
    for i, th in enumerate(LEVEL_THRESHOLDS):
        status = "✅" if lvl == i else "⬜" if lvl > i else "🔘"
        name = LEVEL_NAMES.get(i, f"Level {i}")
        if i == len(LEVEL_THRESHOLDS) - 1: msg += f"{status} {name} ({t(uid, 'master_label')})\n"
        else: msg += f"{status} {name} ({th} → {LEVEL_THRESHOLDS[i+1]} {t(uid, 'tasks_label')})\n"
    kb = [[InlineKeyboardButton(t(uid, 'back_btn'), callback_data="account_back")]]
    if edit: await edit(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await reply(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_my_stats(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    u = get_user(uid)
    if not u: return await reply(t(uid, 'please_start'))
    pts = get_balance(uid)
    lname = get_level_name_i18n(uid, u['level'])
    stats = get_referral_stats(uid)
    ach = get_achievements(uid)
    txns = await get_transactions(uid, 100)
    earned = sum(abs(t['amount']) for t in txns if t['type'] in ['ad','task','referral','checkin','levelup'] and t['amount'] > 0)
    withdrawn = sum(abs(t['amount']) for t in txns if t['type'] == 'withdraw' and t['amount'] < 0)
    joined = u['joined_at'][:10] if u['joined_at'] else t(uid, 'not_specified')
    msg = f"📊 **{t(uid, 'my_stats_title')}**\n━━━━━━━━━━━━━━━━━━\n👤 **{t(uid, 'user_id_label')}:** `{uid}`\n🏅 **{t(uid, 'level_label')}:** {lname}\n━━━━━━━━━━━━━━━━━━\n💰 **{t(uid, 'current_balance_label')}:** {format_points(pts)} {t(uid, 'points_unit')}\n💵 **≈ ${points_to_usd(pts):.2f}**\n━━━━━━━━━━━━━━━━━━\n📋 **{t(uid, 'approved_tasks_label')}:** {u['approved_tasks']}\n💎 **{t(uid, 'total_earned_label')}:** {format_points(earned)} {t(uid, 'points_unit')}\n💸 **{t(uid, 'total_withdrawn_label')}:** {format_points(withdrawn)} {t(uid, 'points_unit')}\n━━━━━━━━━━━━━━━━━━\n👥 **{t(uid, 'referral_total_label')}:** {stats['total']}\n✅ **{t(uid, 'referral_active_label')}:** {stats['active']}\n🎁 **{t(uid, 'referral_earnings_label')}:** {format_points(stats['earnings'])} {t(uid, 'points_unit')}\n━━━━━━━━━━━━━━━━━━\n🎖️ **{t(uid, 'achievements_label')}:** {len(ach)}/10\n📅 **{t(uid, 'joined_date_label')}:** {joined}\n"
    kb = [[InlineKeyboardButton(t(uid, 'back_btn'), callback_data="account_back")]]
    if edit: await edit(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await reply(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_my_achievements(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    u = get_user(uid)
    if not u: return await reply(t(uid, 'please_start'))
    all_ach = {
        "first_ad": {"name": t(uid, 'ach_first_ad'), "desc": t(uid, 'ach_first_ad_desc')},
        "ten_ads": {"name": t(uid, 'ach_ten_ads'), "desc": t(uid, 'ach_ten_ads_desc')},
        "first_task": {"name": t(uid, 'ach_first_task'), "desc": t(uid, 'ach_first_task_desc')},
        "first_referral": {"name": t(uid, 'ach_first_referral'), "desc": t(uid, 'ach_first_referral_desc')},
        "first_withdraw": {"name": t(uid, 'ach_first_withdraw'), "desc": t(uid, 'ach_first_withdraw_desc')},
        "week_streak": {"name": t(uid, 'ach_week_streak'), "desc": t(uid, 'ach_week_streak_desc')},
        "silver": {"name": t(uid, 'ach_silver'), "desc": t(uid, 'ach_silver_desc')},
        "gold": {"name": t(uid, 'ach_gold'), "desc": t(uid, 'ach_gold_desc')},
        "platinum": {"name": t(uid, 'ach_platinum'), "desc": t(uid, 'ach_platinum_desc')},
        "diamond": {"name": t(uid, 'ach_diamond'), "desc": t(uid, 'ach_diamond_desc')},
    }
    unlocked = get_achievements(uid)
    msg = f"🎖️ **{t(uid, 'my_achievements_title')}**\n━━━━━━━━━━━━━━━━━━\n📊 **{t(uid, 'achieved_label')}:** {len(unlocked)} {t(uid, 'of_label')} {len(all_ach)}\n━━━━━━━━━━━━━━━━━━\n\n"
    for key, ach in all_ach.items():
        msg += f"{'✅' if key in unlocked else '⬜'} {ach['name']} — {ach['desc']}\n"
    msg += f"\n💡 {t(uid, 'achievement_tip')}"
    kb = [[InlineKeyboardButton(t(uid, 'back_btn'), callback_data="account_back")]]
    if edit: await edit(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await reply(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def leaderboard(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    leaders = get_leaderboard(10)
    if not leaders: return await reply(t(uid, 'no_users'))
    msg = f"🏆 <b>{t(uid, 'leaderboard_title')}</b>\n\n"
    for i, row in enumerate(leaders, 1):
        name = row['first_name'] or row['username'] or f"{t(uid, 'user')} {row['user_id']}"
        pts = format_points(row['points'])
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        msg += f"{medal} {name} — {pts} {t(uid, 'points_unit')}\n"
    if edit: await edit(msg, reply_markup=get_leaderboard_menu(uid), parse_mode=ParseMode.HTML)
    else: await reply(msg, reply_markup=get_leaderboard_menu(uid), parse_mode=ParseMode.HTML)

async def withdraw(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    pts = get_balance(uid)
    min_pts = usd_to_points(MIN_WITHDRAWAL)
    if pts < min_pts:
        return await reply(t(uid, 'withdraw_min_error', min_usd=MIN_WITHDRAWAL, min_points=format_points(min_pts), points=format_points(pts)))
    context.user_data['awaiting_wallet'] = True
    await reply(t(uid, 'withdraw_prompt'))

async def rewards(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    wd = get_withdrawals(uid, 5)
    msg = f"🎁 <b>{t(uid, 'rewards_title')}</b>\n\n"
    if wd:
        msg += f"📜 <b>{t(uid, 'recent_withdrawals')}</b>\n"
        for w in wd:
            emoji = "✅" if w['status'] == 'approved' else "⏳" if w['status'] == 'pending' else "❌"
            amt_usd = points_to_usd(w['amount'])
            msg += f"{emoji} {format_points(w['amount'])} {t(uid, 'points_unit')} (${amt_usd:.2f}) - {w['status']}\n"
    else:
        msg += t(uid, 'no_withdrawals')
    await reply(msg, parse_mode=ParseMode.HTML)

async def handle_wallet_address(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    wallet = update.message.text.strip()
    if not is_valid_trc20_address(wallet):
        return await reply(t(uid, 'withdraw_invalid_address'))
    pts = get_balance(uid)
    min_pts = usd_to_points(MIN_WITHDRAWAL)
    if pts < min_pts: return await reply(t(uid, 'withdraw_min_error'))
    add_withdrawal(uid, pts, wallet)
    update_balance(uid, -pts, 'withdraw', f'سحب {format_points(pts)} نقطة')
    context.user_data['awaiting_wallet'] = False
    await reply(t(uid, 'withdraw_requested'), reply_markup=get_reply_keyboard(uid))

async def advertiser_balance(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    avail = await get_advertiser_balance(uid)
    frozen = await get_advertiser_frozen_balance(uid)
    total = await get_advertiser_total_balance(uid)
    msg = f"💰 **{t(uid, 'advertiser_wallet_title')}**\n\n🟢 **{t(uid, 'advertiser_available')}:** {avail:.2f}$\n🔒 **{t(uid, 'advertiser_frozen')}:** {frozen:.2f}$\n📊 **{t(uid, 'advertiser_total')}:** {total:.2f}$\n\n🔹 {t(uid, 'advertiser_available_desc')}\n🔹 {t(uid, 'advertiser_frozen_desc')}\n🔹 {t(uid, 'advertiser_spent_desc')}\n🔹 {t(uid, 'advertiser_refund_desc')}"
    if edit: await edit(msg, parse_mode="Markdown")
    else: await reply(msg, parse_mode="Markdown")

async def transaction_history(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    txns = await get_transactions(uid, 20)
    if not txns: return await reply(t(uid, 'no_transactions'))
    labels = {"ad":"📺 "+t(uid,'type_ad'),"task":"📋 "+t(uid,'type_task'),"referral":"👥 "+t(uid,'type_referral'),"checkin":"📅 "+t(uid,'type_checkin'),"levelup":"🏅 "+t(uid,'type_levelup'),"withdraw":"💸 "+t(uid,'type_withdraw'),"admin":"🛠️ "+t(uid,'type_admin'),"charge":"💳 "+t(uid,'type_charge')}
    msg = f"📜 **{t(uid, 'transaction_history_title')}**\n━━━━━━━━━━━━━━━━━━\n"
    for txn in txns:
        label = labels.get(txn['type'], txn['type'])
        amt = txn['amount']
        desc = txn['description'] or ''
        date = txn['created_at'][:16]
        sign = "+" if amt >= 0 else ""
        color = "🟢" if amt >= 0 else "🔴"
        msg += f"{color} {label}\n   {sign}{amt:,} {t(uid, 'points_unit')} | {desc}\n   🕒 {date}\n━━━━━━━━━━━━━━━━━━\n"
    kb = [[InlineKeyboardButton(t(uid, 'back_btn'), callback_data="wallet_back")]]
    if edit: await edit(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else: await reply(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def withdraw_advertiser_balance(update, context):
    reply, edit, uid, cid = get_reply_and_edit_methods(update)
    if is_banned(uid): return await reply("🚫 " + t(uid, 'banned'))
    if not await check_channel_membership(update, context):
        return await reply(t(uid, 'not_subscribed', channel=REQUIRED_CHANNEL))
    avail = await get_advertiser_balance(uid)
    if avail <= 0: return await reply(t(uid, 'advertiser_no_balance'))
    MIN_WITHDRAW = 2.0
    if avail < MIN_WITHDRAW:
        return await reply(f"⚠️ {t(uid, 'advertiser_min_withdraw', min=MIN_WITHDRAW)}\n{t(uid, 'advertiser_available')}: {avail:.2f}$")
    context.user_data['awaiting_advertiser_withdraw'] = True
    context.user_data['advertiser_withdraw_amount'] = avail
    await reply(f"✅ {t(uid, 'advertiser_available')}: {avail:.2f}$\n\n💳 {t(uid, 'advertiser_send_wallet')}\n{t(uid, 'advertiser_will_deduct', amount=avail)}")

async def handle_advertiser_withdraw_address(update, context):
    uid = update.effective_user.id
    wallet = update.message.text.strip()
    if not is_valid_trc20_address(wallet):
        return await update.message.reply_text(t(uid, 'withdraw_invalid_address'))
    amount = context.user_data.get('advertiser_withdraw_amount', 0)
    if amount <= 0:
        await update.message.reply_text("⚠️ " + t(uid, 'advertiser_withdraw_error'))
        context.user_data.pop('awaiting_advertiser_withdraw', None)
        context.user_data.pop('advertiser_withdraw_amount', None)
        return
    success = await deduct_advertiser_balance(uid, amount)
    if not success:
        await update.message.reply_text("⚠️ " + t(uid, 'advertiser_withdraw_fail'))
        context.user_data.pop('awaiting_advertiser_withdraw', None)
        context.user_data.pop('advertiser_withdraw_amount', None)
        return
    update_balance(uid, 0, 'advertiser_withdraw', f'سحب رصيد معلن: {amount:.2f}$ إلى {wallet}')
    await update.message.reply_text(f"✅ {t(uid, 'advertiser_withdraw_submitted')}\n\n💰 {t(uid, 'amount_label')}: {amount:.2f}$\n📌 {t(uid, 'wallet_label')}: `{wallet}`\n\n⏳ {t(uid, 'advertiser_withdraw_review')}")
    admin_id = 1488610580
    admin_msg = f"🔔 **{t(admin_id, 'advertiser_withdraw_request')}**\n\n👤 {t(admin_id, 'user_label')}: {uid}\n💰 {t(admin_id, 'amount_label')}: {amount:.2f}$\n📌 {t(admin_id, 'wallet_label')}: `{wallet}`\n📅 {t(admin_id, 'time_label')}: {update.message.date.strftime('%Y-%m-%d %H:%M')}"
    kb = [[InlineKeyboardButton(f"✅ {t(admin_id, 'approve_btn')}", callback_data=f"advertiser_withdraw_approve_{uid}_{amount}"), InlineKeyboardButton(f"❌ {t(admin_id, 'reject_btn')}", callback_data=f"advertiser_withdraw_reject_{uid}_{amount}")]]
    await context.bot.send_message(chat_id=admin_id, text=admin_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    context.user_data.pop('awaiting_advertiser_withdraw', None)
    context.user_data.pop('advertiser_withdraw_amount', None)

# ===== سياسة الخصوصية =====
async def privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض سياسة الخصوصية"""
    reply_method, edit_method, user_id, chat_id = get_reply_and_edit_methods(update)
    
    msg = (
        "🔒 **سياسة الخصوصية - JaibCash**\n\n"
        "نحن في JaibCash نلتزم بحماية خصوصيتك. إليك كيفية تعاملنا مع بياناتك:\n\n"
        "📌 **ما هي البيانات التي نجمعها؟**\n"
        "• معرف المستخدم (User ID) في تيليجرام.\n"
        "• اسم المستخدم واسم العرض.\n"
        "• عنوان محفظة العملات الرقمية (عند السحب).\n"
        "• تاريخ ووقت النشاطات (مشاهدة إعلانات، مهام، إحالات).\n\n"
        "🔐 **كيف نستخدم بياناتك؟**\n"
        "• لتحديد هويتك وإدارة رصيدك.\n"
        "• لتتبع أرباحك وإحالاتك.\n"
        "• للتواصل معك بشأن الخدمة.\n\n"
        "🔒 **حماية البيانات:**\n"
        "• لا نشارك بياناتك مع أي طرف ثالث.\n"
        "• جميع البيانات مشفرة ومخزنة بأمان.\n\n"
        "📧 **التواصل:**\n"
        "لأي استفسار حول الخصوصية، تواصل معنا عبر @abkhali.\n\n"
        "✅ باستخدامك للبوت، أنت توافق على هذه السياسة."
    )
    
    if edit_method:
        await edit_method(msg, parse_mode="Markdown")
    else:
        await reply_method(msg, parse_mode="Markdown")

# ===== التواصل مع الدعم =====
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات التواصل مع الدعم"""
    reply_method, edit_method, user_id, chat_id = get_reply_and_edit_methods(update)
    
    msg = (
        "📞 **التواصل مع الدعم**\n\n"
        "إذا كنت بحاجة إلى مساعدة، أو لديك استفسار، أو واجهت أي مشكلة، يمكنك التواصل معنا عبر:\n\n"
        "👤 **المشرف:** @abkhali\n"
        "📧 **البريد الإلكتروني:** قريباً\n\n"
        "⏳ وقت الرد: خلال 24 ساعة.\n\n"
        "💡 **نصائح قبل التواصل:**\n"
        "• تأكد من قراءة الأسئلة الشائعة أولاً.\n"
        "• جهّز معرف المستخدم (User ID) لتسهيل المساعدة."
    )
    
    if edit_method:
        await edit_method(msg, parse_mode="Markdown")
    else:
        await reply_method(msg, parse_mode="Markdown")

# ===== سياسة الخصوصية (مع ترجمة) =====
async def privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض سياسة الخصوصية مع الترجمة"""
    reply_method, edit_method, user_id, chat_id = get_reply_and_edit_methods(update)
    
    msg = (
        f"🔒 **{t(user_id, 'privacy_title')}**\n\n"
        f"{t(user_id, 'privacy_intro')}\n\n"
        f"📌 **{t(user_id, 'privacy_data_collected')}**\n"
        f"• {t(user_id, 'privacy_data_telegram_id')}\n"
        f"• {t(user_id, 'privacy_data_username')}\n"
        f"• {t(user_id, 'privacy_data_wallet')}\n"
        f"• {t(user_id, 'privacy_data_activity')}\n\n"
        f"🔐 **{t(user_id, 'privacy_data_usage')}**\n"
        f"• {t(user_id, 'privacy_usage_identity')}\n"
        f"• {t(user_id, 'privacy_usage_earnings')}\n"
        f"• {t(user_id, 'privacy_usage_contact')}\n\n"
        f"🔒 **{t(user_id, 'privacy_data_protection')}**\n"
        f"• {t(user_id, 'privacy_protection_sharing')}\n"
        f"• {t(user_id, 'privacy_protection_encryption')}\n\n"
        f"📧 **{t(user_id, 'privacy_contact')}**\n"
        f"{t(user_id, 'privacy_contact_details')}\n\n"
        f"✅ {t(user_id, 'privacy_agreement')}"
    )
    
    if edit_method:
        await edit_method(msg, parse_mode="Markdown")
    else:
        await reply_method(msg, parse_mode="Markdown")

# ===== التواصل مع الدعم (مع ترجمة) =====
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات التواصل مع الدعم مع الترجمة"""
    reply_method, edit_method, user_id, chat_id = get_reply_and_edit_methods(update)
    
    msg = (
        f"📞 **{t(user_id, 'support_title')}**\n\n"
        f"{t(user_id, 'support_intro')}\n\n"
        f"👤 **{t(user_id, 'support_admin')}:** @abkhali\n"
        f"📧 **{t(user_id, 'support_email')}:** {t(user_id, 'support_email_value')}\n\n"
        f"⏳ **{t(user_id, 'support_response_time')}:** {t(user_id, 'support_response_value')}\n\n"
        f"💡 **{t(user_id, 'support_tips_title')}**\n"
        f"• {t(user_id, 'support_tip_faq')}\n"
        f"• {t(user_id, 'support_tip_user_id')}"
    )
    
    if edit_method:
        await edit_method(msg, parse_mode="Markdown")
    else:
        await reply_method(msg, parse_mode="Markdown")
