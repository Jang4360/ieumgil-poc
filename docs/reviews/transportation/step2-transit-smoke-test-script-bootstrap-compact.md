# Step 2 Transit Smoke Test Script Bootstrap Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/transportation/01_TRANSIT_DATA_SOURCE_SURVEY.md`
- 작업 일자: 2026-04-15
- 구현 산출물: `scripts/transportation/run_transit_api_smoke_tests.py`

## 목적

`01_TRANSIT_DATA_SOURCE_SURVEY.md`에서 확정한 3개 API를 사람이 수동으로 매번 호출하지 않고,
동일한 입력으로 재검증할 수 있는 재현 가능한 스모크 테스트 스크립트를 만든다.

현재 단계에서는 통합 DTO나 서비스 계층 구현이 아니라 아래 범위를 우선 고정한다.

- 출발지 / 도착지 및 경로 조회 가능 여부
- 버스 정류장 / 실시간 도착정보 조회 가능 여부
- 지하철 운행 정보 / 정거장 도착시각 조회 가능 여부
- 각 API에서 이후 연결에 필요한 핵심 필드가 실제로 내려오는지

## 구현 내용

추가한 스크립트:

- `scripts/transportation/run_transit_api_smoke_tests.py`

스크립트 동작:

1. 루트 `.env`를 읽는다.
2. `ODsay searchStation`과 `searchPubTransPathT`를 호출한다.
3. `부산 BIMS busStopList`, `stopArrByBstopid`를 호출한다.
4. `부산도시철도 운행 정보` odcloud REST API를 호출한다.
5. 각 API에서 최소 성공 조건과 핵심 필드를 검증하고 JSON 요약을 출력한다.
6. 하나라도 실패하면 비정상 종료 코드로 반환한다.

## 실행 명령어

```powershell
python scripts/transportation/run_transit_api_smoke_tests.py
```

## 실행 결과

실행 시점 기준 결과:

- `ODsay`: 성공
  - `stationCount=52`
  - 부산 도시코드 `CID=7000`의 `서면` 정류/역 검색 확인
  - `searchPubTransPathT` 기준 `totalTime=8`, `subwayTransitCount=1`
- `Busan BIMS`: 성공
  - `bstopid=164720101`
  - `arsno=13040`
  - `lineId=5200131000`
  - `min1=2`
- `Busan Subway Operation`: 성공
  - `routeNo=S2601`
  - `startStation=노포`
  - `endStation=다대포해수욕장`
  - `speed=39.6km/h`
  - `totalCount=3833`

## 확인된 구현 포인트

1. `ODsay`는 출발지 / 도착지 기반 경로 조회와 총 이동시간 확보에 사용할 수 있다.
2. `부산 BIMS`는 정류장 조회 후 `bstopid`로 실시간 도착정보를 이어서 조회할 수 있다.
3. `부산도시철도 운행 정보`는 `serviceKey`에 `Decoding 키를 URL 인코딩해서 전달`해야 정상 응답한다.
4. 지하철 데이터는 실시간 도착예정이 아니라 기준 운행 정보이므로 이후 응답 조립 시 성격을 분리해야 한다.

## 현재 판단

`01_TRANSIT_DATA_SOURCE_SURVEY.md`의 Step 1 범위에서 "구현 시작"은 완료됐다.

이 단계에서 확보된 것은 아래다.

- API 연결 재현 스크립트 1개
- 각 API의 최소 성공 입력값
- 이후 DTO 설계에 사용할 핵심 필드 샘플

아직 하지 않은 것은 아래다.

- 세 API를 하나의 응답 구조로 합치는 통합 로직
- 지하철 `운행구간정거장`, `정거장도착시각`, `정거장출발시각` 파싱 유틸
- ODsay 경로 결과와 버스/지하철 상세 응답을 연결하는 매핑 로직

## 다음 작업 제안

1. 지하철 문자열 필드를 정거장 단위 배열로 파싱하는 유틸을 만든다.
2. ODsay 경로 응답에서 버스/지하철 구간별 식별 키를 추출하는 규칙을 정리한다.
3. 버스 / 지하철 / ODsay를 하나로 묶는 샘플 응답 JSON을 만든다.
