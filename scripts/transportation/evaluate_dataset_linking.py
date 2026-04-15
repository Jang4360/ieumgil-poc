#!/usr/bin/env python3
"""Evaluate ODsay to Busan BIMS / Busan Subway odcloud linking for Step 3."""

from __future__ import annotations

import json
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
BUS_STOP_LIST_CACHE: dict[str, list[dict[str, Any]]] = {}
BUS_ARRIVAL_CACHE: dict[str, tuple[str | None, list[dict[str, Any]]]] = {}


SCENARIOS = [
    {
        "name": "busan_station_to_seomyeon",
        "start_name": "부산역",
        "start_x": 129.039325,
        "start_y": 35.114495,
        "end_name": "서면",
        "end_x": 129.059385,
        "end_y": 35.158098,
    },
    {
        "name": "seomyeon_to_haeundae",
        "start_name": "서면",
        "start_x": 129.058648,
        "start_y": 35.157667,
        "end_name": "해운대",
        "end_x": 129.158787,
        "end_y": 35.163590,
    },
]

BUS_SEARCH_ALIASES = {
    "부산역": ["부산역"],
    "서면역.롯데호텔백화점": ["서면역.롯데호텔백화점", "서면역 롯데호텔백화점", "서면역", "롯데호텔백화점"],
    "해운대도시철도역": ["해운대도시철도역", "해운대역", "해운대"],
}


class LinkingError(RuntimeError):
    pass


@dataclass
class BusStopMatch:
    role: str
    stop_name: str
    local_station_id: str | None
    direct_id_status: str
    direct_id_reason: str
    fallback_status: str
    fallback_reason: str
    fallback_bims_stop_id: str | None


@dataclass
class BusSegmentResult:
    scenario: str
    path_index: int
    route_no: str
    route_local_id: str | None
    start: BusStopMatch
    end: BusStopMatch


@dataclass
class SubwaySegmentResult:
    scenario: str
    path_index: int
    line_name: str
    start_name: str
    end_name: str
    status: str
    reason: str
    matched_route_name: str | None
    matched_route_no: str | None


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        raise LinkingError(f"env file not found: {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env


def require(env: dict[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise LinkingError(f"missing required env var: {key}")
    return value


def http_get_json(url: str, params: dict[str, Any]) -> Any:
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    request = urllib.request.Request(f"{url}?{query}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def http_get_text(url: str, params: dict[str, Any]) -> str:
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    request = urllib.request.Request(f"{url}?{query}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def first_child_text(parent: ET.Element, tag: str) -> str | None:
    child = parent.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def normalize_name(value: str) -> str:
    if not value:
        return ""

    normalized = value.strip()
    normalized = re.sub(r"\([^)]*\)", "", normalized)
    normalized = normalized.replace("부산 도시철도", "부산")
    normalized = normalized.replace("도시철도역", "역")
    normalized = normalized.replace("지하철역", "역")
    normalized = normalized.replace("역.", "역")
    normalized = normalized.replace("&", "")
    normalized = re.sub(r"[.\-·,/+]", "", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def extract_line_key(line_name: str) -> str:
    match = re.search(r"(\d+)호선", line_name)
    return match.group(1) if match else normalize_name(line_name)


def coord_distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def query_bims_bus_stop_list(env: dict[str, str], stop_name: str) -> list[dict[str, Any]]:
    if stop_name in BUS_STOP_LIST_CACHE:
        return BUS_STOP_LIST_CACHE[stop_name]

    base_url = require(env, "BUSAN_BIMS_API_BASE_URL")
    service_key = require(env, "BUSAN_BIMS_SERVICE_KEY_DECODING")
    raw = http_get_text(
        f"{base_url}/busStopList",
        {
            "pageNo": 1,
            "numOfRows": 50,
            "bstopnm": stop_name,
            "serviceKey": service_key,
        },
    )
    root = ET.fromstring(raw)
    rows: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        rows.append(
            {
                "bstopid": first_child_text(item, "bstopid"),
                "name": first_child_text(item, "bstopnm") or "",
                "x": float(first_child_text(item, "gpsx") or 0.0),
                "y": float(first_child_text(item, "gpsy") or 0.0),
            }
        )
    BUS_STOP_LIST_CACHE[stop_name] = rows
    return rows


def query_bims_arrivals(env: dict[str, str], bstopid: str) -> tuple[str | None, list[dict[str, Any]]]:
    if bstopid in BUS_ARRIVAL_CACHE:
        return BUS_ARRIVAL_CACHE[bstopid]

    base_url = require(env, "BUSAN_BIMS_API_BASE_URL")
    service_key = require(env, "BUSAN_BIMS_SERVICE_KEY_DECODING")
    raw = http_get_text(
        f"{base_url}/stopArrByBstopid",
        {
            "bstopid": bstopid,
            "pageNo": 1,
            "numOfRows": 50,
            "serviceKey": service_key,
        },
    )
    root = ET.fromstring(raw)
    result_code = root.findtext(".//resultCode")
    arrivals = []
    for item in root.findall(".//item"):
        arrivals.append(
            {
                "lineid": first_child_text(item, "lineid"),
                "lineno": first_child_text(item, "lineno"),
                "min1": first_child_text(item, "min1"),
            }
        )
    BUS_ARRIVAL_CACHE[bstopid] = (result_code, arrivals)
    return result_code, arrivals


def matches_route(arrivals: list[dict[str, Any]], route_no: str, route_local_id: str | None) -> bool:
    for arrival in arrivals:
        if route_local_id and arrival["lineid"] == route_local_id:
            return True
        if route_no and arrival["lineno"] == route_no:
            return True
    return False


def probe_direct_id(
    env: dict[str, str],
    local_station_id: str | None,
    route_no: str,
    route_local_id: str | None,
) -> tuple[str, str]:
    if not local_station_id:
        return ("UNAVAILABLE", "ODsay localStationID is missing")

    try:
        result_code, arrivals = query_bims_arrivals(env, local_station_id)
    except Exception as exc:  # noqa: BLE001
        return ("UNMATCHED", f"direct bstopid probe failed: {exc}")

    if result_code != "00":
        return ("UNMATCHED", f"stopArrByBstopid returned resultCode={result_code}")

    if not arrivals:
        return ("UNMATCHED", "stopArrByBstopid returned no arrivals for this stop")

    if matches_route(arrivals, route_no, route_local_id):
        return ("MATCHED", "ODsay localStationID resolved in BIMS and route auxiliary matched")

    return ("PARTIAL", "ODsay localStationID resolved in BIMS but route auxiliary was absent in current arrival snapshot")


def iter_bus_search_names(stop_name: str) -> list[str]:
    names = [stop_name]
    names.extend(BUS_SEARCH_ALIASES.get(stop_name, []))

    paren_removed = re.sub(r"\([^)]*\)", "", stop_name).strip()
    if paren_removed:
        names.append(paren_removed)

    for inner in re.findall(r"\(([^)]*)\)", stop_name):
        inner = inner.strip()
        if inner:
            names.append(inner)

    for token in re.split(r"[.\-/]", stop_name):
        token = token.strip()
        if token:
            names.append(token)

    deduped: list[str] = []
    for name in names:
        if name and name not in deduped:
            deduped.append(name)
    return deduped


def score_bims_candidate(
    candidate: dict[str, Any],
    stop_name: str,
    x: float,
    y: float,
    route_verified: bool,
) -> tuple[int, float]:
    score = 0
    normalized_target = normalize_name(stop_name)
    normalized_candidate = normalize_name(candidate["name"])

    if normalized_candidate == normalized_target:
        score += 200
    elif normalized_target and normalized_target in normalized_candidate:
        score += 120
    elif normalized_candidate and normalized_candidate in normalized_target:
        score += 80

    dist = coord_distance(candidate["x"], candidate["y"], x, y)
    if dist <= 0.0005:
        score += 100
    elif dist <= 0.0010:
        score += 60
    elif dist <= 0.0020:
        score += 30

    if route_verified:
        score += 150

    return score, dist


def preliminary_bims_score(candidate: dict[str, Any], stop_name: str, x: float, y: float) -> tuple[int, float]:
    score = 0
    normalized_target = normalize_name(stop_name)
    normalized_candidate = normalize_name(candidate["name"])

    if normalized_candidate == normalized_target:
        score += 200
    elif normalized_target and normalized_target in normalized_candidate:
        score += 120
    elif normalized_candidate and normalized_candidate in normalized_target:
        score += 80

    dist = coord_distance(candidate["x"], candidate["y"], x, y)
    if dist <= 0.0005:
        score += 100
    elif dist <= 0.0010:
        score += 60
    elif dist <= 0.0020:
        score += 30

    return score, dist


def choose_bims_fallback_match(
    env: dict[str, str],
    stop_name: str,
    x: float,
    y: float,
    route_no: str,
    route_local_id: str | None,
) -> tuple[str, str, str | None]:
    candidates_by_id: dict[str, dict[str, Any]] = {}

    for search_name in iter_bus_search_names(stop_name):
        try:
            rows = query_bims_bus_stop_list(env, search_name)
        except Exception as exc:  # noqa: BLE001
            continue
        for row in rows:
            if row["bstopid"]:
                candidates_by_id[row["bstopid"]] = row

    candidates = list(candidates_by_id.values())
    if not candidates:
        return ("UNMATCHED", "busStopList returned no candidates for normalized search names", None)

    prelim_scored = []
    for candidate in candidates:
        pre_score, pre_dist = preliminary_bims_score(candidate, stop_name, x, y)
        prelim_scored.append((pre_score, pre_dist, candidate))
    prelim_scored.sort(key=lambda item: (-item[0], item[1]))

    scored: list[tuple[int, float, bool, dict[str, Any]]] = []
    for _, _, candidate in prelim_scored[:5]:
        try:
            _, arrivals = query_bims_arrivals(env, candidate["bstopid"])
        except Exception:
            arrivals = []
        route_verified = matches_route(arrivals, route_no, route_local_id)
        score, dist = score_bims_candidate(candidate, stop_name, x, y, route_verified)
        scored.append((score, dist, route_verified, candidate))

    scored.sort(key=lambda item: (-item[0], item[1]))
    top_score, top_dist, route_verified, top_candidate = scored[0]

    if top_score < 180:
        return (
            "UNMATCHED",
            f"best fallback score={top_score}, coord_dist={top_dist:.6f}, route_verified={route_verified}",
            None,
        )

    reasons = []
    normalized_candidate = normalize_name(top_candidate["name"])
    normalized_target = normalize_name(stop_name)
    if normalized_candidate == normalized_target:
        reasons.append("normalized stop name exact match")
    elif normalized_target in normalized_candidate or normalized_candidate in normalized_target:
        reasons.append("normalized stop name partial match")
    reasons.append(f"coord_dist={top_dist:.6f}")
    if route_verified:
        reasons.append("route auxiliary verified by stopArrByBstopid")
    else:
        reasons.append("route auxiliary missing in current arrival snapshot")

    return ("MATCHED", ", ".join(reasons), top_candidate["bstopid"])


def load_subway_rows(env: dict[str, str]) -> list[dict[str, Any]]:
    base_url = require(env, "BUSAN_SUBWAY_OPERATION_API_BASE_URL")
    api_path = require(env, "BUSAN_SUBWAY_OPERATION_API_PATH")
    service_key = require(env, "BUSAN_SUBWAY_OPERATION_SERVICE_KEY_DECODING")

    rows: list[dict[str, Any]] = []
    page = 1
    per_page = 500
    total_count = None

    while True:
        payload = http_get_json(
            f"{base_url}{api_path}",
            {
                "page": page,
                "perPage": per_page,
                "returnType": "JSON",
                "serviceKey": service_key,
            },
        )
        page_rows = payload.get("data", [])
        rows.extend(page_rows)

        if total_count is None:
            total_count = int(payload.get("totalCount", 0))
        if len(rows) >= total_count or not page_rows:
            break
        page += 1

    return rows


def choose_subway_match(
    subway_rows: list[dict[str, Any]],
    line_name: str,
    start_name: str,
    end_name: str,
) -> tuple[str, str, str | None, str | None]:
    target_line_key = extract_line_key(line_name)
    target_start = normalize_name(start_name)
    target_end = normalize_name(end_name)

    candidates: list[dict[str, Any]] = []
    for row in subway_rows:
        route_name = str(row.get("노선명", ""))
        route_key = extract_line_key(route_name)
        if route_key != target_line_key:
            continue

        station_text = normalize_name(str(row.get("운행구간정거장", "")))
        if target_start in station_text and target_end in station_text:
            candidates.append(row)

    if not candidates:
        return (
            "UNMATCHED",
            "no odcloud row contains both stations on the same normalized line key",
            None,
            None,
        )

    matched = candidates[0]
    return (
        "MATCHED",
        "matched by normalized line key + start/end station containment in 운행구간정거장",
        str(matched.get("노선명", "")) or None,
        str(matched.get("노선번호", "")) or None,
    )


def fetch_odsay_paths(env: dict[str, str], scenario: dict[str, Any]) -> list[dict[str, Any]]:
    base_url = require(env, "ODSAY_API_BASE_URL")
    api_key = require(env, "ODSAY_API_KEY")
    payload = http_get_json(
        f"{base_url}/searchPubTransPathT",
        {
            "SX": scenario["start_x"],
            "SY": scenario["start_y"],
            "EX": scenario["end_x"],
            "EY": scenario["end_y"],
            "apiKey": api_key,
        },
    )
    return payload["result"]["path"][:3]


def evaluate() -> dict[str, Any]:
    env = load_env(ENV_PATH)
    subway_rows = load_subway_rows(env)

    bus_results: list[BusSegmentResult] = []
    subway_results: list[SubwaySegmentResult] = []

    for scenario in SCENARIOS:
        for path_index, path in enumerate(fetch_odsay_paths(env, scenario)):
            for sub_path in path.get("subPath", []):
                traffic_type = sub_path.get("trafficType")

                if traffic_type == 2:
                    lane = (sub_path.get("lane") or [{}])[0]
                    route_no = str(lane.get("busNo") or "")
                    route_local_id = str(lane.get("busLocalBlID") or "") or None

                    start_direct_status, start_direct_reason = probe_direct_id(
                        env,
                        str(sub_path.get("startLocalStationID") or "") or None,
                        route_no,
                        route_local_id,
                    )
                    start_fallback_status, start_fallback_reason, start_bims_stop_id = choose_bims_fallback_match(
                        env=env,
                        stop_name=str(sub_path.get("startName") or ""),
                        x=float(sub_path.get("startX") or 0.0),
                        y=float(sub_path.get("startY") or 0.0),
                        route_no=route_no,
                        route_local_id=route_local_id,
                    )

                    end_direct_status, end_direct_reason = probe_direct_id(
                        env,
                        str(sub_path.get("endLocalStationID") or "") or None,
                        route_no,
                        route_local_id,
                    )
                    end_fallback_status, end_fallback_reason, end_bims_stop_id = choose_bims_fallback_match(
                        env=env,
                        stop_name=str(sub_path.get("endName") or ""),
                        x=float(sub_path.get("endX") or 0.0),
                        y=float(sub_path.get("endY") or 0.0),
                        route_no=route_no,
                        route_local_id=route_local_id,
                    )

                    bus_results.append(
                        BusSegmentResult(
                            scenario=scenario["name"],
                            path_index=path_index,
                            route_no=route_no,
                            route_local_id=route_local_id,
                            start=BusStopMatch(
                                role="start",
                                stop_name=str(sub_path.get("startName") or ""),
                                local_station_id=str(sub_path.get("startLocalStationID") or "") or None,
                                direct_id_status=start_direct_status,
                                direct_id_reason=start_direct_reason,
                                fallback_status=start_fallback_status,
                                fallback_reason=start_fallback_reason,
                                fallback_bims_stop_id=start_bims_stop_id,
                            ),
                            end=BusStopMatch(
                                role="end",
                                stop_name=str(sub_path.get("endName") or ""),
                                local_station_id=str(sub_path.get("endLocalStationID") or "") or None,
                                direct_id_status=end_direct_status,
                                direct_id_reason=end_direct_reason,
                                fallback_status=end_fallback_status,
                                fallback_reason=end_fallback_reason,
                                fallback_bims_stop_id=end_bims_stop_id,
                            ),
                        )
                    )

                elif traffic_type == 1:
                    lane = (sub_path.get("lane") or [{}])[0]
                    status, reason, matched_route_name, matched_route_no = choose_subway_match(
                        subway_rows,
                        str(lane.get("name") or ""),
                        str(sub_path.get("startName") or ""),
                        str(sub_path.get("endName") or ""),
                    )
                    subway_results.append(
                        SubwaySegmentResult(
                            scenario=scenario["name"],
                            path_index=path_index,
                            line_name=str(lane.get("name") or ""),
                            start_name=str(sub_path.get("startName") or ""),
                            end_name=str(sub_path.get("endName") or ""),
                            status=status,
                            reason=reason,
                            matched_route_name=matched_route_name,
                            matched_route_no=matched_route_no,
                        )
                    )

    bus_unmatched = []
    for segment in bus_results:
        for point in (segment.start, segment.end):
            if point.fallback_status != "MATCHED":
                bus_unmatched.append(
                    {
                        "scenario": segment.scenario,
                        "path_index": segment.path_index,
                        "route_no": segment.route_no,
                        "role": point.role,
                        "stop_name": point.stop_name,
                        "local_station_id": point.local_station_id,
                        "direct_id_status": point.direct_id_status,
                        "direct_id_reason": point.direct_id_reason,
                        "fallback_reason": point.fallback_reason,
                    }
                )

    subway_unmatched = [
        {
            "scenario": segment.scenario,
            "path_index": segment.path_index,
            "line_name": segment.line_name,
            "start_name": segment.start_name,
            "end_name": segment.end_name,
            "reason": segment.reason,
        }
        for segment in subway_results
        if segment.status != "MATCHED"
    ]

    return {
        "scenarios": SCENARIOS,
        "bus_results": [asdict(segment) for segment in bus_results],
        "subway_results": [asdict(segment) for segment in subway_results],
        "bus_unmatched": bus_unmatched,
        "subway_unmatched": subway_unmatched,
        "summary": {
            "bus_segments_evaluated": len(bus_results),
            "subway_segments_evaluated": len(subway_results),
            "bus_fallback_unmatched_count": len(bus_unmatched),
            "subway_unmatched_count": len(subway_unmatched),
        },
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
