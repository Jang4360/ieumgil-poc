#!/usr/bin/env python3
"""Run reproducible smoke tests for the transit APIs selected in Step 1."""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"


class SmokeTestError(RuntimeError):
    pass


@dataclass
class TestResult:
    name: str
    ok: bool
    summary: dict[str, Any]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        raise SmokeTestError(f"env file not found: {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env


def require(env: dict[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise SmokeTestError(f"missing required env var: {key}")
    return value


def http_get_json(url: str, params: dict[str, Any]) -> Any:
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    request = urllib.request.Request(f"{url}?{query}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def http_get_text(url: str, params: dict[str, Any]) -> str:
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    request = urllib.request.Request(f"{url}?{query}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def first_child_text(parent: ET.Element, tag: str) -> str | None:
    child = parent.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def test_odsay(env: dict[str, str]) -> TestResult:
    base_url = require(env, "ODSAY_API_BASE_URL")
    api_key = require(env, "ODSAY_API_KEY")

    station = http_get_json(
        f"{base_url}/searchStation",
        {
            "stationName": "서면",
            "apiKey": api_key,
        },
    )
    station_count = int(station["result"]["totalCount"])
    if station_count < 1:
        raise SmokeTestError("ODsay station search returned no stations")

    first_station = next(
        (item for item in station["result"]["station"] if item.get("CID") == 7000),
        station["result"]["station"][0],
    )

    route = http_get_json(
        f"{base_url}/searchPubTransPathT",
        {
            "SX": "129.0591028",
            "SY": "35.1577084",
            "EX": "129.0756416",
            "EY": "35.1795543",
            "apiKey": api_key,
        },
    )
    first_path = route["result"]["path"][0]["info"]
    return TestResult(
        name="ODsay",
        ok=True,
        summary={
            "stationCount": station_count,
            "firstStation": first_station["stationName"],
            "firstStationCityCode": first_station.get("CID"),
            "totalTime": first_path.get("totalTime"),
            "payment": first_path.get("payment"),
            "busTransitCount": first_path.get("busTransitCount"),
            "subwayTransitCount": first_path.get("subwayTransitCount"),
        },
    )


def test_bims(env: dict[str, str]) -> TestResult:
    base_url = require(env, "BUSAN_BIMS_API_BASE_URL")
    service_key = require(env, "BUSAN_BIMS_SERVICE_KEY_DECODING")

    bus_stop_xml = http_get_text(
        f"{base_url}/busStopList",
        {
            "pageNo": 1,
            "numOfRows": 3,
            "bstopnm": "부산시청",
            "serviceKey": service_key,
        },
    )
    bus_stop_root = ET.fromstring(bus_stop_xml)
    result_code = bus_stop_root.findtext(".//resultCode")
    if result_code != "00":
        raise SmokeTestError(f"BIMS busStopList failed: resultCode={result_code}")

    first_item = bus_stop_root.find(".//item")
    if first_item is None:
        raise SmokeTestError("BIMS busStopList returned no items")

    bstopid = first_child_text(first_item, "bstopid")
    arsno = first_child_text(first_item, "arsno")
    stop_name = first_child_text(first_item, "bstopnm")
    gps_x = first_child_text(first_item, "gpsx")
    gps_y = first_child_text(first_item, "gpsy")
    if not bstopid:
        raise SmokeTestError("BIMS busStopList missing bstopid")

    arrival_xml = http_get_text(
        f"{base_url}/stopArrByBstopid",
        {
            "bstopid": bstopid,
            "pageNo": 1,
            "numOfRows": 3,
            "serviceKey": service_key,
        },
    )
    arrival_root = ET.fromstring(arrival_xml)
    arrival_code = arrival_root.findtext(".//resultCode")
    if arrival_code != "00":
        raise SmokeTestError(f"BIMS stopArrByBstopid failed: resultCode={arrival_code}")

    first_arrival = arrival_root.find(".//item")
    if first_arrival is None:
        raise SmokeTestError("BIMS stopArrByBstopid returned no items")

    return TestResult(
        name="Busan BIMS",
        ok=True,
        summary={
            "bstopid": bstopid,
            "arsno": arsno,
            "stopName": stop_name,
            "gps": {"x": gps_x, "y": gps_y},
            "lineNo": first_child_text(first_arrival, "lineno"),
            "lineId": first_child_text(first_arrival, "lineid"),
            "min1": first_child_text(first_arrival, "min1"),
            "station1": first_child_text(first_arrival, "station1"),
            "lowplate1": first_child_text(first_arrival, "lowplate1"),
        },
    )


def test_subway_operation(env: dict[str, str]) -> TestResult:
    base_url = require(env, "BUSAN_SUBWAY_OPERATION_API_BASE_URL")
    api_path = require(env, "BUSAN_SUBWAY_OPERATION_API_PATH")
    service_key = require(env, "BUSAN_SUBWAY_OPERATION_SERVICE_KEY_DECODING")

    payload = http_get_json(
        f"{base_url}{api_path}",
        {
            "page": 1,
            "perPage": 1,
            "returnType": "JSON",
            "serviceKey": service_key,
        },
    )
    if int(payload["currentCount"]) < 1:
        raise SmokeTestError("Subway operation API returned no data")

    first = payload["data"][0]
    return TestResult(
        name="Busan Subway Operation",
        ok=True,
        summary={
            "routeName": first.get("노선명"),
            "routeNo": first.get("노선번호"),
            "startStation": first.get("운행구간기점명"),
            "endStation": first.get("운행구간종점명"),
            "arrivalTimesSample": str(first.get("정거장도착시각", ""))[:60],
            "departureTimesSample": str(first.get("정거장출발시각", ""))[:60],
            "speed": first.get("운행속도"),
            "dataDate": first.get("데이터기준일자"),
            "totalCount": payload.get("totalCount"),
        },
    )


def main() -> int:
    env = load_env(ENV_PATH)
    results: list[TestResult] = []
    failures: list[dict[str, str]] = []

    for test_func in (test_odsay, test_bims, test_subway_operation):
        try:
            results.append(test_func(env))
        except Exception as exc:  # noqa: BLE001 - smoke test should always summarize failures.
            failures.append(
                {
                    "name": test_func.__name__,
                    "error": str(exc),
                }
            )

    output = {
        "results": [result.__dict__ for result in results],
        "failures": failures,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
