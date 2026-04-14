import argparse
import json
import math
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen


ON_WALKABLE_MAX_SNAP_METER = 10.0
NEAR_WALKABLE_MAX_SNAP_METER = 80.0


def http_json(url: str) -> dict:
    try:
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = {"message": payload}
        return {
            "__http_error__": True,
            "status_code": exc.code,
            **data,
        }


def route_request(base_url: str, start: tuple[float, float], end: tuple[float, float]) -> dict:
    params = [
        ("profile", "foot"),
        ("point", f"{start[0]},{start[1]}"),
        ("point", f"{end[0]},{end[1]}"),
        ("points_encoded", "false"),
        ("instructions", "true"),
        ("calc_points", "true"),
    ]
    return http_json(f"{base_url.rstrip('/')}/route?{urlencode(params)}")


def load_summary(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["results"]


def select_representative_cases(results: list[dict]) -> list[dict]:
    selected = []

    def first_match(predicate):
        for row in results:
            if predicate(row):
                return row
        return None

    candidates = [
        first_match(lambda row: row["service_decision"] == "ACCEPT" and row["max_snap_distance_meter"] == 0.0),
        first_match(lambda row: row["service_decision"] == "WARN"),
        first_match(lambda row: row["service_decision"] == "REJECT" and row["route_success"]),
        first_match(lambda row: row["service_decision"] == "REJECT" and not row["route_success"]),
    ]

    seen = set()
    for row in candidates:
        if not row:
            continue
        key = (row["scenario_name"], row["case_name"])
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
    return selected


def to_latlng(point: list[float] | None) -> dict | None:
    if not point:
        return None
    lon, lat = point
    return {
        "lat": round(lat, 7),
        "lng": round(lon, 7),
    }


def classify_location_context(snap_distance_meter: float | None, nearest_error: str | None) -> str:
    if nearest_error:
        return "OUT_OF_SERVICE_AREA"
    if snap_distance_meter is None:
        return "OUT_OF_SERVICE_AREA"
    if snap_distance_meter <= ON_WALKABLE_MAX_SNAP_METER:
        return "ON_WALKABLE_NETWORK"
    if snap_distance_meter <= NEAR_WALKABLE_MAX_SNAP_METER:
        return "NEAR_WALKABLE_NETWORK"
    return "OUT_OF_SERVICE_AREA"


def linestring_wkt(coords: list[list[float]]) -> str:
    joined = ", ".join(f"{lon:.7f} {lat:.7f}" for lon, lat in coords)
    return f"LINESTRING({joined})"


def build_segments(path: dict) -> list[dict]:
    points = path.get("points", {}).get("coordinates", [])
    instructions = path.get("instructions", [])
    segments = []
    sequence = 1
    for instruction in instructions:
        if instruction.get("distance", 0.0) <= 0:
            continue
        interval = instruction.get("interval", [])
        if len(interval) != 2:
            continue
        start_idx, end_idx = interval
        geometry_coords = points[start_idx : end_idx + 1]
        if len(geometry_coords) < 2:
            continue
        segments.append(
            {
                "sequence": sequence,
                "geometry": linestring_wkt(geometry_coords),
                "distanceMeter": round(instruction.get("distance", 0.0), 3),
                "hasStairs": None,
                "hasCurbGap": None,
                "hasCrosswalk": None,
                "hasSignal": None,
                "hasAudioSignal": None,
                "hasBrailleBlock": None,
                "riskLevel": None,
                "guidanceMessage": instruction.get("text") or None,
            }
        )
        sequence += 1
    return segments


def build_request_context(case: dict) -> dict:
    return {
        "start": {
            "rawLocation": {
                "lat": case["start_input"][0],
                "lng": case["start_input"][1],
            },
            "snappedRouteAnchor": to_latlng(case.get("start_nearest_point")),
            "locationContext": classify_location_context(
                case.get("start_snap_distance_meter"),
                case.get("start_nearest_error"),
            ),
            "snapDistanceMeter": case.get("start_snap_distance_meter"),
        },
        "end": {
            "rawLocation": {
                "lat": case["end_input"][0],
                "lng": case["end_input"][1],
            },
            "snappedRouteAnchor": to_latlng(case.get("end_nearest_point")),
            "locationContext": classify_location_context(
                case.get("end_snap_distance_meter"),
                case.get("end_nearest_error"),
            ),
            "snapDistanceMeter": case.get("end_snap_distance_meter"),
        },
        "serviceDecision": case["service_decision"],
        "decisionReason": case["decision_reason"],
        "insideBuildingSupport": {
            "supportedInStep9": False,
            "reason": "Building polygon or entrance data is required to distinguish indoor locations from nearby walkable space.",
        },
    }


def build_response_draft(case: dict, route_response: dict) -> dict:
    if route_response.get("__http_error__") or not route_response.get("paths"):
        return {
            "success": False,
            "data": None,
            "message": route_response.get("message", "No route returned"),
        }

    path = route_response["paths"][0]
    return {
        "success": True,
        "data": {
            "routes": [
                {
                    "routeOption": "SHORTEST",
                    "title": "기본 보행 경로",
                    "distanceMeter": round(path.get("distance", 0.0), 3),
                    "estimatedTimeMinute": int(math.ceil(path.get("time", 0) / 60000)),
                    "riskLevel": None,
                    "segments": build_segments(path),
                }
            ]
        },
        "message": None,
    }


def build_mapping_notes(case: dict, response_draft: dict) -> dict:
    return {
        "mappingStatus": "PARTIAL" if response_draft["success"] else "ERROR",
        "validatedRouteOption": "SHORTEST",
        "fieldSource": {
            "routes[].distanceMeter": "GraphHopper paths[].distance",
            "routes[].estimatedTimeMinute": "GraphHopper paths[].time with ceil-minute conversion",
            "routes[].segments[].geometry": "GraphHopper instruction interval sliced from paths[].points",
            "routes[].segments[].distanceMeter": "GraphHopper instructions[].distance",
            "routes[].segments[].guidanceMessage": "GraphHopper instructions[].text",
            "requestContext.rawLocation": "Client input coordinates",
            "requestContext.snappedRouteAnchor": "GraphHopper nearest/route snapped result",
            "requestContext.locationContext": "Step 8 snap-distance based interpretation rule",
        },
        "requiresPostProcessing": [
            "routes[].riskLevel",
            "routes[].segments[].hasStairs",
            "routes[].segments[].hasCurbGap",
            "routes[].segments[].hasCrosswalk",
            "routes[].segments[].hasSignal",
            "routes[].segments[].hasAudioSignal",
            "routes[].segments[].hasBrailleBlock",
            "routes[].segments[].riskLevel",
        ],
        "notes": [
            "GraphHopper route output does not directly expose service road_segments IDs in the current PoC setup.",
            "Instruction-based segments can be created, but segment-level safety attributes require road_segments join or additional public data.",
            "INSIDE_BUILDING cannot be derived reliably in Step 9 without building polygon or entrance data.",
            f"Service decision for this case is {case['service_decision']} and must be handled separately from route engine success.",
        ],
    }


def safe_name(case: dict) -> str:
    return f"{case['scenario_name']}__{case['case_name']}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Step 9 response mapping samples.")
    parser.add_argument("--base-url", required=True, help="GraphHopper base URL")
    parser.add_argument("--step8-summary", required=True, help="Step 8 summary JSON path")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = load_summary(Path(args.step8_summary))
    selected = select_representative_cases(results)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "selected_cases": [],
        "contextRule": {
            "ON_WALKABLE_NETWORK": f"snap distance <= {ON_WALKABLE_MAX_SNAP_METER}m",
            "NEAR_WALKABLE_NETWORK": (
                f"snap distance > {ON_WALKABLE_MAX_SNAP_METER}m and <= {NEAR_WALKABLE_MAX_SNAP_METER}m"
            ),
            "OUT_OF_SERVICE_AREA": (
                f"nearest failed or snap distance > {NEAR_WALKABLE_MAX_SNAP_METER}m"
            ),
            "INSIDE_BUILDING": "Not derivable in Step 9 without external spatial data",
        },
    }

    for case in selected:
        start = tuple(case["start_input"])
        end = tuple(case["end_input"])
        route_response = route_request(args.base_url, start, end)
        request_context = build_request_context(case)
        response_draft = build_response_draft(case, route_response)
        mapping_notes = build_mapping_notes(case, response_draft)

        payload = {
            "scenarioName": case["scenario_name"],
            "caseName": case["case_name"],
            "requestContext": request_context,
            "responseDraft": response_draft,
            "mappingNotes": mapping_notes,
        }
        name = safe_name(case)
        (output_dir / f"{name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary["selected_cases"].append(
            {
                "scenarioName": case["scenario_name"],
                "caseName": case["case_name"],
                "serviceDecision": case["service_decision"],
                "responseSuccess": response_draft["success"],
                "startLocationContext": request_context["start"]["locationContext"],
                "endLocationContext": request_context["end"]["locationContext"],
                "outputFile": f"{name}.json",
            }
        )

    (output_dir / "response_mapping_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"selected_case_count={len(summary['selected_cases'])}")
    print(f"output_dir={output_dir}")


if __name__ == "__main__":
    main()
