# Step 1 Transit Data Source Survey Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/00_EXECUTION_ROADMAP.md`, `docs/plans/graphhopper/01_SCOPE_AND_GOALS.md`, `docs/plans/graphhopper/02_CONSTRAINTS.md`, `docs/plans/transportation/01_TRANSIT_DATA_SOURCE_SURVEY.md`
- 작업 일자: 2026-04-14
- 작업 범위: 구현 착수 전 대중교통 데이터 원천의 웹 접근 가능 여부와 PoC 입력 적합성 확인

## 목적

`docs/plans/transportation/01_TRANSIT_DATA_SOURCE_SURVEY.md` 기준으로 ODsay, 부산 BIMS, 부산교통공사/지하철 공개 데이터가 PoC의 실제 입력 원천이 될 수 있는지 먼저 확인한다.

현재 저장소의 선언된 주 단계는 OSM 검증이지만, 이번 작업은 메인 코드 수정 없이 원천 조사와 리뷰 문서화만 수행하므로 제약을 벗어나지 않도록 범위를 제한했다.

## 조사 결과 요약

| 원천 | 용도 | 공식 문서 확인 | 직접 호출 확인 | 핵심 연결 키 후보 | 1차 판단 |
| --- | --- | --- | --- | --- | --- |
| ODsay | 출발지/도착지 기반 대중교통 경로 조회 | 가능 | 가능 | `stationID`, `busID`, `localBusID`, `x`, `y` | PoC 우선 후보 |
| 부산 BIMS | 버스 정류장/노선/도착 예정 정보 보강 | 가능 | 가능 | `bstopid`, `arsno`, `gpsx`, `gpsy`, 노선 ID | PoC 우선 후보 |
| 부산교통공사 역사/편의시설 API | 지하철 역사/편의시설 보강 | 가능 | 엔드포인트 도달 가능, 샘플 파라미터 재검증 필요 | `scode`, `sname` | 후속 검토 후보 |
| 부산교통공사 역 시설안내도 파일데이터 | 출입구/엘리베이터 위치 보강 | 가능 | 파일데이터 존재 확인 | 역명, 노선, 시설안내도 파일 | 보조 후보 |

## 수행 내용

### 1. ODsay 확인

공식 문서에서 아래 항목을 확인했다.

- `대중교통 길찾기`
- `대중교통 정류장 검색`
- `지하철역 세부 정보 조회`
- `지하철역 환승 정보 조회`

문서 기준 판단:

- 경로 조회 API와 정류장/역 조회 API가 같은 플랫폼에서 제공된다.
- `subwayStationInfo`는 `stationID`, `x`, `y`, 환승역 목록을 제공한다.
- 버스 노선 조회는 `busID`, `localBusID`를 제공한다.
- 모든 주요 API는 `apiKey`가 필수다.

직접 호출 결과:

- `https://api.odsay.com/v1/api/searchPubTransPath?...`를 키 없이 호출했을 때 `{"error":[{"code":"500","message":"[ApiKeyAuthFailed] ApiKey authentication failed."}]}` 응답을 받았다.

판단:

- 서비스는 현재 살아 있고 인증 체계도 정상이다.
- 발급 키만 있으면 PoC의 "출발지/도착지 기반 경로 후보 조회" 요구를 가장 직접적으로 만족한다.
- 대중교통 경로 엔진을 직접 구현하지 않고 PoC를 빠르게 시작하려면 1순위다.

### 2. 부산 BIMS 확인

공식 문서에서 아래 기능을 확인했다.

- 정류소정보 조회
- 노선정보 조회
- 노선 정류소 조회
- 정류소 도착정보 조회(정류장ID)
- 노선 정류소 도착정보 조회
- 정류소 도착정보 조회(ARS 번호)

문서 기준 판단:

- `busStopList`는 `bstopid`, `arsno`, `bstopnm`, `gpsx`, `gpsy`, `stoptype`를 제공한다.
- 문서 상 인증은 공공데이터포털 `serviceKey` 필수다.
- 개발계정 트래픽은 일 10,000건이고 활용신청은 자동승인이다.
- 데이터 포맷은 XML 기준이다.

직접 호출 결과:

- `https://apis.data.go.kr/6260000/BusanBIMS/busStopList?...`를 인증키 없이 호출했을 때 HTTP `401`을 받았다.
- 자리표시용 테스트 키로도 HTTP `401`을 받아 실제 활용 신청 키가 필요함을 확인했다.

판단:

- 인증만 확보되면 부산 버스 쪽 정류장/노선/도착예정 보강 원천으로 바로 쓸 수 있다.
- 정류장 좌표와 정류장 ID가 명시돼 있어 ODsay 결과나 별도 정류장 매핑과 연결하기 쉽다.
- 단, 이 API 자체는 멀티모달 경로 탐색 엔진이 아니라 버스 운영정보 계열이므로 "경로 조회 원천"보다는 "버스 보강 원천"으로 보는 것이 맞다.

### 3. 부산교통공사 지하철 공개 데이터 확인

공식 문서에서 아래 원천을 확인했다.

- `부산교통공사_부산도시철도 장애인 편의시설 정보`
- `부산교통공사_부산도시철도 공공 시설물 정보`
- `부산교통공사_부산도시철도 역사 정보`
- `부산교통공사_도시철도역사정보`

문서 기준 판단:

- 장애인 편의시설 API는 `scode`를 입력으로 받아 `엘리베이터`, `에스컬레이터`, `시각장애인유도로`, `외부경사로`, `장애인화장실` 등 수량을 제공한다.
- 공공 시설물 API는 `scode`, `sname` 기준으로 `주륜장 위치`, `주차장`, `물품보관함`, `무인민원발급기` 등을 제공한다.
- 도시철도 역사 정보 계열에는 역코드, 역명, 주소, 전화번호가 있고, 별도 `부산교통공사_도시철도역사정보` 설명에는 노선번호/노선명, 환승역 여부, 위도/경도 좌표가 포함된다고 명시돼 있다.

직접 호출 결과:

- `http://data.humetro.busan.kr/voc/api/open_api_stationinfo.tnn?act=json&scode=101`
- `http://data.humetro.busan.kr/voc/api/open_api_convenience.tnn?act=json&scode=101`
- `http://data.humetro.busan.kr/voc/api/open_api_public.tnn?act=json&scode=101`

위 세 호출은 모두 HTTP `200`이었지만 본문은 `resultCode=10`, `INVALID REQUEST PARAMETER ERROR.` 였다.

판단:

- 공식 문서와 엔드포인트는 존재하고 서버도 응답한다.
- 다만 문서 예시 수준의 파라미터만으로는 현재 환경에서 정상 데이터 응답이 재현되지 않았다.
- 따라서 지하철 접근성 보강용 후보로는 유효하지만, 구현 시작 시점의 1순위 입력 원천으로 바로 고정하기엔 위험하다.
- 역사 좌표는 `부산교통공사_도시철도역사정보` 설명상 확보 가능하므로, 접근성 API와 연결하는 보조 키로 `scode`/역명 조합을 검토할 가치가 있다.

### 4. 출입구/엘리베이터 관련 보강 원천 확인

`부산교통공사_부산도시철도 역 시설안내도_20251031` 파일데이터가 존재한다.

문서 설명 기준 판단:

- 승강장 위치
- 출입구 번호
- 엘리베이터 및 에스컬레이터
- 고객 편의시설

을 역사 내부 배치 수준으로 시각 확인할 수 있다.

판단:

- 구조화된 OpenAPI가 아니라 파일데이터/안내도 성격이므로, 자동 매핑 원천보다는 QA 또는 수동 검증 보조 자료에 가깝다.
- 그래도 "출입구 데이터가 전혀 없는가"에 대한 답은 아니며, 최소한 시각 보강 자료는 존재한다.

## 구현 시작 관점의 판단

### 바로 사용할 후보

1. `ODsay`
경로 조회 원천으로 가장 적합하다. 출발지/도착지 기반 대중교통 경로 조회 요구를 직접 만족한다.

2. `부산 BIMS`
버스 정류장, 노선, 도착예정 정보 보강용으로 적합하다. 정류장 ID와 좌표가 분명해 조인 키 설계가 쉽다.

### 후속 검토 후보

1. `부산교통공사 장애인 편의시설/공공 시설물 API`
문서는 충분하지만 샘플 파라미터 재현이 막혀 있다. 구현 전 역코드 규칙과 정상 호출 예시를 다시 확보해야 한다.

2. `부산교통공사 역 시설안내도 파일데이터`
출입구/엘리베이터의 존재 확인과 수동 QA에는 유용하지만 자동화 입력으로는 약하다.

## PoC 기준 핵심 연결 키 정리

- ODsay: `stationID`, `busID`, `localBusID`, `x`, `y`
- 부산 BIMS: `bstopid`, `arsno`, `bstopnm`, `gpsx`, `gpsy`
- 부산교통공사 지하철 계열: `scode`, `sname`, 노선명, 위도/경도 설명상 제공

현 시점 1차 연결 전략:

- 경로 후보 조회는 `ODsay`
- 부산 버스 정류장/노선 보강은 `BIMS`
- 지하철 접근성/편의시설 보강은 `부산교통공사 API`
- 출입구/엘리베이터 시각 검증은 `역 시설안내도 파일데이터`

## 확인한 제약

1. `ODsay`와 `BIMS`는 둘 다 인증키가 필요하다.
2. `BIMS`는 XML 중심이라 응답 정규화 계층이 필요하다.
3. 부산교통공사 API는 엔드포인트는 살아 있지만 요청 파라미터 규칙이 문서만으로 바로 재현되지 않는다.
4. 출입구 데이터는 현재 확인된 범위에서 구조화 API보다 파일/안내도 성격이 더 강하다.

## 결론

구현 시작 전 데이터 접근 여부 기준으로 보면 아래 조합이 가장 현실적이다.

- 경로 조회 원천: `ODsay`
- 버스 보강 원천: `부산 BIMS`
- 지하철 접근성 보강 원천: `부산교통공사 장애인 편의시설/공공 시설물 API`
- 출입구 QA 보조 원천: `부산교통공사 역 시설안내도 파일데이터`

즉, "사용 가능한 원천이 있는가"에 대한 답은 `예`다. 다만 지하철 접근성 API는 구현 전에 정상 호출 예시를 하나 확보해야 하므로, 다음 작업은 인증키 확보 후 `ODsay`와 `BIMS`의 최소 응답 샘플을 저장하고, 부산교통공사 API의 정상 역코드/호출 패턴을 다시 검증하는 것이다.

## 실행 기록

```powershell
Invoke-WebRequest -UseBasicParsing `
  "https://api.odsay.com/v1/api/searchPubTransPath?SX=129.0591028&SY=35.1577084&EX=129.061&EY=35.159"

Invoke-WebRequest -UseBasicParsing `
  "https://apis.data.go.kr/6260000/BusanBIMS/busStopList?pageNo=1&numOfRows=1&bstopnm=%EB%B6%80%EC%82%B0"

Invoke-WebRequest -UseBasicParsing `
  "http://data.humetro.busan.kr/voc/api/open_api_stationinfo.tnn?act=json&scode=101"
```

직접 확인한 결과:

- ODsay: `ApiKey authentication failed`
- BIMS: HTTP `401`
- 부산교통공사 stationinfo: HTTP `200` + `INVALID REQUEST PARAMETER ERROR`

## 참고 소스

- [ODsay 메인](https://lab.odsay.com/)
- [ODsay API Reference](https://lab.odsay.com/guide/releaseReference)
- [부산광역시_부산버스정보시스템 OpenAPI](https://www.data.go.kr/data/15092750/openapi.do)
- [부산교통공사_부산도시철도 장애인 편의시설 정보](https://www.data.go.kr/data/15001020/openapi.do)
- [부산교통공사_부산도시철도 공공 시설물 정보](https://www.data.go.kr/data/15001011/openapi.do)
- [부산교통공사_부산도시철도 역사 정보 모음](https://www.data.go.kr/dataset/15001002/openapi.do?lang=ko)
- [부산교통공사_부산도시철도 역 시설안내도_20251031](https://www.data.go.kr/data/15050407/fileData.do?recommendDataYn=Y)
