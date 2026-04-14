# Step 9 Response Mapping Validation Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/09_RESPONSE_MAPPING_VALIDATION.md`
- 참고 명세: `docs/API/보행_네트워크_도메인/2026-04-12_경로_API_명세.md`
- 작업 일자: 2026-04-14

## 목적

Step 7 경로 결과와 Step 8 스냅핑 결과를 기준으로, GraphHopper 응답을 현재 경로 API 형태로 어디까지 바꿀 수 있는지 확인했다.

이번 단계에서는 아래를 분리해서 검증했다.

- 사용자 실제 입력 좌표 (`raw_location`)
- 경로 계산용 보정 좌표 (`snapped_route_anchor`)
- 위치 해석 상태 (`location_context`)

## 반영 내용

수정 문서:

- `docs/plans/graphhopper/09_RESPONSE_MAPPING_VALIDATION.md`

추가 스크립트:

- `ieumgil-osm-etl-poc/scripts/build_response_mapping_samples.py`

생성 산출물:

- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/response_mapping/response_mapping_summary.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/response_mapping/west_to_east_core__exact_reference.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/response_mapping/west_to_east_core__building_plaza_like.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/response_mapping/south_to_north_core__in_bounds_large_snap.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/response_mapping/west_to_east_core__out_of_bounds_far.json`

## 검증 방식

- Step 8 결과에서 대표 케이스 4개를 선택했다.
  - `ACCEPT / ON_WALKABLE_NETWORK`
  - `WARN / NEAR_WALKABLE_NETWORK`
  - `REJECT / route는 성공하지만 snap이 과도한 경우`
  - `REJECT / PointNotFound`
- 각 케이스에 대해 GraphHopper route를 다시 호출했다.
- 응답을 현재 API 명세의 `routes[]` 구조로 1차 변환했다.
- 동시에 `requestContext`에 `raw_location`, `snapped_route_anchor`, `location_context`를 별도 보조 정보로 남겼다.

## 결과

### 1. `raw_location`과 `snapped_route_anchor`는 분리해서 유지할 수 있다

이 부분은 Step 9에서 확인됐다.

- `exact_reference`
  - 시작/종료 `raw_location`과 `snapped_route_anchor`가 동일
  - `location_context = ON_WALKABLE_NETWORK`
- `building_plaza_like`
  - 시작/종료 `raw_location`과 `snapped_route_anchor`가 다름
  - `location_context = NEAR_WALKABLE_NETWORK`
- `in_bounds_large_snap`
  - route는 반환되지만 시작점 snap 거리 `91.21m`
  - `location_context = OUT_OF_SERVICE_AREA`
  - 서비스 판단은 `REJECT`

즉, 사용자 현재 위치와 경로 계산 시작점은 같은 필드로 다루면 안 된다.

### 2. 현재 API `routes[]` 형태로 1차 변환은 가능하다

성공 케이스 기준으로 아래 필드는 바로 채울 수 있었다.

- `routes[].distanceMeter`
- `routes[].estimatedTimeMinute`
- `routes[].segments[].geometry`
- `routes[].segments[].distanceMeter`
- `routes[].segments[].guidanceMessage`

샘플 결과:

- `west_to_east_core__exact_reference.json`
  - 성공
  - 거리 `2915.209m`
  - 시간 `35분`
  - segment `33개`
- `west_to_east_core__building_plaza_like.json`
  - 성공
  - 거리 `2908.841m`
  - 시간 `35분`
  - segment `35개`
- `south_to_north_core__in_bounds_large_snap.json`
  - route는 성공
  - 거리 `2551.219m`
  - 시간 `31분`
  - segment `12개`
  - 하지만 서비스 판단은 `REJECT`

즉, 경로 엔진 성공과 서비스 응답 허용 여부는 별도로 봐야 한다.

### 3. `location_context`는 일부만 자동 판정 가능하다

Step 9 기준 판정 가능 상태:

- `ON_WALKABLE_NETWORK`
- `NEAR_WALKABLE_NETWORK`
- `OUT_OF_SERVICE_AREA`

판정 보류:

- `INSIDE_BUILDING`

이유:

- GraphHopper 응답과 snap 거리만으로는 “건물 내부”와 “건물 앞 광장/공터”를 구분할 수 없다.
- `INSIDE_BUILDING`을 쓰려면 building polygon, 출입구, 공공데이터 또는 별도 공간 join이 필요하다.

### 4. 현재 API `segments[]`는 만들 수 있지만, segment 속성은 아직 비어 있다

이번 PoC에서는 `segments[]`를 instruction interval 기준으로 만들었다.

하지만 아래 필드는 아직 GraphHopper 단독 결과로 채울 수 없었다.

- `routes[].riskLevel`
- `routes[].segments[].hasStairs`
- `routes[].segments[].hasCurbGap`
- `routes[].segments[].hasCrosswalk`
- `routes[].segments[].hasSignal`
- `routes[].segments[].hasAudioSignal`
- `routes[].segments[].hasBrailleBlock`
- `routes[].segments[].riskLevel`

원인:

- 현재 GraphHopper route 응답에는 서비스 DB `road_segments` 식별자가 직접 나오지 않는다.
- 따라서 instruction 기반 geometry segment는 만들 수 있어도, 실제 서비스 레코드 속성은 후처리 join이 필요하다.

## 판단

Step 9 결론은 아래와 같다.

- `raw_location`과 `snapped_route_anchor`를 분리하는 구조는 필요하고, 현재 PoC 결과로도 유지 가능하다.
- `location_context`는 Step 9에서 3개 상태까지는 운영 규칙으로 쓸 수 있다.
- 현재 API 응답 구조로 거리/시간/geometry/guidance 변환은 가능하다.
- 다만 segment 위험/편의 속성은 GraphHopper 단독으로는 부족하고, 서비스 DB 또는 공공데이터 join이 필요하다.
- `INSIDE_BUILDING`은 다음 단계가 아니라 별도 공간 데이터 결합 단계에서 다뤄야 한다.

## 실행 기록

```powershell
docker run -d --name ieumgil-graphhopper-step9 `
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

python ieumgil-osm-etl-poc\scripts\build_response_mapping_samples.py `
  --base-url http://localhost:8989 `
  --step8-summary ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\graphhopper_validation\snapping\snapping_validation_summary.json `
  --output-dir ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\graphhopper_validation\response_mapping
```

## 다음 단계

다음 작업은 `docs/plans/graphhopper/10_ROUTE_OPTION_VALIDATION.md` 기준으로 진행하는 것이 맞다.

다만 Step 10 전에 아래 전제가 이미 정리되어 있어야 한다.

- 공식 API 본문과 PoC request context를 분리할지
- segment 속성은 `road_segments` join 후 채울지
- `SAFE` 경로에서 어떤 속성을 우선 회피 대상으로 둘지
