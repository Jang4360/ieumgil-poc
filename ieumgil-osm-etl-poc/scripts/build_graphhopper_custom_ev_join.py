#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROAD_SEGMENTS_CSV = ROOT / "ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km/road_segments.csv"
SERVICE_SEGMENTS_CSV = ROOT / "ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/road_segments_service.csv"
OUTPUT_CSV = ROOT / "ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/graphhopper_custom_ev_join.csv"


def parse_linestring(wkt: str) -> tuple[tuple[float, float], ...]:
    body = wkt.strip()
    if not body.startswith("LINESTRING"):
        raise ValueError(f"unsupported geometry: {wkt[:40]}")
    body = body[len("LINESTRING") :].strip()[1:-1]
    coords = []
    for part in body.split(","):
        x_str, y_str = part.strip().split()[:2]
        coords.append((round(float(x_str), 7), round(float(y_str), 7)))
    return tuple(coords)


def normalize_coords(coords: tuple[tuple[float, float], ...]) -> tuple[tuple[float, float], ...]:
    reverse = tuple(reversed(coords))
    return min(coords, reverse)


def parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"true", "1", "yes"}


def parse_nullable(raw: str) -> str:
    value = raw.strip()
    return value if value else ""


def load_service_rows() -> dict[tuple[tuple[float, float], ...], list[dict[str, str]]]:
    grouped: dict[tuple[tuple[float, float], ...], list[dict[str, str]]] = {}
    with SERVICE_SEGMENTS_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = normalize_coords(parse_linestring(row["geom"]))
            grouped.setdefault(key, []).append(row)
    return grouped


def main() -> None:
    service_rows = load_service_rows()
    unmatched = []
    written = 0

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with ROAD_SEGMENTS_CSV.open(newline="", encoding="utf-8") as road_handle, OUTPUT_CSV.open(
        "w", newline="", encoding="utf-8"
    ) as out_handle:
        reader = csv.DictReader(road_handle)
        writer = csv.DictWriter(
            out_handle,
            fieldnames=[
                "source_way_id",
                "segment_ordinal",
                "source_osm_from_node_id",
                "source_osm_to_node_id",
                "has_curb_gap",
                "has_audio_signal",
                "width_meter",
            ],
        )
        writer.writeheader()

        for road_row in reader:
            key = normalize_coords(parse_linestring(road_row["geom_wkt"]))
            candidates = service_rows.get(key)
            if not candidates:
                unmatched.append(road_row["segment_id"])
                continue
            service_row = candidates.pop(0)
            if not candidates:
                service_rows.pop(key, None)

            writer.writerow(
                {
                    "source_way_id": road_row["source_way_id"],
                    "segment_ordinal": road_row["segment_id"].rsplit("_", 1)[1],
                    "source_osm_from_node_id": road_row["from_node_id"],
                    "source_osm_to_node_id": road_row["to_node_id"],
                    "has_curb_gap": str(parse_bool(service_row["has_curb_gap"])).lower(),
                    "has_audio_signal": str(parse_bool(service_row["has_audio_signal"])).lower(),
                    "width_meter": parse_nullable(service_row["width_meter"]),
                }
            )
            written += 1

    remaining_service = sum(len(rows) for rows in service_rows.values())
    print(f"written_rows={written}")
    print(f"unmatched_road_rows={len(unmatched)}")
    print(f"remaining_service_rows={remaining_service}")
    if unmatched or remaining_service:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
