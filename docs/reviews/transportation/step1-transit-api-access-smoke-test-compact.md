# Step 1 Transit API Access Smoke Test Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/transportation/00_EXECUTION_ROADMAP.md`, `docs/plans/transportation/01_TRANSIT_DATA_SOURCE_SURVEY.md`
- 작업 일자: 2026-04-14
- 작업 범위: `ODsay`, `부산 BIMS`, `부산 도시철도 열차시각표 조회 서비스`의 실제 호출 가능 여부 1차 검증

## 목적

`docs/plans/transportation/01_TRANSIT_DATA_SOURCE_SURVEY.md` 기준으로 확정한 3개 API가 현재 로컬 환경에서 실제 호출 가능한지 확인한다.

이번 단계에서는 통합 응답 매핑을 구현하지 않고 아래만 검증한다.

- 인증키가 실제로 통과하는지
- 최소 1건 조회가 가능한지
- 출발지 / 도착지 조회, 경로 조회, 도착시간 조회, 이동시간 조회에 필요한 입력값이 확인되는지

## 수행 내용

### 1. ODsay 호출 검증

검증 대상:

- `searchStation`
- `searchPubTransPathT`

입력:

- 역명: `서면역`
- 좌표쌍: `129.0591028,35.1577084` -> `129.0403,35.1151`

결과:

- 두 호출 모두 `{"error":[{"code":"500","message":"[ApiKeyAuthFailed] ApiKey authentication failed."}]}` 응답
- 현재 공인 IP는 `59.20.195.127`로 확인했고 `.env`에 기록된 `ODSAY_SERVER_IP`와 일치
- raw 키와 URL-encoded 키 모두 동일하게 인증 실패

판단:

- 네트워크나 좌표 문제가 아니라 `ODsay Server API Key 인증` 단계에서 막히고 있다.
- 가능한 원인:
  - 애플리케이션 활성화 직후 반영 지연
  - 등록된 플랫폼/키 타입 불일치
  - ODsay 측 인증 상태 미반영

즉, 현재 시점에서는 출발지 / 도착지 조회와 경로 조회를 실제 성공으로 판정할 수 없다.

### 2. 부산 BIMS 호출 검증

검증 대상:

- `busStopList`
- `stopArrByBstopid`

입력:

- 정류장명: `부산시청`

결과:

- `Encoding` 키 사용 시 HTTP `401`
- `Decoding` 키를 URL-encoded 해서 사용해도 HTTP `401`

판단:

- 부산 BIMS는 현재 서비스키 인증 단계에서 막히고 있다.
- 응답 본문이 아니라 HTTP `401`이므로 키 전달/승인 상태를 먼저 다시 확인해야 한다.
- 현재 상태에서는 버스 정류장 조회와 실시간 도착시간 조회를 성공으로 볼 수 없다.

### 3. 부산 도시철도 열차시각표 조회 서비스 검증

공식 문서 기준 확인한 서비스 정보:

- 서비스URL: `http://data.humetro.busan.kr/voc/api/open_api_process.tnn`
- 필수 파라미터: `act`, `scode`
- 옵션 파라미터: `day`, `updown`, `stime`, `etime`, `enum`

검증 대상:

- `open_api_process.tnn`

입력:

- `act=json`
- `scode=101`
- `day=1`
- `updown=0`
- `stime=1300`
- `etime=1400`
- `enum=3`

결과:

- 응답: `{"response":{"header":{"resultCode":"30","resultMsg":"SERVICE KEY IS NOT REGISTERED ERROR."}}}`

판단:

- 서비스 URL과 요청 파라미터 구조는 문서와 일치한다.
- 하지만 현재 공공데이터포털 키가 이 서비스에 등록된 상태로 인식되지 않는다.
- 현재 상태에서는 지하철 도착예정 시각 조회를 성공으로 볼 수 없다.

## API별 상태 요약

| API | 조회 목표 | 호출 결과 | 현재 판단 |
| --- | --- | --- | --- |
| ODsay | 출발지 / 도착지 조회, 경로 조회, 이동시간 조회 | `ApiKeyAuthFailed` | 인증 반영 전, 보류 |
| 부산 BIMS | 버스 정류장 조회, 실시간 도착시간 조회 | HTTP `401` | 서비스키 재확인 필요 |
| 부산 도시철도 열차시각표 | 역 기준 도착예정 시각 조회 | `SERVICE KEY IS NOT REGISTERED ERROR.` | 데이터셋 활용승인/키 매핑 재확인 필요 |

## 확인된 사실

1. 부산 도시철도 열차시각표 조회 서비스의 실제 호출 URL은 문서 기준으로 확인됐다.
2. 로컬 공인 IP는 ODsay 등록값과 일치한다.
3. 세 API 모두 현재는 `응답 구조 검증` 단계까지 못 갔고, `인증 검증` 단계에서 막혔다.

## 현재 단계 판단

`01_TRANSIT_DATA_SOURCE_SURVEY.md` 기준으로 보면, 조회 구조 자체를 더 파기하기 전에 먼저 인증 상태를 정상화해야 한다.

현재 바로 진행 가능한 다음 작업은 아래 순서가 적절하다.

1. ODsay
애플리케이션 설정 화면에서 `Server` 플랫폼, 등록 IP, 발급 키를 다시 확인하고 반영 시간을 둔 뒤 재시도

2. 부산 BIMS
해당 데이터셋 활용신청 상태와 실제 발급된 인증키가 유효한지 재확인

3. 부산 도시철도 열차시각표
해당 데이터셋에도 별도 활용신청이 되었는지, 동일 공공데이터포털 인증키가 실제로 매핑됐는지 재확인

## 환경 정리

이번 작업에서 아래 환경 변수 정보를 보강했다.

- `.env`
- `.env.example`

추가 항목:

- `BUSAN_SUBWAY_TIMETABLE_API_BASE_URL=http://data.humetro.busan.kr/voc/api/open_api_process.tnn`

## 실행 기록

```powershell
Invoke-WebRequest -UseBasicParsing `
  "https://api.odsay.com/v1/api/searchStation?stationName=%EC%84%9C%EB%A9%B4%EC%97%AD&apiKey=..."

Invoke-WebRequest -UseBasicParsing `
  "https://api.odsay.com/v1/api/searchPubTransPathT?SX=129.0591028&SY=35.1577084&EX=129.0403&EY=35.1151&apiKey=..."

Invoke-WebRequest -UseBasicParsing `
  "https://apis.data.go.kr/6260000/BusanBIMS/busStopList?pageNo=1&numOfRows=1&bstopnm=%EB%B6%80%EC%82%B0%EC%8B%9C%EC%B2%AD&serviceKey=..."

Invoke-WebRequest -UseBasicParsing `
  "http://data.humetro.busan.kr/voc/api/open_api_process.tnn?act=json&scode=101&day=1&updown=0&stime=1300&etime=1400&enum=3&serviceKey=..."
```

## 결론

작업은 시작했고, 현재 1차 결과는 `인증 상태 확인 완료, 실제 조회는 아직 미통과`다.

즉 지금 단계의 핵심 산출물은 아래다.

- 세 API의 실제 호출 URL과 입력 파라미터 구조 확인
- 로컬 환경 변수 정리
- 인증 실패 유형 식별
- 다음 조치 순서 확정

인증 상태가 정상화되면 다음 단계는 동일 시나리오로 다시 호출해

- ODsay: 출발지 / 도착지 조회, 경로 조회, 이동시간 필드 확인
- 부산 BIMS: 정류장 조회, 노선 조회, 실시간 도착시간 필드 확인
- 부산 도시철도 열차시각표: 역 기준 도착예정 시각 필드 확인

으로 바로 넘어갈 수 있다.
