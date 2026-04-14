# 05_ROAD_NETWORK_GENERATION_VALIDATION.md

## 단계명

`road_nodes`, `road_segments` 생성 및 DB 적재 가능성 검증

## 목적

샘플 구역 OSM 데이터를 `docs/ARD/erd.md`의 실제 서비스 ERD 구조인 `road_nodes`, `road_segments`로 변환할 수 있는지 확인한다.

이번 단계의 핵심은 임의 PoC 스키마를 만드는 것이 아니라, 서비스 DB 테이블 기준으로 어떤 컬럼을 직접 매핑할 수 있고 어떤 컬럼은 추가 데이터나 설계 보완이 필요한지 검증하는 것이다.

## 구현 접근

1. 샘플 구역에서 보행 가능한 way만 추출한다.
2. 교차점과 분기점을 기준으로 node를 생성한다.
3. node 사이를 segment로 나누고 길이를 계산한다.
4. `road_nodes`, `road_segments` 필수 컬럼에 대응하는 값을 ERD 기준으로 매핑한다.
5. ERD에 있으나 OSM 단독으로 채우기 어려운 컬럼은 별도로 구분한다.
6. `road_nodes`, `road_segments`에 샘플 데이터로 적재한다.
7. 생성 개수, 무결성, 애매한 컬럼 해석을 기록한다.

## ERD 반영 기준

### `road_nodes`

- `vertexId`: 샘플 적재용 순차 PK 생성 가능 여부 확인
- `osm_node_id`: 원본 OSM node id 저장 가능 여부 확인
- `point`: `GEOMETRY(POINT,4326)` 적재 가능 여부 확인

### `road_segments`

- `from_node_id`, `to_node_id`: 생성한 `road_nodes.vertexId` FK 연결 가능 여부 확인
- `geom`: `GEOMETRY(LINESTRING,4326)` 적재 가능 여부 확인
- `length_meter`: 좌표 기반 길이 계산 가능 여부 확인
- `has_stairs`, `has_crosswalk`, `has_signal`, `surface_type`: OSM 태그 기반 직접 매핑 가능 여부 확인
- `avg_slope_percent`, `width_meter`, `has_curb_gap`, `has_elevator`, `has_audio_signal`, `has_braille_block`: OSM 단독 매핑 한계 확인
- `vertexId`: 서비스 ERD 해석이 필요한 보조 FK 컬럼으로 보고 임시 처리 여부와 한계를 기록한다.

## 확인할 것

- node 생성 가능 여부
- edge 생성 가능 여부
- `from_node_id`, `to_node_id`, `geom`, `length_meter` 적재 가능 여부
- 실제 서비스 ERD 컬럼별 직접 매핑 가능 / 불가 구분
- 교차점, 막다른 길, 단일 세그먼트 처리 방식
- FK 무결성 유지 가능 여부
- ERD 해석이 모호한 컬럼 존재 여부
- 샘플 구역 기준 DB 적재 성공 여부

## 산출물

- 샘플 적재 결과
- `road_nodes` 생성 수
- `road_segments` 생성 수
- ERD 컬럼 매핑 표
- 생성 실패 또는 애매한 케이스 기록

## 완료 기준

- 샘플 구간 기준 `road_nodes`, `road_segments` 적재 성공
- 최소 1개 지역에서 세그먼트 생성 확인
- 필수 컬럼 매핑 가능 여부 문서화
- OSM만으로 채울 수 없는 컬럼 목록 정리
- 임시 매핑이 필요한 컬럼은 별도 판단 근거 기록

## 범위 제한

- 부산 전역 일괄 적재는 아직 하지 않는다.
- 운영용 성능 최적화는 포함하지 않는다.
- 메인 프로젝트 ERD 변경은 하지 않는다.
- 접근성 세부 속성을 외부 데이터와 join해서 완성하지는 않는다.

## 다음 단계 입력값

- 지도 시각 검증 대상 `road_segments`
- GraphHopper 비교 검증용 샘플 네트워크 데이터
