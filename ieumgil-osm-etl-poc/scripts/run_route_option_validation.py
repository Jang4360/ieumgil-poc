import argparse
import csv
import heapq
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Edge:
    edge_id: int
    from_node_id: int
    to_node_id: int
    coords: tuple[tuple[float, float], ...]
    length_meter: float
    has_stairs: bool
    has_crosswalk: bool
    has_signal: bool
    component_id: int

    @property
    def has_unsignalized_crosswalk(self) -> bool:
        return self.has_crosswalk and not self.has_signal


def parse_point_wkt(wkt: str) -> tuple[float, float]:
    prefix = "POINT ("
    suffix = ")"
    if not wkt.startswith(prefix) or not wkt.endswith(suffix):
        raise ValueError(f"Unsupported WKT: {wkt}")
    lon, lat = wkt[len(prefix) : -len(suffix)].split(" ")
    return float(lat), float(lon)


def parse_linestring_wkt(wkt: str) -> tuple[tuple[float, float], ...]:
    prefix = "LINESTRING ("
    suffix = ")"
    if not wkt.startswith(prefix) or not wkt.endswith(suffix):
        raise ValueError(f"Unsupported WKT: {wkt}")
    coords = []
    for point in wkt[len(prefix) : -len(suffix)].split(", "):
        lon, lat = point.split(" ")
        coords.append((float(lat), float(lon)))
    return tuple(coords)


def load_nodes(path: Path) -> dict[int, tuple[float, float]]:
    nodes: dict[int, tuple[float, float]] = {}
    with path.open(encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            nodes[int(row["vertexId"])] = parse_point_wkt(row["point"])
    return nodes


def parse_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def load_edges(path: Path, component_id: int) -> tuple[dict[int, Edge], dict[int, list[tuple[int, int, bool]]]]:
    edges: dict[int, Edge] = {}
    adjacency: dict[int, list[tuple[int, int, bool]]] = defaultdict(list)
    with path.open(encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            if int(row["component_id"]) != component_id:
                continue
            edge = Edge(
                edge_id=int(row["edgeId"]),
                from_node_id=int(row["from_node_id"]),
                to_node_id=int(row["to_node_id"]),
                coords=parse_linestring_wkt(row["geom"]),
                length_meter=float(row["length_meter"]),
                has_stairs=parse_bool(row["has_stairs"]),
                has_crosswalk=parse_bool(row["has_crosswalk"]),
                has_signal=parse_bool(row["has_signal"]),
                component_id=int(row["component_id"]),
            )
            edges[edge.edge_id] = edge
            adjacency[edge.from_node_id].append((edge.to_node_id, edge.edge_id, True))
            adjacency[edge.to_node_id].append((edge.from_node_id, edge.edge_id, False))
    return edges, adjacency


def edge_cost(edge: Edge, options: dict) -> Optional[float]:
    if options.get("forbid_stairs") and edge.has_stairs:
        return None
    cost = edge.length_meter
    if edge.has_stairs:
        cost += options.get("stairs_penalty_meter", 0.0)
    if edge.has_unsignalized_crosswalk:
        cost += options.get("unsignalized_crosswalk_penalty_meter", 0.0)
    return cost


def dijkstra(start_node_id: int, adjacency: dict[int, list[tuple[int, int, bool]]], edges: dict[int, Edge], options: dict):
    dist: dict[int, float] = {start_node_id: 0.0}
    previous: dict[int, tuple[int, int, bool]] = {}
    queue = [(0.0, start_node_id)]

    while queue:
        cost_so_far, node_id = heapq.heappop(queue)
        if cost_so_far != dist[node_id]:
            continue
        for neighbor_id, edge_id, forward in adjacency[node_id]:
            edge = edges[edge_id]
            traversal_cost = edge_cost(edge, options)
            if traversal_cost is None:
                continue
            next_cost = cost_so_far + traversal_cost
            if next_cost < dist.get(neighbor_id, float("inf")):
                dist[neighbor_id] = next_cost
                previous[neighbor_id] = (node_id, edge_id, forward)
                heapq.heappush(queue, (next_cost, neighbor_id))
    return dist, previous


def orient_coords(edge: Edge, forward: bool) -> list[tuple[float, float]]:
    coords = list(edge.coords)
    if forward:
        return coords
    return list(reversed(coords))


def build_geometry(path_edges: list[tuple[int, bool]], edges: dict[int, Edge]) -> list[list[float]]:
    geometry: list[list[float]] = []
    for index, (edge_id, forward) in enumerate(path_edges):
        coords = orient_coords(edges[edge_id], forward)
        for point_index, (lat, lon) in enumerate(coords):
            if index > 0 and point_index == 0:
                continue
            geometry.append([round(lat, 7), round(lon, 7)])
    return geometry


def reconstruct_path(
    start_node_id: int,
    end_node_id: int,
    previous: dict[int, tuple[int, int, bool]],
    edges: dict[int, Edge],
) -> Optional[dict]:
    if start_node_id == end_node_id:
        return None
    if end_node_id not in previous:
        return None

    node_ids = [end_node_id]
    traversals: list[tuple[int, bool]] = []
    total_length = 0.0
    stairs_count = 0
    unsignalized_crosswalk_count = 0
    signalized_crosswalk_count = 0

    node_id = end_node_id
    while node_id != start_node_id:
        prev_node_id, edge_id, forward = previous[node_id]
        edge = edges[edge_id]
        traversals.append((edge_id, forward))
        total_length += edge.length_meter
        if edge.has_stairs:
            stairs_count += 1
        if edge.has_crosswalk:
            if edge.has_signal:
                signalized_crosswalk_count += 1
            else:
                unsignalized_crosswalk_count += 1
        node_id = prev_node_id
        node_ids.append(node_id)

    traversals.reverse()
    node_ids.reverse()
    geometry = build_geometry(traversals, edges)

    return {
        "distanceMeter": round(total_length, 3),
        "edgeCount": len(traversals),
        "stairsCount": stairs_count,
        "unsignalizedCrosswalkCount": unsignalized_crosswalk_count,
        "signalizedCrosswalkCount": signalized_crosswalk_count,
        "edgeIds": [edge_id for edge_id, _ in traversals],
        "nodeIds": node_ids,
        "geometry": geometry,
    }


def candidate_for_avoid_stairs(
    start_node_ids: list[int],
    adjacency: dict[int, list[tuple[int, int, bool]]],
    edges: dict[int, Edge],
    preferred_min_detour_meter: float,
) -> dict:
    candidates = []
    node_ids = sorted(adjacency)
    for start_node_id in start_node_ids:
        _, previous_shortest = dijkstra(start_node_id, adjacency, edges, {})
        _, previous_safe = dijkstra(start_node_id, adjacency, edges, {"forbid_stairs": True})
        for end_node_id in node_ids:
            if end_node_id <= start_node_id:
                continue
            shortest = reconstruct_path(start_node_id, end_node_id, previous_shortest, edges)
            safe = reconstruct_path(start_node_id, end_node_id, previous_safe, edges)
            if not shortest or not safe:
                continue
            if shortest["stairsCount"] <= 0:
                continue
            if safe["stairsCount"] != 0:
                continue
            if shortest["edgeIds"] == safe["edgeIds"]:
                continue
            detour = round(safe["distanceMeter"] - shortest["distanceMeter"], 3)
            if detour <= 0:
                continue
            candidates.append(
                {
                    "startNodeId": start_node_id,
                    "endNodeId": end_node_id,
                    "shortest": shortest,
                    "safe": safe,
                    "distanceDetourMeter": detour,
                    "stairsRemoved": shortest["stairsCount"] - safe["stairsCount"],
                }
            )

    if not candidates:
        raise RuntimeError("No stairs avoidance candidate was found in the selected component.")

    preferred = [candidate for candidate in candidates if candidate["distanceDetourMeter"] >= preferred_min_detour_meter]
    pool = preferred or candidates
    pool.sort(key=lambda item: (item["distanceDetourMeter"], item["shortest"]["distanceMeter"]))
    selected = pool[0]
    selected["selectionReason"] = (
        "Shortest path uses stairs, while SAFE removes them entirely with the smallest representative detour."
    )
    return selected


def candidate_for_prefer_signalized_crossing(
    start_node_ids: list[int],
    adjacency: dict[int, list[tuple[int, int, bool]]],
    edges: dict[int, Edge],
    unsignalized_crosswalk_penalty_meter: float,
) -> dict:
    candidates = []
    node_ids = sorted(adjacency)
    options = {"unsignalized_crosswalk_penalty_meter": unsignalized_crosswalk_penalty_meter}
    for start_node_id in start_node_ids:
        _, previous_shortest = dijkstra(start_node_id, adjacency, edges, {})
        _, previous_safe = dijkstra(start_node_id, adjacency, edges, options)
        for end_node_id in node_ids:
            if end_node_id <= start_node_id:
                continue
            shortest = reconstruct_path(start_node_id, end_node_id, previous_shortest, edges)
            safe = reconstruct_path(start_node_id, end_node_id, previous_safe, edges)
            if not shortest or not safe:
                continue
            reduction = shortest["unsignalizedCrosswalkCount"] - safe["unsignalizedCrosswalkCount"]
            if reduction <= 0:
                continue
            if shortest["edgeIds"] == safe["edgeIds"]:
                continue
            detour = round(safe["distanceMeter"] - shortest["distanceMeter"], 3)
            if detour <= 0:
                continue
            candidates.append(
                {
                    "startNodeId": start_node_id,
                    "endNodeId": end_node_id,
                    "shortest": shortest,
                    "safe": safe,
                    "distanceDetourMeter": detour,
                    "unsignalizedCrosswalkReduction": reduction,
                }
            )

    if not candidates:
        raise RuntimeError("No unsignalized-crosswalk avoidance candidate was found in the selected component.")

    candidates.sort(
        key=lambda item: (
            -item["unsignalizedCrosswalkReduction"],
            item["distanceDetourMeter"],
            item["shortest"]["distanceMeter"],
        )
    )
    selected = candidates[0]
    selected["selectionReason"] = (
        "SAFE reduces unsignalized crossings the most while keeping the additional walking distance minimal for that reduction."
    )
    return selected


def evaluate_pair(
    start_node_id: int,
    end_node_id: int,
    adjacency: dict[int, list[tuple[int, int, bool]]],
    edges: dict[int, Edge],
    safe_options: dict,
) -> tuple[dict, dict]:
    _, previous_shortest = dijkstra(start_node_id, adjacency, edges, {})
    _, previous_safe = dijkstra(start_node_id, adjacency, edges, safe_options)
    shortest = reconstruct_path(start_node_id, end_node_id, previous_shortest, edges)
    safe = reconstruct_path(start_node_id, end_node_id, previous_safe, edges)
    if not shortest:
        raise RuntimeError(f"Shortest route could not be reconstructed for pair {start_node_id}->{end_node_id}.")
    if not safe:
        raise RuntimeError(f"SAFE route could not be reconstructed for pair {start_node_id}->{end_node_id}.")
    return shortest, safe


def validate_avoid_stairs_pair(
    start_node_id: int,
    end_node_id: int,
    adjacency: dict[int, list[tuple[int, int, bool]]],
    edges: dict[int, Edge],
) -> dict:
    shortest, safe = evaluate_pair(
        start_node_id,
        end_node_id,
        adjacency,
        edges,
        {"forbid_stairs": True},
    )
    if shortest["stairsCount"] <= 0:
        raise RuntimeError("Selected avoid-stairs pair does not use stairs on SHORTEST route.")
    if safe["stairsCount"] != 0:
        raise RuntimeError("Selected avoid-stairs pair still uses stairs on SAFE route.")
    if shortest["edgeIds"] == safe["edgeIds"]:
        raise RuntimeError("Selected avoid-stairs pair does not change route geometry.")
    return {
        "startNodeId": start_node_id,
        "endNodeId": end_node_id,
        "shortest": shortest,
        "safe": safe,
        "distanceDetourMeter": round(safe["distanceMeter"] - shortest["distanceMeter"], 3),
        "stairsRemoved": shortest["stairsCount"] - safe["stairsCount"],
        "selectionReason": (
            "Fixed representative pair chosen in Step 10 exploration. "
            "SHORTEST uses stairs and SAFE removes them entirely."
        ),
    }


def validate_prefer_signalized_pair(
    start_node_id: int,
    end_node_id: int,
    adjacency: dict[int, list[tuple[int, int, bool]]],
    edges: dict[int, Edge],
    unsignalized_crosswalk_penalty_meter: float,
) -> dict:
    shortest, safe = evaluate_pair(
        start_node_id,
        end_node_id,
        adjacency,
        edges,
        {"unsignalized_crosswalk_penalty_meter": unsignalized_crosswalk_penalty_meter},
    )
    reduction = shortest["unsignalizedCrosswalkCount"] - safe["unsignalizedCrosswalkCount"]
    if reduction <= 0:
        raise RuntimeError("Selected signalized-crossing pair does not reduce unsignalized crossings.")
    if shortest["edgeIds"] == safe["edgeIds"]:
        raise RuntimeError("Selected signalized-crossing pair does not change route geometry.")
    return {
        "startNodeId": start_node_id,
        "endNodeId": end_node_id,
        "shortest": shortest,
        "safe": safe,
        "distanceDetourMeter": round(safe["distanceMeter"] - shortest["distanceMeter"], 3),
        "unsignalizedCrosswalkReduction": reduction,
        "selectionReason": (
            "Fixed representative pair chosen in Step 10 exploration. "
            "SAFE reduces unsignalized crossings materially compared with SHORTEST."
        ),
    }


def build_node_payload(node_id: int, nodes: dict[int, tuple[float, float]]) -> dict:
    lat, lon = nodes[node_id]
    return {
        "nodeId": node_id,
        "lat": round(lat, 7),
        "lng": round(lon, 7),
    }


def build_network_stats(edges: dict[int, Edge], adjacency: dict[int, list[tuple[int, int, bool]]]) -> dict:
    stair_edges = sum(1 for edge in edges.values() if edge.has_stairs)
    crosswalk_edges = sum(1 for edge in edges.values() if edge.has_crosswalk)
    signal_edges = sum(1 for edge in edges.values() if edge.has_signal)
    unsignalized_crosswalk_edges = sum(1 for edge in edges.values() if edge.has_unsignalized_crosswalk)
    return {
        "nodeCount": len(adjacency),
        "edgeCount": len(edges),
        "stairsEdgeCount": stair_edges,
        "crosswalkEdgeCount": crosswalk_edges,
        "signalizedCrosswalkEdgeCount": signal_edges,
        "unsignalizedCrosswalkEdgeCount": unsignalized_crosswalk_edges,
    }


def comparison_payload(name: str, candidate: dict, nodes: dict[int, tuple[float, float]], safe_rule: dict) -> dict:
    shortest = candidate["shortest"]
    safe = candidate["safe"]
    return {
        "strategy": name,
        "selectionReason": candidate["selectionReason"],
        "start": build_node_payload(candidate["startNodeId"], nodes),
        "end": build_node_payload(candidate["endNodeId"], nodes),
        "shortest": {
            "routeOption": "SHORTEST",
            "weighting": "length_meter",
            **shortest,
        },
        "safe": {
            "routeOption": "SAFE",
            "weighting": safe_rule["weighting"],
            **safe,
        },
        "comparison": {
            "distanceDetourMeter": candidate["distanceDetourMeter"],
            "stairsRemoved": shortest["stairsCount"] - safe["stairsCount"],
            "unsignalizedCrosswalkReduction": (
                shortest["unsignalizedCrosswalkCount"] - safe["unsignalizedCrosswalkCount"]
            ),
            "edgeCountDelta": safe["edgeCount"] - shortest["edgeCount"],
            "pathChanged": shortest["edgeIds"] != safe["edgeIds"],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Step 10 route option validation.")
    parser.add_argument("--road-nodes-csv", required=True, help="road_nodes_service.csv path")
    parser.add_argument("--cleaned-segments-csv", required=True, help="road_segments_service_cleaned.csv path")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--component-id", type=int, default=1, help="Connected component id to validate")
    parser.add_argument(
        "--unsignalized-crosswalk-penalty-meter",
        type=float,
        default=80.0,
        help="Penalty applied to unsignalized crosswalk edges for SAFE route selection",
    )
    parser.add_argument("--avoid-stairs-start-node", type=int, default=1244, help="Representative start node")
    parser.add_argument("--avoid-stairs-end-node", type=int, default=1335, help="Representative end node")
    parser.add_argument(
        "--prefer-signalized-start-node",
        type=int,
        default=322,
        help="Representative start node",
    )
    parser.add_argument(
        "--prefer-signalized-end-node",
        type=int,
        default=1218,
        help="Representative end node",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    nodes = load_nodes(Path(args.road_nodes_csv))
    edges, adjacency = load_edges(Path(args.cleaned_segments_csv), args.component_id)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    avoid_stairs = validate_avoid_stairs_pair(
        args.avoid_stairs_start_node,
        args.avoid_stairs_end_node,
        adjacency,
        edges,
    )
    prefer_signalized = validate_prefer_signalized_pair(
        args.prefer_signalized_start_node,
        args.prefer_signalized_end_node,
        adjacency,
        edges,
        unsignalized_crosswalk_penalty_meter=args.unsignalized_crosswalk_penalty_meter,
    )

    avoid_stairs_payload = comparison_payload(
        "avoid_stairs",
        avoid_stairs,
        nodes,
        safe_rule={"weighting": "length_meter with has_stairs forbidden"},
    )
    prefer_signalized_payload = comparison_payload(
        "avoid_unsignalized_crossing",
        prefer_signalized,
        nodes,
        safe_rule={
            "weighting": (
                "length_meter with unsignalized crosswalk penalty "
                f"{args.unsignalized_crosswalk_penalty_meter}m"
            )
        },
    )

    (output_dir / "avoid_stairs_candidate.json").write_text(
        json.dumps(avoid_stairs_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "avoid_unsignalized_crossing_candidate.json").write_text(
        json.dumps(prefer_signalized_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "componentId": args.component_id,
        "inputFiles": {
            "roadNodesCsv": args.road_nodes_csv,
            "cleanedSegmentsCsv": args.cleaned_segments_csv,
        },
        "networkStats": build_network_stats(edges, adjacency),
        "searchConfig": {
            "avoidStairsPair": [args.avoid_stairs_start_node, args.avoid_stairs_end_node],
            "avoidUnsignalizedCrossingPair": [args.prefer_signalized_start_node, args.prefer_signalized_end_node],
            "unsignalizedCrosswalkPenaltyMeter": args.unsignalized_crosswalk_penalty_meter,
        },
        "validatedRouteOptions": {
            "SHORTEST": {
                "description": "Default walking shortest path based on length_meter.",
                "validatedInPreviousStep": "Step 7 and Step 9 outputs",
            },
            "SAFE": {
                "description": "Alternative route option with explicit avoidance or penalty rules.",
                "representativeRules": [
                    {
                        "name": "avoid_stairs",
                        "implementationCandidate": "GraphHopper profile/custom model candidate",
                        "outputFile": "avoid_stairs_candidate.json",
                    },
                    {
                        "name": "avoid_unsignalized_crossing",
                        "implementationCandidate": (
                            "GraphHopper import extension or service-side routing graph candidate"
                        ),
                        "outputFile": "avoid_unsignalized_crossing_candidate.json",
                    },
                ],
                "postProcessingOnly": [
                    "riskLevel",
                    "has_curb_gap",
                    "has_audio_signal",
                    "has_braille_block",
                ],
            },
        },
        "representativeComparisons": [
            {
                "strategy": "avoid_stairs",
                "distanceDetourMeter": avoid_stairs_payload["comparison"]["distanceDetourMeter"],
                "stairsRemoved": avoid_stairs_payload["comparison"]["stairsRemoved"],
                "outputFile": "avoid_stairs_candidate.json",
            },
            {
                "strategy": "avoid_unsignalized_crossing",
                "distanceDetourMeter": prefer_signalized_payload["comparison"]["distanceDetourMeter"],
                "unsignalizedCrosswalkReduction": prefer_signalized_payload["comparison"][
                    "unsignalizedCrosswalkReduction"
                ],
                "outputFile": "avoid_unsignalized_crossing_candidate.json",
            },
        ],
    }

    (output_dir / "route_option_validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"component_id={args.component_id}")
    print(f"edge_count={summary['networkStats']['edgeCount']}")
    print(f"avoid_stairs_detour={avoid_stairs_payload['comparison']['distanceDetourMeter']}")
    print(
        "avoid_unsignalized_crossing_reduction="
        f"{prefer_signalized_payload['comparison']['unsignalizedCrosswalkReduction']}"
    )
    print(f"output_dir={output_dir}")


if __name__ == "__main__":
    main()
