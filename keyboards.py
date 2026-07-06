from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from i18n import t

def get_reply_keyboard(user_id):
    keyboard = [
        [KeyboardButton(t(user_id, 'btn_balance')), KeyboardButton(t(user_id, 'btn_watch')), KeyboardButton(t(user_id, 'btn_tasks'))],
        [KeyboardButton(t(user_id, 'btn_referral')), KeyboardButton(t(user_id, 'btn_checkin')), KeyboardButton(t(user_id, 'btn_rank'))],
        [KeyboardButton(t(user_id, 'btn_withdraw')), KeyboardButton(t(user_id, 'btn_account')), KeyboardButton(t(user_id, 'btn_rewards'))],
        [KeyboardButton(t(user_id, 'btn_advertiser_wallet'))]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_language_selection():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"), InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ])

def get_wallet_menu(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(user_id, 'wallet_charge'), callback_data="wallet_charge")],
        [InlineKeyboardButton(t(user_id, 'wallet_withdraw'), callback_data="wallet_withdraw")],
        [InlineKeyboardButton(t(user_id, 'wallet_advertiser_withdraw'), callback_data="wallet_advertiser_withdraw")],
        [InlineKeyboardButton(t(user_id, 'wallet_history'), callback_data="wallet_history")],
        [InlineKeyboardButton(t(user_id, 'wallet_back'), callback_data="wallet_back")]
    ])

def get_tasks_menu(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(user_id, 'tasks_browse'), callback_data="tasks_browse")],
        [InlineKeyboardButton(t(user_id, 'tasks_create'), callback_data="create_task")],
        [InlineKeyboardButton(t(user_id, 'tasks_achievements'), callback_data="tasks_achievements")],
        [InlineKeyboardButton(t(user_id, 'tasks_my_posts'), callback_data="tasks_my_posts")],
        [InlineKeyboardButton(t(user_id, 'tasks_back'), callback_data="tasks_back")]
    ])

def get_account_menu(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(user_id, 'account_profile'), callback_data="account_profile")],
        [InlineKeyboardButton(t(user_id, 'account_level'), callback_data="account_level")],
        [InlineKeyboardButton(t(user_id, 'account_stats'), callback_data="account_stats")],
        [InlineKeyboardButton(t(user_id, 'account_achievements'), callback_data="account_achievements")],
        [InlineKeyboardButton(t(user_id, 'account_back'), callback_data="account_back")]
    ])

def get_ad_watch_buttons(user_id, click_url, button_name, reward_url, reward_button_name):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(button_name, url=click_url)],
        [InlineKeyboardButton(reward_button_name, url=reward_url)]
    ])

def get_referral_menu(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(user_id, 'referral_share'), callback_data="referral_share")],
        [InlineKeyboardButton(t(user_id, 'referral_stats_btn'), callback_data="referral_stats")],
        [InlineKeyboardButton(t(user_id, 'referral_back'), callback_data="referral_back")]
    ])

def get_leaderboard_menu(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(user_id, 'leaderboard_weekly'), callback_data="leaderboard_weekly")],
        [InlineKeyboardButton(t(user_id, 'leaderboard_monthly'), callback_data="leaderboard_monthly")],
        [InlineKeyboardButton(t(user_id, 'leaderboard_back'), callback_data="leaderboard_back")]
    ])
