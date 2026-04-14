# 07_GRAPHHOPPER_ROUTE_VALIDATION.md

## 단계명

GraphHopper import 및 기본 보행 경로 탐색 검증

## 목적

GraphHopper에 OSM 데이터를 넣고 기본 보행 경로가 계산되는지 확인한다.

단, Step 6에서 확인한 품질 이슈를 그대로 넘기지 않기 위해 GraphHopper 검증 전 `road_segments` QA 메타와 정제 결과를 먼저 만든다. GraphHopper 자체는 원본 OSM을 import하지만, 샘플 시나리오 선정과 결과 해석은 이 QA 결과를 기준으로 한다.

## 구현 접근

1. Step 6 산출물 기준으로 `road_segments` QA 메타를 생성한다.
2. `boundary_clipped_candidate`, `component_id`, `duplicate_type`를 붙인 QA 결과를 만든다.
3. 동일 `from_node_id`, `to_node_id`, 동일 geometry 중복은 제거한다.
4. 역방향 duplicate는 canonical orientation으로 정규화한 정제본을 만든다.
5. GraphHopper를 로컬 또는 Docker로 단독 실행한다.
6. 보행용 profile을 설정한다.
7. 부산 OSM 또는 샘플 구역 OSM 데이터를 적재한다.
8. 샘플 좌표 2~3쌍으로 기본 경로 요청을 테스트한다.
9. import 시간, 메모리 사용량, 응답 품질을 기록한다.

## 확인할 것

- GraphHopper 검증 전 QA 메타 생성 성공 여부
- `boundary_clipped_candidate` 부착 여부
- `component_id` 부착 여부
- `duplicate_type` 부착 여부
- exact duplicate 제거 여부
- reverse duplicate 정규화 여부
- GraphHopper import 성공 여부
- 서버 기동 성공 여부
- 기본 보행 profile 동작 여부
- 샘플 출발지/도착지 경로 반환 여부
- 거리, 소요시간, polyline 반환 여부
- import/build 시간과 메모리 사용량 대략치

## 샘플 시나리오

- 부산역 → 남포동
- 서면역 → 부산시민공원
- 장애물 없는 일반 도심 구간 1개
- 골목 또는 횡단보도 포함 구간 1개

## 산출물

- `road_segments` QA 메타 결과
- 정제된 `road_segments` 결과
- GraphHopper import 실행 기록
- 샘플 좌표 테스트 결과
- 경로 응답 샘플
- 거리/시간/polyline 확인 기록
- 실패 케이스 기록

## 완료 기준

- QA 메타가 부착된 샘플 세그먼트 결과 생성
- exact duplicate 제거 / reverse duplicate 정규화 결과 생성
- 최소 2개 이상 좌표쌍에서 보행 경로 반환
- 경로 거리/시간/geometry 확인 가능
- 기본 보행 profile 사용 가능 여부 판단

## 범위 제한

- 커스텀 weighting, 커스텀 profile 최적화는 아직 하지 않는다.
- API 응답 변환은 다음 단계에서 검토한다.
- `boundary_clipped_candidate`, `component_id`, `duplicate_type`는 검증용 QA 메타이며 서비스 최종 스키마에 바로 넣지 않는다.

## 다음 단계 입력값

- 스냅핑 테스트용 샘플 출발지/도착지 좌표
- 응답 분석용 GraphHopper 원본 응답
