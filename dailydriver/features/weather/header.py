"""Weather header line (live or cached), suffixed with the resolved city."""

import time
from datetime import datetime, timedelta

import jdatetime

from dailydriver.core.location.resolver import resolve_city
from dailydriver.core.state import is_travel_mode

from .conditions import translate_condition
from .service import get_weather

# A schedule-driven city shows "until HH:MM" for this long before handover.
_CITY_UNTIL_WINDOW_SECONDS = 2 * 3600


def _city_suffix(info) -> str:
    if info.reason == "schedule" and info.until is not None:
        remaining = (info.until - datetime.now()).total_seconds()
        if 0 < remaining <= _CITY_UNTIL_WINDOW_SECONDS:
            return f"({info.name}, until {info.until.strftime('%H:%M')})"
    return f"({info.name})"


def get_weather_str(conn, today, is_today):
    if is_travel_mode():
        return "🌍 Travel mode"
    if is_today:
        info = resolve_city(conn)
        weather = get_weather(info)
        if weather:
            cond = weather["condition_en"] if weather["condition_en"] else weather["condition_fa"]
            emoji = weather.get("condition_emoji", "🌡️")
            text = f"{emoji} {weather['temp_c']}°C {cond} {_city_suffix(info)}"
            if time.time() - weather["timestamp"] > 3600:
                jd = jdatetime.datetime.fromtimestamp(weather["timestamp"])
                text += f" {jd.strftime('%H:%M')}"
            return text
        return ""
    else:
        # Past / future day: use cached weather from that day (no city suffix;
        # past-day display is explicitly unchanged).
        y, m, d = map(int, today.split("-"))
        gdate = jdatetime.date(y, m, d).togregorian()
        gstart = datetime(gdate.year, gdate.month, gdate.day, 0, 0, 0)
        gend = gstart + timedelta(hours=24)
        cur = conn.cursor()
        row = cur.execute(
            """SELECT temp_c, condition_fa, timestamp
               FROM weather_log
               WHERE timestamp BETWEEN ? AND ?
               ORDER BY id DESC LIMIT 1""",
            (int(gstart.timestamp()), int(gend.timestamp())),
        ).fetchone()
        if row:
            cond_info = translate_condition(row["condition_fa"])
            cond_en = cond_info["en"] if cond_info and cond_info.get("en") != "NOT TRANSLATED" else row["condition_fa"]
            emoji = cond_info.get("emoji", "🌡️") if cond_info else "🌡️"
            return f"{emoji} {row['temp_c']}°C {cond_en}"
        return ""
