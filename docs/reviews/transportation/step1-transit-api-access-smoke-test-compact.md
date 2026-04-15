# Step 1 Transit API Access Smoke Test Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/transportation/00_EXECUTION_ROADMAP.md`, `docs/plans/transportation/01_TRANSIT_DATA_SOURCE_SURVEY.md`
- 작업 일자: 2026-04-15
- 작업 범위: `부산 BIMS`, `부산교통공사_부산도시철도 운행 정보` 실제 인증 및 최소 조회 재검증

## 목적

`docs/plans/transportation/01_TRANSIT_DATA_SOURCE_SURVEY.md`에서 1차 원천으로 잡은 공공데이터 API 2종을
실제 `.env`에 넣은 키로 다시 호출해 아래를 확인한다.

- 인증이 실제로 통과하는지
- 최소 1건 조회가 가능한지
- Step 1 완료 기준에 필요한 연결 키와 시간 필드가 보이는지

## 이번 재검증 범위

- 포함: `부산 BIMS`, `부산교통공사_부산도시철도 운행 정보`
- 제외: `ODsay`

`ODsay`는 별도 확인이 끝난 상태로 두고, 이 문서는 공공데이터 API 2종 재검증 결과만 반영한다.

## 수행 내용

### 1. 부산 BIMS 호출 검증

검증 대상:

- `busStopList`
- `stopArrByBstopid`

입력:

- 정류장명: `부산시청`
- 정류장 ID: `164720101`

결과:

- `.env`에 `BUSAN_BIMS_SERVICE_KEY_ENCODING`, `BUSAN_BIMS_SERVICE_KEY_DECODING` 값이 존재했다.
- `BUSAN_BIMS_SERVICE_KEY_ENCODING`으로 `busStopList` 호출 시 HTTP `401 Unauthorized`
- `BUSAN_BIMS_SERVICE_KEY_DECODING` 원문 값으로 `busStopList` 호출 시 `resultCode=00`, `resultMsg=NORMAL SERVICE`
- 같은 키로 `부산시청.시청역` 정류장 1건 이상이 조회됐고, 그중 하나의 `bstopid=164720101`, `arsno=13040`, 좌표 `129.075388596308,35.177897282215`를 확인했다.
- 같은 키로 `stopArrByBstopid(bstopid=164720101)` 호출 시 `resultCode=00`, `resultMsg=NORMAL SERVICE`
- 도착정보 응답에서 `lineno`, `lineid`, `min1`, `station1`, `lowplate1`, `min2`, `station2`, `lowplate2` 필드를 확인했다.

판단:

- 부산 BIMS는 실제로 인증 통과와 조회 성공을 확인했다.
- 현재 `.env` 기준으로는 `DECODING` 키를 그대로 사용하면 정상 호출된다.
- 현재 상태에서 BIMS는 Step 1의 `버스 정류장 조회`, `실시간 도착시간 조회`, `연결 키 확인` 용도로 사용할 수 있다.

### 2. 부산교통공사_부산도시철도 운행 정보 호출 검증

공식 문서 기준 서비스 정보:

- Base URL: `https://api.odcloud.kr/api`
- Swagger URL: `https://infuser.odcloud.kr/oas/docs?namespace=15082980/v1`
- 최신 경로: `/15082980/v1/uddi:e9c28907-a511-428d-b5ec-e1c6c988396a`

검증 대상:

- `부산교통공사_부산도시철도 운행 정보_20250714`

입력:

- `page=1`
- `perPage=1`
- `returnType=JSON`

결과:

- `.env`에 `BUSAN_SUBWAY_OPERATION_SERVICE_KEY_ENCODING`, `BUSAN_SUBWAY_OPERATION_SERVICE_KEY_DECODING` 값이 존재했다.
- `BUSAN_SUBWAY_OPERATION_SERVICE_KEY_ENCODING` 값을 `serviceKey`에 그대로 넣어 호출하면 `{"code":-4,"msg":"등록되지 않은 인증키 입니다."}`가 반환됐다.
- `BUSAN_SUBWAY_OPERATION_SERVICE_KEY_DECODING` 값을 `--data-urlencode`로 전달하면 `HTTP 200`으로 정상 응답했다.
- 응답 기준 `currentCount=1`, `totalCount=3833`을 확인했다.
- `data[0]`에서 `노선명`, `노선번호`, `운행구간기점명`, `운행구간종점명`, `운행구간정거장`, `정거장도착시각`, `정거장출발시각`, `운행속도`, `데이터기준일자` 필드를 확인했다.
- 샘플 응답 기준 `부산 도시철도 1호선`, `노포 -> 다대포해수욕장` 구간, `운행속도=39.6km/h`, 정거장별 도착/출발 시각 문자열이 내려왔다.

판단:

- 지하철 원천은 더 이상 `Humetro open_api_process.tnn` 기준으로 보지 않고 `odcloud REST` 기준으로 연결해야 한다.
- 이 데이터셋은 현재 키로 인증과 조회가 가능하다.
- 호출 시 `Decoding 키를 클라이언트에서 URL 인코딩해서 전달`하는 규칙이 핵심이다.
- 응답은 실시간 도착예정이 아니라 기준 운행 정보이므로 PoC에서는 `이동시간 보강`, `정거장 시각 후보 파싱`, `노선/정거장 연결 키 확보` 용도로 보는 것이 맞다.

## API별 상태 요약

| API | 조회 목표 | 호출 결과 | 현재 판단 |
| --- | --- | --- | --- |
| 부산 BIMS | 버스 정류장 조회, 실시간 도착시간 조회 | `DECODING` 키 기준 `NORMAL SERVICE` | 사용 가능 |
| 부산도시철도 운행 정보 | 정거장 도착/출발시각, 운행구간, 운행속도 조회 | `DECODING` 키 + URL 인코딩 기준 `HTTP 200` | 사용 가능 |

## 확인된 사실

1. 워크스페이스 루트 `.env`에는 실제 공공데이터 키가 들어 있다.
2. 부산 BIMS는 `ENCODING` 키로는 실패했고, `DECODING` 키는 현재 `.env` 원문 기준으로 정상 호출된다.
3. 부산 BIMS 응답에서 `bstopid`, `arsno`, 좌표, `lineid`, `lowplate1`, `lowplate2`를 확인했다.
4. 부산도시철도 운행 정보는 `ENCODING` 키로 실패하고, `DECODING` 키를 URL 인코딩해서 보낼 때 정상 응답한다.
5. 지하철 응답에서 `운행구간정거장`, `정거장도착시각`, `정거장출발시각` 문자열을 실제로 확보했다.

## 현재 단계 판단

`01_TRANSIT_DATA_SOURCE_SURVEY.md` 기준으로 보면 공공데이터 2종은 모두 Step 1 목적에 맞게 연결 가능 상태를 확인했다.

현재 바로 진행 가능한 다음 작업은 아래 순서가 적절하다.

1. `운행구간정거장`, `정거장도착시각`, `정거장출발시각` 파싱 규칙을 정의한다.
2. ODsay 경로 조회 결과와 BIMS/지하철 응답을 어떻게 결합할지 역할 분담을 정리한다.
3. 재현 가능한 스모크 테스트 스크립트로 현재 연결 상태를 고정한다.

## 환경 정리

이번 재검증에서 확인한 환경 상태는 아래와 같다.

- `.env` 존재
- `BUSAN_BIMS_SERVICE_KEY_ENCODING` 존재
- `BUSAN_BIMS_SERVICE_KEY_DECODING` 존재
- `BUSAN_SUBWAY_OPERATION_SERVICE_KEY_ENCODING` 존재
- `BUSAN_SUBWAY_OPERATION_SERVICE_KEY_DECODING` 존재

## 실행 기록

```bash
curl -G "https://apis.data.go.kr/6260000/BusanBIMS/busStopList" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=3" \
  --data-urlencode "bstopnm=부산시청" \
  --data-urlencode "serviceKey=$BUSAN_BIMS_SERVICE_KEY_DECODING"

curl -G "https://apis.data.go.kr/6260000/BusanBIMS/stopArrByBstopid" \
  --data-urlencode "bstopid=164720101" \
  --data-urlencode "serviceKey=$BUSAN_BIMS_SERVICE_KEY_DECODING"

curl -G "https://api.odcloud.kr/api/15082980/v1/uddi:e9c28907-a511-428d-b5ec-e1c6c988396a" \
  --data-urlencode "page=1" \
  --data-urlencode "perPage=1" \
  --data-urlencode "returnType=JSON" \
  --data-urlencode "serviceKey=$BUSAN_SUBWAY_OPERATION_SERVICE_KEY_DECODING"
```

## 결론

이번 재검증 기준 Step 1 공공데이터 인증 상태는 아래처럼 정리된다.

- 부산 BIMS: 인증 통과 및 실제 조회 성공
- 부산도시철도 운행 정보: 인증 통과 및 실제 조회 성공

즉 현재 시점의 핵심 산출물은 아래다.

- 버스 정류장 조회 성공
- 버스 도착정보 조회 성공
- 지하철 운행 구간 / 정거장 도착시각 / 정거장 출발시각 조회 성공
- 버스와 지하철 모두 연결 키 및 시간 필드 확보
