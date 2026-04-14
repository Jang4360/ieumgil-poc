# Step 7 GraphHopper Route Validation Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/07_GRAPHHOPPER_ROUTE_VALIDATION.md`
- 입력 파일: `ieumgil-osm-etl-poc/data/raw/busan.osm.pbf`
- 작업 일자: 2026-04-14

## 목적

GraphHopper에 부산 OSM 원본을 실제로 import하고, 기본 `foot` profile로 경로 응답이 반환되는지 검증한다.

이번 단계에서는 Step 6 품질 이슈를 그대로 넘기지 않기 위해, GraphHopper 실행 전에 샘플 `road_segments` QA 메타와 정제본도 함께 만들었다. 단, GraphHopper 자체는 정제 CSV가 아니라 원본 OSM을 import한다.

## 반영 내용

추가한 파일:

- `docs/plans/graphhopper/07_GRAPHHOPPER_ROUTE_VALIDATION.md`
- `infra/graphhopper/config-foot.yml`
- `ieumgil-osm-etl-poc/scripts/prepare_graphhopper_validation_inputs.py`
- `ieumgil-osm-etl-poc/scripts/run_graphhopper_route_validation.py`

생성 산출물:

- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/road_segments_service_qa.csv`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/road_segments_service_cleaned.csv`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/graphhopper_validation_input_summary.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/routes/graphhopper_info.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/routes/graphhopper_route_validation_summary.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/routes/*.json`
- `ieumgil-osm-etl-poc/data/graphhopper/busan/*`

## QA 메타 및 정제 결과

샘플 `road_segments`에 아래 QA 메타를 부착했다.

- `component_id`
- `boundary_clipped_candidate`
- `duplicate_type`
- `keep_in_cleaned`
- `canonical_edge_id`

정제 규칙:

- 동일 `from_node_id`, `to_node_id`, 동일 `geom`은 exact duplicate로 보고 제거
- 역방향 duplicate는 canonical orientation으로 정규화하고 1건만 유지

결과:

- 입력 세그먼트: `2,190`
- 정제 후 세그먼트: `2,188`
- `boundary_clipped_candidate`: `5`
- 제거된 exact duplicate: `1`
- 정규화된 reverse duplicate: `1`
- 연결 컴포넌트 수: 정제 전 `17`, 정제 후 `17`

즉, Step 6에서 잡았던 중복 이슈는 최소 수준으로 정리됐고, 경계 영향 장거리 후보는 별도 메타로 분리됐다.

## GraphHopper 실행 결과

### 1. `foot` profile import 성공

- GraphHopper 버전: `11.0`
- profile: `foot`
- elevation: `false`
- import 대상: `busan.osm.pbf`
- import 시작: `2026-04-14 07:30:12`
- 서버 ready: `2026-04-14 07:30:16`

로그 기준으로 import와 서버 기동까지 약 `5초` 내에 완료됐다.

생성된 graph cache:

- `ieumgil-osm-etl-poc/data/graphhopper/busan/`

주요 import 결과:

- OSM accepted ways: `70,362`
- nodes: `113,753`
- edges: `155,561`
- zero distance edges: `463`

### 2. 샘플 좌표 3쌍 모두 경로 반환 성공

좌표는 정제된 샘플 세그먼트의 메인 컴포넌트(`component_id = 1`)에서 자동 선택했다.

#### `west_to_east_core`

- 시작: `35.1577600, 129.0482700`
- 도착: `35.1562079, 129.0713287`
- 거리: `2915.209m`
- 소요시간: `34.98분`
- geometry point 수: `89`
- instruction 수: `34`
- snapped waypoint 수: `2`

#### `south_to_north_core`

- 시작: `35.1487258, 129.0636539`
- 도착: `35.1664222, 129.0639263`
- 거리: `2640.571m`
- 소요시간: `31.69분`
- geometry point 수: `37`
- instruction 수: `16`
- snapped waypoint 수: `2`

#### `southwest_to_northeast`

- 시작: `35.1518567, 129.0516408`
- 도착: `35.1660227, 129.0734084`
- 거리: `3555.351m`
- 소요시간: `42.66분`
- geometry point 수: `64`
- instruction 수: `32`
- snapped waypoint 수: `2`

### 3. 경로 응답 구조 확인

샘플 응답 기준으로 아래가 모두 확인됐다.

- `paths[].distance`
- `paths[].time`
- `paths[].points`
- `paths[].instructions`
- `paths[].snapped_waypoints`

즉, 다음 단계에서 필요한 거리/시간/polyline/step 추출은 가능하다.

## 핵심 판단

### 1. 기본 보행 경로 탐색은 PoC 기준으로 성립한다

부산 OSM 원본을 GraphHopper에 넣고 `foot` profile로 실제 경로가 반환됐다.

따라서 "GraphHopper 기반 기본 보행 경로 탐색 가능성"은 이번 단계에서 `확인됨`으로 판단할 수 있다.

### 2. Step 6 품질 이슈는 Step 7 진입 전에 최소한의 통제가 됐다

이번 단계에서 만든 QA 메타와 정제본 덕분에 다음과 같은 상태가 됐다.

- 경계 절단 의심 세그먼트는 `boundary_clipped_candidate`로 분리
- 중복 세그먼트는 exact 제거 + reverse 정규화 수행
- 샘플 시나리오는 메인 컴포넌트 기준으로만 선택

즉, 경로 검증 결과를 해석할 때 Step 6의 노이즈를 그대로 끌고 가지 않게 됐다.

### 3. 다만 GraphHopper import는 여전히 raw OSM 기준이다

중요한 점은 이번 QA 정제 결과가 GraphHopper import 입력 자체를 바꾸지는 않는다는 것이다.

- GraphHopper 입력: `busan.osm.pbf`
- QA 정제 입력: `road_segments_service.csv`

따라서 QA 메타는 "검증 해석용 보조 결과"로 봐야 하고, 실제 routing 품질까지 바꾸려면 이후 custom model 또는 OSM 전처리 단계가 추가로 필요하다.

## 결론

이번 Step 7의 결론은 아래와 같다.

- GraphHopper `foot` profile import 성공
- 샘플 좌표 3쌍에서 경로 반환 성공
- 거리/시간/geometry/instructions/snapped waypoint 확인 가능
- Step 6 이슈를 다루기 위한 QA 메타와 정제 결과도 함께 확보

즉, PoC 기준 최소 성공 조건은 충족했다.

## 실행 기록

```powershell
python ieumgil-osm-etl-poc\scripts\prepare_graphhopper_validation_inputs.py `
  --segments-csv ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\road_segments_service.csv `
  --output-dir ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\graphhopper_validation

docker build -t ieumgil-graphhopper:step7 --build-arg GRAPHHOPPER_VERSION=11.0 infra/graphhopper

docker run -d --name ieumgil-graphhopper-step7 `
  -e GRAPHHOPPER_MODE=server `
  -e GRAPHHOPPER_DATA_FILE=/data/raw/busan.osm.pbf `
  -e GRAPHHOPPER_CONFIG_FILE=/config/config-foot.yml `
  -e GRAPHHOPPER_GRAPH_LOCATION=/graphhopper/data `
  -e JAVA_OPTS="-Xms512m -Xmx512m" `
  -p 8989:8989 `
  -v "C:\Users\SSAFY\poc\ieumgil-osm-etl-poc\data\raw:/data/raw:ro" `
  -v "C:\Users\SSAFY\poc\infra\graphhopper:/config:ro" `
  -v "C:\Users\SSAFY\poc\ieumgil-osm-etl-poc\data\graphhopper\busan:/graphhopper/data" `
  ieumgil-graphhopper:step7

python ieumgil-osm-etl-poc\scripts\run_graphhopper_route_validation.py `
  --base-url http://localhost:8989 `
  --road-nodes-csv ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\road_nodes_service.csv `
  --cleaned-segments-csv ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\graphhopper_validation\road_segments_service_cleaned.csv `
  --output-dir ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\graphhopper_validation\routes

docker rm -f ieumgil-graphhopper-step7
```

## 다음 단계

다음 작업은 `docs/plans/graphhopper/08_COORDINATE_SNAPPING_VALIDATION.md`로 넘어가서, 현재 성공한 경로 시나리오를 기준으로 GPS 오차가 있는 좌표에서도 시작/도착 스냅핑이 안정적인지 보는 것이다.
