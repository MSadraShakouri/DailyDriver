#!/usr/bin/env python3
"""Test suite for unified time parser."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from dailydriver.utils.time_parser import parse_duration, parse_time, parse_time_range, parse_prayer_args

def test_parse_duration():
    # valid
    assert parse_duration("30m") == 30
    assert parse_duration("1h") == 60
    assert parse_duration("1h15m") == 75
    assert parse_duration("2hours") == 120
    assert parse_duration("45mins") == 45
    assert parse_duration("90") is None       # not supported
    # invalid
    assert parse_duration("abc") is None
    assert parse_duration("") is None
    print("✓ parse_duration tests passed")

def test_parse_time():
    now = datetime(2025, 5, 2, 12, 0, 0)   # noon
    # 'now'
    assert parse_time("n", now) == now
    assert parse_time("now", now) == now
    # offset
    t = parse_time("-30", now)
    assert t == now - timedelta(minutes=30)
    # HH:MM past
    t = parse_time("09:15", now)
    assert t == now.replace(hour=9, minute=15, second=0, microsecond=0)
    # HH:MM future (will become yesterday by default)
    t = parse_time("14:00", now)
    assert t == now.replace(hour=14, minute=0, second=0, microsecond=0) - timedelta(days=1)
    # with allow_future=True
    t = parse_time("14:00", now, allow_future=True)
    assert t == now.replace(hour=14, minute=0, second=0, microsecond=0)
    # integer hour
    t = parse_time("8", now)
    assert t == now.replace(hour=8, minute=0, second=0, microsecond=0)
    # invalid
    assert parse_time("25:00", now) is None
    assert parse_time("abc", now) is None
    print("✓ parse_time tests passed")

def test_parse_time_range():
    now = datetime(2025, 5, 2, 12, 0, 0)
    # standard two arguments (23:00 → yesterday, 07:15 → today)
    start, end, dur = parse_time_range(["23:00", "07:15"], now)
    yesterday = now - timedelta(days=1)
    assert start == yesterday.replace(hour=23, minute=0, second=0, microsecond=0)
    assert end == now.replace(hour=7, minute=15, second=0, microsecond=0)
    assert dur == 8*60+15

    # compact form as single argument
    start, end, dur = parse_time_range(["23-7:15"], now)
    assert start == yesterday.replace(hour=23, minute=0, second=0, microsecond=0)
    assert end == now.replace(hour=7, minute=15, second=0, microsecond=0)
    assert dur == 8*60+15

    # invalid
    start, end, dur = parse_time_range(["abc"], now)
    assert start is None
    print("✓ parse_time_range tests passed")

def test_parse_prayer_args():
    # empty
    args = []
    res = parse_prayer_args(args)
    assert res == {'offset_min': None, 'explicit_time': None, 'jamaat_location': None, 'shak_count': 0}
    # offset
    args = ["-15"]
    res = parse_prayer_args(args)
    assert res['offset_min'] == 15
    # explicit time
    args = ["05:30"]
    res = parse_prayer_args(args)
    assert res['explicit_time'] == 5*60+30
    # jamaat
    args = ["j", "masjid"]
    res = parse_prayer_args(args)
    assert res['jamaat_location'] == "masjid"
    # shak
    args = ["s", "3"]
    res = parse_prayer_args(args)
    assert res['shak_count'] == 3
    # combination
    args = ["-10", "j", "home", "s", "2"]
    res = parse_prayer_args(args)
    assert res['offset_min'] == 10
    assert res['jamaat_location'] == "home"
    assert res['shak_count'] == 2
    # mixed with explicit time
    args = ["05:30", "j"]
    res = parse_prayer_args(args)
    assert res['explicit_time'] == 5*60+30
    assert res['jamaat_location'] == ''
    print("✓ parse_prayer_args tests passed")

if __name__ == "__main__":
    test_parse_duration()
    test_parse_time()
    test_parse_time_range()
    test_parse_prayer_args()
    print("\nAll time parser tests passed ✅")
