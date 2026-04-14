import argparse
import csv
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


def parse_point_wkt(wkt: str) -> tuple[float, float]:
    prefix = "POINT ("
    suffix = ")"
    if not wkt.startswith(prefix) or not wkt.endswith(suffix):
        raise ValueError(f"Unsupported WKT: {wkt}")
    lon, lat = wkt[len(prefix) : -len(suffix)].split(" ")
    return float(lat), float(lon)


def load_nodes(path: Path) -> dict[int, tuple[float, float]]:
    nodes = {}
    with path.open(encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            nodes[int(row["vertexId"])] = parse_point_wkt(row["point"])
    return nodes


def load_main_component_nodes(path: Path) -> set[int]:
    nodes = set()
    with path.open(encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            if int(row["component_id"]) != 1:
                continue
            nodes.add(int(row["from_node_id"]))
            nodes.add(int(row["to_node_id"]))
    return nodes


def component_bbox(coords: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    lats = [lat for lat, _ in coords]
    lons = [lon for _, lon in coords]
    return min(lats), min(lons), max(lats), max(lons)


def nearest_node(
    target: tuple[float, float], candidate_ids: list[int], node_coords: dict[int, tuple[float, float]], exclude: set[int]
) -> int:
    best_node = None
    best_distance = None
    for node_id in candidate_ids:
        if node_id in exclude:
            continue
        lat, lon = node_coords[node_id]
        distance = math.hypot(lat - target[0], lon - target[1])
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_node = node_id
    if best_node is None:
        raise RuntimeError("Unable to choose a unique node for scenario selection")
    return best_node


def choose_scenarios(node_coords: dict[int, tuple[float, float]], main_nodes: set[int]) -> list[dict]:
    candidate_ids = sorted(main_nodes)
    coords = [node_coords[node_id] for node_id in candidate_ids]
    min_lat, min_lon, max_lat, max_lon = component_bbox(coords)
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2

    scenario_specs = [
        {
            "name": "west_to_east_core",
            "start_target": (center_lat, min_lon + (max_lon - min_lon) * 0.2),
            "end_target": (center_lat, min_lon + (max_lon - min_lon) * 0.8),
        },
        {
            "name": "south_to_north_core",
            "start_target": (min_lat + (max_lat - min_lat) * 0.2, center_lon),
            "end_target": (min_lat + (max_lat - min_lat) * 0.8, center_lon),
        },
        {
            "name": "southwest_to_northeast",
            "start_target": (
                min_lat + (max_lat - min_lat) * 0.25,
                min_lon + (max_lon - min_lon) * 0.25,
            ),
            "end_target": (
                min_lat + (max_lat - min_lat) * 0.75,
                min_lon + (max_lon - min_lon) * 0.75,
            ),
        },
    ]

    scenarios = []
    used_nodes: set[int] = set()
    for spec in scenario_specs:
        start_node = nearest_node(spec["start_target"], candidate_ids, node_coords, used_nodes)
        used_nodes.add(start_node)
        end_node = nearest_node(spec["end_target"], candidate_ids, node_coords, used_nodes | {start_node})
        used_nodes.add(end_node)
        scenarios.append(
            {
                "name": spec["name"],
                "start_node_id": start_node,
                "end_node_id": end_node,
                "start_point": node_coords[start_node],
                "end_point": node_coords[end_node],
            }
        )
    return scenarios


def http_json(url: str) -> dict:
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step 7 GraphHopper route validation.")
    parser.add_argument("--base-url", required=True, help="GraphHopper base URL, e.g. http://localhost:8989")
    parser.add_argument("--road-nodes-csv", required=True, help="road_nodes_service.csv path")
    parser.add_argument("--cleaned-segments-csv", required=True, help="road_segments_service_cleaned.csv path")
    parser.add_argument("--output-dir", required=True, help="Directory for route validation outputs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    node_coords = load_nodes(Path(args.road_nodes_csv))
    main_nodes = load_main_component_nodes(Path(args.cleaned_segments_csv))
    scenarios = choose_scenarios(node_coords, main_nodes)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    info = http_json(f"{args.base_url.rstrip('/')}/info")
    (output_dir / "graphhopper_info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "base_url": args.base_url,
        "scenario_results": [],
    }

    for scenario in scenarios:
        response = route_request(args.base_url, scenario["start_point"], scenario["end_point"])
        (output_dir / f"{scenario['name']}.json").write_text(
            json.dumps(response, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        paths = response.get("paths", [])
        if not paths:
            summary["scenario_results"].append(
                {
                    **scenario,
                    "success": False,
                    "error": response.get("message", "No paths returned"),
                }
            )
            continue

        path = paths[0]
        points = path.get("points", {}).get("coordinates", [])
        snapped = path.get("snapped_waypoints", {}).get("coordinates", [])
        summary["scenario_results"].append(
            {
                **scenario,
                "success": True,
                "distance_meter": path.get("distance"),
                "time_millis": path.get("time"),
                "estimated_time_minute": round(path.get("time", 0) / 60000, 2),
                "point_count": len(points),
                "instruction_count": len(path.get("instructions", [])),
                "snapped_waypoint_count": len(snapped),
            }
        )

    (output_dir / "graphhopper_route_validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    success_count = sum(1 for result in summary["scenario_results"] if result["success"])
    print(f"scenario_count={len(summary['scenario_results'])}")
    print(f"success_count={success_count}")
    print(f"output_dir={output_dir}")


if __name__ == "__main__":
    main()
