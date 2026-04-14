import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def parse_linestring_wkt(wkt: str) -> list[tuple[float, float]]:
    prefix = "LINESTRING ("
    suffix = ")"
    if not wkt.startswith(prefix) or not wkt.endswith(suffix):
        raise ValueError(f"Unsupported WKT: {wkt}")
    coords = []
    for point in wkt[len(prefix) : -len(suffix)].split(", "):
        lon, lat = point.split(" ")
        coords.append((float(lon), float(lat)))
    return coords


def linestring_wkt(coords: list[tuple[float, float]]) -> str:
    return "LINESTRING (" + ", ".join(f"{lon:.7f} {lat:.7f}" for lon, lat in coords) + ")"


def load_segments(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            coords = parse_linestring_wkt(row["geom"])
            rows.append(
                {
                    "edgeId": int(row["edgeId"]),
                    "from_node_id": int(row["from_node_id"]),
                    "to_node_id": int(row["to_node_id"]),
                    "geom": row["geom"],
                    "coords": coords,
                    "length_meter": float(row["length_meter"]),
                    "avg_slope_percent": row["avg_slope_percent"],
                    "width_meter": row["width_meter"],
                    "has_stairs": row["has_stairs"],
                    "has_curb_gap": row["has_curb_gap"],
                    "has_elevator": row["has_elevator"],
                    "has_crosswalk": row["has_crosswalk"],
                    "has_signal": row["has_signal"],
                    "has_audio_signal": row["has_audio_signal"],
                    "has_braille_block": row["has_braille_block"],
                    "surface_type": row["surface_type"],
                }
            )
    return rows


def compute_bbox(rows: list[dict]) -> tuple[float, float, float, float]:
    lons = [lon for row in rows for lon, _ in row["coords"]]
    lats = [lat for row in rows for _, lat in row["coords"]]
    return min(lons), min(lats), max(lons), max(lats)


def near_bbox_edge(
    coords: list[tuple[float, float]], bbox: tuple[float, float, float, float], margin: float
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


def assign_component_ids(rows: list[dict]) -> list[dict]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for row in rows:
        adjacency[row["from_node_id"]].add(row["to_node_id"])
        adjacency[row["to_node_id"]].add(row["from_node_id"])

    node_to_component: dict[int, int] = {}
    components = []
    component_seed = 0
    for start in adjacency:
        if start in node_to_component:
            continue
        component_seed += 1
        stack = [start]
        node_to_component[start] = component_seed
        nodes = []
        edge_pairs = set()
        while stack:
            node = stack.pop()
            nodes.append(node)
            for nxt in adjacency[node]:
                edge_pairs.add(tuple(sorted((node, nxt))))
                if nxt not in node_to_component:
                    node_to_component[nxt] = component_seed
                    stack.append(nxt)
        components.append(
            {
                "seed_component_id": component_seed,
                "node_count": len(nodes),
                "edge_count": len(edge_pairs),
            }
        )

    components.sort(key=lambda item: (item["node_count"], item["edge_count"]), reverse=True)
    component_rank = {
        component["seed_component_id"]: rank + 1 for rank, component in enumerate(components)
    }
    for row in rows:
        row["component_id"] = component_rank[node_to_component[row["from_node_id"]]]
    return components


def annotate_duplicates(rows: list[dict]) -> dict:
    exact_groups: dict[tuple[int, int, str], list[dict]] = defaultdict(list)
    for row in rows:
        exact_groups[(row["from_node_id"], row["to_node_id"], row["geom"])].append(row)

    removed_exact = 0
    for group in exact_groups.values():
        group.sort(key=lambda item: item["edgeId"])
        canonical = group[0]
        canonical["duplicate_type"] = canonical.get("duplicate_type", "none")
        canonical["keep_in_cleaned"] = True
        canonical["canonical_edge_id"] = canonical["edgeId"]
        for duplicate in group[1:]:
            duplicate["duplicate_type"] = "exact_duplicate"
            duplicate["keep_in_cleaned"] = False
            duplicate["canonical_edge_id"] = canonical["edgeId"]
            removed_exact += 1

    canonical_by_reverse_key: dict[tuple[int, int, str], dict] = {}
    normalized_reverse = 0
    for row in sorted(rows, key=lambda item: item["edgeId"]):
        if row.get("keep_in_cleaned") is False:
            continue

        reversed_coords = list(reversed(row["coords"]))
        reversed_geom = linestring_wkt(reversed_coords)
        direct_key = (row["from_node_id"], row["to_node_id"], row["geom"])
        reverse_key = (row["to_node_id"], row["from_node_id"], reversed_geom)
        canonical_key = min(direct_key, reverse_key)

        existing = canonical_by_reverse_key.get(canonical_key)
        if existing is None:
            canonical_by_reverse_key[canonical_key] = row
            row["keep_in_cleaned"] = True
            row["canonical_edge_id"] = row["edgeId"]
            if "duplicate_type" not in row:
                row["duplicate_type"] = "none"
            continue

        row["duplicate_type"] = "reverse_duplicate"
        row["keep_in_cleaned"] = False
        row["canonical_edge_id"] = existing["edgeId"]
        normalized_reverse += 1

    for row in rows:
        if "duplicate_type" not in row:
            row["duplicate_type"] = "none"
        if "keep_in_cleaned" not in row:
            row["keep_in_cleaned"] = True
        if "canonical_edge_id" not in row:
            row["canonical_edge_id"] = row["edgeId"]

    return {
        "removed_exact_duplicates": removed_exact,
        "normalized_reverse_duplicates": normalized_reverse,
    }


def canonicalize_rows(rows: list[dict]) -> list[dict]:
    cleaned = []
    for row in rows:
        if not row["keep_in_cleaned"]:
            continue
        from_node = row["from_node_id"]
        to_node = row["to_node_id"]
        coords = row["coords"]
        if from_node > to_node:
            from_node, to_node = to_node, from_node
            coords = list(reversed(coords))
        cleaned.append(
            {
                **row,
                "from_node_id": from_node,
                "to_node_id": to_node,
                "coords": coords,
                "geom": linestring_wkt(coords),
            }
        )
    return cleaned


def write_csv(path: Path, rows: list[dict], include_qa: bool) -> None:
    fieldnames = [
        "edgeId",
        "from_node_id",
        "to_node_id",
        "geom",
        "length_meter",
        "avg_slope_percent",
        "width_meter",
        "has_stairs",
        "has_curb_gap",
        "has_elevator",
        "has_crosswalk",
        "has_signal",
        "has_audio_signal",
        "has_braille_block",
        "surface_type",
    ]
    if include_qa:
        fieldnames.extend(
            [
                "component_id",
                "boundary_clipped_candidate",
                "duplicate_type",
                "keep_in_cleaned",
                "canonical_edge_id",
            ]
        )
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload = {key: row.get(key, "") for key in fieldnames}
            writer.writerow(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare QA metadata and cleaned segments for Step 7.")
    parser.add_argument("--segments-csv", required=True, help="Input road_segments_service.csv")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--long-threshold", type=float, default=500.0, help="Long segment threshold in meters")
    parser.add_argument(
        "--bbox-margin",
        type=float,
        default=0.0006,
        help="Boundary detection margin in decimal degrees",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_segments(Path(args.segments_csv))
    bbox = compute_bbox(rows)
    components = assign_component_ids(rows)

    for row in rows:
        row["boundary_clipped_candidate"] = (
            row["length_meter"] >= args.long_threshold
            and near_bbox_edge(row["coords"], bbox, args.bbox_margin)
        )

    duplicate_summary = annotate_duplicates(rows)
    cleaned_rows = canonicalize_rows(rows)
    assign_component_ids(cleaned_rows)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "road_segments_service_qa.csv", rows, include_qa=True)
    write_csv(output_dir / "road_segments_service_cleaned.csv", cleaned_rows, include_qa=True)

    summary = {
        "input_segment_count": len(rows),
        "cleaned_segment_count": len(cleaned_rows),
        "component_count_before_cleaning": len(components),
        "component_count_after_cleaning": len({row["component_id"] for row in cleaned_rows}),
        "boundary_clipped_candidate_count": sum(
            1 for row in rows if row["boundary_clipped_candidate"]
        ),
        "duplicate_type_counts": {
            key: sum(1 for row in rows if row["duplicate_type"] == key)
            for key in sorted({row["duplicate_type"] for row in rows})
        },
        **duplicate_summary,
        "bbox": {
            "min_lon": bbox[0],
            "min_lat": bbox[1],
            "max_lon": bbox[2],
            "max_lat": bbox[3],
        },
    }
    (output_dir / "graphhopper_validation_input_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"input_segment_count={summary['input_segment_count']}")
    print(f"cleaned_segment_count={summary['cleaned_segment_count']}")
    print(f"boundary_clipped_candidate_count={summary['boundary_clipped_candidate_count']}")
    print(f"removed_exact_duplicates={summary['removed_exact_duplicates']}")
    print(f"normalized_reverse_duplicates={summary['normalized_reverse_duplicates']}")
    print(f"output_dir={output_dir}")


if __name__ == "__main__":
    main()
