# Step 4 Road Network Generation Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/05_ROAD_NETWORK_GENERATION_VALIDATION.md`, `docs/ARD/erd.md`
- 입력 파일: `ieumgil-osm-etl-poc/data/samples/seomyeon_station_1km.osm.pbf`
- 작업 일자: 2026-04-14

## 목적

샘플 OSM 데이터를 실제 서비스 ERD의 `road_nodes`, `road_segments` 구조에 매핑할 수 있는지 검증한다.

이번 검증의 핵심은 임의 PoC 스키마를 만드는 것이 아니라, `docs/ARD/erd.md` 기준 컬럼에 어떤 값을 넣을 수 있는지 확인하는 것이다.

## 반영 내용

### 1. ERD 기준 검증 스키마로 재작성

이전의 임의 검증 스키마는 폐기하고 아래 파일로 다시 구성했다.

- `ieumgil-osm-etl-poc/sql/poc_service_road_network.sql`
- `ieumgil-osm-etl-poc/scripts/build_road_network_sample.py`

검증용 DB schema:

- `poc_service_mapping.road_nodes`
- `poc_service_mapping.road_segments`

테이블 컬럼은 `docs/ARD/erd.md`의 서비스 ERD를 그대로 따라갔다.

### 2. 실제 서비스 ERD 기준 매핑

#### `road_nodes`

| ERD 컬럼 | 매핑 방식 | 판단 |
| --- | --- | --- |
| `vertexId` | 샘플 적재 시 순차 PK 생성 | 가능 |
| `osm_node_id` | anchor node의 원본 OSM node id 저장 | 가능 |
| `point` | OSM node 좌표를 `GEOMETRY(POINT,4326)`로 저장 | 가능 |

#### `road_segments`

| ERD 컬럼 | 매핑 방식 | 판단 |
| --- | --- | --- |
| `edgeId` | 샘플 적재 시 순차 PK 생성 | 가능 |
| `from_node_id` | 시작 anchor의 `road_nodes.vertexId` 참조 | 가능 |
| `to_node_id` | 종료 anchor의 `road_nodes.vertexId` 참조 | 가능 |
| `geom` | anchor 사이 LineString 저장 | 가능 |
| `length_meter` | segment 좌표 기준 haversine 계산 | 가능 |
| `avg_slope_percent` | OSM만으로 계산 불가 | 현재 불가 |
| `width_meter` | `width` 태그가 있으면 파싱, 없으면 NULL | 제한적 가능 |
| `has_stairs` | `highway=steps`이면 true | 가능 |
| `has_curb_gap` | OSM 샘플만으로 직접 판단 불가 | 현재 불가 |
| `has_elevator` | `elevator=yes` 또는 `highway=elevator`일 때만 true | 제한적 가능 |
| `has_crosswalk` | `crossing=*` 태그 존재 시 true | 가능 |
| `has_signal` | `crossing=traffic_signals` 또는 `traffic_signals=yes` 시 true | 가능 |
| `has_audio_signal` | OSM 샘플만으로 직접 판단 불가 | 현재 불가 |
| `has_braille_block` | `tactile_paving=yes|contrasted`일 때만 true | 제한적 가능 |
| `surface_type` | `surface` 태그를 `ASPHALT/BLOCK/CONCRETE/GRAVEL/UNPAVED/UNKNOWN`로 변환 | 가능 |
| `vertexId` | ERD 의미가 모호하여 현재는 `from_node_id`와 동일 값으로 임시 매핑 | 가능하나 해석 추가 필요 |

## 실행 결과

### 생성 및 적재 결과

- eligible ways: `1,012`
- `road_nodes`: `1,631`
- `road_segments`: `2,190`
- DB 적재 성공:
  - `poc_service_mapping.road_nodes`: `1,631`
  - `poc_service_mapping.road_segments`: `2,190`
- 재실행 검증 기준으로도 동일 결과 확인

### 무결성 확인

- `from_node_id = to_node_id`: `0`
- `length_meter <= 0`: `0`
- `road_segments.geom` 유효성: `2,190 / 2,190` 모두 `true`
- `road_nodes.osm_node_id` 채움: `1,631 / 1,631`

### 실제 컬럼 채움 상태

- `has_stairs = true`: `7`
- `has_crosswalk = true`: `68`
- `has_signal = true`: `5`
- `has_elevator = true`: `0`
- `has_audio_signal = true`: `0`
- `has_braille_block = true`: `0`
- `avg_slope_percent IS NULL`: `2,190`
- `width_meter IS NULL`: `2,190`
- `road_segments.vertexId = from_node_id`: `2,190`
- `road_segments.vertexId = to_node_id`: `0`

### surface_type 분포

- `UNKNOWN`: `1,600`
- `ASPHALT`: `512`
- `BLOCK`: `73`
- `CONCRETE`: `3`
- `UNPAVED`: `2`

## 산출물

- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/road_nodes_service.csv`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/road_segments_service.csv`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/road_network_mapping_debug.json`

## 핵심 판단

### 1. 실제 서비스 테이블 핵심 매핑은 가능

아래 핵심 컬럼은 OSM 샘플만으로도 채울 수 있다.

- `road_nodes.vertexId`
- `road_nodes.osm_node_id`
- `road_nodes.point`
- `road_segments.from_node_id`
- `road_segments.to_node_id`
- `road_segments.geom`
- `road_segments.length_meter`
- `road_segments.has_stairs`
- `road_segments.has_crosswalk`
- `road_segments.has_signal`
- `road_segments.surface_type`

즉, 보행 네트워크의 기본 골격 테이블 적재는 가능하다. 이번 Step 4의 기준은 "OSM 데이터를 실제 서비스 DB 테이블에 넣을 수 있는가"였고, 그 질문에는 조건부로 `예`라고 답할 수 있다.

### 2. 서비스 ERD의 일부 컬럼은 OSM만으로는 부족

아래는 현재 OSM 샘플만으로 신뢰도 있게 채울 수 없다.

- `avg_slope_percent`
- `width_meter`
- `has_curb_gap`
- `has_elevator`
- `has_audio_signal`
- `has_braille_block`

이 컬럼들은 후속 단계에서 아래 중 하나가 필요하다.

- 추가 공공데이터 join
- 수동/반자동 보정 데이터
- DEM 기반 계산
- 현장 데이터 또는 별도 접근성 데이터셋

### 3. `road_segments.vertexId`는 ERD 해석이 더 필요

이 컬럼이 가장 애매하다.

ERD 설명상:
- `from_node_id`, `to_node_id`는 시작/종료 정점
- `vertexId`는 “보조 정점 참조 컬럼”

하지만 segment가 이미 `from_node_id`, `to_node_id`를 가지므로 `vertexId`의 역할이 분명하지 않다.

이번 검증에서는 아래처럼 임시 처리했다.

- `road_segments.vertexId = from_node_id`

이유:

- FK 무결성을 만족시킬 수 있다.
- 실제 서비스에서 이 컬럼이 어떤 의미인지 아직 명확하지 않다.

따라서 이 컬럼은 구현 전 별도 설계 확인이 필요하다. 현재 검증 스크립트는 이 애매함을 숨기지 않고, 임시 매핑이라는 전제를 문서와 코드에 함께 남긴다.

## 결론

OSM 데이터를 실제 서비스 DB 테이블에 매핑시키는 것은 가능하다. 다만 “전체 컬럼을 완전하게 채운다”가 아니라 아래처럼 봐야 한다.

- 기본 네트워크 골격 컬럼은 OSM만으로 적재 가능
- 위험도/접근성 세부 속성 컬럼은 OSM 단독으로는 불충분
- `road_segments.vertexId`는 ERD 의미 재확인이 필요

즉, 이번 Step 4의 결론은:

- `road_nodes`, `road_segments`의 기본 적재 가능성은 확인됨
- 서비스 ERD 전체 컬럼을 완성하려면 추가 데이터 소스와 설계 보완이 필요함

## 실행 기록

```powershell
docker compose up -d postgres

python ieumgil-osm-etl-poc\scripts\build_road_network_sample.py `
  --source ieumgil-osm-etl-poc\data\samples\seomyeon_station_1km.osm.pbf `
  --output-dir ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping
```

## 다음 단계

다음 작업은 `docs/plans/graphhopper/06_SEGMENT_VISUAL_QA.md`에 앞서, `road_segments.vertexId`의 의미를 설계 관점에서 먼저 확인하는 것이 안전하다. 그 다음 `geom` 시각 검증으로 넘어가는 흐름이 맞다.
