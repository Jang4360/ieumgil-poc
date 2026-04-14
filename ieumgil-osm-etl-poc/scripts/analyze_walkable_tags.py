import argparse
from collections import Counter
from pathlib import Path

import osmium


INTERESTING_HIGHWAYS = {
    "footway",
    "pedestrian",
    "path",
    "steps",
    "cycleway",
    "living_street",
    "residential",
    "service",
    "unclassified",
    "tertiary",
    "tertiary_link",
    "secondary",
    "secondary_link",
    "primary",
    "primary_link",
    "trunk",
    "trunk_link",
}


class WalkableTagAnalyzer(osmium.SimpleHandler):
    def __init__(self, sample_limit: int):
        super().__init__()
        self.sample_limit = sample_limit
        self.highway = Counter()
        self.foot = Counter()
        self.sidewalk = Counter()
        self.access = Counter()
        self.crossing = Counter()
        self.samples: list[tuple[int, dict[str, str]]] = []

    def way(self, w):
        tags = dict(w.tags)
        highway = tags.get("highway")

        if highway:
            self.highway[highway] += 1
        if "foot" in tags:
            self.foot[tags["foot"]] += 1
        if "sidewalk" in tags:
            self.sidewalk[tags["sidewalk"]] += 1
        if "access" in tags:
            self.access[tags["access"]] += 1
        if "crossing" in tags:
            self.crossing[tags["crossing"]] += 1

        if len(self.samples) >= self.sample_limit:
            return

        interesting = (
            highway in INTERESTING_HIGHWAYS
            or "foot" in tags
            or "sidewalk" in tags
            or "access" in tags
            or "crossing" in tags
        )
        if interesting:
            keep = {
                key: tags[key]
                for key in [
                    "name",
                    "highway",
                    "foot",
                    "sidewalk",
                    "crossing",
                    "access",
                    "service",
                    "surface",
                ]
                if key in tags
            }
            self.samples.append((w.id, keep))


def print_counter(title: str, counter: Counter, topn: int) -> None:
    print(title)
    for key, value in counter.most_common(topn):
        print(f"  {key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze walkable-tag candidates in an OSM PBF file.")
    parser.add_argument("--source", required=True, help="Input .osm.pbf path")
    parser.add_argument("--topn", type=int, default=20, help="Top N values to print per tag group")
    parser.add_argument("--sample-limit", type=int, default=40, help="Number of sample ways to print")
    args = parser.parse_args()

    source = Path(args.source)
    analyzer = WalkableTagAnalyzer(sample_limit=args.sample_limit)
    analyzer.apply_file(str(source), locations=False)

    print(f"source={source}")
    print_counter("HIGHWAY", analyzer.highway, args.topn)
    print_counter("FOOT", analyzer.foot, args.topn)
    print_counter("SIDEWALK", analyzer.sidewalk, args.topn)
    print_counter("ACCESS", analyzer.access, args.topn)
    print_counter("CROSSING", analyzer.crossing, args.topn)
    print("SAMPLES")
    for way_id, tags in analyzer.samples:
        print(f"  way_id={way_id} tags={tags}")


if __name__ == "__main__":
    main()
