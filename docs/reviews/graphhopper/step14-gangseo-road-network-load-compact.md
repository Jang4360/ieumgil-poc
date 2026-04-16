# Step 14 Gangseo Road Network Load Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/05_ROAD_NETWORK_GENERATION_VALIDATION.md`, `docs/ARD/erd.md`
- 원천 파일: `ieumgil-osm-etl-poc/data/raw/busan.osm.pbf`
- 행정경계 파일: `ieumgil-osm-etl-poc/data/reference/admin_boundaries/gangseo_gu_busan.geojson`
- 적재 스키마: `poc_service_mapping.road_nodes`, `poc_service_mapping.road_segments`
- 작업 일자: 2026-04-16

## 목적

기존 국소 샘플 대신 부산 강서구 범위의 보행 가능 edge를 `road_segments`에 적재할 수 있는지 확인한다.

이번 작업은 메인 서비스 스키마 변경이 아니라, 기존 PoC 적재 스크립트를 강서구 행정경계 기준으로 재실행해 DB와 산출물을 갱신하는 검증이다.

## 반영 내용

### 1. 강서구 경계 기반 필터를 스크립트에 추가

- 수정 파일: `ieumgil-osm-etl-poc/scripts/build_road_network_sample.py`
- 추가 내용:
  - `--boundary-geojson` 옵션 추가
  - GeoJSON `Polygon` / `MultiPolygon` 경계 로드
  - `matplotlib.path.Path` 기반 point-in-polygon 판정 적용
  - 경계 내부 좌표가 없는 segment 제외
  - `from_node_id = to_node_id` self-loop segment 제외

즉, 원천은 부산 전체 `.osm.pbf`를 유지하되, 적재 대상 way / segment만 강서구 경계 기준으로 줄였다.

### 2. 강서구 행정경계 GeoJSON 산출물 추가

- 파일: `ieumgil-osm-etl-poc/data/reference/admin_boundaries/gangseo_gu_busan.geojson`
- 출처: Nominatim 검색 결과 `Gangseo-gu, Busan, South Korea`
- OSM relation id: `3972378`

### 3. 강서구 기준 road network 재생성 및 DB 재적재

기존 스크립트는 schema SQL을 다시 실행하므로, 이번 적재는 이전 국소 샘플 데이터를 덮어쓰는 방식으로 수행됐다.

## 적재 결과

### 생성 결과

- eligible ways: `4,767`
- direct rule ways: `1,105`
- conditional rule ways: `3,662`
- `road_nodes`: `7,840`
- `road_segments`: `10,424`
- direct rule segments: `2,207`
- conditional rule segments: `8,217`

### DB 적재 결과

- `poc_service_mapping.road_nodes`: `7,840`
- `poc_service_mapping.road_segments`: `10,424`

## 검증 결과

### 기본 무결성

- `from_node_id = to_node_id`: `0`
- `length_meter <= 0`: `0`
- `ST_IsValid(geom) = true`: `10,424 / 10,424`

### 강서구 경계 적합성

- 경계와 교차하는 segment: `10,424`
- 경계 밖 완전 이탈 segment: `0`
- 경계 안에 완전히 포함된 segment: `10,305`
- 경계와 교차하지만 일부 구간이 밖으로 나가는 segment: `119`

즉, 현재 적재본은 모든 edge가 강서구 경계와는 교차하지만, `119`건은 boundary clipping 없이 원래 OSM segment 단위를 유지해 일부 선형이 경계 밖으로 이어진다.

### 속성 채움 상태

- `has_stairs = true`: `11`
- `has_crosswalk = true`: `335`
- `has_signal = true`: `9`
- `has_elevator = true`: `0`
- `has_braille_block = true`: `0`
- `width_meter IS NULL`: `10,413`
- `avg_slope_percent IS NULL`: `10,424`

### surface_type 분포

- `UNKNOWN`: `9,522`
- `ASPHALT`: `636`
- `UNPAVED`: `202`
- `CONCRETE`: `39`
- `BLOCK`: `14`
- `GRAVEL`: `11`

### 길이 분포

- 최소 길이: `0.54m`
- 최대 길이: `4,627.10m`
- 평균 길이: `128.21m`

## 산출물

- `ieumgil-osm-etl-poc/data/reference/admin_boundaries/gangseo_gu_busan.geojson`
- `ieumgil-osm-etl-poc/data/derived/gangseo_gu_service_mapping/road_nodes_service.csv`
- `ieumgil-osm-etl-poc/data/derived/gangseo_gu_service_mapping/road_segments_service.csv`
- `ieumgil-osm-etl-poc/data/derived/gangseo_gu_service_mapping/road_network_mapping_debug.json`

## 판단

### 1. 강서구 단위 적재는 가능하다

부산 전체 OSM 원천 파일 하나를 유지한 채, 행정경계 GeoJSON만 추가해 강서구 기준 `road_nodes`, `road_segments` 재생성과 DB 적재가 가능함을 확인했다.

### 2. 현재 적재 기준은 "강서구와 교차하는 edge"에 가깝다

완전 이탈 edge는 없지만, `119`건은 경계를 가로지르는 segment다.

따라서 현재 결과는 PoC 검증용으로는 사용할 수 있지만, "강서구 내부 선형만" 엄밀하게 남기려면 다음 보완이 필요하다.

- boundary crossing segment를 `ST_Intersection` 기준으로 clip
- clip 지점에 대응하는 synthetic node 생성
- clipped edge 기준으로 `from_node_id`, `to_node_id` 재구성

### 3. 접근성 속성은 여전히 OSM 단독으로는 제한적이다

강서구로 범위를 넓혀도 Step 4의 결론은 그대로다.

- `length_meter`, `geom`, `has_stairs`, `has_crosswalk`, `has_signal`, `surface_type`는 직접 적재 가능
- `avg_slope_percent`, `has_curb_gap`, `has_audio_signal`, `has_braille_block`는 추가 데이터 없이는 채우기 어렵다

## 실행 기록

```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

docker compose up -d postgres

python ieumgil-osm-etl-poc\scripts\build_road_network_sample.py `
  --source ieumgil-osm-etl-poc\data\raw\busan.osm.pbf `
  --boundary-geojson ieumgil-osm-etl-poc\data\reference\admin_boundaries\gangseo_gu_busan.geojson `
  --output-dir ieumgil-osm-etl-poc\data\derived\gangseo_gu_service_mapping
```

## 다음 단계

강서구 edge를 바로 GraphHopper 검증 입력으로 써도 되지만, 경계 교차 `119`건을 엄밀히 정리하려면 clipping 기반 후처리를 먼저 넣는 편이 안전하다.
