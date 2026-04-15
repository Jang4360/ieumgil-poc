#!/usr/bin/env python3
"""Expanded Haeundae-gu transit linking validation with fixed random seed."""

from __future__ import annotations

import json
import random
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import evaluate_dataset_linking as base


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
RANDOM_SEED = 20260415
TARGET_BUS_SEGMENTS = 10
TARGET_SUBWAY_SEGMENTS = 10

POINT_SPECS = [
    {"label": "센텀시티역", "type": "station", "queries": ["센텀시티"]},
    {"label": "벡스코역", "type": "station", "queries": ["벡스코"]},
    {"label": "동백역", "type": "station", "queries": ["동백"]},
    {"label": "해운대역", "type": "station", "queries": ["해운대"]},
    {"label": "중동역", "type": "station", "queries": ["중동"]},
    {"label": "장산역", "type": "station", "queries": ["장산"]},
    {"label": "신해운대역", "type": "station", "queries": ["신해운대"]},
    {"label": "송정역", "type": "station", "queries": ["송정"]},
    {"label": "재송역", "type": "station", "queries": ["재송"]},
    {"label": "오시리아역", "type": "station", "queries": ["오시리아"]},
    {"label": "반송시장", "type": "bus_stop", "queries": ["반송시장"]},
    {"label": "반여농산물도매시장", "type": "bus_stop", "queries": ["반여농산물도매시장", "반여농산물시장"]},
    {"label": "해운대구청", "type": "bus_stop", "queries": ["해운대구청"]},
    {"label": "송정해수욕장입구", "type": "bus_stop", "queries": ["송정해수욕장입구"]},
    {"label": "올림픽교차로환승센터", "type": "bus_stop", "queries": ["올림픽교차로환승센터", "올림픽교차로"]},
    {"label": "센텀고등학교", "type": "bus_stop", "queries": ["센텀고등학교"]},
]


def resolve_station_point(env: dict[str, str], queries: list[str], label: str) -> dict[str, Any] | None:
    base_url = base.require(env, "ODSAY_API_BASE_URL")
    api_key = base.require(env, "ODSAY_API_KEY")

    for query in queries:
        payload = base.http_get_json(
            f"{base_url}/searchStation",
            {
                "stationName": query,
                "CID": 7000,
                "apiKey": api_key,
            },
        )
        stations = payload.get("result", {}).get("station", [])
        if not stations:
            continue

        exact = next((row for row in stations if row.get("stationName") == query), None)
        chosen = exact or stations[0]
        return {
            "label": label,
            "query": query,
            "type": "station",
            "x": float(chosen["x"]),
            "y": float(chosen["y"]),
            "source_name": chosen["stationName"],
            "source_id": str(chosen["stationID"]),
        }
    return None


def first_child_text(parent: ET.Element, tag: str) -> str | None:
    child = parent.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def resolve_bus_stop_point(env: dict[str, str], queries: list[str], label: str) -> dict[str, Any] | None:
    base_url = base.require(env, "BUSAN_BIMS_API_BASE_URL")
    service_key = base.require(env, "BUSAN_BIMS_SERVICE_KEY_DECODING")

    for query in queries:
        raw = base.http_get_text(
            f"{base_url}/busStopList",
            {
                "pageNo": 1,
                "numOfRows": 20,
                "bstopnm": query,
                "serviceKey": service_key,
            },
        )
        root = ET.fromstring(raw)
        items = root.findall(".//item")
        if not items:
            continue

        rows = []
        for item in items:
            rows.append(
                {
                    "bstopid": first_child_text(item, "bstopid"),
                    "name": first_child_text(item, "bstopnm") or "",
                    "x": float(first_child_text(item, "gpsx") or 0.0),
                    "y": float(first_child_text(item, "gpsy") or 0.0),
                }
            )
        normalized_query = base.normalize_name(query)
        exact = next((row for row in rows if base.normalize_name(row["name"]) == normalized_query), None)
        chosen = exact or rows[0]
        return {
            "label": label,
            "query": query,
            "type": "bus_stop",
            "x": chosen["x"],
            "y": chosen["y"],
            "source_name": chosen["name"],
            "source_id": chosen["bstopid"],
        }
    return None


def resolve_points(env: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolved = []
    unresolved = []

    for spec in POINT_SPECS:
        if spec["type"] == "station":
            point = resolve_station_point(env, spec["queries"], spec["label"])
        else:
            point = resolve_bus_stop_point(env, spec["queries"], spec["label"])

        if point is None:
            unresolved.append({"label": spec["label"], "type": spec["type"], "queries": spec["queries"]})
        else:
            resolved.append(point)

    return resolved, unresolved


def evaluate_bus_segment(env: dict[str, str], scenario_name: str, path_index: int, sub_path: dict[str, Any]) -> dict[str, Any]:
    lane = (sub_path.get("lane") or [{}])[0]
    route_no = str(lane.get("busNo") or "")
    route_local_id = str(lane.get("busLocalBlID") or "") or None

    start_direct_status, start_direct_reason = base.probe_direct_id(
        env,
        str(sub_path.get("startLocalStationID") or "") or None,
        route_no,
        route_local_id,
    )
    start_fallback_status, start_fallback_reason, start_fallback_id = base.choose_bims_fallback_match(
        env=env,
        stop_name=str(sub_path.get("startName") or ""),
        x=float(sub_path.get("startX") or 0.0),
        y=float(sub_path.get("startY") or 0.0),
        route_no=route_no,
        route_local_id=route_local_id,
    )
    end_direct_status, end_direct_reason = base.probe_direct_id(
        env,
        str(sub_path.get("endLocalStationID") or "") or None,
        route_no,
        route_local_id,
    )
    end_fallback_status, end_fallback_reason, end_fallback_id = base.choose_bims_fallback_match(
        env=env,
        stop_name=str(sub_path.get("endName") or ""),
        x=float(sub_path.get("endX") or 0.0),
        y=float(sub_path.get("endY") or 0.0),
        route_no=route_no,
        route_local_id=route_local_id,
    )

    return {
        "scenario": scenario_name,
        "path_index": path_index,
        "route_no": route_no,
        "route_local_id": route_local_id,
        "start_name": str(sub_path.get("startName") or ""),
        "start_local_station_id": str(sub_path.get("startLocalStationID") or "") or None,
        "start_direct_status": start_direct_status,
        "start_direct_reason": start_direct_reason,
        "start_fallback_status": start_fallback_status,
        "start_fallback_reason": start_fallback_reason,
        "start_fallback_bims_stop_id": start_fallback_id,
        "end_name": str(sub_path.get("endName") or ""),
        "end_local_station_id": str(sub_path.get("endLocalStationID") or "") or None,
        "end_direct_status": end_direct_status,
        "end_direct_reason": end_direct_reason,
        "end_fallback_status": end_fallback_status,
        "end_fallback_reason": end_fallback_reason,
        "end_fallback_bims_stop_id": end_fallback_id,
    }


def evaluate_subway_segment(subway_rows: list[dict[str, Any]], scenario_name: str, path_index: int, sub_path: dict[str, Any]) -> dict[str, Any]:
    lane = (sub_path.get("lane") or [{}])[0]
    status, reason, matched_route_name, matched_route_no = base.choose_subway_match(
        subway_rows,
        str(lane.get("name") or ""),
        str(sub_path.get("startName") or ""),
        str(sub_path.get("endName") or ""),
    )
    return {
        "scenario": scenario_name,
        "path_index": path_index,
        "line_name": str(lane.get("name") or ""),
        "start_name": str(sub_path.get("startName") or ""),
        "end_name": str(sub_path.get("endName") or ""),
        "status": status,
        "reason": reason,
        "matched_route_name": matched_route_name,
        "matched_route_no": matched_route_no,
    }


def collect_random_samples(env: dict[str, str], points: list[dict[str, Any]]) -> dict[str, Any]:
    random_generator = random.Random(RANDOM_SEED)
    subway_rows = base.load_subway_rows(env)

    ordered_pairs = []
    for start in points:
        for end in points:
            if start["label"] != end["label"]:
                ordered_pairs.append((start, end))
    random_generator.shuffle(ordered_pairs)

    bus_samples = []
    subway_samples = []
    bus_seen = set()
    subway_seen = set()
    scenarios_checked = []
    scenarios_skipped = []

    for start, end in ordered_pairs:
        if len(bus_samples) >= TARGET_BUS_SEGMENTS and len(subway_samples) >= TARGET_SUBWAY_SEGMENTS:
            break

        scenario_name = f"{start['label']}->{end['label']}"
        try:
            paths = base.fetch_odsay_paths(
                env,
                {
                    "start_x": start["x"],
                    "start_y": start["y"],
                    "end_x": end["x"],
                    "end_y": end["y"],
                },
            )
        except Exception as exc:  # noqa: BLE001
            scenarios_skipped.append(
                {
                    "scenario": scenario_name,
                    "start_label": start["label"],
                    "end_label": end["label"],
                    "reason": str(exc),
                }
            )
            continue
        scenarios_checked.append(
            {
                "scenario": scenario_name,
                "start_label": start["label"],
                "end_label": end["label"],
                "start_type": start["type"],
                "end_type": end["type"],
            }
        )

        for path_index, path in enumerate(paths):
            for sub_path in path.get("subPath", []):
                traffic_type = sub_path.get("trafficType")

                if traffic_type == 2 and len(bus_samples) < TARGET_BUS_SEGMENTS:
                    lane = (sub_path.get("lane") or [{}])[0]
                    route_no = str(lane.get("busNo") or "")
                    unique_key = (
                        route_no,
                        str(sub_path.get("startName") or ""),
                        str(sub_path.get("endName") or ""),
                        str(sub_path.get("startLocalStationID") or ""),
                        str(sub_path.get("endLocalStationID") or ""),
                    )
                    if unique_key in bus_seen:
                        continue
                    bus_seen.add(unique_key)
                    bus_samples.append(evaluate_bus_segment(env, scenario_name, path_index, sub_path))

                if traffic_type == 1 and len(subway_samples) < TARGET_SUBWAY_SEGMENTS:
                    lane = (sub_path.get("lane") or [{}])[0]
                    unique_key = (
                        str(lane.get("name") or ""),
                        str(sub_path.get("startName") or ""),
                        str(sub_path.get("endName") or ""),
                    )
                    if unique_key in subway_seen:
                        continue
                    subway_seen.add(unique_key)
                    subway_samples.append(evaluate_subway_segment(subway_rows, scenario_name, path_index, sub_path))

                if len(bus_samples) >= TARGET_BUS_SEGMENTS and len(subway_samples) >= TARGET_SUBWAY_SEGMENTS:
                    break
            if len(bus_samples) >= TARGET_BUS_SEGMENTS and len(subway_samples) >= TARGET_SUBWAY_SEGMENTS:
                break

    bus_unmatched = []
    for item in bus_samples:
        if item["start_fallback_status"] != "MATCHED":
            bus_unmatched.append(
                {
                    "scenario": item["scenario"],
                    "route_no": item["route_no"],
                    "role": "start",
                    "stop_name": item["start_name"],
                    "local_station_id": item["start_local_station_id"],
                    "direct_id_status": item["start_direct_status"],
                    "direct_id_reason": item["start_direct_reason"],
                    "fallback_reason": item["start_fallback_reason"],
                }
            )
        if item["end_fallback_status"] != "MATCHED":
            bus_unmatched.append(
                {
                    "scenario": item["scenario"],
                    "route_no": item["route_no"],
                    "role": "end",
                    "stop_name": item["end_name"],
                    "local_station_id": item["end_local_station_id"],
                    "direct_id_status": item["end_direct_status"],
                    "direct_id_reason": item["end_direct_reason"],
                    "fallback_reason": item["end_fallback_reason"],
                }
            )

    subway_unmatched = [
        {
            "scenario": item["scenario"],
            "line_name": item["line_name"],
            "start_name": item["start_name"],
            "end_name": item["end_name"],
            "reason": item["reason"],
        }
        for item in subway_samples
        if item["status"] != "MATCHED"
    ]

    return {
        "random_seed": RANDOM_SEED,
        "resolved_points": points,
        "scenarios_checked": scenarios_checked,
        "scenarios_skipped": scenarios_skipped,
        "bus_samples": bus_samples,
        "subway_samples": subway_samples,
        "bus_unmatched": bus_unmatched,
        "subway_unmatched": subway_unmatched,
        "summary": {
            "points_resolved": len(points),
            "scenarios_checked": len(scenarios_checked),
            "scenarios_skipped": len(scenarios_skipped),
            "bus_samples_collected": len(bus_samples),
            "subway_samples_collected": len(subway_samples),
            "bus_unmatched_count": len(bus_unmatched),
            "subway_unmatched_count": len(subway_unmatched),
        },
    }


def main() -> int:
    env = base.load_env(ENV_PATH)
    points, unresolved = resolve_points(env)
    result = collect_random_samples(env, points)
    result["unresolved_points"] = unresolved
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
