# Step 8 Coordinate Snapping Validation Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/08_COORDINATE_SNAPPING_VALIDATION.md`
- 입력 파일: `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/routes/graphhopper_route_validation_summary.json`
- 작업 일자: 2026-04-14

## 목적

사용자 GPS 좌표가 도로 위 정확한 점이 아니어도, GraphHopper가 실제 보행 가능한 시작/도착 anchor로 안정적으로 붙일 수 있는지 확인한다.

이번 단계에서는 엔진 자체의 스냅 성공 여부와, 서비스가 그 결과를 받아들일지 거절할지를 분리해서 봤다.

## 반영 내용

추가한 스크립트:

- `ieumgil-osm-etl-poc/scripts/run_coordinate_snapping_validation.py`

생성 산출물:

- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/snapping/snapping_validation_summary.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/snapping/snapping_validation_summary.csv`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/snapping/*_snapping_cases.json`

검증 방식:

- Step 7에서 성공한 3개 시나리오를 기준점으로 사용
- 각 시나리오마다 아래 6개 케이스를 적용
  - `exact_reference`
  - `gps_small_error`
  - `building_plaza_like`
  - `too_far_candidate`
  - `in_bounds_large_snap`
  - `out_of_bounds_far`
- `nearest`로 각 점의 스냅 거리 확인
- `route`로 실제 경로 시작 가능 여부 확인

## 서비스 판단 기준

이번 PoC에서는 아래 기준을 임시 서비스 규칙으로 두었다.

- `ACCEPT`: 최대 스냅 거리 `<= 30m`
- `WARN`: 최대 스냅 거리 `> 30m` and `<= 80m`
- `REJECT`: 최대 스냅 거리 `> 80m` 또는 `PointNotFound`

이 기준은 이번 샘플 기준 경험칙이며, 이후 실제 사용자 로그가 쌓이면 재조정 대상이다.

## 실행 결과

### 전체 요약

- 총 케이스: `18`
- `ACCEPT`: `12`
- `WARN`: `2`
- `REJECT`: `4`
- GraphHopper route 성공: `15`

스냅 거리 구간:

- `ACCEPT` 최대값: `25.40m`
- `WARN` 범위: `42.22m ~ 44.72m`
- `REJECT` 스냅 기반 사례: `91.21m`

### 1. 일반 GPS 오차 범위는 안정적으로 붙는다

- `exact_reference` 3건 모두 `ACCEPT`
- `gps_small_error` 3건 모두 `ACCEPT`
- 소형 GPS 오차 케이스의 최대 스냅 거리: `17.92m`

즉, 일반적인 GPS 오차 수준에서는 경로 시작 자체에 큰 문제가 없었다.

### 2. 건물 앞 / 광장형 좌표는 “붙기는 하지만” 일부는 경고가 필요하다

`building_plaza_like` 결과:

- `west_to_east_core`: `42.22m`, `WARN`
- `south_to_north_core`: `14.60m`, `ACCEPT`
- `southwest_to_northeast`: `25.40m`, `ACCEPT`

즉, 건물 앞/광장형 입력은 항상 실패하지는 않지만, 도심 구조에 따라 `30m`를 넘는 경우가 생긴다.

### 3. 단순한 입력 오프셋 크기만으로는 실패를 판단할 수 없다

`too_far_candidate`와 `in_bounds_large_snap`가 이 점을 보여준다.

`too_far_candidate`:

- `west_to_east_core`: `25.21m`, `ACCEPT`
- `south_to_north_core`: `3.84m`, `ACCEPT`
- `southwest_to_northeast`: `44.72m`, `WARN`

`in_bounds_large_snap`:

- `west_to_east_core`: `14.71m`, `ACCEPT`
- `south_to_north_core`: `91.21m`, `REJECT`
- `southwest_to_northeast`: `3.30m`, `ACCEPT`

같은 수준의 좌표 이동이라도, 주변 도로 밀도와 보행 네트워크 구조에 따라 스냅 거리가 크게 달라진다.

따라서 서비스는 "입력 좌표가 몇 m 이동했는가"가 아니라, "실제 snapped point까지 몇 m였는가"를 기준으로 판단해야 한다.

### 4. 너무 먼 좌표는 엔진 단계에서 바로 실패한다

`out_of_bounds_far` 3건은 모두 `REJECT`였다.

- `nearest`: `Point 35.05,128.9 is either out of bounds or cannot be found`
- `route`: `Cannot find point 0: 35.05,128.9`

즉, 보행 네트워크 바깥 좌표는 GraphHopper가 `PointNotFound`로 거절한다.

## 핵심 판단

### 1. 일반 GPS 오차 범위 스냅핑은 가능하다

Step 8의 최소 성공 기준인 "일반적인 GPS 오차 범위에서 경로 탐색 성공"은 충족했다.

### 2. 엔진 성공과 서비스 허용은 분리해야 한다

가장 중요한 사례는 `south_to_north_core / in_bounds_large_snap`이다.

- GraphHopper route: 성공
- 최대 스냅 거리: `91.21m`
- 서비스 판단: `REJECT`

즉, 엔진이 경로를 반환했다고 해서 서비스가 그대로 받아들이면 안 된다.

### 3. 예외 처리 방향은 세 단계가 적절하다

- `ACCEPT`: 그대로 경로 진행
- `WARN`: snapped point로 보정하되, 사용자 의도와 다를 수 있음을 알림
- `REJECT`: 시작/도착 위치 재입력 요청

## 예외 처리 방향

이번 단계 기준 추천 처리:

- `<= 30m`
  - 정상 처리
  - snapped anchor를 그대로 시작/도착점으로 사용
- `30m ~ 80m`
  - 경고 처리
  - snapped anchor 사용 가능
  - 다만 UI/로그에 "입력 위치와 차이가 있음" 표시 필요
- `> 80m`
  - 거절 처리
  - "가까운 보행 가능 위치를 찾을 수 없음" 메시지 반환
- `PointNotFound`
  - 즉시 거절
  - 서비스 영역 밖 또는 네트워크 미연결 좌표로 취급

## 결론

이번 Step 8 결론은 아래와 같다.

- 일반 GPS 오차 범위 좌표는 안정적으로 스냅됨
- 건물 앞/광장형 좌표는 일부 경고 처리 필요
- 너무 먼 좌표는 `PointNotFound` 또는 과도한 스냅 거리로 거절 가능
- 서비스는 GraphHopper 성공 여부만 보지 말고 `snap distance` 기준을 함께 가져가야 함

즉, 다음 단계 API 응답 설계에서는 snapped point 자체와 함께, 서비스 내부 판단용 snap distance도 같이 계산하는 방향이 맞다.

## 실행 기록

```powershell
docker run -d --name ieumgil-graphhopper-step8 `
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

python ieumgil-osm-etl-poc\scripts\run_coordinate_snapping_validation.py `
  --base-url http://localhost:8989 `
  --step7-summary ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\graphhopper_validation\routes\graphhopper_route_validation_summary.json `
  --output-dir ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\graphhopper_validation\snapping

docker rm -f ieumgil-graphhopper-step8
```

## 다음 단계

다음 작업은 `docs/plans/graphhopper/09_RESPONSE_MAPPING_VALIDATION.md`로 넘어가서, Step 7과 Step 8에서 확인한 거리/시간/instruction/snapped point를 현재 API 응답 구조로 어떻게 매핑할지 검토하는 것이다.
