import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def parse_linestring_wkt(wkt: str) -> list[tuple[float, float]]:
    prefix = "LINESTRING ("
    suffix = ")"
    if not wkt.startswith(prefix) or not wkt.endswith(suffix):
        raise ValueError(f"Unsupported WKT: {wkt}")
    raw_points = wkt[len(prefix) : -len(suffix)].split(", ")
    coords = []
    for point in raw_points:
        lon, lat = point.split(" ")
        coords.append((float(lon), float(lat)))
    return coords


def load_segments(path: Path) -> list[dict]:
    segments = []
    with path.open(encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            coords = parse_linestring_wkt(row["geom"])
            segments.append(
                {
                    "edgeId": int(row["edgeId"]),
                    "from_node_id": int(row["from_node_id"]),
                    "to_node_id": int(row["to_node_id"]),
                    "length_meter": float(row["length_meter"]),
                    "coords": coords,
                }
            )
    return segments


def build_components(segments: list[dict]) -> tuple[dict[int, int], list[dict]]:
    adj: dict[int, set[int]] = defaultdict(set)
    edge_ids_by_pair: dict[tuple[int, int], list[int]] = defaultdict(list)
    for segment in segments:
        a = segment["from_node_id"]
        b = segment["to_node_id"]
        adj[a].add(b)
        adj[b].add(a)
        edge_ids_by_pair[tuple(sorted((a, b)))].append(segment["edgeId"])

    node_component: dict[int, int] = {}
    components: list[dict] = []
    component_id = 0

    for start_node in adj:
        if start_node in node_component:
            continue
        component_id += 1
        stack = [start_node]
        node_component[start_node] = component_id
        nodes = []
        undirected_edges = set()

        while stack:
            node = stack.pop()
            nodes.append(node)
            for nxt in adj[node]:
                undirected_edges.add(tuple(sorted((node, nxt))))
                if nxt not in node_component:
                    node_component[nxt] = component_id
                    stack.append(nxt)

        components.append(
            {
                "component_id": component_id,
                "node_count": len(nodes),
                "edge_count": len(undirected_edges),
            }
        )

    components.sort(key=lambda item: (item["node_count"], item["edge_count"]), reverse=True)
    rank_by_component = {
        component["component_id"]: rank + 1 for rank, component in enumerate(components)
    }
    node_rank = {
        node_id: rank_by_component[component_id]
        for node_id, component_id in node_component.items()
    }
    return node_rank, components


def compute_bbox(segments: list[dict]) -> tuple[float, float, float, float]:
    lons = [lon for segment in segments for lon, _ in segment["coords"]]
    lats = [lat for segment in segments for _, lat in segment["coords"]]
    return min(lons), min(lats), max(lons), max(lats)


def near_bbox_edge(
    coords: list[tuple[float, float]], bbox: tuple[float, float, float, float], margin: float = 0.0006
) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    for lon, lat in coords:
        if (
            abs(lon - min_lon) <= margin
            or abs(lon - max_lon) <= margin
            or abs(lat - min_lat) <= margin
            or abs(lat - max_lat) <= margin
        ):
            return True
    return False


def plot_overview(segments: list[dict], output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 10))
    for segment in segments:
        rank = segment["component_rank"]
        color = "#1f2937" if rank == 1 else "#f97316"
        alpha = 0.85 if rank == 1 else 0.9
        linewidth = 1.0 if rank == 1 else 1.2
        xs = [lon for lon, _ in segment["coords"]]
        ys = [lat for _, lat in segment["coords"]]
        ax.plot(xs, ys, color=color, alpha=alpha, linewidth=linewidth)

    ax.set_title("Seomyeon 1km Sample Road Segments\nLargest component: dark / minor components: orange")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_outliers(
    segments: list[dict], long_threshold: float, short_threshold: float, output_path: Path
) -> None:
    fig, ax = plt.subplots(figsize=(10, 10))
    for segment in segments:
        xs = [lon for lon, _ in segment["coords"]]
        ys = [lat for _, lat in segment["coords"]]
        color = "#d1d5db"
        linewidth = 0.8
        alpha = 0.6
        if segment["length_meter"] >= long_threshold:
            color = "#dc2626"
            linewidth = 1.6
            alpha = 0.95
        elif segment["length_meter"] <= short_threshold:
            color = "#2563eb"
            linewidth = 1.4
            alpha = 0.95
        ax.plot(xs, ys, color=color, alpha=alpha, linewidth=linewidth)

    ax.set_title(
        f"Segment Length Outliers\nRed >= {long_threshold:.0f}m / Blue <= {short_threshold:.0f}m"
    )
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_summary(
    segments: list[dict],
    components: list[dict],
    bbox: tuple[float, float, float, float],
    long_threshold: float,
    short_threshold: float,
) -> dict:
    longest = sorted(segments, key=lambda item: item["length_meter"], reverse=True)[:10]
    shortest = sorted(segments, key=lambda item: item["length_meter"])[:10]
    largest_component_nodes = components[0]["node_count"] if components else 0
    largest_component_edges = components[0]["edge_count"] if components else 0

    return {
        "segment_count": len(segments),
        "component_count": len(components),
        "largest_component": {
            "node_count": largest_component_nodes,
            "edge_count": largest_component_edges,
        },
        "minor_components": components[1:],
        "length_thresholds": {
            "long_meter": long_threshold,
            "short_meter": short_threshold,
        },
        "counts": {
            "long_segments": sum(1 for segment in segments if segment["length_meter"] >= long_threshold),
            "short_segments": sum(1 for segment in segments if segment["length_meter"] <= short_threshold),
            "segments_near_bbox_edge": sum(
                1 for segment in segments if near_bbox_edge(segment["coords"], bbox)
            ),
        },
        "bbox": {
            "min_lon": bbox[0],
            "min_lat": bbox[1],
            "max_lon": bbox[2],
            "max_lat": bbox[3],
        },
        "top_longest_segments": [
            {
                "edgeId": segment["edgeId"],
                "length_meter": segment["length_meter"],
                "from_node_id": segment["from_node_id"],
                "to_node_id": segment["to_node_id"],
                "component_rank": segment["component_rank"],
                "near_bbox_edge": near_bbox_edge(segment["coords"], bbox),
            }
            for segment in longest
        ],
        "top_shortest_segments": [
            {
                "edgeId": segment["edgeId"],
                "length_meter": segment["length_meter"],
                "from_node_id": segment["from_node_id"],
                "to_node_id": segment["to_node_id"],
                "component_rank": segment["component_rank"],
                "near_bbox_edge": near_bbox_edge(segment["coords"], bbox),
            }
            for segment in shortest
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render road segment visual QA artifacts.")
    parser.add_argument("--segments-csv", required=True, help="road_segments_service.csv path")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--long-threshold", type=float, default=500.0, help="Long segment threshold in meters")
    parser.add_argument("--short-threshold", type=float, default=5.0, help="Short segment threshold in meters")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    segments = load_segments(Path(args.segments_csv))
    node_rank, components = build_components(segments)
    for segment in segments:
        segment["component_rank"] = node_rank[segment["from_node_id"]]

    bbox = compute_bbox(segments)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_overview(segments, output_dir / "segment_overview.png")
    plot_outliers(
        segments,
        args.long_threshold,
        args.short_threshold,
        output_dir / "segment_length_outliers.png",
    )

    summary = build_summary(segments, components, bbox, args.long_threshold, args.short_threshold)
    (output_dir / "segment_visual_qa_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"segment_count={summary['segment_count']}")
    print(f"component_count={summary['component_count']}")
    print(f"largest_component_nodes={summary['largest_component']['node_count']}")
    print(f"largest_component_edges={summary['largest_component']['edge_count']}")
    print(f"long_segments={summary['counts']['long_segments']}")
    print(f"short_segments={summary['counts']['short_segments']}")
    print(f"output_dir={output_dir}")


if __name__ == "__main__":
    main()
