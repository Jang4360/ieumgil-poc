import argparse
import csv
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import osmium
import psycopg
from matplotlib.path import Path as MplPath


DIRECT_WALK_HIGHWAYS = {"footway", "pedestrian", "path", "steps", "living_street"}
CONDITIONAL_ROAD_HIGHWAYS = {
    "residential",
    "unclassified",
    "tertiary",
    "tertiary_link",
    "secondary",
    "secondary_link",
    "primary",
    "service",
}
EXCLUDED_MAJOR_HIGHWAYS = {"trunk", "trunk_link", "primary_link"}
ALLOWED_FOOT_VALUES = {"yes", "designated", "permissive"}
ALLOWED_SIDEWALK_VALUES = {"both", "left", "right", "separate"}
EXCLUDED_SERVICE_VALUES = {"parking_aisle", "driveway"}
SURFACE_BLOCK = {"paving_stones", "cobblestone", "sett"}
SURFACE_CONCRETE = {"concrete", "concrete:lanes", "concrete:plates"}
SURFACE_GRAVEL = {"gravel", "fine_gravel", "pebblestone"}
SURFACE_UNPAVED = {"unpaved", "ground", "earth", "dirt", "grass", "sand"}
SURFACE_ASPHALT = {"asphalt", "paved"}


@dataclass
class EligibleWay:
    way_id: int
    refs: list[int]
    coords: list[tuple[float, float]]
    tags: dict[str, str]
    rule_bucket: str


@dataclass
class BoundaryArea:
    polygons: list[list[list[tuple[float, float]]]]
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    name: str | None = None
    polygon_paths: list[tuple[MplPath, list[MplPath]]] | None = None

    @classmethod
    def from_geojson(cls, geojson_path: Path) -> "BoundaryArea":
        payload = json.loads(geojson_path.read_text(encoding="utf-8"))
        geometry = payload.get("geometry", payload)
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates", [])

        if geometry_type == "Polygon":
            polygons = [cls._normalize_polygon(coordinates)]
        elif geometry_type == "MultiPolygon":
            polygons = [cls._normalize_polygon(polygon) for polygon in coordinates]
        else:
            raise ValueError(f"Unsupported geometry type: {geometry_type}")

        lats = [lat for polygon in polygons for ring in polygon for _, lat in ring]
        lons = [lon for polygon in polygons for ring in polygon for lon, _ in ring]
        properties = payload.get("properties", {})
        return cls(
            polygons=polygons,
            min_lat=min(lats),
            min_lon=min(lons),
            max_lat=max(lats),
            max_lon=max(lons),
            name=properties.get("display_name") or properties.get("name"),
            polygon_paths=[
                (MplPath(polygon[0]), [MplPath(hole) for hole in polygon[1:]]) for polygon in polygons
            ],
        )

    @staticmethod
    def _normalize_polygon(raw_polygon: list[list[list[float]]]) -> list[list[tuple[float, float]]]:
        return [[(float(lon), float(lat)) for lon, lat in ring] for ring in raw_polygon]

    def contains(self, lat: float, lon: float) -> bool:
        if not (self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon):
            return False
        for polygon, (outer_path, hole_paths) in zip(self.polygons, self.polygon_paths or []):
            if outer_path.contains_point((lon, lat), radius=1e-12) and not any(
                hole_path.contains_point((lon, lat), radius=1e-12) for hole_path in hole_paths
            ):
                return True
        return False


def haversine_meter(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    sin_dlat = math.sin(dlat / 2)
    sin_dlon = math.sin(dlon / 2)
    aa = sin_dlat**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * sin_dlon**2
    return 2 * r * math.atan2(math.sqrt(aa), math.sqrt(1 - aa))


def point_on_segment(x: float, y: float, ax: float, ay: float, bx: float, by: float) -> bool:
    cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
    if abs(cross) > 1e-12:
        return False
    dot = (x - ax) * (bx - ax) + (y - ay) * (by - ay)
    if dot < 0:
        return False
    squared_length = (bx - ax) ** 2 + (by - ay) ** 2
    return dot <= squared_length


def parse_numeric(value: str | None) -> float | None:
    if not value:
        return None
    token = value.split()[0].replace("m", "")
    try:
        return float(token)
    except ValueError:
        return None


def map_surface_type(surface: str | None) -> str:
    if not surface:
        return "UNKNOWN"
    value = surface.lower()
    if value in SURFACE_ASPHALT:
        return "ASPHALT"
    if value in SURFACE_BLOCK:
        return "BLOCK"
    if value in SURFACE_CONCRETE:
        return "CONCRETE"
    if value in SURFACE_GRAVEL:
        return "GRAVEL"
    if value in SURFACE_UNPAVED:
        return "UNPAVED"
    return "UNKNOWN"


def classify_way(tags: dict[str, str]) -> str | None:
    highway = tags.get("highway")
    foot = tags.get("foot")
    sidewalk = tags.get("sidewalk")
    access = tags.get("access")
    service = tags.get("service")
    area = tags.get("area")

    if area == "yes":
        return None
    if foot == "no" or access == "no":
        return None

    if highway in DIRECT_WALK_HIGHWAYS:
        return "direct"
    if highway == "cycleway":
        return "direct" if foot in ALLOWED_FOOT_VALUES else None
    if service in EXCLUDED_SERVICE_VALUES:
        return None
    if sidewalk in ALLOWED_SIDEWALK_VALUES or foot in ALLOWED_FOOT_VALUES:
        return "direct"
    if highway in EXCLUDED_MAJOR_HIGHWAYS:
        return None
    if highway in CONDITIONAL_ROAD_HIGHWAYS:
        return "conditional"
    return None


class NetworkBuilder(osmium.SimpleHandler):
    def __init__(self, boundary_area: BoundaryArea | None = None):
        super().__init__()
        self.eligible_ways: list[EligibleWay] = []
        self.boundary_area = boundary_area

    def way(self, w):
        tags = dict(w.tags)
        rule_bucket = classify_way(tags)
        if not rule_bucket:
            return

        refs: list[int] = []
        coords: list[tuple[float, float]] = []
        for node in w.nodes:
            if not node.location.valid():
                return
            refs.append(node.ref)
            coords.append((node.location.lat, node.location.lon))

        if len(refs) < 2:
            return

        if self.boundary_area and not any(
            self.boundary_area.contains(lat, lon) for lat, lon in coords
        ):
            return

        self.eligible_ways.append(
            EligibleWay(
                way_id=w.id,
                refs=refs,
                coords=coords,
                tags=tags,
                rule_bucket=rule_bucket,
            )
        )


def point_wkt(coord: tuple[float, float]) -> str:
    lat, lon = coord
    return f"POINT ({lon:.7f} {lat:.7f})"


def linestring_wkt(coords: list[tuple[float, float]]) -> str:
    parts = [f"{lon:.7f} {lat:.7f}" for lat, lon in coords]
    return "LINESTRING (" + ", ".join(parts) + ")"


def build_network(
    ways: list[EligibleWay], boundary_area: BoundaryArea | None = None
) -> tuple[list[dict], list[dict]]:
    node_ref_counts: Counter[int] = Counter()
    all_node_coords: dict[int, tuple[float, float]] = {}
    for way in ways:
        node_ref_counts.update(way.refs)
        for ref, coord in zip(way.refs, way.coords):
            all_node_coords[ref] = coord

    anchor_nodes: set[int] = set()
    for way in ways:
        anchor_nodes.add(way.refs[0])
        anchor_nodes.add(way.refs[-1])
        for ref in way.refs:
            if node_ref_counts[ref] > 1:
                anchor_nodes.add(ref)

    segments_raw: list[dict] = []
    for way in ways:
        anchor_indices = [idx for idx, ref in enumerate(way.refs) if ref in anchor_nodes]
        if len(anchor_indices) < 2:
            anchor_indices = [0, len(way.refs) - 1]
        if len(anchor_indices) == 2 and way.refs[0] == way.refs[-1] and len(way.refs) > 3:
            anchor_indices.insert(1, (len(way.refs) - 1) // 2)
        anchor_indices = sorted(set(anchor_indices))

        part = 1
        for start_idx, end_idx in zip(anchor_indices, anchor_indices[1:]):
            if end_idx <= start_idx:
                continue
            refs = way.refs[start_idx : end_idx + 1]
            coords = way.coords[start_idx : end_idx + 1]
            if len(refs) < 2:
                continue
            if refs[0] == refs[-1]:
                continue
            if boundary_area and not any(boundary_area.contains(lat, lon) for lat, lon in coords):
                continue
            length_meter = round(
                sum(haversine_meter(coords[i], coords[i + 1]) for i in range(len(coords) - 1)), 2
            )
            segments_raw.append(
                {
                    "source_way_id": way.way_id,
                    "part": part,
                    "from_osm_node_id": refs[0],
                    "to_osm_node_id": refs[-1],
                    "coords": coords,
                    "tags": way.tags,
                    "rule_bucket": way.rule_bucket,
                    "length_meter": length_meter,
                }
            )
            part += 1

    used_osm_nodes = {s["from_osm_node_id"] for s in segments_raw} | {s["to_osm_node_id"] for s in segments_raw}
    vertex_id_by_osm_node = {osm_node_id: idx for idx, osm_node_id in enumerate(sorted(used_osm_nodes), start=1)}

    road_nodes = []
    for osm_node_id, vertex_id in vertex_id_by_osm_node.items():
        coord = all_node_coords[osm_node_id]
        road_nodes.append(
            {
                "vertexId": vertex_id,
                "osm_node_id": osm_node_id,
                "point_wkt": point_wkt(coord),
                "lat": coord[0],
                "lon": coord[1],
            }
        )

    road_segments = []
    for edge_id, segment in enumerate(segments_raw, start=1):
        tags = segment["tags"]
        surface_type = map_surface_type(tags.get("surface"))
        from_vertex_id = vertex_id_by_osm_node[segment["from_osm_node_id"]]
        to_vertex_id = vertex_id_by_osm_node[segment["to_osm_node_id"]]
        # The service ERD defines road_segments.vertexId as an extra FK, but its
        # semantics are not clear beyond from/to node references. Keep the load
        # reproducible by pinning it to from_node_id for validation purposes.
        road_segments.append(
            {
                "edgeId": edge_id,
                "from_node_id": from_vertex_id,
                "to_node_id": to_vertex_id,
                "geom_wkt": linestring_wkt(segment["coords"]),
                "length_meter": segment["length_meter"],
                "avg_slope_percent": None,
                "width_meter": parse_numeric(tags.get("width")),
                "has_stairs": tags.get("highway") == "steps",
                "has_curb_gap": False,
                "has_elevator": tags.get("elevator") == "yes" or tags.get("highway") == "elevator",
                "has_crosswalk": "crossing" in tags,
                "has_signal": tags.get("crossing") == "traffic_signals" or tags.get("traffic_signals") == "yes",
                "has_audio_signal": False,
                "has_braille_block": tags.get("tactile_paving") in {"yes", "contrasted"},
                "surface_type": surface_type,
                "vertexId": from_vertex_id,
                "source_way_id": segment["source_way_id"],
                "rule_bucket": segment["rule_bucket"],
                "source_osm_from_node_id": segment["from_osm_node_id"],
                "source_osm_to_node_id": segment["to_osm_node_id"],
            }
        )

    return road_nodes, road_segments


def write_outputs(road_nodes: list[dict], road_segments: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    road_nodes_csv = output_dir / "road_nodes_service.csv"
    with road_nodes_csv.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["vertexId", "osm_node_id", "point"])
        for row in road_nodes:
            writer.writerow([row["vertexId"], row["osm_node_id"], row["point_wkt"]])

    road_segments_csv = output_dir / "road_segments_service.csv"
    with road_segments_csv.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(
            [
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
                "vertexId",
            ]
        )
        for row in road_segments:
            writer.writerow(
                [
                    row["edgeId"],
                    row["from_node_id"],
                    row["to_node_id"],
                    row["geom_wkt"],
                    row["length_meter"],
                    row["avg_slope_percent"],
                    row["width_meter"],
                    row["has_stairs"],
                    row["has_curb_gap"],
                    row["has_elevator"],
                    row["has_crosswalk"],
                    row["has_signal"],
                    row["has_audio_signal"],
                    row["has_braille_block"],
                    row["surface_type"],
                    row["vertexId"],
                ]
            )

    mapping_json = output_dir / "road_network_mapping_debug.json"
    mapping_payload = {
        "road_nodes": road_nodes[:20],
        "road_segments": [
            {
                key: row[key]
                for key in [
                    "edgeId",
                    "source_way_id",
                    "source_osm_from_node_id",
                    "source_osm_to_node_id",
                    "from_node_id",
                    "to_node_id",
                    "rule_bucket",
                    "surface_type",
                    "length_meter",
                    "vertexId",
                ]
            }
            for row in road_segments[:50]
        ],
    }
    mapping_json.write_text(json.dumps(mapping_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_schema(conn: psycopg.Connection, schema_sql_path: Path) -> None:
    conn.execute(schema_sql_path.read_text(encoding="utf-8"))


def insert_into_postgres(
    road_nodes: list[dict],
    road_segments: list[dict],
    dsn: str,
    schema_sql_path: Path,
) -> tuple[int, int]:
    with psycopg.connect(dsn) as conn:
        load_schema(conn, schema_sql_path)
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO poc_service_mapping.road_nodes ("vertexId", osm_node_id, point)
                VALUES (%s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))
                """,
                [(row["vertexId"], row["osm_node_id"], row["point_wkt"]) for row in road_nodes],
            )
            cur.executemany(
                """
                INSERT INTO poc_service_mapping.road_segments (
                    "edgeId", from_node_id, to_node_id, geom, length_meter,
                    avg_slope_percent, width_meter, has_stairs, has_curb_gap,
                    has_elevator, has_crosswalk, has_signal, has_audio_signal,
                    has_braille_block, surface_type, "vertexId"
                ) VALUES (
                    %s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326), %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s::poc_service_mapping.surface_type_enum, %s
                )
                """,
                [
                    (
                        row["edgeId"],
                        row["from_node_id"],
                        row["to_node_id"],
                        row["geom_wkt"],
                        row["length_meter"],
                        row["avg_slope_percent"],
                        row["width_meter"],
                        row["has_stairs"],
                        row["has_curb_gap"],
                        row["has_elevator"],
                        row["has_crosswalk"],
                        row["has_signal"],
                        row["has_audio_signal"],
                        row["has_braille_block"],
                        row["surface_type"],
                        row["vertexId"],
                    )
                    for row in road_segments
                ],
            )
            cur.execute('SELECT COUNT(*) FROM poc_service_mapping.road_nodes')
            node_count = cur.fetchone()[0]
            cur.execute('SELECT COUNT(*) FROM poc_service_mapping.road_segments')
            segment_count = cur.fetchone()[0]
        conn.commit()
    return node_count, segment_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build road network mapped to the service ERD tables.")
    parser.add_argument("--source", required=True, help="Input sample .osm.pbf")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument(
        "--boundary-geojson",
        help="Optional GeoJSON Polygon/MultiPolygon used to keep only ways intersecting the boundary",
    )
    parser.add_argument(
        "--dsn",
        default="postgresql://ieumgil:ieumgil@localhost:5432/ieumgil",
        help="PostgreSQL DSN",
    )
    parser.add_argument(
        "--schema-sql",
        default=str(Path(__file__).resolve().parents[1] / "sql" / "poc_service_road_network.sql"),
        help="SQL schema path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    output_dir = Path(args.output_dir)
    schema_sql_path = Path(args.schema_sql)
    boundary_area = BoundaryArea.from_geojson(Path(args.boundary_geojson)) if args.boundary_geojson else None

    builder = NetworkBuilder(boundary_area=boundary_area)
    builder.apply_file(str(source), locations=True)

    road_nodes, road_segments = build_network(builder.eligible_ways, boundary_area=boundary_area)
    write_outputs(road_nodes, road_segments, output_dir)
    db_node_count, db_segment_count = insert_into_postgres(
        road_nodes, road_segments, args.dsn, schema_sql_path
    )

    way_rule_counts = Counter(way.rule_bucket for way in builder.eligible_ways)
    segment_rule_counts = Counter(row["rule_bucket"] for row in road_segments)

    print(f"source={source}")
    if args.boundary_geojson:
        print(f"boundary_geojson={args.boundary_geojson}")
        print(f"boundary_name={boundary_area.name or 'unknown'}")
    print(f"eligible_ways={len(builder.eligible_ways)}")
    print(f"way_rule_direct={way_rule_counts.get('direct', 0)}")
    print(f"way_rule_conditional={way_rule_counts.get('conditional', 0)}")
    print(f"road_nodes={len(road_nodes)}")
    print(f"road_segments={len(road_segments)}")
    print(f"segment_rule_direct={segment_rule_counts.get('direct', 0)}")
    print(f"segment_rule_conditional={segment_rule_counts.get('conditional', 0)}")
    print(f"db_road_nodes={db_node_count}")
    print(f"db_road_segments={db_segment_count}")
    print(f"output_dir={output_dir}")


if __name__ == "__main__":
    main()
