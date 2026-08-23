import os
import sqlite3

from jdatetime import date as jdate
from jdatetime import timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "daily.db")


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all sleep+nap data aggregated by date
    query = """
    SELECT jalali_date, SUM(duration_minutes) AS total_minutes
    FROM (
        SELECT jalali_date, duration_minutes FROM sleep_logs
        UNION ALL
        SELECT jalali_date, duration_minutes FROM nap_logs
    )
    GROUP BY jalali_date
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    if not rows:
        print("No data found.")
        return

    # Build a dict: date -> minutes
    sleep_by_date = {row[0]: row[1] for row in rows}

    # Get min and max dates
    min_date_str = min(sleep_by_date.keys())
    max_date_str = max(sleep_by_date.keys())

    # Convert to jdatetime objects
    min_date = jdate(*map(int, min_date_str.split("-")))
    max_date = jdate(*map(int, max_date_str.split("-")))

    # Iterate over all days in range
    total_minutes = 0
    day_count = 0
    current = min_date
    while current <= max_date:
        date_str = current.strftime("%Y-%m-%d")
        minutes = sleep_by_date.get(date_str, 0)  # 0 if no log
        total_minutes += minutes
        day_count += 1
        current += timedelta(days=1)  # <-- fixed: timedelta from jdatetime

    # Compute averages
    avg_minutes = total_minutes / day_count

    total_h = total_minutes // 60
    total_m = total_minutes % 60
    avg_h = int(avg_minutes // 60)
    avg_m = int(avg_minutes % 60)

    print("--- Summary (including empty days as 0) ---")
    print(f"Date range:           {min_date_str} → {max_date_str}")
    print(f"Total days in range:  {day_count}")
    print(f"Days with data:       {len(sleep_by_date)}")
    print(f"Total sleep (incl. naps):  {total_h}h {total_m:02d}m")
    print(f"Average per day:            {avg_h}h {avg_m:02d}m")
    print(f"Average in minutes:         {avg_minutes:.1f} min")

    conn.close()


if __name__ == "__main__":
    main()
