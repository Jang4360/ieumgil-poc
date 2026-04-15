# Step 4-6 Mixed Transit Walk Validation

## 목적
- `04_WALK_SEGMENT_EXTRACTION_VALIDATION.md`
- `05_WALK_ROUTE_INPUT_MAPPING_VALIDATION.md`
- `06_ACCESSIBILITY_DATA_INTEGRATION_REVIEW.md`

위 3개 문서를 기준으로, `도보 + 버스 + 지하철`이 섞인 실제 대중교통 후보 경로 1건을 골라 다음을 검증했다.

1. ODsay 경로에서 도보 구간을 안정적으로 추출할 수 있는지
2. 추출한 도보 anchor를 현재 보행 경로 API 입력 구조 `startPoint/endPoint`로 변환할 수 있는지
3. 변환된 도보 입력을 GraphHopper 보행 프로필에 실제로 넣어 route/snapping 검증이 가능한지
4. 같은 mixed path 안에서 버스/지하철 접근성 데이터를 현재 단계에서 어디까지 붙일 수 있는지

## 추가 구현 여부
- Step 4~6 계획 문서는 도보 구간 추출, 입력 매핑, 접근성 통합 검토를 각각 정의하고 있었지만, `도보 + 버스 + 지하철 혼합 path`를 하나의 실제 시나리오로 끝까지 관통 검증하는 스크립트는 없었다.
- 이번 작업에서 mixed path 전용 검증 스크립트를 새로 추가했다.

## 구현 산출물
- 스크립트: [validate_mixed_transit_walk_path.py](C:/Users/SSAFY/poc/scripts/transportation/validate_mixed_transit_walk_path.py)
- 실행 아티팩트: [step4-6-mixed-transit-walk-validation-artifact.json](C:/Users/SSAFY/poc/docs/reviews/transportation/step4-6-mixed-transit-walk-validation-artifact.json)

## 재현 명령
```powershell
python C:\Users\SSAFY\poc\scripts\transportation\validate_mixed_transit_walk_path.py
```

## 검증 시나리오
- 시나리오: `반송시장 -> 오시리아역`
- 기준일: `2026-04-15`
- 사용 데이터셋:
  - 경로 후보: `ODsay`
  - 버스 접근성/도착: `부산 BIMS`
  - 지하철 운영 데이터: `부산교통공사/odcloud`
  - 도보 라우팅 검증: 로컬 `GraphHopper wheelchair_safe / wheelchair_shortest`

## ODsay mixed path 확인 결과
반송시장 -> 오시리아역의 상위 3개 경로는 모두 mixed path였다.

| path index | 총 시간 | 모드 시퀀스 | mixed 여부 |
| --- | --- | --- | --- |
| 0 | `42분` | `WALK -> BUS -> WALK -> SUBWAY -> WALK` | 예 |
| 1 | `50분` | `WALK -> BUS -> WALK -> SUBWAY -> WALK` | 예 |
| 2 | `48분` | `WALK -> BUS -> WALK -> SUBWAY -> WALK` | 예 |

이번 검증은 가장 빠른 `path 0`을 기준 path로 선택했다.

## 선택 경로 구조
| 순서 | 구간 타입 | 거리 | 시간 | 세부 |
| --- | --- | --- | --- | --- |
| 1 | WALK | `12m` | `1분` | 출발지 -> 반송시장 버스 승차 anchor |
| 2 | BUS | `9593m` | `33분` | `기장군11`, `반송시장 -> 동해선기장역.기장중학교` |
| 3 | WALK | `233m` | `3분` | 버스 하차 -> 기장역 출구 anchor |
| 4 | SUBWAY | `5700m` | `4분` | `동해선`, `기장 -> 오시리아` |
| 5 | WALK | `1m` | `1분` | 오시리아 출구 anchor -> 최종 도착지 |

## Step 4: 도보 구간 추출 결과
ODsay `subPath`에서 `trafficType=3` 구간 3개를 추출했다.

도보 구간 anchor 우선순위는 아래처럼 정했다.
- 출발 도보: `사용자 입력 좌표 -> 다음 transit 승차 좌표`
- 환승 도보: `이전 transit 하차 좌표 -> 다음 transit 승차 좌표`
- 지하철 연결 시: 역 내부 좌표보다 `startExitX/Y`, `endExitX/Y`가 있으면 출구 좌표를 우선 사용
- 도착 도보: `이전 transit 하차 좌표 -> 사용자 입력 좌표`

## Step 5: 보행 경로 입력 매핑 결과
현재 보행 경로 API 명세의 `startPoint`, `endPoint`, `routeOptions` 구조로 3개 도보 구간 모두 변환했다.

| 도보 구간 | 역할 | 시작 anchor | 종료 anchor | 매핑 결과 |
| --- | --- | --- | --- | --- |
| 1 | ACCESS | `USER_REQUEST(반송시장)` | `TRANSIT_START(반송시장)` | 성공 |
| 2 | TRANSFER | `BUS 하차 정류장` | `SUBWAY_EXIT(기장 출구 1)` | 성공 |
| 3 | EGRESS | `SUBWAY_EXIT(오시리아 출구 1)` | `USER_REQUEST(오시리아역)` | 성공 |

실제 생성된 요청 구조 예시는 아래와 같다.

```json
{
  "startPoint": { "lat": 35.243524, "lng": 129.216579 },
  "endPoint": { "lat": 35.24348095488466, "lng": 129.2186160647464 },
  "routeOptions": ["SAFE", "SHORTEST"]
}
```

## Step 5: GraphHopper 실행 테스트 결과
스크립트는 로컬 GraphHopper 서버가 내려가 있으면 `graphhopper-web-11.0.jar`와 기존 Busan graph cache를 이용해 서버를 자동 기동한 뒤, 각 도보 구간을 `wheelchair_safe`, `wheelchair_shortest` 프로필로 모두 호출했다.

3개 도보 구간 모두 route 계산은 성공했다.

| 도보 구간 | SAFE 거리 | SAFE snap 상태 | SHORTEST 거리 | SHORTEST snap 상태 | 해석 |
| --- | --- | --- | --- | --- | --- |
| 1 | `14.911m` | 시작 `ACCEPT`, 종료 `ACCEPT` | `14.911m` | 시작 `ACCEPT`, 종료 `ACCEPT` | 출발 도보는 안정적 |
| 2 | `273.324m` | 시작 `ACCEPT`, 종료 `ACCEPT` | `273.324m` | 시작 `ACCEPT`, 종료 `ACCEPT` | 환승 도보도 안정적 |
| 3 | `44.893m` | 시작 `ACCEPT`, 종료 `WARN` | `44.893m` | 시작 `ACCEPT`, 종료 `WARN` | ODsay상 1m지만 실제 보행 anchor는 더 벌어짐 |

중요한 점은 마지막 egress 도보다.
- ODsay 구간 정보는 `1m`로 매우 짧게 나오지만
- 실제 출구 좌표와 사용자 도착 좌표를 GraphHopper에 넣으면 약 `44.9m`
- 종료 snap distance는 약 `33.5m`로 `WARN`

즉, mixed path에서도 `도보 구간 수치만 믿지 말고`, 실제 anchor 좌표로 다시 보행 네트워크 검증을 해야 한다.

## Step 6: 접근성 데이터 통합 결과

### 1. 도보 구간
현재 단계에서 즉시 붙일 수 있는 값:
- `distance_meter`
- `estimated_time_minute`
- `snap_status`
- `average_slope_range`
- `has_elevator`
- `has_curb_gap`
- `has_audio_signal`
- `has_braille_block`
- `width_meter_range`

이번 실행에서는 세 도보 구간 모두 GraphHopper 결과를 받았고, 경로 입력 매핑도 문제 없었다.

### 2. 버스 구간
선택 경로의 버스 구간은 `기장군11`이었다.

부산 BIMS에서 바로 붙일 수 있는 값:
- `min1`, `station1`
- `lowplate1`
- `min2`, `station2`
- `lowplate2`

실행 결과:
- 승차 정류장 `반송시장(184870102)` 기준 실시간 도착 조회 성공
- 해당 노선 `기장군11(5291611000)` 매칭 성공
- `lowplate1=0`, `lowplate2=0`

즉, mixed path 내부 버스 구간에 대해서는 `실시간 도착`과 `저상버스 여부`를 현재 구조에서도 붙일 수 있다.

### 3. 지하철 구간
선택 경로의 지하철 구간은 `동해선`, `기장 -> 오시리아`였다.

실행 결과:
- `부산교통공사/odcloud` 운영 데이터셋과 매칭 실패
- 현재 매칭 사유: `no odcloud row contains both stations on the same normalized line key`
- 역 엘리베이터/출입구 접근성 필드는 현재 연결된 데이터셋에 없음

즉, mixed path 내부 지하철 구간은 이번 케이스에서 `운영 데이터 매칭`조차 실패했고, 역사 접근성까지 붙이기에는 현재 데이터셋 구성이 부족하다.

## 종합 판단
- `도보 + 버스 + 지하철` 혼합 경로는 ODsay 응답에서 실제로 추출된다.
- 도보 구간 3개는 모두 현재 보행 경로 API 입력 구조로 변환 가능하다.
- 변환된 도보 입력은 GraphHopper `wheelchair_safe/shortest` 프로필에서 실제 route/snapping 검증까지 성공했다.
- 버스 구간은 BIMS 기준으로 `실시간 도착 + 저상버스 여부`를 붙일 수 있다.
- 지하철 구간은 이번 mixed path의 `동해선`에서 `부산교통공사/odcloud` 매칭이 실패했고, 역사 접근성 데이터도 현재 연결되어 있지 않다.

## 결론
현재 PoC 기준으로 mixed path 구현 가능 범위는 다음과 같다.

- 가능:
  - ODsay mixed path 추출
  - 도보 구간 분리
  - 도보 구간을 우리 보행 API 입력으로 매핑
  - GraphHopper로 도보 leg 재검증
  - 버스 실시간/저상버스 정보 결합

- 보류:
  - `동해선` 구간의 odcloud 매칭 안정화
  - 지하철 역사 엘리베이터/출입구 접근성 결합
  - 역 내부 동선까지 포함한 세밀한 환승 보행 anchor 보정

## 후속 작업
- `동해선` 운영 주체 기준 데이터셋을 별도로 확인해야 한다.
- 지하철 접근성은 운영 시각표 데이터가 아니라 `역사/출입구/엘리베이터` 단위 데이터셋을 추가로 연결해야 한다.
- mixed path의 egress walk처럼 ODsay의 매우 짧은 도보 구간도 실제 보행 네트워크에서는 더 길어질 수 있으므로, 최종 서비스 응답은 transit 원본 거리 대신 `재계산된 walk leg`를 우선 사용해야 한다.
