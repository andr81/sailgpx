"""Устойчивый парсер GPX и базовая статистика трека (kt/nm). Только stdlib."""
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from math import radians, sin, cos, asin, sqrt
from typing import Optional, List

MS_TO_KT = 1.94384       # м/с → узлы
M_TO_NM = 1.0 / 1852.0   # метры → морские мили
_EARTH_M = 6371000.0


@dataclass
class TrackPoint:
    time: Optional[datetime]
    lat: float
    lon: float
    speed_kt: Optional[float]   # из extension (м/с→kt), если есть
    course: Optional[float]     # градусы, если есть


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_time(text: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_gpx(path: str) -> List[TrackPoint]:
    root = ET.parse(path).getroot()
    points: List[TrackPoint] = []
    for el in root.iter():
        if _localname(el.tag) != "trkpt":
            continue
        lat = float(el.get("lat"))
        lon = float(el.get("lon"))
        t = speed_ms = course = None
        for child in el.iter():
            ln = _localname(child.tag)
            txt = (child.text or "").strip()
            if not txt:
                continue
            if ln == "time" and t is None:
                t = _parse_time(txt)
            elif ln == "speed" and speed_ms is None:
                try:
                    speed_ms = float(txt)
                except ValueError:
                    pass
            elif ln == "course" and course is None:
                try:
                    course = float(txt)
                except ValueError:
                    pass
        speed_kt = round(speed_ms * MS_TO_KT, 2) if speed_ms is not None else None
        points.append(TrackPoint(t, lat, lon, speed_kt, course))
    return points


def haversine_nm(a: TrackPoint, b: TrackPoint) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (a.lat, a.lon, b.lat, b.lon))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * _EARTH_M * asin(sqrt(h)) * M_TO_NM


def basic_stats(points: List[TrackPoint]) -> dict:
    zero = {"duration_min": 0.0, "distance_nm": 0.0, "max_speed_kt": 0.0, "avg_speed_kt": 0.0}
    if len(points) < 2:
        return zero
    dist_nm = sum(haversine_nm(points[i], points[i + 1]) for i in range(len(points) - 1))
    times = [p.time for p in points if p.time is not None]
    dur_min = (times[-1] - times[0]).total_seconds() / 60.0 if len(times) >= 2 else 0.0

    speeds = [p.speed_kt for p in points if p.speed_kt is not None]
    if not speeds:
        for i in range(len(points) - 1):
            a, b = points[i], points[i + 1]
            if a.time and b.time:
                dt_h = (b.time - a.time).total_seconds() / 3600.0
                if dt_h > 0:
                    speeds.append(haversine_nm(a, b) / dt_h)
    max_kt = max(speeds) if speeds else 0.0
    avg_kt = dist_nm / (dur_min / 60.0) if dur_min > 0 else 0.0
    return {
        "duration_min": round(dur_min, 1),
        "distance_nm": round(dist_nm, 2),
        "max_speed_kt": round(max_kt, 1),
        "avg_speed_kt": round(avg_kt, 1),
    }
