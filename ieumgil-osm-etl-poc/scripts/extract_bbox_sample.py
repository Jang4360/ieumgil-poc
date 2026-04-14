import argparse
import math
from dataclasses import dataclass, field
from pathlib import Path

import osmium


def km_to_lat_delta(km: float) -> float:
    return km / 111.32


def km_to_lon_delta(km: float, lat: float) -> float:
    return km / (111.32 * math.cos(math.radians(lat)))


@dataclass
class ExtractionState:
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    keep_node_ids: set[int] = field(default_factory=set)
    keep_way_ids: set[int] = field(default_factory=set)
    keep_relation_ids: set[int] = field(default_factory=set)
    node_count: int = 0
    way_count: int = 0
    relation_count: int = 0

    def contains(self, lat: float, lon: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon


class FirstPassHandler(osmium.SimpleHandler):
    def __init__(self, state: ExtractionState):
        super().__init__()
        self.state = state

    def node(self, n):
        if n.location.valid() and self.state.contains(n.location.lat, n.location.lon):
            self.state.keep_node_ids.add(n.id)
            self.state.node_count += 1

    def way(self, w):
        if any(
            n.location.valid() and self.state.contains(n.location.lat, n.location.lon)
            for n in w.nodes
        ):
            self.state.keep_way_ids.add(w.id)
            self.state.way_count += 1
            for n in w.nodes:
                self.state.keep_node_ids.add(n.ref)

    def relation(self, r):
        member_ids = {m.ref for m in r.members}
        if member_ids & (self.state.keep_node_ids | self.state.keep_way_ids):
            self.state.keep_relation_ids.add(r.id)
            self.state.relation_count += 1


class SecondPassHandler(osmium.SimpleHandler):
    def __init__(self, state: ExtractionState, writer: osmium.SimpleWriter):
        super().__init__()
        self.state = state
        self.writer = writer

    def node(self, n):
        if n.id in self.state.keep_node_ids:
            self.writer.add_node(n)

    def way(self, w):
        if w.id in self.state.keep_way_ids:
            self.writer.add_way(w)

    def relation(self, r):
        if r.id in self.state.keep_relation_ids:
            self.writer.add_relation(r)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a reproducible OSM PBF sample from a source PBF using a bbox."
    )
    parser.add_argument("--source", required=True, help="Source .osm.pbf file")
    parser.add_argument("--output", required=True, help="Output .osm.pbf file")
    parser.add_argument("--center-lat", type=float, required=True, help="BBox center latitude")
    parser.add_argument("--center-lon", type=float, required=True, help="BBox center longitude")
    parser.add_argument(
        "--radius-km",
        type=float,
        default=1.0,
        help="Half-size of bbox in km from the center. Default: 1.0",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    source = Path(args.source)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    lat_delta = km_to_lat_delta(args.radius_km)
    lon_delta = km_to_lon_delta(args.radius_km, args.center_lat)

    state = ExtractionState(
        min_lat=args.center_lat - lat_delta,
        min_lon=args.center_lon - lon_delta,
        max_lat=args.center_lat + lat_delta,
        max_lon=args.center_lon + lon_delta,
    )

    first_pass = FirstPassHandler(state)
    first_pass.apply_file(str(source), locations=True)

    header = osmium.io.Header()
    header.set("generator", "ieumgil-osm-etl-poc/extract_bbox_sample.py")
    header.add_box(
        osmium.osm.Box(
            osmium.osm.Location(state.min_lon, state.min_lat),
            osmium.osm.Location(state.max_lon, state.max_lat),
        )
    )

    writer = osmium.SimpleWriter(str(output), header=header, overwrite=True)
    second_pass = SecondPassHandler(state, writer)
    second_pass.apply_file(str(source), locations=False)
    writer.close()

    print(f"source={source}")
    print(f"output={output}")
    print(f"center_lat={args.center_lat}")
    print(f"center_lon={args.center_lon}")
    print(f"radius_km={args.radius_km}")
    print(
        "bbox="
        f"{state.min_lon:.7f},{state.min_lat:.7f},{state.max_lon:.7f},{state.max_lat:.7f}"
    )
    print(f"kept_nodes={len(state.keep_node_ids)}")
    print(f"kept_ways={len(state.keep_way_ids)}")
    print(f"kept_relations={len(state.keep_relation_ids)}")


if __name__ == "__main__":
    main()
