# 10_ROUTE_OPTION_VALIDATION.md

## 단계명

`SAFE` / `SHORTEST` 분기 가능성 검증

## 목적

기본 보행 최단 경로 외에 안전 우선 경로를 별도 옵션으로 분리할 수 있는지 확인한다.

이번 단계의 핵심은 추천 품질 자체를 완성하는 것이 아니라, 어떤 제약은 실제 경로 선택 단계에서 분기 가능하고 어떤 제약은 현재 구조상 후처리 메타로만 붙일 수 있는지 구분하는 것이다.

## 구현 원칙

1. `SHORTEST`는 Step 7에서 검증한 기본 `foot` 경로를 기준으로 둔다.
2. `SAFE`는 Step 4에서 만든 `road_segments` 속성과 Step 9의 후처리 한계를 함께 고려해 평가한다.
3. 실제 결과 차이가 작더라도 경로 선택 로직을 분리할 수 있으면 구조 분리 가능으로 판단한다.
4. GraphHopper 내부 분기 후보와 서비스 후처리 후보를 분리해서 기록한다.
5. 현재 단계에서는 운영용 안전 점수 모델을 만들지 않는다.

## 옵션 정의 가정

### 1. `SHORTEST`

- 기본 보행 경로
- 현재 GraphHopper `foot` profile 결과를 그대로 사용
- 거리/시간 최소화를 우선

### 2. `SAFE`

- 계단 회피
- 비신호 횡단 회피 또는 신호 횡단 선호
- 향후 위험 구간 속성 결합 가능성 고려

## 제약 후보 분류

### 1. GraphHopper 내부 분기 후보

- `stairs`
- 이유: OSM 태그 기반 제약이며, Step 4에서도 `has_stairs`를 직접 매핑했다.
- 목표: profile 분리 또는 custom model 후보로 검토

### 2. GraphHopper 확장 또는 별도 라우팅 그래프가 필요한 후보

- `has_crosswalk`
- `has_signal`
- 이유: 서비스 `road_segments`에는 존재하지만 Step 9 기준 현재 GraphHopper 응답만으로는 segment 속성을 직접 식별할 수 없다.
- 목표: import 확장, encoded value 추가, 또는 서비스 그래프 기반 탐색 후보로 분리

### 3. 후처리 메타로만 가능한 후보

- `has_curb_gap`
- `has_audio_signal`
- `has_braille_block`
- `riskLevel`
- 이유: 현재 OSM 단독으로는 데이터가 부족하거나, GraphHopper 현재 응답만으로 경로 자체를 바꾸는 입력으로 쓰기 어렵다.

## 구현 계획

1. Step 4의 `road_nodes_service.csv`, `road_segments_service.csv`를 기준으로 경로 그래프를 재구성한다.
2. `SHORTEST`는 `length_meter`만 비용으로 사용하는 기본 경로로 둔다.
3. `SAFE` 후보 규칙을 최소 2개 검증한다.
4. 계단 회피는 `has_stairs = true` 세그먼트를 금지 또는 강한 penalty로 비교한다.
5. 횡단 안전 후보는 `has_crosswalk = true and has_signal = false` 세그먼트에 penalty를 주는 방식으로 비교한다.
6. 각 규칙마다 대표 OD 1건 이상을 뽑아 `SHORTEST`와 `SAFE` 길이/제약 노출 차이를 기록한다.
7. 각 후보 규칙이 아래 중 어디에 속하는지 문서화한다.
   - GraphHopper profile/custom model 후보
   - GraphHopper import 확장 필요
   - 서비스 DB 후처리 메타 전용

## 확인할 것

- `SHORTEST`와 `SAFE`를 서로 다른 비용 함수로 실제 분리할 수 있는가
- 최소 1개 이상 회피 규칙에서 경로 선택 변화가 발생하는가
- 계단 회피 규칙을 현재 PoC 데이터로 설명할 수 있는가
- 비신호 횡단 회피 같은 후보가 데이터상 존재하는가
- 현재 GraphHopper 설정만으로 가능한 제약과 불가능한 제약은 무엇인가
- 위험 구간 정보는 현재 단계에서 경로 분기 입력인지, 후처리 메타인지

## 산출물

- `SAFE` / `SHORTEST` 분리 전략 메모
- 대표 OD 기준 비교 JSON
- 제약 후보별 구현 위치 정리
- 추가 데이터 또는 후처리 필요 항목 기록

## 완료 기준

- `SAFE` / `SHORTEST` 분기 구조 가능 여부 판단
- 최소 1개 이상 회피 규칙 후보 정리
- 대표 비교 케이스 1건 이상 산출
- 후처리 필요 지점 문서화

## 범위 제한

- 경사도, 점자블록, 공공데이터까지 한 번에 모두 반영하지 않는다.
- GraphHopper import 확장 구현까지 이번 단계 완료 조건에 넣지 않는다.
- 운영 수준의 추천 품질 비교는 목표가 아니다.
- 사용자별 장애 유형별 세부 가중치 설계는 하지 않는다.

## 다음 단계 입력값

- 향후 API `routeOption` 정의 방향
- GraphHopper custom model 또는 profile 분리 후보
- 세그먼트 속성 후처리 설계 후보
- `SAFE` 경로 구현 시 추가로 필요한 데이터 목록
