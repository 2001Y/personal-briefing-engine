import json
import math
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from hermes_pulse.models import CollectedItem, Provenance


JST = ZoneInfo("Asia/Tokyo")
DEFAULT_ENV_PATH = Path.home() / "services" / "dawarich" / ".env"
DEFAULT_DB_CONTAINER = "dawarich_db"
DEFAULT_POSTGRES_QUERY_LIMIT = 240


class LocationContextConnector:
    id = "location_context"
    source_family = "location"

    def __init__(
        self,
        runner: Callable[[], dict[str, Any]] | None = None,
        error_handler: Callable[[str, str], None] | None = None,
        success_handler: Callable[[str], None] | None = None,
    ) -> None:
        self._runner = runner or _run_location_context
        self._uses_default_runner = runner is None
        self._error_handler = error_handler
        self._success_handler = success_handler

    def collect(self) -> list[CollectedItem]:
        try:
            payload = self._runner()
        except Exception as exc:
            if self._uses_default_runner:
                if self._error_handler is not None:
                    self._error_handler(self.id, str(exc))
                return []
            raise
        if not payload:
            if self._success_handler is not None:
                self._success_handler(self.id)
            return []
        place = payload.get("place") or "Unknown place"
        maps_url = payload.get("maps_url")
        context = payload.get("context") or []
        detected_reason = payload.get("detected_reason") or _infer_detected_reason(payload)
        body = "\n".join(f"- {value}" for value in context)
        if self._success_handler is not None:
            self._success_handler(self.id)
        return [
            CollectedItem(
                id=f"location_context:{place}",
                source="location_context",
                source_kind="place",
                title=place,
                body=body,
                url=maps_url,
                provenance=Provenance(
                    provider="location_context",
                    acquisition_mode="local_store",
                    raw_record_id=str(payload.get("arrived_at") or place),
                ),
                metadata={
                    "arrived_at": payload.get("arrived_at"),
                    "context": context,
                    "maps_url": maps_url,
                    "local_time": payload.get("local_time"),
                    "dwell_minutes": payload.get("dwell_minutes"),
                    "place_category": payload.get("place_category"),
                    "detected_reason": detected_reason,
                },
            )
        ]


def _infer_detected_reason(payload: dict[str, Any]) -> str:
    local_time = payload.get("local_time")
    dwell_minutes = payload.get("dwell_minutes") or 0
    if dwell_minutes and dwell_minutes < 15:
        return "transient_stop"
    hour = _extract_hour(local_time)
    if hour is None:
        return "stopped_moving"
    if 11 <= hour < 14 or 17 <= hour < 20:
        return "meal_window"
    if 14 <= hour < 17:
        return "snack_window"
    return "stopped_moving"


def _extract_hour(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).hour
    except ValueError:
        return None


def load_location_context_fixture(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def _run_location_context() -> dict[str, Any]:
    points = _fetch_recent_points(DEFAULT_DB_CONTAINER, DEFAULT_ENV_PATH, DEFAULT_POSTGRES_QUERY_LIMIT)
    if not points:
        return {}
    payload = _detect_dwell_payload(
        points,
        now=datetime.now(timezone.utc),
        dwell_radius_m=80.0,
        min_dwell_minutes=15,
        max_staleness_minutes=90,
    )
    return payload or {}


def _load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env


def _run_psql_query(container: str, env_path: Path, sql: str) -> str:
    env = _load_env(env_path)
    command = [
        "docker",
        "exec",
        container,
        "psql",
        "-U",
        env["POSTGRES_USER"],
        "-d",
        env["POSTGRES_DB"],
        "-AtF",
        "\t",
        "-c",
        sql,
    ]
    return subprocess.check_output(command, text=True)


def _fetch_recent_points(container: str, env_path: Path, limit: int) -> list[dict[str, float | int | None]]:
    sql = (
        "SELECT timestamp, ST_Y(lonlat::geometry) AS lat, ST_X(lonlat::geometry) AS lon, accuracy, velocity "
        f"FROM points WHERE lonlat IS NOT NULL ORDER BY timestamp DESC LIMIT {limit};"
    )
    output = _run_psql_query(container, env_path, sql)
    points: list[dict[str, float | int | None]] = []
    for raw in output.splitlines():
        if not raw.strip():
            continue
        ts, lat, lon, accuracy, velocity = raw.split("\t")
        points.append(
            {
                "timestamp": int(ts),
                "lat": float(lat),
                "lon": float(lon),
                "accuracy": float(accuracy) if accuracy else None,
                "velocity": float(velocity) if velocity not in {"", "-1"} else None,
            }
        )
    return points


def _detect_dwell_payload(
    points: list[dict[str, float | int | None]],
    *,
    now: datetime,
    dwell_radius_m: float,
    min_dwell_minutes: int,
    max_staleness_minutes: int,
) -> dict[str, Any] | None:
    latest = points[0]
    latest_dt = datetime.fromtimestamp(int(latest["timestamp"]), tz=timezone.utc)
    age_minutes = (now - latest_dt).total_seconds() / 60
    if age_minutes > max_staleness_minutes:
        return None

    cluster = [latest]
    for point in points[1:]:
        distance = _haversine_m(
            float(latest["lat"]),
            float(latest["lon"]),
            float(point["lat"]),
            float(point["lon"]),
        )
        if distance > dwell_radius_m:
            break
        cluster.append(point)

    earliest = cluster[-1]
    dwell_minutes = int((int(latest["timestamp"]) - int(earliest["timestamp"])) / 60)
    if dwell_minutes < min_dwell_minutes:
        return None

    local_dt = latest_dt.astimezone(JST)
    detected_reason = _infer_runtime_reason(local_dt)
    lat = float(latest["lat"])
    lon = float(latest["lon"])
    return {
        "place": f"{lat:.5f}, {lon:.5f}",
        "maps_url": f"https://maps.google.com/?q={lat},{lon}",
        "context": _build_runtime_context(detected_reason, dwell_minutes),
        "local_time": local_dt.isoformat(),
        "dwell_minutes": dwell_minutes,
        "detected_reason": detected_reason,
        "arrived_at": datetime.fromtimestamp(int(earliest["timestamp"]), tz=timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _infer_runtime_reason(local_dt: datetime) -> str:
    hour = local_dt.hour
    if 11 <= hour < 14 or 17 <= hour < 20:
        return "meal_window"
    if 14 <= hour < 17:
        return "snack_window"
    return "stopped_moving"


def _build_runtime_context(reason: str, dwell_minutes: int) -> list[str]:
    base = [f"Stopped here for about {dwell_minutes} minutes."]
    if reason == "meal_window":
        return ["Meal timing is open for this stop."] + base
    if reason == "snack_window":
        return ["Snack / coffee timing fits this stop."] + base
    return ["Movement has paused long enough to surface local context."] + base
