import os, sys, math, tempfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
from sailtrack.gpx import TrackPoint
from sailtrack.analyze import (analyze_track, estimate_twd, resample_1hz,
                               derive_cog_sog, norm360, circ_mean)
from sailtrack.render import render_svg

fail = 0
def check(c, m):
    global fail
    if not c:
        print("FAIL:", m); fail = 1


def make_track():
    """Синтетический windward-leeward: лавировка ±45° от N (TWD_from≈0), затем спуск на юг."""
    pts = []
    lat, lon = 53.97, 27.38
    t = datetime(2026, 6, 13, 8, 0, 0, tzinfo=timezone.utc)

    def step(heading, speed, secs):
        nonlocal lat, lon, t
        for _ in range(secs):
            d_nm = speed / 3600.0
            lat += (d_nm / 60.0) * math.cos(math.radians(heading))
            lon += (d_nm / 60.0) * math.sin(math.radians(heading)) / math.cos(math.radians(lat))
            pts.append(TrackPoint(t, lat, lon, speed, heading))
            t += timedelta(seconds=1)

    for _ in range(3):            # лавировка вверх: 3 галса на каждый борт
        step(45, 4.0, 40)         # port
        step(315, 4.0, 40)        # starboard
    step(180, 5.5, 120)          # спуск на юг (run)
    return pts


track = make_track()

# --- circular helpers ---
check(norm360(360.0) == 0.0, "norm360(360)->0")
cm = circ_mean([350, 10])
check(cm is not None and (cm < 1 or cm > 359), f"circ_mean wrap ~0 got {cm}")

# --- оценка TWD (смешанный трек: лавировка + спуск) ---
twd = estimate_twd(derive_cog_sog(resample_1hz(track)))
check(twd is not None, "twd estimated")
if twd is not None:
    diff = min(abs(twd - 0), abs(twd - 360))
    check(diff <= 25, f"estimated TWD ~0 (N), got {twd}")

# --- одномодовый трек (только спуск на юг) → TWD неоднозначен → None ---
def make_downwind():
    pts = []
    lat, lon = 53.97, 27.38
    t = datetime(2026, 6, 13, 9, 0, 0, tzinfo=timezone.utc)
    for _ in range(300):
        d_nm = 5.5 / 3600.0
        lat += (d_nm / 60.0) * math.cos(math.radians(180))
        lon += (d_nm / 60.0) * math.sin(math.radians(180)) / math.cos(math.radians(lat))
        pts.append(TrackPoint(t, lat, lon, 5.5, 180))
        t += timedelta(seconds=1)
    return pts

twd_pure = estimate_twd(derive_cog_sog(resample_1hz(make_downwind())))
check(twd_pure is None, f"pure-downwind TWD ambiguous -> None, got {twd_pure}")

# --- полный анализ ---
res = analyze_track(track)   # без явного TWD → оценка
check("error" not in res, f"no error: {res.get('error')}")
check(res["maneuvers"]["tacks"] >= 2, f"tacks>=2, got {res['maneuvers']['tacks']}")
leg_types = {l["type"] for l in res["legs"]}
check("upwind" in leg_types, f"upwind leg present, legs={leg_types}")
check("downwind" in leg_types, f"downwind leg present, legs={leg_types}")
check(res["speed"]["max_kt"] >= 5.0, f"max speed ~5.5, got {res['speed']['max_kt']}")
check(res["groove_twa_std_deg"] is not None, "groove computed")

# --- analyze с явным TWD=0 даёт положительный upwind VMG где-то ---
res2 = analyze_track(track, twd=0.0)
check(res2["wind"]["twd_source"] == "provided", "twd_source provided")
ups = [l for l in res2["legs"] if l["type"] == "upwind"]
check(ups and ups[0]["avg_vmg_kt"] is not None and ups[0]["avg_vmg_kt"] > 0,
      f"upwind avg_vmg>0, got {ups[0]['avg_vmg_kt'] if ups else None}")

# --- рендер SVG ---
out = os.path.join(tempfile.mkdtemp(), "track.svg")
render_svg(track, out)
svg = open(out, encoding="utf-8").read()
check(svg.startswith("<svg") and "<line" in svg, "svg rendered with lines")

print("PASS test_analyze" if fail == 0 else "TESTS FAILED")
sys.exit(fail)
