"""CLI анализатора: python3 -m sailtrack.cli <track.gpx> [--twd N] [--boat-json '{...}'] [--svg out.svg].

Печатает JSON summary в stdout. Запуск: PYTHONPATH=$SAILING_REPO/lib python3 -m sailtrack.cli ...
"""
import argparse
import json

from .gpx import parse_gpx
from .analyze import analyze_track
from .render import render_svg


def main(argv=None):
    ap = argparse.ArgumentParser(description="Анализ парусного GPX-трека (kt/nm).")
    ap.add_argument("gpx", help="путь к .gpx")
    ap.add_argument("--twd", type=float, default=None, help="TWD 'from' в градусах (иначе оценка из трека)")
    ap.add_argument("--boat-json", default=None, help='JSON параметров лодки: {"upwind_twa":45,"downwind_twa":150,"hull_length_m":4.2}')
    ap.add_argument("--svg", default=None, help="путь для SVG-рендера трека")
    a = ap.parse_args(argv)

    points = parse_gpx(a.gpx)
    boat = json.loads(a.boat_json) if a.boat_json else None
    res = analyze_track(points, twd=a.twd, boat=boat)
    if a.svg:
        render_svg(points, a.svg)
        res["svg"] = a.svg
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
