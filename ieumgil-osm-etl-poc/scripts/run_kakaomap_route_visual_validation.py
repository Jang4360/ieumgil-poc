import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DETAILS = [
    "crossing",
    "surface",
    "has_curb_gap",
    "has_elevator",
    "has_audio_signal",
    "has_braille_block",
    "width_meter",
]

SCENARIOS = [
    {
        "name": "visual_crossing_compare",
        "family": "visual",
        "start": {"lat": 35.1497707, "lng": 129.0656452},
        "end": {"lat": 35.1578066, "lng": 129.0510036},
    },
    {
        "name": "wheelchair_stairs_compare",
        "family": "wheelchair",
        "start": {"lat": 35.1517986, "lng": 129.0665998},
        "end": {"lat": 35.1618369, "lng": 129.0700577},
    },
    {
        "name": "snapped_offset_demo",
        "family": "visual",
        "start": {"lat": 35.1581373, "lng": 129.0486875},
        "end": {"lat": 35.1558845, "lng": 129.0709771},
    },
]


def http_json(url: str, origin: str | None = None) -> tuple[dict, dict]:
    request = Request(url)
    if origin:
        request.add_header("Origin", origin)
    try:
        with urlopen(request) as response:
            body = response.read().decode("utf-8")
            headers = dict(response.headers.items())
            return json.loads(body), headers
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"message": body}
        payload["__http_error__"] = True
        payload["status_code"] = exc.code
        return payload, dict(exc.headers.items())


def route_request(base_url: str, profile: str, start: dict, end: dict) -> tuple[dict, dict]:
    params = [
        ("profile", profile),
        ("point", f"{start['lat']},{start['lng']}"),
        ("point", f"{end['lat']},{end['lng']}"),
        ("points_encoded", "false"),
        ("instructions", "true"),
        ("calc_points", "true"),
    ]
    for detail in DETAILS:
        params.append(("details", detail))
    return http_json(f"{base_url.rstrip('/')}/route?{urlencode(params)}")


def info_request(base_url: str) -> tuple[dict, dict]:
    return http_json(f"{base_url.rstrip('/')}/info")


def cors_probe(base_url: str, origin: str) -> tuple[bool, str | None]:
    _, headers = http_json(f"{base_url.rstrip('/')}/info", origin=origin)
    allowed_origin = headers.get("Access-Control-Allow-Origin")
    return bool(allowed_origin), allowed_origin


def profile_summary(profile: str, payload: dict) -> dict:
    paths = payload.get("paths", [])
    if not paths:
        return {
            "profile": profile,
            "success": False,
            "message": payload.get("message"),
        }
    path = paths[0]
    details = path.get("details", {})
    snapped = path.get("snapped_waypoints", {}).get("coordinates", [])
    return {
        "profile": profile,
        "success": True,
        "distanceMeter": path.get("distance"),
        "estimatedTimeMinute": round(path.get("time", 0) / 60000, 2),
        "pointCount": len(path.get("points", {}).get("coordinates", [])),
        "instructionCount": len(path.get("instructions", [])),
        "snappedWaypointCount": len(snapped),
        "detailKeys": sorted(details.keys()),
        "detailRangeCounts": {key: len(value) for key, value in details.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step 13 KakaoMap route visual validation support checks.")
    parser.add_argument("--base-url", required=True, help="GraphHopper base URL")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    info_payload, info_headers = info_request(args.base_url)
    cors_enabled, allowed_origin = cors_probe(args.base_url, origin="http://localhost:8080")

    (output_dir / "graphhopper_info.json").write_text(
        json.dumps(info_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "baseUrl": args.base_url,
        "corsProbe": {
            "origin": "http://localhost:8080",
            "corsEnabled": cors_enabled,
            "accessControlAllowOrigin": allowed_origin,
            "infoResponseHeaderCount": len(info_headers),
        },
        "profiles": [profile["name"] for profile in info_payload.get("profiles", [])],
        "scenarios": [],
    }

    for scenario in SCENARIOS:
        scenario_payload = {
            "name": scenario["name"],
            "family": scenario["family"],
            "start": scenario["start"],
            "end": scenario["end"],
            "results": [],
        }
        profiles = [f"{scenario['family']}_shortest", f"{scenario['family']}_safe"]
        for profile in profiles:
            response, _ = route_request(args.base_url, profile, scenario["start"], scenario["end"])
            (output_dir / f"{scenario['name']}__{profile}.json").write_text(
                json.dumps(response, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            scenario_payload["results"].append(profile_summary(profile, response))

        shortest = next((row for row in scenario_payload["results"] if row["profile"].endswith("_shortest")), None)
        safe = next((row for row in scenario_payload["results"] if row["profile"].endswith("_safe")), None)
        if shortest and safe and shortest["success"] and safe["success"]:
            scenario_payload["comparison"] = {
                "distanceDeltaMeter": round(safe["distanceMeter"] - shortest["distanceMeter"], 3),
                "timeDeltaMinute": round(safe["estimatedTimeMinute"] - shortest["estimatedTimeMinute"], 2),
                "detailKeysShared": sorted(set(shortest["detailKeys"]) & set(safe["detailKeys"])),
            }
        summary["scenarios"].append(scenario_payload)

    (output_dir / "kakaomap_visual_validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"scenario_count={len(summary['scenarios'])}")
    print(f"cors_enabled={summary['corsProbe']['corsEnabled']}")
    print(f"output_dir={output_dir}")


if __name__ == "__main__":
    main()
