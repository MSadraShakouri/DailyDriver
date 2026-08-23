"""IRIMO HTTP client and current-weather parser."""

import re
import ssl
import urllib.request

IRIMO_URL = (
    "https://www.irimo.ir/far/index.php?module=web_directory&wd_id=701&id=17561"
    "&ctitle=%D9%BE%D9%8A%D8%B4%20%D8%A8%D9%8A%D9%86%D9%8A%20%D9%88%D8%B6%D8%B9%20"
    "%D9%87%D9%88%D8%A7%D9%8A%20%D8%AA%D9%87%D8%B1%D8%A7%D9%86"
)


def fetch_weather() -> tuple[int, str] | None:
    """Fetch ``(temperature_celsius, Persian condition)`` from IRIMO."""
    context = ssl.create_default_context()
    context.set_ciphers("DEFAULT:@SECLEVEL=1")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        request = urllib.request.Request(IRIMO_URL, headers=headers)
        with urllib.request.urlopen(request, context=context, timeout=15) as response:
            html = response.read().decode("utf-8")
    except Exception:
        return None

    match = re.search(
        r"هوای حاضر.*?<div[^>]*?font-size:48px.*?>(.*?)°\s*c\s*</div>.*?<div[^>]*?font-size:18px.*?>(.*?)</div>",
        html,
        re.DOTALL,
    )
    if not match:
        return None

    digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    return int(match.group(1).strip().translate(digits)), match.group(2).strip()
