import argparse
import csv
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError


ACCEPT_THRESHOLD_METER = 30.0
WARN_THRESHOLD_METER = 80.0


def meter_offset_to_latlon(lat: float, lon: float, east_meter: float, north_meter: float) -> tuple[float, float]:
    delta_lat = north_meter / 111320.0
    delta_lon = east_meter / (111320.0 * math.cos(math.radians(lat)))
    return lat + delta_lat, lon + delta_lon


def haversine_meter(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    radius = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    sin_dlat = math.sin(dlat / 2)
    sin_dlon = math.sin(dlon / 2)
    aa = sin_dlat**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * sin_dlon**2
    return 2 * radius * math.atan2(math.sqrt(aa), math.sqrt(1 - aa))


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


def nearest_request(base_url: str, point: tuple[float, float]) -> dict:
    params = [
        ("profile", "foot"),
        ("point", f"{point[0]},{point[1]}"),
    ]
    url = f"{base_url.rstrip('/')}/nearest?{urlencode(params)}"
    return http_json(url)


def route_request(base_url: str, start: tuple[float, float], end: tuple[float, float]) -> dict:
    params = [
        ("profile", "foot"),
        ("point", f"{start[0]},{start[1]}"),
        ("point", f"{end[0]},{end[1]}"),
        ("points_encoded", "false"),
        ("instructions", "true"),
        ("calc_points", "true"),
    ]
    url = f"{base_url.rstrip('/')}/route?{urlencode(params)}"
    return http_json(url)


def load_step7_scenarios(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["scenario_results"]


def classify_case(max_snap_distance: float | None, route_success: bool, nearest_failed: bool) -> tuple[str, str]:
    if nearest_failed:
        return "REJECT", "Point is out of bounds or cannot be matched to walkable network"
    if not route_success or max_snap_distance is None:
        return "REJECT", "No route returned"
    if max_snap_distance <= ACCEPT_THRESHOLD_METER:
        return "ACCEPT", "Within normal GPS error range"
    if max_snap_distance <= WARN_THRESHOLD_METER:
        return "WARN", "Route is possible but snap distance is larger than normal GPS error"
    return "REJECT", "Snap distance is too large for reliable user intent"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step 8 coordinate snapping validation.")
    parser.add_argument("--base-url", required=True, help="GraphHopper base URL")
    parser.add_argument("--step7-summary", required=True, help="Step 7 route summary JSON path")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenarios = load_step7_scenarios(Path(args.step7_summary))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    case_profiles = [
        {
            "case_name": "exact_reference",
            "case_type": "baseline",
            "start_offset_meter": (0.0, 0.0),
            "end_offset_meter": (0.0, 0.0),
        },
        {
            "case_name": "gps_small_error",
            "case_type": "gps_error",
            "start_offset_meter": (12.0, -8.0),
            "end_offset_meter": (-10.0, 15.0),
        },
        {
            "case_name": "building_plaza_like",
            "case_type": "off_road_but_near",
            "start_offset_meter": (38.0, 42.0),
            "end_offset_meter": (-32.0, -36.0),
        },
        {
            "case_name": "too_far_candidate",
            "case_type": "far_off_road",
            "start_offset_meter": (220.0, 180.0),
            "end_offset_meter": (-210.0, 160.0),
        },
        {
            "case_name": "in_bounds_large_snap",
            "case_type": "large_snap_but_still_in_bounds",
            "start_offset_meter": (1200.0, 900.0),
            "end_offset_meter": (0.0, 0.0),
        },
        {
            "case_name": "out_of_bounds_far",
            "case_type": "hard_fail",
            "start_absolute": (35.05, 128.9),
            "end_offset_meter": (0.0, 0.0),
        },
    ]

    results = []
    for scenario in scenarios:
        base_start = tuple(scenario["start_point"])
        base_end = tuple(scenario["end_point"])
        scenario_cases = []
        for case in case_profiles:
            if "start_absolute" in case:
                start_input = case["start_absolute"]
                start_offset_meter = None
            else:
                start_input = meter_offset_to_latlon(
                    base_start[0], base_start[1], case["start_offset_meter"][0], case["start_offset_meter"][1]
                )
                start_offset_meter = list(case["start_offset_meter"])

            if "end_absolute" in case:
                end_input = case["end_absolute"]
                end_offset_meter = None
            else:
                end_input = meter_offset_to_latlon(
                    base_end[0], base_end[1], case["end_offset_meter"][0], case["end_offset_meter"][1]
                )
                end_offset_meter = list(case["end_offset_meter"])

            start_nearest = nearest_request(args.base_url, start_input)
            end_nearest = nearest_request(args.base_url, end_input)
            nearest_failed = bool(start_nearest.get("__http_error__")) or bool(end_nearest.get("__http_error__"))
            route_response = route_request(args.base_url, start_input, end_input)

            paths = route_response.get("paths", [])
            route_success = bool(paths)
            snapped_start_distance = start_nearest.get("distance")
            snapped_end_distance = end_nearest.get("distance")
            snapped_route_points = []
            distance_meter = None
            estimated_time_minute = None
            instruction_count = None
            if route_success:
                path = paths[0]
                snapped_route_points = path.get("snapped_waypoints", {}).get("coordinates", [])
                distance_meter = path.get("distance")
                estimated_time_minute = round(path.get("time", 0) / 60000, 2)
                instruction_count = len(path.get("instructions", []))

            max_snap_distance = None
            if snapped_start_distance is not None and snapped_end_distance is not None:
                max_snap_distance = max(snapped_start_distance, snapped_end_distance)
            service_decision, decision_reason = classify_case(max_snap_distance, route_success, nearest_failed)

            case_result = {
                "scenario_name": scenario["name"],
                "case_name": case["case_name"],
                "case_type": case["case_type"],
                "start_input": [round(start_input[0], 7), round(start_input[1], 7)],
                "end_input": [round(end_input[0], 7), round(end_input[1], 7)],
                "start_offset_meter": start_offset_meter,
                "end_offset_meter": end_offset_meter,
                "start_snap_distance_meter": snapped_start_distance,
                "end_snap_distance_meter": snapped_end_distance,
                "max_snap_distance_meter": max_snap_distance,
                "route_success": route_success,
                "distance_meter": distance_meter,
                "estimated_time_minute": estimated_time_minute,
                "instruction_count": instruction_count,
                "service_decision": service_decision,
                "decision_reason": decision_reason,
                "start_nearest_point": start_nearest.get("coordinates"),
                "end_nearest_point": end_nearest.get("coordinates"),
                "start_nearest_error": start_nearest.get("message") if start_nearest.get("__http_error__") else None,
                "end_nearest_error": end_nearest.get("message") if end_nearest.get("__http_error__") else None,
                "route_error": route_response.get("message") if route_response.get("__http_error__") else None,
                "route_snapped_waypoints": snapped_route_points,
            }
            scenario_cases.append(case_result)
            results.append(case_result)

        (output_dir / f"{scenario['name']}_snapping_cases.json").write_text(
            json.dumps(scenario_cases, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    summary = {
        "thresholds": {
            "accept_max_snap_meter": ACCEPT_THRESHOLD_METER,
            "warn_max_snap_meter": WARN_THRESHOLD_METER,
        },
        "counts": {
            "total_cases": len(results),
            "accept": sum(1 for row in results if row["service_decision"] == "ACCEPT"),
            "warn": sum(1 for row in results if row["service_decision"] == "WARN"),
            "reject": sum(1 for row in results if row["service_decision"] == "REJECT"),
            "route_success": sum(1 for row in results if row["route_success"]),
        },
        "results": results,
    }
    (output_dir / "snapping_validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (output_dir / "snapping_validation_summary.csv").open("w", newline="", encoding="utf-8") as fp:
        fieldnames = [
            "scenario_name",
            "case_name",
            "case_type",
            "start_input",
            "end_input",
            "start_snap_distance_meter",
            "end_snap_distance_meter",
            "max_snap_distance_meter",
            "route_success",
            "distance_meter",
            "estimated_time_minute",
            "instruction_count",
            "service_decision",
            "decision_reason",
        ]
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            payload = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(payload)

    print(f"total_cases={summary['counts']['total_cases']}")
    print(f"accept={summary['counts']['accept']}")
    print(f"warn={summary['counts']['warn']}")
    print(f"reject={summary['counts']['reject']}")
    print(f"route_success={summary['counts']['route_success']}")
    print(f"output_dir={output_dir}")


if __name__ == "__main__":
    main()
