"""Георефересная карта давления: спутник (Esri World Imagery) + накладка ячеек
средней скорости на лавировке, совмещённые по координатам (Web Mercator). stdlib.

Сетка считается по close-hauled-точкам (прокси «давления»); спутник тянется по bbox
треков. Возвращает самодостаточный SVG (PNG вшит base64) — встраивается в Obsidian.
"""
import base64
import math
import urllib.parse
import urllib.request

from .gpx import parse_gpx
from .analyze import resample_1hz, derive_cog_sog, _classify

_R = 6378137.0
_ESRI = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
         "World_Imagery/MapServer/export")


def merc(lat, lon):
    x = _R * math.radians(lon)
    y = _R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y


def collect_close_hauled(tracks, boat=None):
    """tracks: [(gpx_path, twd), ...] → ([(lat,lon,sog)...], [(lat,lon)...all])."""
    boat = boat or {"upwind_twa": 42, "downwind_twa": 145}
    ch, allpts = [], []
    for path, twd in tracks:
        S = derive_cog_sog(resample_1hz(parse_gpx(path)))
        _classify(S, twd, boat)
        for s in S:
            allpts.append((s.lat, s.lon))
            if s.pos == "close-hauled":
                ch.append((s.lat, s.lon, s.sog))
    return ch, allpts


def _color(t):
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        r, g = 255, int(255 * t / 0.5)
    else:
        r, g = int(255 * (1 - (t - 0.5) / 0.5)), 200
    return f"#{r:02x}{g:02x}00"


def fetch_esri_png(x0, y0, x1, y1, w, h):
    url = _ESRI + "?" + urllib.parse.urlencode({
        "bbox": f"{x0},{y0},{x1},{y1}", "bboxSR": 3857, "imageSR": 3857,
        "size": f"{w},{h}", "format": "png", "f": "image"})
    req = urllib.request.Request(url, headers={"User-Agent": "sailgpx/1.0"})
    return urllib.request.urlopen(req, timeout=30).read()


def build_pressure_svg(grid_points, all_points, out_path, marks=None,
                       nx=12, ny=8, min_n=8, width=1000, view_pad_frac=0.6,
                       label="Среднее давление (скорость на лавировке, kt)"):
    # ВИД (спутник) — широкий, чтобы были видны берега
    vlats = [p[0] for p in all_points]
    vlons = [p[1] for p in all_points]
    dla = (max(vlats) - min(vlats)) * view_pad_frac
    dlo = (max(vlons) - min(vlons)) * view_pad_frac
    la0, la1 = min(vlats) - dla, max(vlats) + dla
    lo0, lo1 = min(vlons) - dlo, max(vlons) + dlo
    x0, y0 = merc(la0, lo0)
    x1, y1 = merc(la1, lo1)
    W = width
    H = int(W * (y1 - y0) / (x1 - x0))

    try:
        png = fetch_esri_png(x0, y0, x1, y1, W, H)
        b64 = base64.b64encode(png).decode()
        bg = (f'<image x="0" y="0" width="{W}" height="{H}" '
              f'xlink:href="data:image/png;base64,{b64}" '
              f'href="data:image/png;base64,{b64}"/>')
        bgrect = ""
    except Exception:
        bg = ""
        bgrect = f'<rect width="{W}" height="{H}" fill="#9ab"/>'

    def px(lon):
        x, _ = merc((la0 + la1) / 2, lon)
        return (x - x0) / (x1 - x0) * W

    def py(lat):
        _, y = merc(lat, (lo0 + lo1) / 2)
        return (y1 - y) / (y1 - y0) * H

    # СЕТКА — по экстенту лавировочных точек (плотно, не растягиваем на весь вид)
    glats = [p[0] for p in grid_points]
    glons = [p[1] for p in grid_points]
    gla0, gla1 = min(glats), max(glats)
    glo0, glo1 = min(glons), max(glons)
    cells = {}
    for la, lo, v in grid_points:
        cx = min(nx - 1, int((lo - glo0) / (glo1 - glo0 + 1e-9) * nx))
        cy = min(ny - 1, int((la - gla0) / (gla1 - gla0 + 1e-9) * ny))
        cells.setdefault((cx, cy), []).append(v)
    means = {k: sum(v) / len(v) for k, v in cells.items() if len(v) >= min_n}
    if means:
        vmin, vmax = min(means.values()), max(means.values())
    else:
        vmin, vmax = 0.0, 1.0

    def lbl(x, y, text, size=14):
        # чёрный жирный текст с белым ореолом (paint-order) — читается на любом фоне
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="bold" '
                f'text-anchor="middle" paint-order="stroke" style="paint-order:stroke" '
                f'fill="#000" stroke="#fff" stroke-width="3" stroke-linejoin="round">{text}</text>')

    rects = []
    for (cx, cy), v in means.items():
        cl = glo0 + cx / nx * (glo1 - glo0)
        cr = glo0 + (cx + 1) / nx * (glo1 - glo0)
        cb = gla0 + cy / ny * (gla1 - gla0)
        ct = gla0 + (cy + 1) / ny * (gla1 - gla0)
        xL, xR, yT, yB = px(cl), px(cr), py(ct), py(cb)
        t = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5
        rects.append(
            f'<rect x="{xL:.1f}" y="{yT:.1f}" width="{xR - xL:.1f}" height="{yB - yT:.1f}" '
            f'fill="{_color(t)}" fill-opacity="0.5" stroke="#000" stroke-opacity="0.25"/>'
            + lbl((xL + xR) / 2, (yT + yB) / 2 + 4, f"{v:.1f}", 13))

    mk = []
    for la, lo, name, color in (marks or []):
        mk.append(f'<circle cx="{px(lo):.1f}" cy="{py(la):.1f}" r="6" fill="{color}" '
                  f'stroke="#fff" stroke-width="1.5"/>'
                  + lbl(px(lo) + 30, py(la) + 4, name, 13))

    leg = (f'<rect x="0" y="0" width="{W}" height="22" fill="#000" fill-opacity="0.55"/>'
           f'<text x="8" y="15" font-size="13" fill="#fff">{label} · '
           f'красный=медленно ({vmin:.1f}) → зелёный=быстро ({vmax:.1f}) kt</text>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">{bgrect}{bg}'
           + "".join(rects) + "".join(mk) + leg + "</svg>")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    return out_path
