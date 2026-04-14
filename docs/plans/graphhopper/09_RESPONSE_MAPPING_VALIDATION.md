# 09_RESPONSE_MAPPING_VALIDATION.md

## 단계명
GraphHopper 응답 분석 및 API 응답 형태 변환 검증

## 목적

GraphHopper 결과를 현재 경로 API 구조로 어디까지 변환할 수 있는지 확인한다.

이번 단계에서는 단순히 `routes[]`만 맞추는 것이 아니라, 아래 세 가지를 분리해서 다룬다.

- 사용자 실제 GPS 위치 (`raw_location`)
- 경로 계산을 위해 보정한 시작/도착 anchor (`snapped_route_anchor`)
- 실제 위치를 어떻게 해석할지에 대한 상태 (`location_context`)

즉, 지도에 보여줄 위치와 라우팅 엔진에 넣을 위치를 분리한 상태로 API 매핑 가능성을 검증한다.

## 구현 원칙

1. 현재 API 명세의 본문 구조는 유지한다.
2. `raw_location`, `snapped_route_anchor`, `location_context`는 Step 9 검증용 보조 정보로 별도 정리한다.
3. `location_context`는 사용자 설명과 예외 처리 기준을 위한 상태값으로 사용한다.
4. GraphHopper가 바로 주는 값과, 서비스 DB 또는 후처리 join이 필요한 값을 구분해서 기록한다.
5. 현재 단계에서는 최종 운영 API를 확정하지 않는다.

## 위치 해석 기준

### 1. `raw_location`
- 사용자가 실제로 입력한 GPS 좌표
- 지도 표시와 현재 위치 설명의 기준

### 2. `snapped_route_anchor`
- GraphHopper route 계산을 위해 보행 네트워크에 붙인 좌표
- 시작점/도착점 anchor로 사용

### 3. `location_context`
- `raw_location`을 서비스가 어떻게 해석하는지 나타내는 상태값
- 이번 단계에서는 아래 값만 검증한다.
  - `ON_WALKABLE_NETWORK`
  - `NEAR_WALKABLE_NETWORK`
  - `OUT_OF_SERVICE_AREA`

### 4. 보류 상태
- `INSIDE_BUILDING`은 GraphHopper 응답만으로 확정할 수 없다.
- 건물 polygon, 출입구, 공공데이터 또는 별도 공간 데이터 join이 필요하다.
- 따라서 이번 단계에서는 `INSIDE_BUILDING`을 설계 후보로만 기록하고, 자동 판정 성공 기준에는 넣지 않는다.

## 구현 계획

1. Step 7 경로 응답과 Step 8 스냅핑 결과를 함께 사용한다.
2. 현재 경로 API 명세를 기준으로 PoC 응답 초안을 만든다.
3. `distance`, `time`, `polyline/geometry`, `instructions`는 GraphHopper 직접 값으로 채운다.
4. `raw_location`, `snapped_route_anchor`, `location_context`는 별도 request context로 정리한다.
5. `routes[].segments[]`는 instruction interval 기준으로 1차 분해해 본다.
6. 서비스 DB와 1:1 매핑되지 않는 필드는 `후처리 필요`로 표시한다.
7. 성공/경고/거절 케이스를 각각 1건 이상 샘플로 남긴다.

## 확인할 것

- 현재 API의 `routes[]` 구조로 거리/시간/geometry/instruction 매핑 가능 여부
- `guidanceMessage`를 GraphHopper instruction으로 만들 수 있는지
- `raw_location`과 `snapped_route_anchor`를 분리해서 유지할 수 있는지
- `location_context`를 최소한 `ON_WALKABLE_NETWORK`, `NEAR_WALKABLE_NETWORK`, `OUT_OF_SERVICE_AREA`로 나눌 수 있는지
- `segments[]`를 instruction 기반으로 만들 수 있는지
- `hasStairs`, `hasCrosswalk`, `hasSignal` 등 구간 속성을 GraphHopper 단독 응답만으로 채울 수 있는지
- 실제 서비스 DB `road_segments`와의 join이 필요한 필드가 무엇인지

## 산출물

- GraphHopper 응답 분석 문서
- API 응답 형태 매핑 샘플 JSON
- request context 초안
- 필드별 매핑 가능/불가 표
- 후처리 필요 항목 목록

## 완료 기준

- 샘플 경로 1건 이상을 현재 API 형태로 변환 성공
- `raw_location`, `snapped_route_anchor`, `location_context` 분리 결과 문서화
- `segments[]` 1차 생성 성공
- 직접 매핑 가능한 필드와 후처리 필요 필드 구분 완료

## 범위 제한

- 최종 운영 API 명세 확정은 하지 않는다.
- `INSIDE_BUILDING` 자동 판정은 이번 단계 완료 조건에 넣지 않는다.
- 공공데이터 join 구현은 하지 않는다.
- `SAFE` / `SHORTEST` 분기 구현은 다음 단계에서 다룬다.

## 다음 단계 입력값

- Step 7 경로 응답 JSON
- Step 8 스냅핑 검증 결과
- 현재 경로 API 명세
- 서비스 DB `road_segments` 필드 매핑 결과
