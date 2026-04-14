# Step 2 Sample Area Extraction Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/03_EXECUTION_ROADMAP.md`, `docs/plans/graphhopper/04_WALKABLE_SEGMENT_CRITERIA.md`
- 작업 일자: 2026-04-14
- 작업 위치: `ieumgil-osm-etl-poc`

## 목적

부산 전체 OSM 데이터 대신 반복 검증용 샘플 지역을 먼저 확정하고, 재현 가능한 방식으로 별도 PBF 파일을 생성한다.

## 수행 내용

### 1. 샘플 중심 좌표 확정

부산 원본 파일에서 `Seomyeon` / `서면역` 객체를 조회해 아래 node를 샘플 중심으로 사용했다.

- node id: `355173724`
- name: `서면역`
- lat/lon: `35.1577084`, `129.0591028`
- tags: `public_transport=stop_position`, `railway=stop`, `subway=yes`

### 2. 샘플 구역 추출 스크립트 추가

재현 가능성을 위해 아래 스크립트를 추가했다.

- `ieumgil-osm-etl-poc/scripts/extract_bbox_sample.py`

기능:

- 원본 `.osm.pbf`에서 bbox 기준 샘플 추출
- 중심 좌표와 반경(km) 입력 지원
- bbox 메타데이터를 헤더에 기록
- 추출된 node / way / relation 수 출력

### 3. 샘플 파일 생성

생성 파일:

- `ieumgil-osm-etl-poc/data/samples/seomyeon_station_1km.osm.pbf`

생성 기준:

- 중심: 서면역 `35.1577084, 129.0591028`
- 반경: `1.0 km`
- bbox: `129.0481152,35.1487253,129.0700904,35.1666915`

## 결과

### 샘플 파일 정보

- 파일 경로: `ieumgil-osm-etl-poc/data/samples/seomyeon_station_1km.osm.pbf`
- 파일 크기: `254,392 bytes`
- header box: `(129.0481152/35.1487253 129.0700904/35.1666915)`
- header generator: `ieumgil-osm-etl-poc/extract_bbox_sample.py`

### 추출 객체 수

- nodes: `16,598`
- ways: `2,711`
- relations: `126`

### 보행 관련 태그 분포

- `highway=*`: `1,079`
- `highway=footway`: `98`
- `highway=pedestrian`: `6`
- `highway=path`: `25`
- `highway=steps`: `6`
- `sidewalk=*`: `15`
- `foot=*`: `7`
- `crossing=*`: `28`
- `elevator`: `0`

### 샘플 확인

- `way_id=165267651`: `highway=footway`
- `way_id=244223422`: `name=부전로66번길`, `highway=pedestrian`
- `way_id=131872804`: `name=서면로68번길`, `highway=residential`, `sidewalk=no`
- `way_id=164687893`: `name=동서고가로`, `highway=trunk`, `foot=no`, `sidewalk=no`

## 판단

서면역 1km bbox 샘플은 다음 단계 검증용 입력으로 적절하다.

- 원본 부산 OSM에서 재현 가능하게 다시 만들 수 있다.
- 파일 크기가 작아 반복 실험과 디버깅에 유리하다.
- 보행 가능/불가 판단에 필요한 태그가 이미 충분히 포함되어 있다.
- 이후 `road_nodes`, `road_segments` 생성과 GraphHopper 샘플 검증의 시작점으로 사용할 수 있다.

## 실행 기록

```powershell
python ieumgil-osm-etl-poc\scripts\extract_bbox_sample.py `
  --source ieumgil-osm-etl-poc\data\raw\busan.osm.pbf `
  --output ieumgil-osm-etl-poc\data\samples\seomyeon_station_1km.osm.pbf `
  --center-lat 35.1577084 `
  --center-lon 129.0591028 `
  --radius-km 1.0
```

## 다음 단계

다음 작업은 `docs/plans/graphhopper/04_WALKABLE_SEGMENT_CRITERIA.md` 기준으로 샘플 파일에서 보행 가능 / 제외 / 예외 태그 기준표를 만드는 것이다.
