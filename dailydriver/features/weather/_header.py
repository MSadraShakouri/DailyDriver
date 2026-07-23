# dailydriver/features/weather/_header.py
"""Weather header line (live or cached)."""

import time
from datetime import datetime, timedelta

import jdatetime

from ._logic import _translate_condition, get_weather
from dailydriver.core.travel_mode import is_travel_mode


def get_weather_str(conn, today, is_today):
    if is_travel_mode():
        return "🌍 Travel mode"
    if is_today:
        weather = get_weather()
        if weather:
            cond = weather["condition_en"] if weather["condition_en"] else weather["condition_fa"]
            emoji = weather.get("condition_emoji", "🌡️")
            text = f"{emoji} {weather['temp_c']}°C {cond}"
            if time.time() - weather["timestamp"] > 3600:
                jd = jdatetime.datetime.fromtimestamp(weather["timestamp"])
                text += f" {jd.strftime('%H:%M')}"
            return text
        return ""
    else:
        # Past / future day: use cached weather from that day
        y, m, d = map(int, today.split("-"))
        gdate = jdatetime.date(y, m, d).togregorian()
        gstart = datetime(gdate.year, gdate.month, gdate.day, 0, 0, 0)
        gend = gstart + timedelta(hours=24)
        cur = conn.cursor()
        row = cur.execute(
            "SELECT temp_c, condition_fa, timestamp FROM weather_log WHERE timestamp BETWEEN ? AND ? ORDER BY id DESC LIMIT 1",
            (int(gstart.timestamp()), int(gend.timestamp())),
        ).fetchone()
        if row:
            cond_info = _translate_condition(row["condition_fa"])
            cond_en = cond_info["en"] if cond_info and cond_info.get("en") != "NOT TRANSLATED" else row["condition_fa"]
            emoji = cond_info.get("emoji", "🌡️") if cond_info else "🌡️"
            return f"{emoji} {row['temp_c']}°C {cond_en}"
        return ""
