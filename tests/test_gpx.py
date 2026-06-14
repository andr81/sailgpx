import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
from sailtrack.gpx import parse_gpx, basic_stats

FIX = os.path.join(HERE, "fixtures")
fail = 0

def check(cond, msg):
    global fail
    if not cond:
        print("FAIL:", msg); fail = 1

pts = parse_gpx(os.path.join(FIX, "mini.gpx"))
check(len(pts) == 3, f"expected 3 points, got {len(pts)}")
check(abs(pts[0].speed_kt - 5.0) < 0.05, f"pt0 speed_kt ~5.0, got {pts[0].speed_kt}")
check(abs(pts[1].speed_kt - 10.0) < 0.05, f"pt1 speed_kt ~10.0, got {pts[1].speed_kt}")
check(pts[0].course == 10.0, f"pt0 course 10, got {pts[0].course}")
check(pts[0].time is not None, "pt0 time parsed")

st = basic_stats(pts)
check(abs(st["duration_min"] - 2.0) < 0.05, f"duration_min ~2.0, got {st['duration_min']}")
check(st["max_speed_kt"] == 10.0, f"max_speed_kt 10.0, got {st['max_speed_kt']}")
check(st["distance_nm"] > 0, f"distance_nm > 0, got {st['distance_nm']}")

pts2 = parse_gpx(os.path.join(FIX, "nospeed.gpx"))
check(all(p.speed_kt is None for p in pts2), "nospeed: extension speed absent")
st2 = basic_stats(pts2)
check(st2["max_speed_kt"] > 0, f"nospeed computed max > 0, got {st2['max_speed_kt']}")

print("PASS test_gpx" if fail == 0 else "TESTS FAILED")
sys.exit(fail)
