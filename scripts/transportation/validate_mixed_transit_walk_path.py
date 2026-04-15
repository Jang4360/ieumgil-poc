#!/usr/bin/env python3
"""Validate mixed walk+bus+subway path extraction and walk-route mapping."""

from __future__ import annotations

import json
import math
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import evaluate_dataset_linking as base


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
INFRA_DIR = ROOT_DIR / "infra" / "graphhopper"
JAR_PATH = INFRA_DIR / "graphhopper-web-11.0.jar"
GRAPH_DIR = ROOT_DIR / "ieumgil-osm-etl-poc" / "data" / "graphhopper" / "busan_custom_ev_v1"
PBF_PATH = ROOT_DIR / "ieumgil-osm-etl-poc" / "data" / "raw" / "busan.osm.pbf"
OUTPUT_JSON = ROOT_DIR / "docs" / "reviews" / "transportation" / "step4-6-mixed-transit-walk-validation-artifact.json"
GRAPHHOPPER_OUT_LOG = ROOT_DIR / "tmp-transport-mixed-graphhopper.out.log"
GRAPHHOPPER_ERR_LOG = ROOT_DIR / "tmp-transport-mixed-graphhopper.err.log"
BASE_URL = "http://localhost:8989"

SCENARIO = {
    "name": "bansong_market_to_osiria_station",
    "display_name": "반송시장 -> 오시리아역",
    "start_point": {"lat": 35.226908613652, "lng": 129.148626778943, "label": "반송시장"},
    "end_point": {"lat": 35.196256, "lng": 129.208291, "label": "오시리아역"},
}

WALK_ROUTE_OPTION_TO_PROFILE = {
    "SAFE": "wheelchair_safe",
    "SHORTEST": "wheelchair_shortest",
}


def http_json(url: str) -> Any:
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def http_json_params(url: str, params: list[tuple[str, str]]) -> Any:
    query = urllib.parse.urlencode(params)
    return http_json(f"{url}?{query}")


def first_child_text(parent: ET.Element, tag: str) -> str | None:
    child = parent.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def is_graphhopper_alive(base_url: str) -> bool:
    try:
        http_json(f"{base_url.rstrip('/')}/info")
    except Exception:
        return False
    return True


def build_temp_graphhopper_config() -> Path:
    config_text = f"""graphhopper:
  datareader.file: "{PBF_PATH.as_posix()}"
  graph.location: "{GRAPH_DIR.as_posix()}"

  profiles:
    - name: visual_shortest
      custom_model_files: [ieumgil-foot-base.json, visual-shortest.json]
    - name: visual_safe
      custom_model_files: [ieumgil-foot-base.json, visual-safe.json]
    - name: wheelchair_shortest
      custom_model_files: [ieumgil-foot-base.json, wheelchair-shortest.json]
    - name: wheelchair_safe
      custom_model_files: [ieumgil-foot-base.json, wheelchair-safe.json]

  profiles_ch: []
  profiles_lm: []

  graph.encoded_values: foot_access, foot_priority, foot_average_speed, foot_road_access, hike_rating, mtb_rating, country, road_class, crossing, footway, surface, average_slope, osm_way_id, has_curb_gap, has_elevator, has_audio_signal, has_braille_block, width_meter

  prepare.min_network_size: 2
  prepare.subnetworks.threads: 1
  routing.snap_preventions_default: tunnel, bridge, ferry
  routing.non_ch.max_waypoint_distance: 1000000
  import.osm.ignored_highways: motorway,trunk
  graph.dataaccess.default_type: RAM_STORE

server:
  application_connectors:
    - type: http
      port: 8989
      bind_host: 0.0.0.0
      max_request_header_size: 50k
  request_log:
    appenders: []
  admin_connectors:
    - type: http
      port: 8990
      bind_host: 0.0.0.0

logging:
  appenders:
    - type: console
"""
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yml",
        prefix="graphhopper-mixed-",
        dir=INFRA_DIR,
        delete=False,
        encoding="utf-8",
    )
    handle.write(config_text)
    handle.close()
    return Path(handle.name)


def ensure_graphhopper(base_url: str) -> tuple[subprocess.Popen[str] | None, Path | None]:
    if is_graphhopper_alive(base_url):
        return None, None

    config_path = build_temp_graphhopper_config()
    out_log = GRAPHHOPPER_OUT_LOG.open("w", encoding="utf-8")
    err_log = GRAPHHOPPER_ERR_LOG.open("w", encoding="utf-8")

    process = subprocess.Popen(
        ["java", "-jar", str(JAR_PATH), "server", str(config_path)],
        cwd=str(INFRA_DIR),
        stdout=out_log,
        stderr=err_log,
        text=True,
    )

    for _ in range(60):
        if process.poll() is not None:
            raise RuntimeError(
                f"GraphHopper exited early with code {process.returncode}. "
                f"See {GRAPHHOPPER_OUT_LOG} and {GRAPHHOPPER_ERR_LOG}"
            )
        if is_graphhopper_alive(base_url):
            return process, config_path
        time.sleep(1)

    raise RuntimeError("GraphHopper did not become ready within 60 seconds")


def shutdown_graphhopper(process: subprocess.Popen[str] | None, config_path: Path | None) -> None:
    if process is not None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    if config_path is not None and config_path.exists():
        config_path.unlink()


def fetch_odsay_paths(env: dict[str, str]) -> list[dict[str, Any]]:
    return base.fetch_odsay_paths(
        env,
        {
            "start_x": SCENARIO["start_point"]["lng"],
            "start_y": SCENARIO["start_point"]["lat"],
            "end_x": SCENARIO["end_point"]["lng"],
            "end_y": SCENARIO["end_point"]["lat"],
        },
    )


def traffic_label(traffic_type: int) -> str:
    return {
        1: "SUBWAY",
        2: "BUS",
        3: "WALK",
    }.get(traffic_type, f"UNKNOWN_{traffic_type}")


def summarize_path(path_index: int, path: dict[str, Any]) -> dict[str, Any]:
    mode_sequence = [traffic_label(int(sub_path["trafficType"])) for sub_path in path.get("subPath", [])]
    return {
        "path_index": path_index,
        "path_type": path.get("pathType"),
        "total_time": path.get("info", {}).get("totalTime"),
        "payment": path.get("info", {}).get("payment"),
        "mode_sequence": mode_sequence,
        "has_mixed_walk_bus_subway": {"WALK", "BUS", "SUBWAY"}.issubset(set(mode_sequence)),
    }


def choose_mixed_path(paths: list[dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    for path_index, path in enumerate(paths):
        summary = summarize_path(path_index, path)
        if summary["has_mixed_walk_bus_subway"]:
            return path_index, path
    raise RuntimeError("No mixed walk+bus+subway path found in top ODsay candidates")


def transit_start_anchor(sub_path: dict[str, Any]) -> dict[str, Any]:
    if sub_path["trafficType"] == 1 and sub_path.get("startExitX") and sub_path.get("startExitY"):
        return {
            "lat": float(sub_path["startExitY"]),
            "lng": float(sub_path["startExitX"]),
            "source": "SUBWAY_EXIT",
            "label": f"{sub_path.get('startName')} 출구 {sub_path.get('startExitNo')}",
        }
    return {
        "lat": float(sub_path.get("startY") or 0.0),
        "lng": float(sub_path.get("startX") or 0.0),
        "source": "TRANSIT_START",
        "label": str(sub_path.get("startName") or ""),
    }


def transit_end_anchor(sub_path: dict[str, Any]) -> dict[str, Any]:
    if sub_path["trafficType"] == 1 and sub_path.get("endExitX") and sub_path.get("endExitY"):
        return {
            "lat": float(sub_path["endExitY"]),
            "lng": float(sub_path["endExitX"]),
            "source": "SUBWAY_EXIT",
            "label": f"{sub_path.get('endName')} 출구 {sub_path.get('endExitNo')}",
        }
    return {
        "lat": float(sub_path.get("endY") or 0.0),
        "lng": float(sub_path.get("endX") or 0.0),
        "source": "TRANSIT_END",
        "label": str(sub_path.get("endName") or ""),
    }


def extract_walk_segments(path: dict[str, Any]) -> list[dict[str, Any]]:
    sub_paths = path.get("subPath", [])
    walk_segments = []

    for index, sub_path in enumerate(sub_paths):
        if sub_path.get("trafficType") != 3:
            continue

        previous_transit = sub_paths[index - 1] if index > 0 else None
        next_transit = sub_paths[index + 1] if index + 1 < len(sub_paths) else None

        if previous_transit is None:
            role = "ACCESS"
            start_anchor = {
                "lat": SCENARIO["start_point"]["lat"],
                "lng": SCENARIO["start_point"]["lng"],
                "source": "USER_REQUEST",
                "label": SCENARIO["start_point"]["label"],
            }
        else:
            role = "TRANSFER"
            start_anchor = transit_end_anchor(previous_transit)

        if next_transit is None:
            role = "EGRESS" if previous_transit is not None else role
            end_anchor = {
                "lat": SCENARIO["end_point"]["lat"],
                "lng": SCENARIO["end_point"]["lng"],
                "source": "USER_REQUEST",
                "label": SCENARIO["end_point"]["label"],
            }
        else:
            end_anchor = transit_start_anchor(next_transit)

        walk_segments.append(
            {
                "sequence": len(walk_segments) + 1,
                "sub_path_index": index,
                "role": role,
                "odsay_distance_meter": sub_path.get("distance"),
                "odsay_section_time_minute": sub_path.get("sectionTime"),
                "start_anchor": start_anchor,
                "end_anchor": end_anchor,
                "walk_route_request": {
                    "startPoint": {"lat": start_anchor["lat"], "lng": start_anchor["lng"]},
                    "endPoint": {"lat": end_anchor["lat"], "lng": end_anchor["lng"]},
                    "routeOptions": ["SAFE", "SHORTEST"],
                },
            }
        )

    return walk_segments


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


def snap_status(distance_meter: float) -> str:
    if distance_meter <= 30:
        return "ACCEPT"
    if distance_meter <= 80:
        return "WARN"
    return "REJECT"


def summarize_path_details(path_details: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}

    slope_values = [entry[2] for entry in path_details.get("average_slope", []) if isinstance(entry[2], (int, float))]
    if slope_values:
        summary["average_slope_range"] = {
            "min": min(slope_values),
            "max": max(slope_values),
        }

    width_values = [entry[2] for entry in path_details.get("width_meter", []) if isinstance(entry[2], (int, float))]
    if width_values:
        summary["width_meter_range"] = {
            "min": min(width_values),
            "max": max(width_values),
        }

    for key in ("has_elevator", "has_curb_gap", "has_audio_signal", "has_braille_block"):
        detail_entries = path_details.get(key, [])
        summary[key] = any(bool(entry[2]) for entry in detail_entries if len(entry) >= 3)

    crossing_values = sorted({str(entry[2]) for entry in path_details.get("crossing", []) if len(entry) >= 3})
    if crossing_values:
        summary["crossing_values"] = crossing_values

    return summary


def request_graphhopper_route(base_url: str, profile: str, walk_request: dict[str, Any]) -> dict[str, Any]:
    params = [
        ("profile", profile),
        ("point", f"{walk_request['startPoint']['lat']},{walk_request['startPoint']['lng']}"),
        ("point", f"{walk_request['endPoint']['lat']},{walk_request['endPoint']['lng']}"),
        ("points_encoded", "false"),
        ("instructions", "true"),
        ("calc_points", "true"),
        ("details", "average_slope"),
        ("details", "has_elevator"),
        ("details", "has_curb_gap"),
        ("details", "has_audio_signal"),
        ("details", "has_braille_block"),
        ("details", "width_meter"),
        ("details", "crossing"),
    ]
    payload = http_json_params(f"{base_url.rstrip('/')}/route", params)

    paths = payload.get("paths", [])
    if not paths:
        return {
            "success": False,
            "error": payload.get("message", "No path returned"),
        }

    path = paths[0]
    snapped = path.get("snapped_waypoints", {}).get("coordinates", [])
    start_input = walk_request["startPoint"]
    end_input = walk_request["endPoint"]

    if len(snapped) >= 2:
        start_snap_distance = haversine_meter(
            start_input["lat"],
            start_input["lng"],
            snapped[0][1],
            snapped[0][0],
        )
        end_snap_distance = haversine_meter(
            end_input["lat"],
            end_input["lng"],
            snapped[1][1],
            snapped[1][0],
        )
    else:
        start_snap_distance = None
        end_snap_distance = None

    detail_summary = summarize_path_details(path.get("details", {}))
    return {
        "success": True,
        "profile": profile,
        "distance_meter": path.get("distance"),
        "estimated_time_minute": round(path.get("time", 0) / 60000, 2),
        "instruction_count": len(path.get("instructions", [])),
        "start_snap_distance_meter": start_snap_distance,
        "start_snap_status": snap_status(start_snap_distance) if start_snap_distance is not None else None,
        "end_snap_distance_meter": end_snap_distance,
        "end_snap_status": snap_status(end_snap_distance) if end_snap_distance is not None else None,
        "detail_summary": detail_summary,
    }


def enrich_walk_segments_with_graphhopper(base_url: str, walk_segments: list[dict[str, Any]]) -> None:
    for walk_segment in walk_segments:
        walk_segment["graphhopper_results"] = {}
        for route_option, profile in WALK_ROUTE_OPTION_TO_PROFILE.items():
            walk_segment["graphhopper_results"][route_option] = request_graphhopper_route(
                base_url,
                profile,
                walk_segment["walk_route_request"],
            )


def query_bims_arrivals_detailed(env: dict[str, str], bstopid: str) -> list[dict[str, Any]]:
    base_url = base.require(env, "BUSAN_BIMS_API_BASE_URL")
    service_key = base.require(env, "BUSAN_BIMS_SERVICE_KEY_DECODING")
    raw = base.http_get_text(
        f"{base_url}/stopArrByBstopid",
        {
            "bstopid": bstopid,
            "pageNo": 1,
            "numOfRows": 50,
            "serviceKey": service_key,
        },
    )
    root = ET.fromstring(raw)
    rows = []
    for item in root.findall(".//item"):
        rows.append(
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
    return rows


def bus_accessibility_review(env: dict[str, str], bus_segment: dict[str, Any]) -> dict[str, Any]:
    lane = (bus_segment.get("lane") or [{}])[0]
    route_no = str(lane.get("busNo") or "")
    route_local_id = str(lane.get("busLocalBlID") or "") or None
    arrivals = query_bims_arrivals_detailed(env, str(bus_segment.get("startLocalStationID") or ""))
    matched = next(
        (
            row
            for row in arrivals
            if row["lineid"] == route_local_id or row["lineno"] == route_no
        ),
        None,
    )
    return {
        "route_no": route_no,
        "route_local_id": route_local_id,
        "board_stop_name": bus_segment.get("startName"),
        "board_stop_id": bus_segment.get("startLocalStationID"),
        "alight_stop_name": bus_segment.get("endName"),
        "alight_stop_id": bus_segment.get("endLocalStationID"),
        "matched_arrival_snapshot": matched,
        "low_floor_realtime_supported": matched is not None,
        "low_floor_fields_available": bool(matched and ("lowplate1" in matched or "lowplate2" in matched)),
    }


def subway_accessibility_review(subway_rows: list[dict[str, Any]], subway_segment: dict[str, Any]) -> dict[str, Any]:
    lane = (subway_segment.get("lane") or [{}])[0]
    status, reason, matched_route_name, matched_route_no = base.choose_subway_match(
        subway_rows,
        str(lane.get("name") or ""),
        str(subway_segment.get("startName") or ""),
        str(subway_segment.get("endName") or ""),
    )
    return {
        "line_name": lane.get("name"),
        "start_name": subway_segment.get("startName"),
        "end_name": subway_segment.get("endName"),
        "odcloud_match_status": status,
        "odcloud_match_reason": reason,
        "matched_route_name": matched_route_name,
        "matched_route_no": matched_route_no,
        "elevator_or_exit_accessibility_supported": False,
        "note": (
            "Current configured odcloud dataset is operation/timetable oriented and does not expose station elevator or exit accessibility fields."
        ),
    }


def segment_overview(sub_path: dict[str, Any]) -> dict[str, Any]:
    overview = {
        "traffic_type": traffic_label(int(sub_path["trafficType"])),
        "distance_meter": sub_path.get("distance"),
        "section_time_minute": sub_path.get("sectionTime"),
    }
    if sub_path["trafficType"] == 1:
        lane = (sub_path.get("lane") or [{}])[0]
        overview.update(
            {
                "line_name": lane.get("name"),
                "start_name": sub_path.get("startName"),
                "end_name": sub_path.get("endName"),
            }
        )
    elif sub_path["trafficType"] == 2:
        lane = (sub_path.get("lane") or [{}])[0]
        overview.update(
            {
                "route_no": lane.get("busNo"),
                "start_name": sub_path.get("startName"),
                "end_name": sub_path.get("endName"),
            }
        )
    return overview


def build_result() -> dict[str, Any]:
    env = base.load_env(ENV_PATH)
    paths = fetch_odsay_paths(env)
    path_summaries = [summarize_path(index, path) for index, path in enumerate(paths)]
    selected_path_index, selected_path = choose_mixed_path(paths)

    walk_segments = extract_walk_segments(selected_path)
    bus_segments = [sub_path for sub_path in selected_path.get("subPath", []) if sub_path.get("trafficType") == 2]
    subway_segments = [sub_path for sub_path in selected_path.get("subPath", []) if sub_path.get("trafficType") == 1]

    process = None
    config_path = None
    try:
        process, config_path = ensure_graphhopper(BASE_URL)
        enrich_walk_segments_with_graphhopper(BASE_URL, walk_segments)
    finally:
        shutdown_graphhopper(process, config_path)

    subway_rows = base.load_subway_rows(env)
    bus_reviews = [bus_accessibility_review(env, segment) for segment in bus_segments]
    subway_reviews = [subway_accessibility_review(subway_rows, segment) for segment in subway_segments]

    immediate_accessibility = {
        "walk_segments": {
            "route_input_mapping_supported": True,
            "graphhopper_execution_supported": all(
                result["success"]
                for walk_segment in walk_segments
                for result in walk_segment["graphhopper_results"].values()
            ),
            "fields_now": [
                "distance_meter",
                "estimated_time_minute",
                "snap_status",
                "average_slope_range",
                "has_elevator",
                "has_curb_gap",
                "has_audio_signal",
                "has_braille_block",
                "width_meter_range",
            ],
        },
        "bus_segments": {
            "realtime_arrival_supported": any(review["matched_arrival_snapshot"] for review in bus_reviews),
            "low_floor_realtime_supported": any(review["low_floor_realtime_supported"] for review in bus_reviews),
            "fields_now": ["min1", "station1", "lowplate1", "min2", "station2", "lowplate2"],
        },
        "subway_segments": {
            "operation_dataset_match_supported": any(review["odcloud_match_status"] == "MATCHED" for review in subway_reviews),
            "station_accessibility_supported": False,
            "fields_now": ["line_name", "start_name", "end_name", "matched_route_name", "matched_route_no"],
        },
    }

    return {
        "scenario": SCENARIO,
        "path_summaries": path_summaries,
        "selected_path_index": selected_path_index,
        "selected_path_overview": [segment_overview(sub_path) for sub_path in selected_path.get("subPath", [])],
        "walk_segments": walk_segments,
        "bus_accessibility_reviews": bus_reviews,
        "subway_accessibility_reviews": subway_reviews,
        "immediate_accessibility_integration": immediate_accessibility,
        "limitations": [
            "Selected mixed path uses Donghae line, but current odcloud operation dataset did not match this leg.",
            "Subway station elevator/exit accessibility fields are not available in the currently configured datasets.",
            "Walk leg validation used local GraphHopper wheelchair profiles, not a production transit API.",
        ],
    }


def main() -> int:
    result = build_result()
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"output_json={OUTPUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
