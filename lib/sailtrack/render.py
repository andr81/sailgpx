"""SVG-рендер трека (раскраска по скорости). Без сторонних зависимостей.

Obsidian встраивает SVG как изображение: ![[files/track-render.svg]].
"""
import math
from typing import List

from .gpx import TrackPoint


def _color_by_speed(v: float, vmax: float) -> str:
    t = 0.0 if vmax <= 0 else max(0.0, min(1.0, v / vmax))
    r = int(255 * t)
    b = int(255 * (1 - t))
    return f"#{r:02x}50{b:02x}"


def render_svg(points: List[TrackPoint], out_path: str, by: str = "speed",
               width: int = 800, height: int = 600, pad: int = 24) -> str:
    pts = [p for p in points]
    if len(pts) < 2:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"></svg>')
        return out_path

    latc = math.radians((min(p.lat for p in pts) + max(p.lat for p in pts)) / 2)
    xs = [(p.lon) * math.cos(latc) for p in pts]
    ys = [p.lat for p in pts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    spanx = (maxx - minx) or 1e-9
    spany = (maxy - miny) or 1e-9
    scale = min((width - 2 * pad) / spanx, (height - 2 * pad) / spany)

    def sx(x):
        return pad + (x - minx) * scale

    def sy(y):
        return height - pad - (y - miny) * scale   # север вверх

    speeds = [p.speed_kt if p.speed_kt is not None else 0.0 for p in pts]
    vmax = max(speeds) or 1.0

    segs = []
    for i in range(len(pts) - 1):
        segs.append(
            f'<line x1="{sx(xs[i]):.1f}" y1="{sy(ys[i]):.1f}" '
            f'x2="{sx(xs[i + 1]):.1f}" y2="{sy(ys[i + 1]):.1f}" '
            f'stroke="{_color_by_speed(speeds[i], vmax)}" stroke-width="2"/>'
        )
    start = f'<circle cx="{sx(xs[0]):.1f}" cy="{sy(ys[0]):.1f}" r="5" fill="#1a9850"/>'
    end = f'<circle cx="{sx(xs[-1]):.1f}" cy="{sy(ys[-1]):.1f}" r="5" fill="#222"/>'
    legend = f'<text x="{pad}" y="{height - 6}" font-size="12" fill="#444">синий — медленно · красный — быстро (max {vmax:.1f} kt)</text>'
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="{width}" height="{height}" fill="white"/>'
        + "".join(segs) + start + end + legend + "</svg>"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    return out_path
