# Step 2 Busan Arrival And Travel Time Strategy Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/transportation/01_TRANSIT_DATA_SOURCE_SURVEY.md`
- 작업 일자: 2026-04-14
- 작업 범위: 부산 버스/지하철의 실시간 도착정보 및 이동시간 산출 방안 조사, 대체 루트 및 공개 구현 사례 확인

## 목적

부산 버스와 부산 지하철에 대해 아래를 확인한다.

1. 실시간 도착정보를 공식적으로 얻을 수 있는가
2. 출발지에서 목적지까지 걸리는 시간을 공식 데이터만으로 얻을 수 있는가
3. 공식 데이터가 부족할 때 어떤 대체 루트가 현실적인가
4. 기존 공개 저장소는 이 문제를 어떻게 구현했는가

## 핵심 결론

### 1. 버스

- `실시간 도착정보`는 부산 BIMS OpenAPI로 가능하다.
- 하지만 `출발지-목적지 전체 이동시간`은 BIMS 단독으로 바로 주지 않는다.
- 전체 이동시간은 `ODsay 경로 API` 같은 경로 엔진을 쓰거나, 별도 계산 로직을 만들어야 한다.

### 2. 지하철

- `역사 기본정보`, `편의시설`, `열차시각표`, `역간 운행정보`는 공공데이터로 확인됐다.
- 반면 `부산 지하철 실시간 도착예정 OpenAPI`는 2026-04-14 기준 공개 문서/데이터셋에서 확인하지 못했다.
- 그래서 지하철은 현재 확인 범위에서 `실시간 ETA`보다는 `시간표 기반 예정 도착시각`과 `역간 이동시간 계산`이 현실적이다.

### 3. 가장 현실적인 구현 조합

- `버스 실시간 도착`: 부산 BIMS
- `버스/지하철 전체 소요시간`: ODsay `searchPubTransPathT` 또는 `searchPubTransPathR`
- `지하철 역간 이동시간 보강`: 부산교통공사 `부산도시철도 운행 정보`
- `지하철 예정 도착시각`: 부산교통공사 `부산 도시철도 열차시각표 조회 서비스`

## 조사 결과

### 1. 부산 버스에서 가능한 것

공식 데이터셋:

- [부산광역시_부산버스정보시스템 OpenAPI](https://www.data.go.kr/data/15092750/openapi.do)

확인된 기능:

- `busStopList`: 정류소 조회
- `busInfo`: 노선정보 조회
- `busInfoByRouteId`: 노선 정류소 및 실시간 버스 위치정보
- `stopArrByBstopid`: 정류소ID 기준 실시간 도착정보
- `busStopArrByBstopidLineid`: 정류소ID + 노선ID 기준 도착정보
- `bitArrByArsno`: ARS 번호 기준 실시간 도착정보

판단:

- 버스는 정류장 단위 실시간 도착예정 정보를 공식적으로 제공한다.
- 따라서 "이 정류장에 몇 분 뒤 도착하는가"는 가능하다.
- 하지만 "여기서 저기까지 총 몇 분 걸리는가"는 BIMS 설명 범위만으로는 직접 제공되지 않는다.

### 2. 부산 지하철에서 가능한 것

공식 데이터셋:

- [부산교통공사_도시철도역사정보](https://www.data.go.kr/data/15043686/fileData.do)
- [부산교통공사_부산 도시철도 열차시각표 조회 서비스](https://www.data.go.kr/dataset/15000522/openapi.do)
- [부산교통공사_부산도시철도 운행 정보_20250714](https://www.data.go.kr/data/15082980/fileData.do)
- [부산교통공사_부산도시철도 장애인 편의시설 정보](https://www.data.go.kr/data/15001020/openapi.do)
- [부산교통공사_부산도시철도 공공 시설물 정보](https://www.data.go.kr/data/15001011/openapi.do)

확인된 내용:

- `도시철도역사정보`: 역사명, 노선번호, 환승역 구분, 위도/경도 등 기본 메타데이터
- `열차시각표 조회 서비스`: 역별 열차 도착시각, 방향, 종착역, 역코드, 호선 정보
- `부산도시철도 운행 정보`: 출발역/도착역 코드, 이동거리, 이동시간, 정차시간, 환승구분

중요한 제한:

- `열차시각표 조회 서비스` 설명에 "표준 열차도착 시각이며 실제 도착시각과 다를 수 있습니다."라고 명시돼 있다.
- `부산도시철도 운행 정보` 설명에도 "역간 이동시간은 표준 시각이며 실제 이동시간과는 다소 차이가 있을 수 있습니다."라고 명시돼 있다.
- 즉, 둘 다 `실시간`이 아니라 `표준/시간표 기반`이다.

판단:

- 부산 지하철은 현재 확인된 공식 데이터만으로는 `실시간 도착예정 API`를 확보했다고 보기 어렵다.
- 대신 `다음 예정 열차 시각`과 `구간별 표준 이동시간`을 조합하는 형태는 가능하다.

## 이동시간을 어떻게 얻을 것인가

### A. 공식 데이터만으로 버스 이동시간을 얻는 경우

가능한 정보:

- 정류장 도착예정 시간
- 노선별 정류장 목록
- 실시간 버스 위치

하지만 부족한 정보:

- 임의 출발지/도착지 사이의 전체 경로 선택
- 환승 포함 총 소요시간
- 버스와 지하철 혼합 경로 계산

따라서:

- BIMS 단독으로는 "내가 지금 여기서 저 목적지까지 몇 분 걸리는가"를 안정적으로 계산하기 어렵다.
- 공식-only로 가려면 노선 그래프, 정류장 연결, 환승 규칙, 구간별 평균 소요시간 모델을 직접 만들어야 한다.
- PoC 단계에서는 비용 대비 효율이 좋지 않다.

### B. 공식 데이터만으로 지하철 이동시간을 얻는 경우

가능한 정보:

- 역 코드 / 좌표 / 노선 정보
- 역별 열차 시각표
- 역간 이동시간 / 정차시간 / 환승구분

가능한 계산 방식:

1. 현재 시각 기준으로 출발역의 다음 열차 시각 선택
2. 출발역에서 목적역까지 구간별 `이동시간 + 정차시간` 합산
3. 환승역이면 환승 시간 규칙을 추가
4. 결과를 `예정 소요시간`으로 제공

이 방식의 성격:

- 실시간이 아니라 `예정 기반 ETA`
- 지연, 장애, 임시운휴 반영 불가

### C. 가장 현실적인 방식: ODsay로 총시간, 공식 데이터로 보강

ODsay 공식 문서:

- [ODsay API Reference](https://lab.odsay.com/guide/releaseReference)

확인된 기능:

- `searchPubTransPathT`: 대중교통 경로 검색
- `searchPubTransPathR`: 대중교통 경로 검색
- `realtimeStation`: 실시간 버스 도착정보
- `subwayPath`: 지하철 경로검색
- `subwayStationInfo`: 지하철역 세부 정보

문서 기준 확인된 필드:

- `path.info.totalTime`: 총 소요시간
- `subPath[].sectionTime`: 구간별 소요시간
- `subwayPath` 결과의 `departureTime`, `arrivalTime`
- `realtimeStation`은 버스 정류장 기준 실시간 도착용

판단:

- 버스/지하철 혼합 경로의 총 소요시간은 ODsay가 가장 직접적으로 준다.
- 버스 실시간 도착은 ODsay 또는 부산 BIMS 둘 다 후보가 된다.
- 지하철 실시간 도착은 ODsay 공식 문서에서도 확인하지 못했고, 시간표/경로 기반 정보가 중심이다.

## 공공데이터포털 외 다른 루트

### 1. ODsay

가장 현실적인 외부 루트다.

- 장점: 부산 포함 전국 대중교통 경로검색, 총시간, 환승 수, 구간 시간 제공
- 장점: 버스 도착 관련 API도 존재
- 단점: 유료/쿼터 관리 필요, 외부 서비스 의존

### 2. 비공식 웹/앱 내부 API

가능성은 있지만 이번 조사 범위에서는 공식 문서와 공개 저장소 기준으로 재현 가능한 부산 지하철 `실시간 도착예정 API`를 확인하지 못했다.

판단:

- 기술적으로 웹/앱 네트워크를 분석해 비공개 엔드포인트를 찾을 가능성은 있다.
- 하지만 계약/안정성/차단 위험이 크므로 PoC 기본 방안으로 두기 어렵다.

### 3. 네이버/카카오 등 지도 API

이번 조사 범위에서 부산 대중교통 경로를 ODsay처럼 공개적으로 제공하는 공식 개발자 API는 확인하지 못했다.

판단:

- 실사용 앱에는 대중교통 길찾기가 있어도, 개발자용 공개 API는 별개다.
- PoC에서 합법적이고 재현 가능한 경로 엔진 후보는 현재 확인 범위에서 `ODsay`가 가장 명확하다.

## 기존 공개 저장소 구현 방식

### 1. ODsay로 총 이동시간을 가져오는 패턴

예시 저장소:

- [yeongseon/seoul-transit-navi - `api/src/lib/odsay.ts`](https://github.com/yeongseon/seoul-transit-navi/blob/930e913018046ac273480ad161221a589522be4b/api/src/lib/odsay.ts)
- [Team-MOISAM/moisam-server - `OdsayTransitRouteSearchClient.java`](https://github.com/Team-MOISAM/moisam-server/blob/99db8e8e6cc74b381da75dc051e3a127925666ab/src/main/java/com/meetup/server/global/clients/odsay/OdsayTransitRouteSearchClient.java)

확인한 방식:

- `searchPubTransPathT` 호출
- `SX`, `SY`, `EX`, `EY` 좌표 기반 요청
- 응답의 `totalTime`, `payment`, `sectionTime`, `stationCount`, `subwayTransitCount` 파싱
- API 키 쿼리스트링 전달
- 캐시/쿼터/재시도 처리 추가

의미:

- 실제 서비스들은 "전체 이동시간"을 자체 계산보다 `ODsay 응답`에서 직접 받는 패턴이 많다.

### 2. 버스 실시간 도착과 총시간을 섞는 패턴

예시 저장소:

- [chungddong/CATCH - `app/odsay_service.py`](https://github.com/chungddong/CATCH/blob/1f38021de9370a81adaa2c58dec9b0190906fb5b/app/odsay_service.py)

확인한 방식:

- `searchPubTransPathR`로 버스 경로와 `totalTime` 확보
- `realtimeStation`으로 첫 버스 도착예정(`arrivalSec`) 확보
- 실시간 도착이 없으면 `intervalTime`으로 fallback

의미:

- "총 이동시간"과 "곧 오는 첫 차"는 서로 다른 데이터 소스/엔드포인트를 조합해 제공하는 식이 현실적이다.
- 이 패턴이 부산 PoC에도 가장 잘 맞는다.

### 3. 부산 BIMS만 붙이는 패턴

예시 저장소:

- [INMD1-Repo/Code-481-Backend - `BusanBimsApiClient.java`](https://github.com/INMD1-Repo/Code-481-Backend/blob/ba5b48a3fc577931f040e8b80bc44b66a3de5c8c/src/main/java/com/deu/java/backend/apiClient/BusanBimsApiClient.java)

확인한 방식:

- `stopArrByBstopid` 호출
- XML 응답을 JSON으로 변환
- `min1` 같은 도착예정 필드를 파싱
- 정류장 단위 도착정보에 집중

의미:

- 부산 BIMS 활용 저장소도 주로 "정류장 도착정보"를 다루고 있다.
- BIMS 단독으로 종합 경로 시간까지 푸는 구현은 이번 조사에서 확인하지 못했다.

## PoC 권장안

### 권장안 1. 가장 빠른 구현

- 경로 탐색과 총 이동시간: `ODsay`
- 부산 버스 실시간 도착: `부산 BIMS`
- 부산 지하철 기본 메타데이터: `도시철도역사정보`
- 부산 지하철 예정 시각/구간시간: `열차시각표 + 운행 정보`

장점:

- 구현 난이도가 가장 낮다.
- 버스는 실시간, 지하철은 예정 기반으로 빠르게 화면에 올릴 수 있다.

한계:

- 지하철은 실시간 지연 반영이 어렵다.

### 권장안 2. 공식 데이터 우선, 외부 의존 최소화

- 버스: `부산 BIMS`
- 지하철: `역사정보 + 열차시각표 + 운행정보`
- 경로 계산: 자체 계산

장점:

- 공공데이터 중심 구조

한계:

- 환승 경로/총시간 계산 엔진을 직접 구현해야 한다.
- PoC 범위 대비 부담이 크다.

### 권장안 3. 완전 실시간 지향

- 버스: `부산 BIMS`
- 지하철: 비공식 내부 API 또는 앱 크롤링 시도

판단:

- 현재 단계에서는 권장하지 않는다.
- 유지보수/합법성/안정성 리스크가 크다.

## 최종 판단

2026-04-14 기준으로 가장 방어적인 결론은 아래다.

1. 부산 버스의 실시간 도착정보는 공식 OpenAPI로 확보 가능하다.
2. 부산 지하철의 공개 `실시간 도착예정 API`는 이번 조사에서 확인하지 못했다.
3. 부산 지하철은 공식 데이터 기준으로 `시간표 기반 예정 도착`과 `역간 이동시간 계산`이 가능하다.
4. 전체 이동시간은 `ODsay` 같은 경로 엔진을 쓰는 것이 공개 구현 사례와 PoC 효율 측면에서 가장 현실적이다.

## 다음 단계 제안

1. 버스 smoke test
`stopArrByBstopid`, `busInfoByRouteId` 실제 응답 샘플 저장

2. 지하철 smoke test
`열차시각표 조회 서비스`, `부산도시철도 운행 정보` 샘플 추출

3. 설계 결론 고정
`버스 실시간 + 지하철 예정기반 + ODsay 총시간` 조합을 PoC 기본안으로 확정할지 결정

## 참고 소스

- [부산광역시_부산버스정보시스템 OpenAPI](https://www.data.go.kr/data/15092750/openapi.do)
- [부산교통공사_도시철도역사정보](https://www.data.go.kr/data/15043686/fileData.do)
- [부산교통공사_부산 도시철도 열차시각표 조회 서비스](https://www.data.go.kr/dataset/15000522/openapi.do)
- [부산교통공사_부산도시철도 운행 정보_20250714](https://www.data.go.kr/data/15082980/fileData.do)
- [ODsay API Reference](https://lab.odsay.com/guide/releaseReference)
- [ODsay Release Note](https://lab.odsay.com/guide/releaseNoteV1)
- [yeongseon/seoul-transit-navi - odsay.ts](https://github.com/yeongseon/seoul-transit-navi/blob/930e913018046ac273480ad161221a589522be4b/api/src/lib/odsay.ts)
- [Team-MOISAM/moisam-server - OdsayTransitRouteSearchClient.java](https://github.com/Team-MOISAM/moisam-server/blob/99db8e8e6cc74b381da75dc051e3a127925666ab/src/main/java/com/meetup/server/global/clients/odsay/OdsayTransitRouteSearchClient.java)
- [chungddong/CATCH - odsay_service.py](https://github.com/chungddong/CATCH/blob/1f38021de9370a81adaa2c58dec9b0190906fb5b/app/odsay_service.py)
- [INMD1-Repo/Code-481-Backend - BusanBimsApiClient.java](https://github.com/INMD1-Repo/Code-481-Backend/blob/ba5b48a3fc577931f040e8b80bc44b66a3de5c8c/src/main/java/com/deu/java/backend/apiClient/BusanBimsApiClient.java)
