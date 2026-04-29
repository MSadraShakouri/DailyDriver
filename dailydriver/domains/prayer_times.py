# dailydriver/domains/prayer_times.py
"""Tehran prayer times based on University of Tehran calendar (1403).
Data for 1st, 8th, 15th, 22nd of each Jalali month.
Times are interpolated for dates in between.
"""
from bisect import bisect_right

# Each month: list of (day, (fajr_h, fajr_m), (dhuhr_h, dhuhr_m), (maghrib_h, maghrib_m))
# Day numbers: 1, 8, 15, 22   (approximate – actual calendar used these days)
_DATA = {
    1: [  # Farvardin
        (1,  (4, 42), (12, 12), (18, 36)),
        (8,  (4, 31), (12, 10), (18, 41)),
        (15, (4, 20), (12, 8),  (18, 47)),
        (22, (4, 9),  (12, 5),  (18, 54)),
    ],
    2: [  # Ordibehesht
        (1,  (3, 55), (12, 4),  (19, 1)),
        (8,  (3, 44), (12, 2),  (19, 7)),
        (15, (3, 30), (12, 1),  (19, 16)),
        (22, (3, 22), (12, 1),  (19, 22)),
    ],
    3: [  # Khordad
        (1,  (3, 14), (12, 1),  (19, 28)),
        (8,  (3, 6),  (12, 2),  (19, 35)),
        (15, (3, 3),  (12, 4),  (19, 42)),
        (22, (3, 1),  (12, 5),  (19, 44)),
    ],
    4: [  # Tir
        (1,  (3, 2),  (12, 7),  (19, 45)),
        (8,  (3, 3),  (12, 7),  (19, 46)),
        (15, (3, 10), (12, 9),  (19, 40)),
        (22, (3, 17), (12, 10), (19, 33)),
    ],
    5: [  # Mordad
        (1,  (3, 24), (12, 11), (19, 37)),
        (8,  (3, 32), (12, 11), (19, 31)),
        (15, (3, 40), (12, 11), (19, 24)),
        (22, (3, 50), (12, 9),  (19, 16)),
    ],
    6: [  # Shahrivar
        (1,  (4, 2),  (12, 6),  (19, 1)),
        (8,  (4, 13), (12, 3),  (18, 44)),
        (15, (4, 21), (12, 1),  (18, 31)),
        (22, (4, 27), (11, 59), (18, 20)),
    ],
    7: [  # Mehr
        (1,  (4, 36), (11, 53), (18, 4)),
        (8,  (4, 47), (11, 50), (17, 47)),
        (15, (4, 53), (11, 49), (17, 37)),
        (22, (4, 59), (11, 48), (17, 28)),
    ],
    8: [  # Aban
        (1,  (4, 53), (11, 49), (17, 39)),
        (8,  (4, 58), (11, 48), (17, 32)),
        (15, (5, 2),  (11, 49), (17, 26)),
        (22, (5, 7),  (11, 51), (17, 21)),
    ],
    9: [  # Azar
        (1,  (5, 18), (11, 50), (17, 14)),
        (8,  (5, 24), (11, 53), (17, 12)),
        (15, (5, 30), (11, 55), (17, 11)),
        (22, (5, 35), (11, 59), (17, 12)),
    ],
    10: [  # Dey
        (1,  (5, 41), (12, 4),  (17, 17)),
        (8,  (5, 43), (12, 6),  (17, 20)),
        (15, (5, 45), (12, 10), (17, 25)),
        (22, (5, 45), (12, 14), (17, 31)),
    ],
    11: [  # Bahman
        (1,  (5, 42), (12, 17), (17, 44)),
        (8,  (5, 41), (12, 17), (17, 46)),
        (15, (5, 37), (12, 19), (17, 53)),
        (22, (5, 31), (12, 19), (18, 1)),
    ],
    12: [  # Esfand
        (1,  (5, 23), (12, 19), (18, 9)),
        (8,  (5, 12), (12, 18), (18, 17)),
        (15, (5, 5),  (12, 17), (18, 23)),
        (22, (4, 56), (12, 16), (18, 28)),
    ],
}

def _to_minutes(h, m):
    return h * 60 + m

def _from_minutes(mins):
    h = mins // 60
    m = mins % 60
    return (h, m)

def _interpolate(t, t1, t2, v1, v2):
    """Linearly interpolate between v1 at t1 and v2 at t2."""
    if t1 == t2:
        return v1
    frac = (t - t1) / (t2 - t1)
    val = v1 + frac * (v2 - v1)
    return val

def _next_month(month):
    return month % 12 + 1

def _prev_month(month):
    return (month - 2) % 12 + 1

def get_approximate_times(jalali_month: int, day: int):
    """Return dict with keys 'fajr', 'dhuhr', 'maghrib' for a given Jalali month/day.
    Values are (hour, minute) tuples.
    """
    if not (1 <= jalali_month <= 12):
        raise ValueError("Month must be 1..12")
    if not (1 <= day <= 31):
        raise ValueError("Day must be 1..31")

    points = _DATA[jalali_month]
    # Extract days and values (in minutes)
    days = [p[0] for p in points]
    vals_fajr = [_to_minutes(*p[1]) for p in points]
    vals_dhuhr = [_to_minutes(*p[2]) for p in points]
    vals_maghrib = [_to_minutes(*p[3]) for p in points]

    # Find surrounding data points
    idx = bisect_right(days, day)  # index of first day > target
    if idx == 0:
        # day before first data point: use first point (rare)
        return {
            'fajr': points[0][1],
            'dhuhr': points[0][2],
            'maghrib': points[0][3],
        }
    if idx == len(days):
        # day after last data point: extrapolate using next month's first point
        next_m = _next_month(jalali_month)
        next_points = _DATA[next_m]
        t1 = days[-1]
        t2 = next_points[0][0] + 31  # approximate, but okay for small gap
        v1_f = vals_fajr[-1]
        v2_f = _to_minutes(*next_points[0][1])
        v1_d = vals_dhuhr[-1]
        v2_d = _to_minutes(*next_points[0][2])
        v1_m = vals_maghrib[-1]
        v2_m = _to_minutes(*next_points[0][3])
        t = day
        # Use t2 as next month's day 1 + 31 (same month length ~31)
        # Slight inaccuracy, but adequate for daily times.
        res_f = _from_minutes(round(_interpolate(t, t1, t2, v1_f, v2_f)))
        res_d = _from_minutes(round(_interpolate(t, t1, t2, v1_d, v2_d)))
        res_m = _from_minutes(round(_interpolate(t, t1, t2, v1_m, v2_m)))
        return {'fajr': res_f, 'dhuhr': res_d, 'maghrib': res_m}
    else:
        # normal interpolation between points[idx-1] and points[idx]
        t1 = days[idx-1]
        t2 = days[idx]
        v1_f, v2_f = vals_fajr[idx-1], vals_fajr[idx]
        v1_d, v2_d = vals_dhuhr[idx-1], vals_dhuhr[idx]
        v1_m, v2_m = vals_maghrib[idx-1], vals_maghrib[idx]
        t = day
        res_f = _from_minutes(round(_interpolate(t, t1, t2, v1_f, v2_f)))
        res_d = _from_minutes(round(_interpolate(t, t1, t2, v1_d, v2_d)))
        res_m = _from_minutes(round(_interpolate(t, t1, t2, v1_m, v2_m)))
        return {'fajr': res_f, 'dhuhr': res_d, 'maghrib': res_m}
