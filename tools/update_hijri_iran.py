#!/usr/bin/env python3
"""Refresh the offline Iranian Hijri month-start table.

The runtime application never fetches this source.  This script is intended for
release maintenance (and the scheduled GitHub Actions updater) and turns the
Iranian converter data maintained by Persian Calendar into DailyDriver's small,
explicit month-anchor table.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import date, timedelta
from pathlib import Path

SOURCE_URL = (
    "https://raw.githubusercontent.com/persian-calendar/calendar/main/"
    "src/main/kotlin/io/github/persiancalendar/calendar/islamic/"
    "IranianIslamicDateConverter.kt"
)
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "hijri_iran.json"
SUPPORTED_START_JDN = 2_396_005
MONTH_ROW_RE = re.compile(r"/\*(\d+)\*/\s+0b([01_]+)")


def _gregorian_from_jdn(jdn: int) -> date:
    """Convert an integer Julian day number to a proleptic Gregorian date."""
    # Fliegel–Van Flandern integer algorithm.  The converter's JDN values use
    # the same midnight/day-number convention as the source table.
    value = jdn + 68_569
    century = (4 * value) // 146_097
    value -= (146_097 * century + 3) // 4
    year_part = (4_000 * (value + 1)) // 1_461_001
    value -= (1_461 * year_part) // 4 - 31
    month_part = (80 * value) // 2_447
    day = value - (2_447 * month_part) // 80
    value = month_part // 11
    month = month_part + 2 - 12 * value
    year = 100 * (century - 49) + year_part + value
    return date(year, month, day)


def parse_month_rows(source: str) -> list[tuple[int, str]]:
    """Extract and validate the packed Iranian month-length rows."""
    rows = [(int(year), bits.replace("_", "")) for year, bits in MONTH_ROW_RE.findall(source)]
    if not rows:
        raise ValueError("Iranian converter source contained no month rows")

    if rows[0][0] != 1264:
        raise ValueError(f"Iranian converter source must start at 1264, got {rows[0][0]}")

    expected_year = rows[0][0]
    for year, bits in rows:
        if year != expected_year:
            raise ValueError(f"missing or out-of-order Iranian year row: expected {expected_year}, got {year}")
        if len(bits) != 12:
            raise ValueError(f"Iranian year {year} has {len(bits)} month bits, expected 12")
        expected_year += 1
    return rows


def build_payload(source: str, *, source_url: str = SOURCE_URL) -> dict:
    """Build a stable JSON payload from the upstream packed rows."""
    rows = parse_month_rows(source)
    current_jdn = SUPPORTED_START_JDN
    months = []

    for year, bits in rows:
        for month, bit in enumerate(bits, start=1):
            length = 30 if bit == "1" else 29
            months.append(
                {
                    "hijri": f"{year:04}-{month:02}",
                    "start": _gregorian_from_jdn(current_jdn).isoformat(),
                    "days": length,
                }
            )
            current_jdn += length

    return {
        "schema_version": 1,
        "calendar": "iranian-month-start-table",
        "future_policy": "provisional-until-official-confirmation",
        "source": source_url,
        "source_range": {
            "first": f"{rows[0][0]:04}-01",
            "last": f"{rows[-1][0]:04}-12",
        },
        "months": months,
    }


def _fetch_source(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "DailyDriver Hijri updater"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def _has_future_horizon(payload: dict, minimum_months: int, today: date) -> bool:
    future = [entry for entry in payload["months"] if date.fromisoformat(entry["start"]) > today]
    return len(future) >= minimum_months


def refresh(
    *,
    output: Path = OUTPUT_FILE,
    source_url: str = SOURCE_URL,
    source_file: Path | None = None,
    minimum_future_months: int = 18,
    today: date | None = None,
) -> bool:
    """Refresh *output* and return whether its contents changed.

    ``source_file`` is useful for deterministic local tests.  Normal updates
    fetch the upstream file.  The horizon check prevents a scheduled updater
    from silently accepting a table that is about to run out of future data.
    """
    if minimum_future_months < 0:
        raise ValueError("minimum_future_months must be non-negative")

    source = source_file.read_text(encoding="utf-8") if source_file is not None else _fetch_source(source_url)
    payload = build_payload(source, source_url=source_url)
    current_day = today or date.today()
    if not _has_future_horizon(payload, minimum_future_months, current_day):
        last_start = payload["months"][-1]["start"]
        raise RuntimeError(
            f"Iranian table ends at {last_start}; it has fewer than "
            f"{minimum_future_months} future month starts after {current_day}"
        )

    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    old = output.read_text(encoding="utf-8") if output.exists() else None
    if old == rendered:
        return False

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(output)
    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    parser.add_argument("--source-url", default=SOURCE_URL)
    parser.add_argument("--source-file", type=Path, help="Read a local Kotlin source instead of downloading it")
    parser.add_argument(
        "--minimum-future-months",
        type=int,
        default=18,
        help="Refuse to write data with less than this many future month starts (default: 18)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    changed = refresh(
        output=args.output,
        source_url=args.source_url,
        source_file=args.source_file,
        minimum_future_months=args.minimum_future_months,
    )
    print(f"Iranian Hijri table {'updated' if changed else 'already current'}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
