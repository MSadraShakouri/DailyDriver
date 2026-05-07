# dailydriver/utils/weather.py
"""Fetch and cache Tehran weather from IRIMO."""
import json
import os
import re
import ssl
import time
import urllib.request
from dailydriver.core.database import get_connection_cm
# Per‑session flag to avoid repeated failed fetches
_fetch_failed_this_session = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
TRANSLATION_FILE = os.path.join(DATA_DIR, "weather_conditions.json")

IRIMO_URL = "https://www.irimo.ir/far/index.php?module=web_directory&wd_id=701&id=17561&ctitle=%D9%BE%D9%8A%D8%B4%20%D8%A8%D9%8A%D9%86%D9%8A%20%D9%88%D8%B6%D8%B9%20%D9%87%D9%88%D8%A7%D9%8A%20%D8%AA%D9%87%D8%B1%D8%A7%D9%86"

CACHE_HOURS = 1

def _load_translations():
    if not os.path.exists(TRANSLATION_FILE):
        return {}
    with open(TRANSLATION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_translations(trans):
    with open(TRANSLATION_FILE, "w", encoding="utf-8") as f:
        json.dump(trans, f, ensure_ascii=False, indent=2)

def _translate_condition(condition_fa):
    """Return dict with 'en' and 'emoji', or None if untranslated."""
    trans = _load_translations()
    if condition_fa not in trans:
        trans[condition_fa] = {"en": "NOT TRANSLATED", "emoji": "❓"}
        _save_translations(trans)
        return None
    entry = trans[condition_fa]
    if entry["en"] == "NOT TRANSLATED":
        return None
    return entry

def _fetch_weather():
    """Return (temp_c, condition_fa) or None on failure."""
    ctx = ssl.create_default_context()
    ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        req = urllib.request.Request(IRIMO_URL, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode('utf-8')
    except Exception:
        return None

    # Find temperature number before ° c in the current weather section
    # Extract relevant chunk: look for "هوای حاضر" section
    m = re.search(r'هوای حاضر.*?<div[^>]*?font-size:48px.*?>(.*?)°\s*c\s*</div>.*?<div[^>]*?font-size:18px.*?>(.*?)</div>',
                  html, re.DOTALL)
    if not m:
        return None
    temp_str = m.group(1).strip()
    condition = m.group(2).strip()
    # Convert Persian digits to ASCII
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    ascii_digits = '0123456789'
    trans_table = str.maketrans(persian_digits, ascii_digits)
    temp_c = int(temp_str.translate(trans_table))
    return temp_c, condition

def _update_weather(conn):
    global _fetch_failed_this_session
    data = _fetch_weather()
    if data is None:
        _fetch_failed_this_session = True
        return None
    temp_c, condition_fa = data
    ts = int(time.time())
    cur = conn.cursor()
    cur.execute("INSERT INTO weather_log (city, temp_c, condition_fa, timestamp) VALUES (?,?,?,?)",
                ("Tehran", temp_c, condition_fa, ts))
    conn.commit()
    return temp_c, condition_fa

def get_weather():
    global _fetch_failed_this_session
    if _fetch_failed_this_session:
        with get_connection_cm(auto=False) as conn:
            cur = conn.cursor()
            cur.execute("SELECT temp_c, condition_fa, timestamp FROM weather_log ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row is None:
                return None
            cond_info = _translate_condition(row['condition_fa'])
            condition_en = cond_info['en'] if cond_info else None
            condition_emoji = cond_info['emoji'] if cond_info else '🌡️'
            return {
                'temp_c': row['temp_c'],
                'condition_fa': row['condition_fa'],
                'condition_en': condition_en,
                'condition_emoji': condition_emoji,
                'city': 'Tehran',
                'timestamp': row['timestamp'],
            }

    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT temp_c, condition_fa, timestamp FROM weather_log ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        now = int(time.time())
        if row is None or (now - row['timestamp']) > CACHE_HOURS * 3600:
            data = _update_weather(conn)
            if data is not None:
                temp_c, condition_fa = data
                ts = now
            else:
                if row is None:
                    return None
                temp_c = row['temp_c']
                condition_fa = row['condition_fa']
                ts = row['timestamp']
        else:
            temp_c = row['temp_c']
            condition_fa = row['condition_fa']
            ts = row['timestamp']

        cond_info = _translate_condition(condition_fa)
        condition_en = cond_info['en'] if cond_info else None
        condition_emoji = cond_info['emoji'] if cond_info else '🌡️'
        return {
            'temp_c': temp_c,
            'condition_fa': condition_fa,
            'condition_en': condition_en,
            'condition_emoji': condition_emoji,
            'city': 'Tehran',
            'timestamp': ts,
        }
