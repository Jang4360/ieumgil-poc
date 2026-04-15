# 09_VIEWER_HYBRID_TRANSIT_INTEGRATION_PLAN.md

## 단계명
GraphHopper Viewer에 대중교통 혼합 경로 반영 계획

## 목적

현재 `http://localhost:8080/`의 GraphHopper KakaoMap viewer는 보행 경로만 시각화한다.  
이번 단계의 목적은 `출발지 / 도착지` 입력을 기준으로, 직선거리 또는 초기 보행 후보가 `1km`를 넘는 경우 `버스` 또는 `지하철`을 포함한 혼합 경로를 viewer에 반영할 수 있는 구조를 설계하는 것이다.

핵심 목표는 아래와 같다.

1. `1km 이하`에서는 기존 GraphHopper 보행 viewer 흐름을 유지한다.
2. `1km 초과`에서는 `ODsay`로 대중교통 후보를 조회한다.
3. 선택된 대중교통 후보의 `WALK` 구간은 GraphHopper 보행 경로로 재계산한다.
4. `BUS`, `SUBWAY`, `WALK`를 하나의 viewer 화면에서 구간별로 구분해 시각화한다.
5. 버스는 `부산 BIMS`, 지하철은 `부산교통공사/odcloud`를 기준 데이터셋으로 붙인다.

## 구현 방향

1. viewer 입력 기준 분기 규칙을 만든다.
2. `보행 전용 모드`와 `혼합 대중교통 모드`를 분리한다.
3. 혼합 모드에서는 `ODsay -> 도보 구간 추출 -> GraphHopper 재계산 -> BIMS/odcloud 보강` 순서로 처리한다.
4. viewer는 최종적으로 `통합 route model` 하나만 받아서 렌더링하도록 맞춘다.
5. MVP에서는 `추천 1개 경로` 우선 표시를 기본으로 하고, 이후 `복수 후보 비교`는 확장 범위로 둔다.

## 구현 범위

### 1. 입력 분기
- 사용자가 viewer에서 `출발지`, `도착지`를 입력한다.
- 1차 기준:
  - 직선거리 `<= 1km` 이면 기존 GraphHopper 보행 경로 조회
  - 직선거리 `> 1km` 이면 대중교통 혼합 후보 조회
- 보완 기준:
  - 직선거리 `<= 1km`라도 보행 경로 계산 결과가 과도하게 길거나 snap 실패가 발생하면 대중교통 모드 fallback 가능 여부를 검토한다.

### 2. 혼합 경로 후보 조회
- `ODsay searchPubTransPathT`를 호출해 상위 후보를 받는다.
- 후보 중 `WALK + BUS`, `WALK + SUBWAY`, `WALK + BUS + SUBWAY` 조합을 허용한다.
- MVP에서는 아래 우선순위를 둔다.
  1. 총 소요시간이 가장 짧은 경로
  2. mixed path 중 `WALK` 구간 anchor를 안정적으로 추출할 수 있는 경로
  3. `BUS`는 BIMS 매핑 가능, `SUBWAY`는 odcloud 매핑 가능한 경로를 우선

### 3. 도보 구간 재계산
- ODsay `subPath`에서 `trafficType=3`을 추출한다.
- 각 도보 구간을 `startPoint/endPoint` 구조로 변환한다.
- 지하철 구간은 가능하면 `startExitX/Y`, `endExitX/Y`를 우선 anchor로 사용한다.
- 변환된 도보 구간을 GraphHopper `wheelchair_safe` 또는 `visual_safe` 프로필에 넣어 실제 geometry를 재계산한다.

### 4. 버스 정보 반영
- `BUS` 구간은 `부산 BIMS`를 기준으로 아래를 붙인다.
  - 승차 정류장명
  - 하차 정류장명
  - 노선번호
  - 실시간 도착정보
  - `lowplate` 기반 저상버스 여부
- viewer에서는 `BUS` 구간 클릭 시 최소한 위 정보를 side panel에 노출한다.

### 5. 지하철 정보 반영
- `SUBWAY` 구간은 `부산교통공사/odcloud`를 기준으로 아래를 붙인다.
  - 노선명
  - 시작역 / 도착역
  - 운행 정보 매칭 여부
- 현재 단계에서는 운영/시간표 데이터 중심 반영만 목표로 한다.
- 역사 엘리베이터 / 출입구 접근성은 별도 데이터셋이 확보되기 전까지 `미지원` 또는 `추후 보강` 상태로 둔다.

### 6. viewer 렌더링 구조
- 기존 viewer가 `단일 보행 polyline` 중심이라면, 이를 `구간 리스트` 기반 렌더링으로 바꾼다.
- 구간 타입별 렌더링 예시:
  - `WALK`: 실선 polyline
  - `BUS`: 점선 또는 파란색 transit line
  - `SUBWAY`: 다른 색상의 transit line
- anchor marker:
  - 출발지
  - 버스 승차/하차
  - 지하철 진입/하차
  - 도착지
- side panel:
  - 총 시간
  - 총 요금
  - 구간별 시간 / 거리 / 교통수단
  - 버스 실시간 / 저상버스 여부
  - 지하철 매칭 상태

### 7. 조회 결과 요약 패널
- 사용자가 `출발지`, `도착지`를 조회하면 지도 위 경로와 함께 상단 또는 우측 요약 패널을 보여준다.
- 요약 패널은 최소한 아래 정보를 포함해야 한다.

#### 공통 요약
- 출발지명
- 도착지명
- 경로 모드
  - `WALK_ONLY`
  - `HYBRID_TRANSIT`
- 총 거리
- 총 소요시간
- 총 요금
- 사용한 데이터 소스 요약
  - `도보: GraphHopper`
  - `버스: ODsay + 부산 BIMS`
  - `지하철: ODsay + 부산교통공사/odcloud`

#### 구간별 요약
- 각 구간을 `도보 -> 버스 -> 도보 -> 지하철 -> 도보` 순서로 나열한다.
- 각 구간마다 아래 정보를 표시한다.

`WALK`
- 구간 제목
  - 예: `출발 도보`, `환승 도보`, `도착 도보`
- 사용 엔진
  - `GraphHopper wheelchair_safe` 또는 `GraphHopper visual_safe`
- 시작 anchor
- 종료 anchor
- 거리
- 시간
- snap 상태
  - `ACCEPT`, `WARN`, `REJECT`

`BUS`
- 노선번호
- 승차 정류장
- 하차 정류장
- ODsay 기준 구간 거리
- ODsay 기준 구간 시간
- BIMS 실시간 도착정보
  - `몇 분 후 도착`
  - `정류장 전 수`
- 저상버스 여부
  - 가능하면 `저상버스 운행`
  - 아니면 `저상버스 정보 없음` 또는 `일반버스`

`SUBWAY`
- 노선명
- 승차역
- 하차역
- ODsay 기준 구간 거리
- ODsay 기준 구간 시간
- odcloud 매칭 상태
  - `MATCHED`
  - `UNMATCHED`
- 운영 데이터 매칭 시 노선번호 또는 기준 데이터명

#### 요약 패널 문구 예시
- `총 42분, 15.5km, 1,600원`
- `도보 3구간은 GraphHopper로 재계산`
- `버스 구간은 부산 BIMS 실시간 도착 반영`
- `지하철 구간은 부산교통공사/odcloud 매칭 상태 표시`

## 통합 데이터 흐름

1. viewer 입력 수집
2. 거리 기준으로 `walk-only` 또는 `hybrid-transit` 모드 결정
3. hybrid-transit이면 ODsay 경로 후보 조회
4. 선택 경로의 `WALK` 구간 anchor 추출
5. 각 `WALK` 구간을 GraphHopper로 재계산
6. `BUS` 구간은 BIMS로 보강
7. `SUBWAY` 구간은 odcloud로 보강
8. 결과를 `viewer route model`로 통합
9. KakaoMap에 구간별로 렌더링

## viewer 통합 응답 구조 초안

```json
{
  "mode": "HYBRID_TRANSIT",
  "thresholdMeter": 1000,
  "summary": {
    "totalDistanceMeter": 15539,
    "totalTimeMinute": 42,
    "payment": 1600,
    "dataSources": {
      "walk": "GraphHopper",
      "bus": ["ODsay", "Busan BIMS"],
      "subway": ["ODsay", "Busan Subway odcloud"]
    }
  },
  "segments": [
    {
      "type": "WALK",
      "sequence": 1,
      "title": "출발 도보",
      "engine": "GraphHopper wheelchair_safe",
      "startPoint": { "lat": 35.2269, "lng": 129.1486 },
      "endPoint": { "lat": 35.2270, "lng": 129.1485 },
      "graphhopperProfile": "wheelchair_safe",
      "distanceMeter": 14.9,
      "estimatedTimeMinute": 0.18,
      "snapStatus": "ACCEPT"
    },
    {
      "type": "BUS",
      "sequence": 2,
      "routeNo": "기장군11",
      "startName": "반송시장",
      "endName": "동해선기장역.기장중학교",
      "distanceMeter": 9593,
      "estimatedTimeMinute": 33,
      "realtime": {
        "min1": "1",
        "lowplate1": "0"
      }
    },
    {
      "type": "SUBWAY",
      "sequence": 4,
      "lineName": "동해선",
      "startName": "기장",
      "endName": "오시리아",
      "distanceMeter": 5700,
      "estimatedTimeMinute": 4,
      "matchStatus": "UNMATCHED"
    }
  ]
}
```

## viewer 요약 표시 규칙

- `1km 이하`
  - 기본적으로 `WALK_ONLY`
  - 요약 패널에는 `도보 경로`, `GraphHopper 프로필`, `총 거리`, `총 시간`만 표시

- `1km 초과`
  - 기본적으로 `HYBRID_TRANSIT`
  - 요약 패널 상단에는 아래 형식의 한 줄 요약을 표시
    - `도보 3분 -> 버스 33분 -> 도보 3분 -> 지하철 4분 -> 도보 1분`
  - 각 구간 카드에는 해당 구간이 어떤 데이터로 계산됐는지 명시
    - `도보: GraphHopper`
    - `버스: ODsay + 부산 BIMS`
    - `지하철: ODsay + 부산교통공사/odcloud`

- 거리/시간 표시는 아래 원칙을 따른다.
  - `WALK`는 GraphHopper 재계산 값을 우선 사용
  - `BUS`, `SUBWAY`는 ODsay 구간 거리/시간을 사용
  - 총합은 최종 반영된 구간 값의 합으로 계산

## 확인할 것

- `1km` 기준을 직선거리로만 볼지, 초기 보행 route 결과까지 같이 볼지
- ODsay 후보 중 어떤 기준으로 viewer 기본 선택 경로를 정할지
- `WALK` 구간 재계산 후 ODsay 원래 시간/거리와 충돌할 때 어느 값을 UI에 우선 노출할지
- `BUS`, `SUBWAY` geometry를 ODsay 좌표 기반으로 그릴지, pass stop anchor만 요약 렌더링할지
- 지하철 `동해선`처럼 odcloud에 바로 매핑되지 않는 구간을 viewer에서 어떻게 표기할지
- GraphHopper viewer를 그대로 확장할지, transit 전용 별도 패널을 추가할지

## 결과물

- viewer hybrid mode 분기 설계 문서
- 통합 route model 초안
- 구간 타입별 렌더링 규칙 메모
- BIMS / odcloud / GraphHopper 역할 분리표
- mixed path 시나리오 기준 QA 체크리스트

## 완료 기준

- viewer에서 `1km 초과` 입력에 대해 hybrid mode 진입 규칙이 문서화되어 있다.
- `ODsay + GraphHopper + BIMS + odcloud`의 연결 순서가 명확히 정리되어 있다.
- viewer가 받아야 할 최소 통합 응답 구조가 정의되어 있다.
- `WALK`, `BUS`, `SUBWAY` 구간별 표시 방식이 정리되어 있다.
- 조회 결과 요약 패널에 표시할 항목과 데이터 소스가 정의되어 있다.
- MVP 범위와 보류 범위가 구분되어 있다.

## MVP 범위

- `1km 초과`일 때 hybrid mode 진입
- ODsay 후보 1개 선택
- `WALK` 구간 GraphHopper 재계산
- `BUS` 실시간 / 저상버스 여부 표시
- `SUBWAY` 기본 노선/역 정보 및 매칭 상태 표시
- KakaoMap 상에서 구간별 색상/스타일 구분

## 보류 범위

- 복수 hybrid 후보 경로 비교 UI
- 지하철 역사 내부 동선
- 역사 엘리베이터 / 출입구 상세 접근성
- 버스 차량 위치 실시간 애니메이션
- 실시간 재탐색 / reroute
- viewer를 메인 서비스 UI 수준으로 정교화하는 작업

## 범위 제한

- 이 단계는 viewer 구현 계획 문서이며, 메인 서비스 API 최종 확정 문서는 아니다.
- 대중교통 구간의 실제 geometry 정밀 복원은 MVP에서 필수 범위가 아니다.
- 지하철 접근성 데이터 부족 문제를 이번 단계에서 해결하지는 않는다.

## 다음 단계 입력값

- hybrid viewer에 연결할 실제 endpoint 초안
- viewer side panel wireframe
- mixed path 선택 정책
- `동해선` 미매핑 보완 데이터셋 검토 결과
