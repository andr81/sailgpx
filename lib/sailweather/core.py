"""Open-Meteo мульти-модель: парсинг, агрегация, лог точности. kt/градусы. stdlib."""
import json
import urllib.request
import urllib.parse
from math import radians, degrees, sin, cos, atan2

_CARD8 = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def wind_cardinal(deg):
    return _CARD8[int((deg % 360) / 45 + 0.5) % 8]


def wind_bucket(kt):
    for hi, label in ((5, "0-5"), (10, "5-10"), (15, "10-15"), (20, "15-20")):
        if kt < hi:
            return label
    return "20+"


def circular_mean_deg(degs):
    vals = [d for d in degs if d is not None]
    if not vals:
        return None
    x = sum(cos(radians(d)) for d in vals)
    y = sum(sin(radians(d)) for d in vals)
    if abs(x) < 1e-9 and abs(y) < 1e-9:
        return None
    return degrees(atan2(y, x)) % 360


def circular_abs_diff(a, b):
    d = abs((a - b) % 360)
    return min(d, 360 - d)


def parse_openmeteo(data, models):
    h = data["hourly"]
    times = h["time"]
    out = {}
    for m in models:
        def col(base):
            return h.get(f"{base}_{m}", h.get(base))
        sp = col("wind_speed_10m")
        if sp is None:
            continue
        out[m] = {"time": times, "speed": sp,
                  "gust": col("wind_gusts_10m"), "dir": col("wind_direction_10m")}
    return out


def aggregate_window(times, speed, gust, direction, start, end):
    idx = [i for i, t in enumerate(times) if start <= t <= end]
    if not idx:
        idx = list(range(len(times)))

    def pick(series):
        return [series[i] for i in idx if series and series[i] is not None]

    sp, gu, di = pick(speed), pick(gust), pick(direction)
    avg_sp = round(sum(sp) / len(sp), 1) if sp else None
    max_gu = round(max(gu), 1) if gu else None
    cdir = circular_mean_deg(di)
    return {
        "wind_speed_kt": avg_sp,
        "wind_gust_kt": max_gu,
        "wind_dir_deg": round(cdir) if cdir is not None else None,
        "wind_dir_card": wind_cardinal(cdir) if cdir is not None else None,
        "wind_bucket": wind_bucket(avg_sp) if avg_sp is not None else None,
    }


def build_forecast(parsed, start, end):
    sources = []
    for m, s in parsed.items():
        agg = aggregate_window(s["time"], s["speed"], s["gust"], s["dir"], start, end)
        sources.append({"source": f"open-meteo:{m}", **agg})
    sp = [s["wind_speed_kt"] for s in sources if s["wind_speed_kt"] is not None]
    gu = [s["wind_gust_kt"] for s in sources if s["wind_gust_kt"] is not None]
    di = [s["wind_dir_deg"] for s in sources if s["wind_dir_deg"] is not None]
    avg_sp = round(sum(sp) / len(sp), 1) if sp else None
    cdir = circular_mean_deg(di)
    canonical = {
        "method": "ensemble-mean",
        "wind_speed_kt": avg_sp,
        "wind_gust_kt": round(sum(gu) / len(gu), 1) if gu else None,
        "wind_dir_deg": round(cdir) if cdir is not None else None,
        "wind_dir_card": wind_cardinal(cdir) if cdir is not None else None,
        "wind_bucket": wind_bucket(avg_sp) if avg_sp is not None else None,
    }
    return canonical, sources


def accuracy_update(acc, sources, actual):
    for s in sources:
        key = s["source"]
        rec = acc.get(key, {"n": 0, "wind_speed_mae_kt": 0.0, "wind_dir_mae_deg": 0.0,
                            "gust_mae_kt": 0.0, "bias_speed_kt": 0.0})
        n = rec["n"]

        def upd(field, err):
            rec[field] = round((rec[field] * n + err) / (n + 1), 2)

        if s.get("wind_speed_kt") is not None and actual.get("wind_speed_kt") is not None:
            upd("wind_speed_mae_kt", abs(s["wind_speed_kt"] - actual["wind_speed_kt"]))
            upd("bias_speed_kt", s["wind_speed_kt"] - actual["wind_speed_kt"])
        if s.get("wind_gust_kt") is not None and actual.get("wind_gust_kt") is not None:
            upd("gust_mae_kt", abs(s["wind_gust_kt"] - actual["wind_gust_kt"]))
        if s.get("wind_dir_deg") is not None and actual.get("wind_dir_deg") is not None:
            upd("wind_dir_mae_deg", circular_abs_diff(s["wind_dir_deg"], actual["wind_dir_deg"]))
        rec["n"] = n + 1
        acc[key] = rec
    return acc


def ranking(acc):
    items = [{"source": k, **v} for k, v in acc.items()]
    return sorted(items, key=lambda r: r.get("wind_speed_mae_kt", 9e9))


_DEFAULT_MODELS = ["ecmwf_ifs025", "icon_eu", "icon_d2", "gfs_global", "best_match"]
_HOURLY = ("wind_speed_10m,wind_direction_10m,wind_gusts_10m,"
           "temperature_2m,surface_pressure,precipitation,cloud_cover")


def build_forecast_url(lat, lon, models=None):
    models = models or _DEFAULT_MODELS
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "models": ",".join(models),
        "hourly": _HOURLY, "wind_speed_unit": "kn", "timezone": "Europe/Minsk",
    })
    return f"https://api.open-meteo.com/v1/forecast?{q}"


def build_archive_url(lat, lon, start_date, end_date):
    q = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon, "start_date": start_date, "end_date": end_date,
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m,temperature_2m",
        "wind_speed_unit": "kn", "timezone": "Europe/Minsk",
    })
    return f"https://archive-api.open-meteo.com/v1/archive?{q}"


def fetch_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)
