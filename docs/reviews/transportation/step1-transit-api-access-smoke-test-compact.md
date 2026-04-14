# Step 1 Transit API Access Smoke Test Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/transportation/00_EXECUTION_ROADMAP.md`, `docs/plans/transportation/01_TRANSIT_DATA_SOURCE_SURVEY.md`
- 작업 일자: 2026-04-14
- 작업 범위: `부산 BIMS`, `부산 도시철도 열차시각표 조회 서비스` 실제 인증 재검증

## 목적

`docs/plans/transportation/01_TRANSIT_DATA_SOURCE_SURVEY.md`에서 1차 원천으로 잡은 공공데이터 API 2종을
실제 `.env`에 넣은 키로 다시 호출해 아래를 확인한다.

- 인증이 실제로 통과하는지
- 최소 1건 조회가 가능한지
- Step 1 완료 기준에 필요한 연결 키와 시간 필드가 보이는지

## 이번 재검증 범위

- 포함: `부산 BIMS`, `부산 도시철도 열차시각표 조회 서비스`
- 제외: `ODsay`

`ODsay`는 이번 요청 범위에서 제외했고, 아래 내용은 공공데이터 API 재검증 결과만 반영한다.

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
- 샘플 응답 기준으로 `131`, `141` 노선이 조회됐고 두 노선 모두 `lowplate1=1`, `lowplate2=1` 값이 포함됐다.

판단:

- 부산 BIMS는 실제로 인증 통과와 조회 성공을 확인했다.
- 현재 `.env` 기준으로는 `DECODING` 키를 그대로 사용하면 정상 호출된다.
- 현재 상태에서 BIMS는 Step 1의 `버스 정류장 조회`, `실시간 도착시간 조회`, `연결 키 확인` 용도로 사용할 수 있다.

### 2. 부산 도시철도 열차시각표 조회 서비스 검증

공식 문서 기준 서비스 정보:

- 서비스URL: `http://data.humetro.busan.kr/voc/api/open_api_process.tnn`
- 필수 파라미터: `act`, `scode`
- 옵션 파라미터: `day`, `updown`, `stime`, `etime`, `enum`

검증 대상:

- `open_api_process.tnn`

입력:

- `act=xml`
- `scode=101`
- `day=1`
- `updown=0`
- `stime=1300`
- `etime=1400`
- `enum=1`

결과:

- `.env`에 `BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_ENCODING`, `BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_DECODING` 값이 존재했다.
- 이미지 예시와 동일한 요청 형태인 `act=xml`, `scode=101`, `day=1`, `updown=0`, `stime=1300`, `etime=1400`, `enum=1`로 재호출했다.
- `BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_ENCODING`을 URL에 그대로 붙여 호출해도 XML 응답 기준 `resultCode=30`, `SERVICE KEY IS NOT REGISTERED ERROR.`
- `BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_DECODING`을 `--data-urlencode`로 전달해도 XML 응답 기준 `resultCode=30`, `SERVICE KEY IS NOT REGISTERED ERROR.`
- `BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_ENCODING`을 `--data-urlencode`로 전달해도 XML 응답 기준 `resultCode=30`, `SERVICE KEY IS NOT REGISTERED ERROR.`
- 비교용으로 `act=json`, `enum=1` 조합도 호출했지만 JSON 응답 기준 동일하게 `resultCode=30`, `SERVICE KEY IS NOT REGISTERED ERROR.`
- HTTP 레벨에서는 모두 `200 OK`로 응답했고, 엔드포인트와 파라미터 구조 자체는 정상 동작한다.

판단:

- 부산 도시철도 열차시각표 조회 서비스는 엔드포인트 접근은 가능하지만, 현재 키가 이 서비스에 등록된 상태로 인식되지 않는다.
- 문서 예시 파라미터로 바꿔도 결과가 동일하므로, 현재 이슈는 요청 형식보다 `서비스키 등록/매핑 상태`에 가깝다.
- 이번 재검증에서도 실제 시간표 데이터는 받지 못했다.
- 현재 상태에서는 Step 1의 `지하철 도착예정 시각 조회용 API 확정`을 완료로 보기 어렵다.

## API별 상태 요약

| API | 조회 목표 | 호출 결과 | 현재 판단 |
| --- | --- | --- | --- |
| 부산 BIMS | 버스 정류장 조회, 실시간 도착시간 조회 | `DECODING` 키 기준 `NORMAL SERVICE` | 사용 가능 |
| 부산 도시철도 열차시각표 | 역 기준 도착예정 시각 조회 | `SERVICE KEY IS NOT REGISTERED ERROR.` | 활용승인/키 매핑 재확인 필요 |

## 확인된 사실

1. 워크스페이스 루트 `.env`에는 실제 공공데이터 키가 들어 있다.
2. 부산 BIMS는 `ENCODING` 키로는 실패했고, `DECODING` 키는 현재 `.env` 원문 기준으로 정상 호출된다.
3. 부산 BIMS 응답에서 `bstopid`, `arsno`, 좌표, `lineid`, `lowplate1`, `lowplate2`를 확인했다.
4. 부산 도시철도 열차시각표 서비스는 문서 예시 파라미터와 다른 전달 방식으로 다시 호출해도 현재 키를 `등록되지 않은 키`로 처리한다.

## 현재 단계 판단

`01_TRANSIT_DATA_SOURCE_SURVEY.md` 기준으로 보면 버스 쪽은 Step 1 목적을 충족했고, 지하철 쪽은 아직 인증 정리가 남았다.

현재 바로 진행 가능한 다음 작업은 아래 순서가 적절하다.

1. 부산 도시철도 열차시각표
`15000522` 데이터셋 활용신청 상태와 현재 서비스키 매핑 상태를 다시 확인한다.

2. 지하철 재검증
키 매핑이 정상화되면 같은 시나리오로 다시 호출해 역 기준 시간표 필드와 도착예정 시각 필드를 확인한다.

## 환경 정리

이번 재검증에서 확인한 환경 상태는 아래와 같다.

- `.env` 존재
- `BUSAN_BIMS_SERVICE_KEY_ENCODING` 존재
- `BUSAN_BIMS_SERVICE_KEY_DECODING` 존재
- `BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_ENCODING` 존재
- `BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_DECODING` 존재

## 실행 기록

```bash
set -a && source .env && set +a

curl -sS -D - -G "$BUSAN_BIMS_API_BASE_URL/busStopList" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=3" \
  --data-urlencode "bstopnm=부산시청" \
  --data-urlencode "serviceKey=$BUSAN_BIMS_SERVICE_KEY_ENCODING"

curl -sS -D - -G "$BUSAN_BIMS_API_BASE_URL/busStopList" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=3" \
  --data-urlencode "bstopnm=부산시청" \
  --data-urlencode "serviceKey=$BUSAN_BIMS_SERVICE_KEY_DECODING"

curl -sS -D - -G "$BUSAN_BIMS_API_BASE_URL/busStopList" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=3" \
  --data-urlencode "bstopnm=부산시청" \
  --data-urlencode "serviceKey=$BUSAN_BIMS_SERVICE_KEY_DECODING"

curl -sS -D - -G "$BUSAN_BIMS_API_BASE_URL/stopArrByBstopid" \
  --data-urlencode "bstopid=164720101" \
  --data-urlencode "serviceKey=$BUSAN_BIMS_SERVICE_KEY_DECODING"

curl -sS -D - \
  "$BUSAN_SUBWAY_TIMETABLE_API_BASE_URL?act=xml&scode=101&day=1&updown=0&stime=1300&etime=1400&enum=1&serviceKey=$BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_ENCODING"

curl -sS -D - -G "$BUSAN_SUBWAY_TIMETABLE_API_BASE_URL" \
  --data-urlencode "act=xml" \
  --data-urlencode "scode=101" \
  --data-urlencode "day=1" \
  --data-urlencode "updown=0" \
  --data-urlencode "stime=1300" \
  --data-urlencode "etime=1400" \
  --data-urlencode "enum=1" \
  --data-urlencode "serviceKey=$BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_ENCODING"

curl -sS -D - -G "$BUSAN_SUBWAY_TIMETABLE_API_BASE_URL" \
  --data-urlencode "act=xml" \
  --data-urlencode "scode=101" \
  --data-urlencode "day=1" \
  --data-urlencode "updown=0" \
  --data-urlencode "stime=1300" \
  --data-urlencode "etime=1400" \
  --data-urlencode "enum=1" \
  --data-urlencode "serviceKey=$BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_DECODING"

curl -sS -D - -G "$BUSAN_SUBWAY_TIMETABLE_API_BASE_URL" \
  --data-urlencode "act=json" \
  --data-urlencode "scode=101" \
  --data-urlencode "day=1" \
  --data-urlencode "updown=0" \
  --data-urlencode "stime=1300" \
  --data-urlencode "etime=1400" \
  --data-urlencode "enum=1" \
  --data-urlencode "serviceKey=$BUSAN_SUBWAY_TIMETABLE_SERVICE_KEY_DECODING"
```

## 결론

이번 재검증 기준 Step 1 공공데이터 인증 상태는 아래처럼 정리된다.

- 부산 BIMS: 인증 통과 및 실제 조회 성공
- 부산 도시철도 열차시각표: 엔드포인트 접근 가능, 인증 미통과

즉 현재 시점의 핵심 산출물은 아래다.

- 버스 정류장 조회 성공
- 버스 도착정보 조회 성공
- 버스 연결 키와 저상버스 관련 필드 확인
- 지하철 서비스키 미등록 상태 확인

Step 1을 완전히 닫으려면 부산 도시철도 열차시각표 서비스의 키 매핑부터 정상화해야 한다.
