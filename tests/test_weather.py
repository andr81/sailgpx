import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
from sailweather.core import (wind_cardinal, wind_bucket, circular_mean_deg,
    circular_abs_diff, parse_openmeteo, aggregate_window, build_forecast,
    accuracy_update, ranking)

fail = 0
def check(c, m):
    global fail
    if not c:
        print("FAIL:", m); fail = 1

check(wind_cardinal(270) == "W", f"270->W got {wind_cardinal(270)}")
check(wind_cardinal(45) == "NE", f"45->NE got {wind_cardinal(45)}")
check(wind_cardinal(0) == "N", "0->N")
check(wind_bucket(11) == "10-15", f"11 bucket {wind_bucket(11)}")
check(wind_bucket(3) == "0-5", "3->0-5")
check(wind_bucket(25) == "20+", "25->20+")

cm = circular_mean_deg([350, 10])
check(cm is not None and (cm < 1 or cm > 359), f"circ mean 350,10 ~0 got {cm}")
check(circular_abs_diff(350, 10) == 20, f"diff 350,10 =20 got {circular_abs_diff(350,10)}")

data = {"hourly": {
    "time": ["2026-06-13T11:00", "2026-06-13T12:00", "2026-06-13T13:00"],
    "wind_speed_10m_ecmwf_ifs025": [10.0, 12.0, 14.0],
    "wind_gusts_10m_ecmwf_ifs025": [15.0, 16.0, 18.0],
    "wind_direction_10m_ecmwf_ifs025": [270, 270, 270],
    "wind_speed_10m_icon_eu": [12.0, 14.0, 16.0],
    "wind_gusts_10m_icon_eu": [17.0, 18.0, 20.0],
    "wind_direction_10m_icon_eu": [280, 280, 280],
}}
parsed = parse_openmeteo(data, ["ecmwf_ifs025", "icon_eu"])
check(set(parsed.keys()) == {"ecmwf_ifs025", "icon_eu"}, "parsed 2 models")
check(parsed["ecmwf_ifs025"]["speed"] == [10.0, 12.0, 14.0], "ecmwf speed series")

agg = aggregate_window(parsed["ecmwf_ifs025"]["time"], parsed["ecmwf_ifs025"]["speed"],
                       parsed["ecmwf_ifs025"]["gust"], parsed["ecmwf_ifs025"]["dir"],
                       "2026-06-13T11:00", "2026-06-13T12:00")
check(agg["wind_speed_kt"] == 11.0, f"ecmwf avg 11.0 got {agg['wind_speed_kt']}")
check(agg["wind_gust_kt"] == 16.0, f"ecmwf gust max 16.0 got {agg['wind_gust_kt']}")
check(agg["wind_dir_card"] == "W", f"dir W got {agg['wind_dir_card']}")

canon, sources = build_forecast(parsed, "2026-06-13T11:00", "2026-06-13T13:00")
check(len(sources) == 2, "2 sources")
check(canon["wind_speed_kt"] == 13.0, f"canonical speed 13.0 got {canon['wind_speed_kt']}")
check(canon["method"] == "ensemble-mean", "method")
check(abs(canon["wind_dir_deg"] - 275) <= 1, f"canonical dir ~275 got {canon['wind_dir_deg']}")

acc = {}
acc = accuracy_update(acc, sources, {"wind_speed_kt": 13.0, "wind_gust_kt": 18.0, "wind_dir_deg": 277})
check("open-meteo:ecmwf_ifs025" in acc, "acc has ecmwf")
check(acc["open-meteo:ecmwf_ifs025"]["n"] == 1, "n=1")
check(abs(acc["open-meteo:ecmwf_ifs025"]["wind_speed_mae_kt"] - 1.0) < 0.01,
      f"ecmwf mae 1.0 got {acc['open-meteo:ecmwf_ifs025']['wind_speed_mae_kt']}")
acc = accuracy_update(acc, sources, {"wind_speed_kt": 13.0, "wind_dir_deg": 277})
check(acc["open-meteo:ecmwf_ifs025"]["n"] == 2, "n=2 after second")

r = ranking(acc)
check(r and "source" in r[0], "ranking returns sorted list")

print("PASS test_weather" if fail == 0 else "TESTS FAILED")
sys.exit(fail)
