# ============================================================
# JaibCash Bot - i18n.py (محرك الترجمة)
# ============================================================

import json
import os
from typing import Dict, Any
from database import get_language

# تحميل ملفات الترجمة
_locales = {}

def load_locale(lang: str) -> Dict[str, Any]:
    """تحميل ملف ترجمة معين مع التخزين المؤقت"""
    if lang in _locales:
        return _locales[lang]
    
    file_path = os.path.join('locales', f'{lang}.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _locales[lang] = data
            return data
    except FileNotFoundError:
        if lang != 'ar':
            return load_locale('ar')
        return {}

def reload_locale(lang: str):
    """إعادة تحميل ملف الترجمة (للتحديث بعد تغيير اللغة)"""
    if lang in _locales:
        del _locales[lang]
    return load_locale(lang)

def t(user_id: int, key: str, **kwargs) -> str:
    """دالة الترجمة الأساسية"""
    lang = get_language(user_id)
    if not lang:
        lang = 'ar'
    
    locale = load_locale(lang)
    text = locale.get(key, f"Missing: {key}")
    
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text

def get_level_name(user_id: int, level: int) -> str:
    lang = get_language(user_id) or 'ar'
    locale = load_locale(lang)
    level_names = locale.get('level_names', {})
    return level_names.get(str(level), f"Level {level}")

def get_text_by_lang(lang: str, key: str, **kwargs) -> str:
    locale = load_locale(lang)
    text = locale.get(key, f"Missing: {key}")
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text
