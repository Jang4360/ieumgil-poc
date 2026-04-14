# Step 3 Walkable Segment Criteria Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/03_EXECUTION_ROADMAP.md`, `docs/plans/graphhopper/04_WALKABLE_SEGMENT_CRITERIA.md`
- 분석 대상 파일: `ieumgil-osm-etl-poc/data/samples/seomyeon_station_1km.osm.pbf`
- 작업 일자: 2026-04-14

## 목적

서면역 1km 샘플 구역에서 보행 가능한 OSM way를 어떤 기준으로 추출할지 1차 규칙을 정리한다.

## 수행 내용

### 1. 재현 가능한 분석 스크립트 추가

- `ieumgil-osm-etl-poc/scripts/analyze_walkable_tags.py`

용도:

- 샘플 PBF의 `highway`, `foot`, `sidewalk`, `access`, `crossing` 분포 확인
- 보행 태그 후보와 경계 케이스 샘플 추출

### 2. 샘플 구역 태그 분포 확인

주요 `highway` 분포:

- `residential`: 321
- `service`: 310
- `secondary`: 141
- `footway`: 98
- `secondary_link`: 50
- `tertiary`: 40
- `path`: 25
- `living_street`: 19
- `primary`: 17
- `cycleway`: 14
- `pedestrian`: 6
- `steps`: 6
- `trunk`: 2

보행 보조 태그:

- `foot=yes|designated`: 5
- `foot=no`: 2
- `sidewalk=both|left|right`: 12
- `sidewalk=no`: 3
- `access=no`: 1
- `crossing=uncontrolled|marked|traffic_signals`: 28

### 3. 경계 케이스 확인

- `way_id=164687893`: `highway=trunk`, `foot=no`, `sidewalk=no`
- `way_id=165373658`: `highway=service`, `service=parking_aisle`
- `way_id=244223416`: `highway=service`, `service=driveway`
- `way_id=432993243`: `highway=footway`, `foot=yes`, `access=no`
- `way_id=544582357`: `highway=cycleway`, `foot=designated`
- `way_id=544582359`: `highway=cycleway`
- `way_id=545587650`: `highway=footway`, `crossing=marked`
- `way_id=549452966`: `highway=steps`

## 1차 추출 규칙

### 직접 포함

아래는 보행 세그먼트로 바로 포함한다.

- `highway=footway`
- `highway=pedestrian`
- `highway=path`
- `highway=steps`
- `highway=living_street`
- `crossing=*`가 있는 `highway=footway`
- `foot=yes|designated|permissive`가 명시된 way
- `sidewalk=both|left|right|separate`가 명시된 way
- `highway=cycleway` 이더라도 `foot=yes|designated|permissive`가 있으면 포함

### 제외

아래는 1차 규칙에서 제외한다.

- `foot=no`
- `access=no`
- `highway=trunk`
- `highway=trunk_link`
- `highway=primary_link`
- `highway=cycleway` 이면서 `foot` 허용 정보가 없는 경우
- `highway=service` 이면서 `service=parking_aisle`
- `highway=service` 이면서 `service=driveway`

### 조건부 포함

아래는 보행 가능성이 높지만 OSM 태그가 충분하지 않아 `조건부 포함`으로 둔다.

- `highway=residential`
- `highway=unclassified`
- `highway=tertiary`
- `highway=tertiary_link`
- `highway=secondary`
- `highway=secondary_link`
- `highway=primary`
- `highway=service` 이지만 `parking_aisle`, `driveway`가 아닌 경우
- `highway=service` 이면서 `service=alley`

조건부 포함 사유:

- 샘플 구역에서 위 도로 다수는 `foot` / `sidewalk` 태그가 비어 있지만 실제 도심 보행 네트워크의 연결축으로 보인다.
- 태그 누락이 흔해 완전 제외하면 네트워크가 과도하게 끊길 가능성이 높다.
- 대신 이후 `road_segments` 생성과 시각 검증 단계에서 재검토가 필요하다.

### 예외 검토

아래는 별도 규칙이 필요하다.

- `highway=footway` 이지만 `access=no`와 충돌하는 경우
- `elevator` 관련 객체
  - 현재 샘플에서는 way 기준으로 확인되지 않았고, 향후 node 기반 검토가 필요하다
- `sidewalk=no`가 붙은 일반 도로
  - carriageway 자체를 보행 세그먼트로 볼지 후속 단계에서 재검토 필요

## 샘플 적용 결과

현재 1차 규칙을 샘플 way에 적용하면 대략 아래처럼 나뉜다.

- 직접 포함: 167
- 제외: 62
- 조건부 포함: 850

세부 예시:

- 직접 포함 예시: `footway`, `pedestrian`, `steps`, `living_street`, `sidewalk=left`
- 제외 예시: `trunk + foot=no`, `service=parking_aisle`, `cycleway` 단독
- 조건부 포함 예시: `secondary`, `tertiary`, `residential`, `service`

## 판단

샘플 구역 기준으로 보행 가능 세그먼트 1차 추출 규칙은 문서화 가능하다.

- 직접 포함 대상은 비교적 명확하다.
- 완전 제외 대상도 `trunk`, `foot=no`, `vehicle-only service` 등으로 분명하다.
- 핵심 쟁점은 `residential/secondary/service` 계열의 태그 누락 구간이며, 이들은 1차에서 `조건부 포함`으로 두는 것이 현실적이다.

## 실행 기록

```powershell
python ieumgil-osm-etl-poc\scripts\analyze_walkable_tags.py `
  --source ieumgil-osm-etl-poc\data\samples\seomyeon_station_1km.osm.pbf `
  --topn 20 `
  --sample-limit 30
```

## 다음 단계

다음 작업은 `docs/plans/graphhopper/05_ROAD_NETWORK_GENERATION_VALIDATION.md` 기준으로, 위 1차 규칙을 적용해 `road_nodes`, `road_segments` 생성 가능성을 검증하는 것이다.
