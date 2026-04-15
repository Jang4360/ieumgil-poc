#!/usr/bin/env python3
"""Serve the GraphHopper KakaoMap viewer with a local hybrid transit API."""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
VIEWER_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / ".env"
TRANSPORT_SCRIPTS_DIR = ROOT_DIR / "scripts" / "transportation"

if str(TRANSPORT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(TRANSPORT_SCRIPTS_DIR))

import evaluate_dataset_linking as transit_base  # noqa: E402


HOST = "127.0.0.1"
PORT = 8080
HYBRID_DISTANCE_THRESHOLD_METER = 1000.0

DETAILS = [
    "crossing",
    "surface",
    "has_curb_gap",
    "has_elevator",
    "has_audio_signal",
    "has_braille_block",
    "width_meter",
    "average_slope",
]


def first_child_text(parent: ET.Element, tag: str) -> str | None:
    child = parent.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def haversine_meter(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def snap_status(distance_meter: float | None) -> str | None:
    if distance_meter is None:
        return None
    if distance_meter <= 30:
        return "ACCEPT"
    if distance_meter <= 80:
        return "WARN"
    return "REJECT"


def http_json(url: str) -> Any:
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def graphhopper_route(base_url: str, profile: str, start: dict[str, float], end: dict[str, float]) -> dict[str, Any]:
    params: list[tuple[str, str]] = [
        ("profile", profile),
        ("point", f"{start['lat']},{start['lng']}"),
        ("point", f"{end['lat']},{end['lng']}"),
        ("points_encoded", "false"),
        ("instructions", "true"),
        ("calc_points", "true"),
    ]
    for detail in DETAILS:
        params.append(("details", detail))
    query = urllib.parse.urlencode(params)
    return http_json(f"{base_url.rstrip('/')}/route?{query}")


def summarize_graphhopper_details(details: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}

    slope_values = [entry[2] for entry in details.get("average_slope", []) if isinstance(entry[2], (int, float))]
    if slope_values:
        summary["averageSlopeRange"] = {"min": min(slope_values), "max": max(slope_values)}

    width_values = [entry[2] for entry in details.get("width_meter", []) if isinstance(entry[2], (int, float))]
    if width_values:
        summary["widthMeterRange"] = {"min": min(width_values), "max": max(width_values)}

    for key in ("has_elevator", "has_curb_gap", "has_audio_signal", "has_braille_block"):
        summary[key] = any(bool(entry[2]) for entry in details.get(key, []) if len(entry) >= 3)

    summary["crossingValues"] = sorted(
        {str(entry[2]) for entry in details.get("crossing", []) if len(entry) >= 3}
    )
    return summary


def route_walk_segment(
    graphhopper_base_url: str,
    profile: str,
    title: str,
    start_anchor: dict[str, Any],
    end_anchor: dict[str, Any],
    original_distance_meter: float,
    original_time_minute: float,
) -> dict[str, Any]:
    payload = graphhopper_route(
        graphhopper_base_url,
        profile,
        {"lat": start_anchor["lat"], "lng": start_anchor["lng"]},
        {"lat": end_anchor["lat"], "lng": end_anchor["lng"]},
    )
    paths = payload.get("paths", [])
    if not paths:
        raise RuntimeError(payload.get("message", "No GraphHopper path returned"))

    path = paths[0]
    snapped = path.get("snapped_waypoints", {}).get("coordinates", [])
    start_snap_distance = None
    end_snap_distance = None
    if len(snapped) >= 2:
        start_snap_distance = haversine_meter(
            start_anchor["lat"],
            start_anchor["lng"],
            snapped[0][1],
            snapped[0][0],
        )
        end_snap_distance = haversine_meter(
            end_anchor["lat"],
            end_anchor["lng"],
            snapped[1][1],
            snapped[1][0],
        )

    return {
        "type": "WALK",
        "title": title,
        "dataSources": ["GraphHopper"],
        "engine": profile,
        "startName": start_anchor["label"],
        "endName": end_anchor["label"],
        "startPoint": {"lat": start_anchor["lat"], "lng": start_anchor["lng"]},
        "endPoint": {"lat": end_anchor["lat"], "lng": end_anchor["lng"]},
        "originalDistanceMeter": original_distance_meter,
        "originalTimeMinute": original_time_minute,
        "distanceMeter": path.get("distance"),
        "estimatedTimeMinute": round(path.get("time", 0) / 60000, 2),
        "snapStatus": {
            "start": snap_status(start_snap_distance),
            "end": snap_status(end_snap_distance),
        },
        "snapDistanceMeter": {
            "start": start_snap_distance,
            "end": end_snap_distance,
        },
        "geometry": path.get("points", {}).get("coordinates", []),
        "detailSummary": summarize_graphhopper_details(path.get("details", {})),
    }


def bus_arrivals(env: dict[str, str], bstopid: str) -> list[dict[str, Any]]:
    base_url = transit_base.require(env, "BUSAN_BIMS_API_BASE_URL")
    service_key = transit_base.require(env, "BUSAN_BIMS_SERVICE_KEY_DECODING")
    raw = transit_base.http_get_text(
        f"{base_url}/stopArrByBstopid",
        {
            "bstopid": bstopid,
            "pageNo": 1,
            "numOfRows": 50,
            "serviceKey": service_key,
        },
    )
    root = ET.fromstring(raw)
    items = []
    for item in root.findall(".//item"):
        items.append(
            {
                "lineid": first_child_text(item, "lineid"),
                "lineno": first_child_text(item, "lineno"),
                "min1": first_child_text(item, "min1"),
                "station1": first_child_text(item, "station1"),
                "lowplate1": first_child_text(item, "lowplate1"),
                "min2": first_child_text(item, "min2"),
                "station2": first_child_text(item, "station2"),
                "lowplate2": first_child_text(item, "lowplate2"),
            }
        )
    return items


def bus_segment_from_subpath(env: dict[str, str], sub_path: dict[str, Any]) -> dict[str, Any]:
    lane = (sub_path.get("lane") or [{}])[0]
    route_no = str(lane.get("busNo") or "")
    route_local_id = str(lane.get("busLocalBlID") or "") or None
    arrivals = bus_arrivals(env, str(sub_path.get("startLocalStationID") or ""))
    realtime = next(
        (
            item
            for item in arrivals
            if item["lineid"] == route_local_id or item["lineno"] == route_no
        ),
        None,
    )

    station_rows = sub_path.get("passStopList", {}).get("stations", [])
    geometry = []
    for station in station_rows:
        try:
            geometry.append([float(station["x"]), float(station["y"])])
        except Exception:
            continue

    return {
        "type": "BUS",
        "title": f"버스 {route_no}",
        "dataSources": ["ODsay", "Busan BIMS"],
        "routeNo": route_no,
        "routeId": route_local_id,
        "startName": sub_path.get("startName"),
        "endName": sub_path.get("endName"),
        "distanceMeter": sub_path.get("distance"),
        "estimatedTimeMinute": sub_path.get("sectionTime"),
        "stationCount": sub_path.get("stationCount"),
        "geometry": geometry,
        "realtime": realtime,
    }


def subway_segment_from_subpath(subway_rows: list[dict[str, Any]], sub_path: dict[str, Any]) -> dict[str, Any]:
    lane = (sub_path.get("lane") or [{}])[0]
    status, reason, matched_route_name, matched_route_no = transit_base.choose_subway_match(
        subway_rows,
        str(lane.get("name") or ""),
        str(sub_path.get("startName") or ""),
        str(sub_path.get("endName") or ""),
    )

    station_rows = sub_path.get("passStopList", {}).get("stations", [])
    geometry = []
    for station in station_rows:
        try:
            geometry.append([float(station["x"]), float(station["y"])])
        except Exception:
            continue

    return {
        "type": "SUBWAY",
        "title": str(lane.get("name") or "지하철"),
        "dataSources": ["ODsay", "Busan Subway odcloud"],
        "lineName": lane.get("name"),
        "startName": sub_path.get("startName"),
        "endName": sub_path.get("endName"),
        "distanceMeter": sub_path.get("distance"),
        "estimatedTimeMinute": sub_path.get("sectionTime"),
        "stationCount": sub_path.get("stationCount"),
        "geometry": geometry,
        "matchStatus": status,
        "matchReason": reason,
        "matchedRouteName": matched_route_name,
        "matchedRouteNo": matched_route_no,
    }


def traffic_label(traffic_type: int) -> str:
    return {1: "SUBWAY", 2: "BUS", 3: "WALK"}.get(traffic_type, f"UNKNOWN_{traffic_type}")


def segment_korean_label(segment_type: str) -> str:
    return {
        "WALK": "도보",
        "BUS": "버스",
        "SUBWAY": "지하철",
    }.get(segment_type, segment_type)


def choose_hybrid_path(paths: list[dict[str, Any]]) -> dict[str, Any]:
    for path in paths:
        modes = {traffic_label(int(sub_path.get("trafficType", 0))) for sub_path in path.get("subPath", [])}
        if "WALK" in modes and ("BUS" in modes or "SUBWAY" in modes):
            return path
    if paths:
        return paths[0]
    raise RuntimeError("No transit candidate paths returned")


def build_walk_only_response(
    graphhopper_base_url: str,
    profile: str,
    start: dict[str, float],
    end: dict[str, float],
) -> dict[str, Any]:
    walk = route_walk_segment(
        graphhopper_base_url,
        profile,
        "도보 경로",
        {"lat": start["lat"], "lng": start["lng"], "label": "출발지"},
        {"lat": end["lat"], "lng": end["lng"], "label": "도착지"},
        original_distance_meter=haversine_meter(start["lat"], start["lng"], end["lat"], end["lng"]),
        original_time_minute=0,
    )
    return {
        "mode": "WALK_ONLY",
        "thresholdMeter": HYBRID_DISTANCE_THRESHOLD_METER,
        "summary": {
            "headline": f"도보 {round(walk['estimatedTimeMinute'])}분",
            "totalDistanceMeter": walk["distanceMeter"],
            "totalTimeMinute": walk["estimatedTimeMinute"],
            "payment": 0,
            "dataSources": {
                "walk": ["GraphHopper"],
                "bus": [],
                "subway": [],
            },
        },
        "segments": [walk],
    }


def build_hybrid_response(
    env: dict[str, str],
    graphhopper_base_url: str,
    profile: str,
    start: dict[str, float],
    end: dict[str, float],
) -> dict[str, Any]:
    paths = transit_base.fetch_odsay_paths(
        env,
        {
            "start_x": start["lng"],
            "start_y": start["lat"],
            "end_x": end["lng"],
            "end_y": end["lat"],
        },
    )
    path = choose_hybrid_path(paths)
    subway_rows = transit_base.load_subway_rows(env)
    segments: list[dict[str, Any]] = []
    sub_paths = path.get("subPath", [])

    for index, sub_path in enumerate(sub_paths):
        traffic_type = int(sub_path.get("trafficType", 0))
        if traffic_type == 3:
            previous_transit = sub_paths[index - 1] if index > 0 else None
            next_transit = sub_paths[index + 1] if index + 1 < len(sub_paths) else None

            if previous_transit is None:
                title = "출발 도보"
                start_anchor = {"lat": start["lat"], "lng": start["lng"], "label": "출발지"}
            else:
                title = "환승 도보"
                start_anchor = (
                    {
                        "lat": float(previous_transit["endExitY"]),
                        "lng": float(previous_transit["endExitX"]),
                        "label": f"{previous_transit.get('endName')} 출구 {previous_transit.get('endExitNo')}",
                    }
                    if int(previous_transit.get("trafficType", 0)) == 1
                    and previous_transit.get("endExitX")
                    and previous_transit.get("endExitY")
                    else {
                        "lat": float(previous_transit.get("endY") or 0.0),
                        "lng": float(previous_transit.get("endX") or 0.0),
                        "label": str(previous_transit.get("endName") or "환승 지점"),
                    }
                )

            if next_transit is None:
                title = "도착 도보"
                end_anchor = {"lat": end["lat"], "lng": end["lng"], "label": "도착지"}
            else:
                end_anchor = (
                    {
                        "lat": float(next_transit["startExitY"]),
                        "lng": float(next_transit["startExitX"]),
                        "label": f"{next_transit.get('startName')} 출구 {next_transit.get('startExitNo')}",
                    }
                    if int(next_transit.get("trafficType", 0)) == 1
                    and next_transit.get("startExitX")
                    and next_transit.get("startExitY")
                    else {
                        "lat": float(next_transit.get("startY") or 0.0),
                        "lng": float(next_transit.get("startX") or 0.0),
                        "label": str(next_transit.get("startName") or "환승 지점"),
                    }
                )

            segments.append(
                route_walk_segment(
                    graphhopper_base_url,
                    profile,
                    title,
                    start_anchor,
                    end_anchor,
                    original_distance_meter=float(sub_path.get("distance") or 0.0),
                    original_time_minute=float(sub_path.get("sectionTime") or 0.0),
                )
            )
        elif traffic_type == 2:
            segments.append(bus_segment_from_subpath(env, sub_path))
        elif traffic_type == 1:
            segments.append(subway_segment_from_subpath(subway_rows, sub_path))

    total_distance_meter = sum(float(segment.get("distanceMeter") or 0.0) for segment in segments)
    total_time_minute = sum(float(segment.get("estimatedTimeMinute") or 0.0) for segment in segments)
    headline = " -> ".join(
        f"{segment_korean_label(segment['type'])} {round(float(segment.get('estimatedTimeMinute') or 0.0))}분"
        for segment in segments
    )

    return {
        "mode": "HYBRID_TRANSIT",
        "thresholdMeter": HYBRID_DISTANCE_THRESHOLD_METER,
        "summary": {
            "headline": headline,
            "totalDistanceMeter": total_distance_meter,
            "totalTimeMinute": total_time_minute,
            "payment": path.get("info", {}).get("payment"),
            "dataSources": {
                "walk": ["GraphHopper"],
                "bus": ["ODsay", "Busan BIMS"],
                "subway": ["ODsay", "Busan Subway odcloud"],
            },
        },
        "segments": segments,
        "pathInfo": {
            "pathType": path.get("pathType"),
            "totalTime": path.get("info", {}).get("totalTime"),
            "payment": path.get("info", {}).get("payment"),
        },
    }


class ViewerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(VIEWER_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        sys.stdout.write(f"[viewer] {self.address_string()} - {format % args}\n")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/hybrid-route":
            self.handle_hybrid_route(parsed)
            return
        super().do_GET()

    def handle_hybrid_route(self, parsed: urllib.parse.ParseResult) -> None:
        try:
            query = urllib.parse.parse_qs(parsed.query)
            start_lat = float(query["startLat"][0])
            start_lng = float(query["startLng"][0])
            end_lat = float(query["endLat"][0])
            end_lng = float(query["endLng"][0])
            profile = query.get("profile", ["wheelchair_safe"])[0]

            env = transit_base.load_env(ENV_PATH)
            graphhopper_base_url = os.environ.get("GRAPHHOPPER_BASE_URL", "http://localhost:8989")
            straight_distance = haversine_meter(start_lat, start_lng, end_lat, end_lng)

            if straight_distance <= HYBRID_DISTANCE_THRESHOLD_METER:
                payload = build_walk_only_response(
                    graphhopper_base_url,
                    profile,
                    {"lat": start_lat, "lng": start_lng},
                    {"lat": end_lat, "lng": end_lng},
                )
            else:
                payload = build_hybrid_response(
                    env,
                    graphhopper_base_url,
                    profile,
                    {"lat": start_lat, "lng": start_lng},
                    {"lat": end_lat, "lng": end_lng},
                )

            payload["request"] = {
                "startPoint": {"lat": start_lat, "lng": start_lng},
                "endPoint": {"lat": end_lat, "lng": end_lng},
                "profile": profile,
                "straightDistanceMeter": straight_distance,
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:  # noqa: BLE001
            body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), ViewerHandler)
    print(f"viewer_server=http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
