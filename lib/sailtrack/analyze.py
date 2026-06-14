"""Анализатор парусного трека (тренер-тактик). Только stdlib, поверх gpx.py.

Пайплайн: resample(1 Гц) → COG/SOG (сглаживание) → TWD (задан или оценка из трека) →
TWA/класс курса → детект поворотов (tack/gybe) + углы/цена → сегментация ног →
агрегаты (скорость, VMG, groove, % галсов). Углы — циклическая арифметика, 0°=N.
"""
from dataclasses import dataclass
from math import radians, degrees, sin, cos, atan2, sqrt
from typing import List, Optional

from .gpx import TrackPoint, haversine_nm, MS_TO_KT  # noqa: F401

# --- углы ---------------------------------------------------------------


def norm360(d: float) -> float:
    return d % 360.0


def signed_diff(a: float, b: float) -> float:
    """a-b в диапазоне (-180, 180]."""
    return ((a - b + 180.0) % 360.0) - 180.0


def circ_abs_diff(a: float, b: float) -> float:
    return abs(signed_diff(a, b))


def circ_mean(degs) -> Optional[float]:
    vals = [d for d in degs if d is not None]
    if not vals:
        return None
    x = sum(cos(radians(d)) for d in vals)
    y = sum(sin(radians(d)) for d in vals)
    if abs(x) < 1e-9 and abs(y) < 1e-9:
        return None
    return norm360(degrees(atan2(y, x)))


def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = radians(lat1), radians(lat2)
    dl = radians(lon2 - lon1)
    y = sin(dl) * cos(p2)
    x = cos(p1) * sin(p2) - sin(p1) * cos(p2) * cos(dl)
    return norm360(degrees(atan2(y, x)))


# --- ресемплинг и производные -------------------------------------------


@dataclass
class Sample:
    t: float            # секунды от старта
    lat: float
    lon: float
    sog: float          # kt (сглаженная)
    cog: Optional[float]  # градусы (сглаженный), None при дрейфе
    twa: Optional[float] = None    # |TWA|, 0..180
    tack: Optional[str] = None     # 'stbd' | 'port'
    pos: Optional[str] = None      # close-hauled|reach|run
    vmg: Optional[float] = None    # kt, + к ветру


def _epoch(points: List[TrackPoint]) -> List[float]:
    return [p.time.timestamp() for p in points]


def resample_1hz(points: List[TrackPoint]):
    """Линейная интерполяция позиции/скорости на равномерную сетку 1 Гц."""
    pts = [p for p in points if p.time is not None]
    if len(pts) < 2:
        return []
    ts = _epoch(pts)
    t0, tn = ts[0], ts[-1]
    has_speed = any(p.speed_kt is not None for p in pts)
    out = []
    j = 0
    n = int(tn - t0)
    for k in range(n + 1):
        tt = t0 + k
        while j < len(ts) - 2 and ts[j + 1] < tt:
            j += 1
        a, b = pts[j], pts[j + 1]
        span = ts[j + 1] - ts[j]
        f = 0.0 if span <= 0 else (tt - ts[j]) / span
        f = max(0.0, min(1.0, f))
        lat = a.lat + (b.lat - a.lat) * f
        lon = a.lon + (b.lon - a.lon) * f
        sog = None
        if has_speed and a.speed_kt is not None and b.speed_kt is not None:
            sog = a.speed_kt + (b.speed_kt - a.speed_kt) * f
        out.append(Sample(t=float(k), lat=lat, lon=lon, sog=sog if sog is not None else 0.0, cog=None))
    return out


def _median(xs):
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2.0


def derive_cog_sog(samples, compute_speed_if_missing=True):
    """COG из позиций (сглаженный циклически), SOG сглаженный (медиана3→среднее5)."""
    nn = len(samples)
    # сырой COG между соседями
    raw_cog = [None] * nn
    for i in range(nn - 1):
        a, b = samples[i], samples[i + 1]
        if haversine_nm(a, b) * 1852.0 > 0.3:   # > 0.3 м смещение
            raw_cog[i] = bearing_deg(a.lat, a.lon, b.lat, b.lon)
    if nn >= 2:
        raw_cog[-1] = raw_cog[-2]
    # скорость: если не было extension — посчитать из позиций (kt)
    if compute_speed_if_missing and all(s.sog == 0.0 for s in samples):
        for i in range(nn - 1):
            d_nm = haversine_nm(samples[i], samples[i + 1])
            samples[i].sog = d_nm * 3600.0  # за 1 c → nm/h = kt
        if nn >= 2:
            samples[-1].sog = samples[-2].sog
    # сглаживание SOG
    sm = [s.sog for s in samples]
    win = 3
    med = [_median(sm[max(0, i - win // 2): i + win // 2 + 1]) for i in range(nn)]
    win2 = 5
    for i in range(nn):
        lo, hi = max(0, i - win2 // 2), min(nn, i + win2 // 2 + 1)
        samples[i].sog = round(sum(med[lo:hi]) / (hi - lo), 2)
    # циклическое сглаживание COG (окно 5)
    for i in range(nn):
        lo, hi = max(0, i - 2), min(nn, i + 3)
        chunk = [raw_cog[k] for k in range(lo, hi) if raw_cog[k] is not None]
        cmean = circ_mean(chunk) if chunk else None
        # гейт по скорости: при дрейфе COG не считаем
        samples[i].cog = round(cmean, 1) if (cmean is not None and samples[i].sog >= 0.5) else None
    return samples


# --- ветер и углы -------------------------------------------------------


def estimate_twd(samples) -> Optional[float]:
    """Оценка TWD ('from') из трека: главная ось COG (axial tensor) + выбор конца
    по меньшей средней скорости (апвинд медленнее)."""
    pairs = [(s.cog, s.sog) for s in samples if s.cog is not None and s.sog >= 0.5]
    if len(pairs) < 10:
        return None
    # axial: усредняем удвоенный угол, взвешивая дистанцией (~ sog)
    x = sum(w * cos(radians(2 * c)) for c, w in pairs)
    y = sum(w * sin(radians(2 * c)) for c, w in pairs)
    axis = norm360(0.5 * degrees(atan2(y, x)))     # 0..360, но это ось (mod 180)
    cand = [axis % 360, (axis + 180) % 360]
    # выбрать конец, к которому боат идёт медленнее (апвинд)
    def mean_speed_toward(theta):
        sel = [w for c, w in pairs if circ_abs_diff(c, theta) <= 50]
        return sum(sel) / len(sel) if sel else 9e9
    twd = min(cand, key=mean_speed_toward)   # апвинд COG ≈ TWD_from
    return round(twd, 1)


def _classify(samples, twd, boat):
    up = boat.get("upwind_twa", 45)
    dn = boat.get("downwind_twa", 150)
    ch_lim = up + 12          # close-hauled, если |TWA| <= upwind+12
    run_lim = dn - 15         # run, если |TWA| >= downwind-15
    for s in samples:
        if s.cog is None:
            continue
        sd = signed_diff(s.cog, twd)        # + : ветер слева? зависит, но знак = галс
        twa = abs(sd)
        s.twa = round(twa, 1)
        s.tack = "stbd" if sd < 0 else "port"
        s.pos = "close-hauled" if twa <= ch_lim else ("run" if twa >= run_lim else "reach")
        s.vmg = round(s.sog * cos(radians(twa)), 2)   # + к ветру (twa<90), - от ветра
    return samples


# --- повороты -----------------------------------------------------------


def detect_maneuvers(samples, debounce=5):
    """Повороты = устойчивые смены галса (>= debounce сек). tack (апвинд) / gybe (даунвинд)."""
    labeled = [(i, s) for i, s in enumerate(samples) if s.tack is not None]
    maneuvers = []
    if len(labeled) < 2 * debounce:
        return maneuvers
    prev_side = labeled[0][1].tack
    run_start = 0
    runs = []  # (side, start_idx_in_labeled, end_idx_in_labeled)
    for k in range(1, len(labeled)):
        if labeled[k][1].tack != prev_side:
            runs.append((prev_side, run_start, k - 1))
            run_start = k
            prev_side = labeled[k][1].tack
    runs.append((prev_side, run_start, len(labeled) - 1))
    # оставить только устойчивые отрезки
    stable = [r for r in runs if (r[2] - r[1] + 1) >= debounce]
    def settled_cog(center, direction):
        """Устоявшийся COG в окне 3..13 c со сдвигом от границы поворота."""
        lo, hi = sorted((center + direction * 3, center + direction * 13))
        chunk = [samples[k].cog for k in range(max(0, lo), min(len(samples), hi + 1))
                 if samples[k].cog is not None]
        return circ_mean(chunk)

    for a, b in zip(stable, stable[1:]):
        # переход между концом a и началом b
        i_before = labeled[a[2]][0]
        i_after = labeled[b[1]][0]
        s_before, s_after = samples[i_before], samples[i_after]
        twa_avg = ((s_before.twa or 0) + (s_after.twa or 0)) / 2.0
        kind = "tack" if twa_avg < 90 else "gybe"
        # угол поворота — из устоявшихся участков, а не на самой границе
        cog_b, cog_a = settled_cog(i_before, -1), settled_cog(i_after, +1)
        ang = circ_abs_diff(cog_b, cog_a) if (cog_b is not None and cog_a is not None) else None
        # фильтр шумовых смен галса у оси ветра: реальный поворот меняет курс заметно
        if ang is None or ang < 35:
            continue
        # цена: мин скорость между, скорость входа, восстановление
        seg = samples[i_before:i_after + 1]
        entry = s_before.sog
        vmin = min((s.sog for s in seg), default=entry)
        loss = round(entry - vmin, 2)
        # восстановление: время от vmin до >=95% entry (в сек = индексы 1Гц)
        recover = None
        try:
            vmin_idx = min(range(len(seg)), key=lambda q: seg[q].sog)
            for q in range(vmin_idx, len(seg)):
                if seg[q].sog >= 0.95 * entry:
                    recover = q - vmin_idx
                    break
        except ValueError:
            recover = None
        maneuvers.append({
            "kind": kind, "t": s_before.t,
            "angle_deg": round(ang, 1) if ang is not None else None,
            "speed_loss_kt": loss,
            "recover_s": recover,
        })
    return maneuvers


# --- ноги и агрегаты ----------------------------------------------------


def _smooth_pos(samples, win=15):
    """Мажоритарное сглаживание класса курса — убирает дребезг у границ для сегментации ног."""
    poss = [s.pos for s in samples]
    half = win // 2
    out = list(poss)
    for i in range(len(samples)):
        lo, hi = max(0, i - half), min(len(samples), i + half + 1)
        chunk = [poss[k] for k in range(lo, hi) if poss[k] is not None]
        if chunk:
            out[i] = max(set(chunk), key=chunk.count)
    for i, s in enumerate(samples):
        if s.pos is not None:
            s.pos = out[i]
    return samples


def _segment_legs(samples, min_len=30):
    legs = []
    cur = None
    for s in samples:
        if s.pos is None:
            continue
        key = "upwind" if s.pos == "close-hauled" else ("downwind" if s.pos == "run" else "reach")
        if cur and cur["type"] == key:
            cur["samples"].append(s)
        else:
            if cur and len(cur["samples"]) >= min_len:
                legs.append(cur)
            cur = {"type": key, "samples": [s]}
    if cur and len(cur["samples"]) >= min_len:
        legs.append(cur)
    return legs


def _leg_stats(leg):
    ss = leg["samples"]
    sogs = [s.sog for s in ss]
    vmgs = [s.vmg for s in ss if s.vmg is not None]
    stbd = sum(1 for s in ss if s.tack == "stbd")
    return {
        "type": leg["type"],
        "duration_min": round(len(ss) / 60.0, 1),
        "avg_speed_kt": round(sum(sogs) / len(sogs), 1) if sogs else 0.0,
        "avg_vmg_kt": round(sum(vmgs) / len(vmgs), 2) if vmgs else None,
        "pct_starboard": round(100.0 * stbd / len(ss)) if ss else None,
    }


def _stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def analyze_track(points: List[TrackPoint], twd: Optional[float] = None, boat: Optional[dict] = None) -> dict:
    boat = boat or {}
    samples = resample_1hz(points)
    if len(samples) < 10:
        return {"error": "too few points", "n_samples": len(samples)}
    derive_cog_sog(samples)
    twd_used = twd if twd is not None else estimate_twd(samples)
    twd_source = "provided" if twd is not None else "estimated"
    maneuvers = []
    legs_out = []
    groove = None
    if twd_used is not None:
        _classify(samples, twd_used, boat)
        maneuvers = detect_maneuvers(samples)
        _smooth_pos(samples)
        legs_out = [_leg_stats(l) for l in _segment_legs(samples)]
        up_twa = [s.twa for s in samples if s.pos == "close-hauled" and s.twa is not None]
        groove = round(_stdev(up_twa), 1) if len(up_twa) >= 5 else None

    sogs = [s.sog for s in samples]
    dist_nm = sum(haversine_nm(samples[i], samples[i + 1]) for i in range(len(samples) - 1))
    tacks = sum(1 for m in maneuvers if m["kind"] == "tack")
    gybes = sum(1 for m in maneuvers if m["kind"] == "gybe")
    tack_angles = [m["angle_deg"] for m in maneuvers if m["kind"] == "tack" and m["angle_deg"] is not None]

    return {
        "n_samples": len(samples),
        "duration_min": round(len(samples) / 60.0, 1),
        "distance_nm": round(dist_nm, 2),
        "speed": {
            "max_kt": round(max(sogs), 1),
            "avg_kt": round(sum(sogs) / len(sogs), 1),
        },
        "wind": {"twd_deg": twd_used, "twd_source": twd_source},
        "maneuvers": {
            "tacks": tacks,
            "gybes": gybes,
            "avg_tacking_angle_deg": round(sum(tack_angles) / len(tack_angles), 1) if tack_angles else None,
            "list": maneuvers,
        },
        "legs": legs_out,
        "groove_twa_std_deg": groove,
    }
