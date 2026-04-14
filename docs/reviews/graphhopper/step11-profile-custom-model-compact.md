# Step 11 Profile Custom Model Compact Review

- 기준 문서: `AGENTS.md`, `docs/ARD/erd.md`, `docs/plans/graphhopper/10_ROUTE_OPTION_VALIDATION.md`
- 참고 문서: `docs/reviews/graphhopper/step10-graphhopper-encoded-value-alignment-compact.md`, `docs/reviews/graphhopper/step10-route-option-validation-compact.md`
- 작업 일자: 2026-04-14

## 목적

시각장애인과 휠체어 사용자를 1차 서비스 사용자군으로 두고, `SHORTEST` / `SAFE`를 profile 수준에서 분리한 4개 GraphHopper custom model을 구성한다.

이번 단계의 목표는 운영용 품질을 완성하는 것이 아니라, 아래 네 profile이 실제 GraphHopper graph 위에서 함께 로드되고 최소한의 라우팅 차이를 만들어내는지 확인하는 것이다.

- `visual_shortest`
- `visual_safe`
- `wheelchair_shortest`
- `wheelchair_safe`

## 반영 내용

수정 파일:

- `infra/graphhopper/config-foot.yml`
- `infra/graphhopper/ieumgil-foot-base.json`
- `infra/graphhopper/visual-shortest.json`
- `infra/graphhopper/visual-safe.json`
- `infra/graphhopper/wheelchair-shortest.json`
- `infra/graphhopper/wheelchair-safe.json`

생성 산출물:

- `ieumgil-osm-etl-poc/data/graphhopper/busan_profiles_v1`

## 설계 기준

### 1. `SHORTEST`

- 각 사용자군에서 “최소한의 이동 가능성 제약”만 반영한 profile
- 거리 성향을 강하게 두기 위해 `distance_influence`를 높게 설정

### 2. `SAFE`

- 같은 사용자군 안에서 안전/편의 penalty를 추가한 profile
- detour 허용을 위해 `distance_influence`를 낮추고, `priority` / `speed`로 회피 규칙을 부여

### 3. 사용자군별 차이

- `visual`
  - 비신호 횡단 회피
  - 신호 횡단 및 sidewalk 계열 선호
  - 계단은 완전 금지가 아니라 강한 회피
- `wheelchair`
  - 계단은 `SHORTEST`부터 하드 금지
  - `SAFE`에서는 bad surface, 경사, 비신호 횡단 추가 회피

## 프로필별 규칙

### `visual_shortest`

- `distance_influence = 120`
- 추가 회피 규칙 없음

의도:

- 기존 `foot`에 가장 가까운 shortest 기준
- 시각장애인용 `SAFE`와 비교할 기준선 역할

### `visual_safe`

- `distance_influence = 45`
- `road_class == STEPS`: 강한 회피
- `crossing == TRAFFIC_SIGNALS`: 선호
- `crossing == UNCONTROLLED || crossing == UNMARKED`: 회피
- `footway == SIDEWALK || footway == TRAFFIC_ISLAND`: 선호

의도:

- 비신호 횡단 회피를 최우선 안전 규칙으로 둔다
- 계단은 차선 회피 규칙으로 둔다

### `wheelchair_shortest`

- `distance_influence = 110`
- `road_class == STEPS`: 금지

의도:

- 휠체어의 최소 feasibility를 `SHORTEST`부터 반영한다
- 추가 안전 penalty는 아직 넣지 않는다

### `wheelchair_safe`

- `distance_influence = 35`
- `road_class == STEPS`: 금지
- `crossing == TRAFFIC_SIGNALS`: 선호
- `crossing == UNCONTROLLED || crossing == UNMARKED`: 회피
- `surface == COBBLESTONE/GRAVEL/FINE_GRAVEL/GROUND/DIRT/GRASS/SAND/OTHER`: 강한 회피
- `footway == SIDEWALK || footway == ACCESS_AISLE`: 선호
- `average_slope >= 4`: 감속

의도:

- 휠체어 사용자의 실질적 부담 요인인 계단, 거친 surface, 비신호 횡단을 동시에 줄인다

## 검증 결과

### 1. 4개 profile이 GraphHopper `/info`에 정상 등록됐다

확인된 profile:

- `visual_shortest`
- `visual_safe`
- `wheelchair_shortest`
- `wheelchair_safe`

동시에 `crossing`, `footway`, `surface`, `average_slope`, `osm_way_id` EV도 유지됐다.

### 2. 비신호 횡단 후보 OD에서는 `SAFE`가 실제로 다른 경로를 선택했다

검증 OD:

- 시작: `35.1497707, 129.0656452`
- 종료: `35.1578066, 129.0510036`

결과:

- `visual_shortest`
  - 거리: `1914.875m`
  - 시간: `1378.711s`
- `visual_safe`
  - 거리: `2044.669m`
  - 시간: `1472.162s`
- `wheelchair_shortest`
  - 거리: `1914.875m`
  - 시간: `1378.711s`
- `wheelchair_safe`
  - 거리: `2044.669m`
  - 시간: `1472.162s`

해석:

- `SAFE` 두 profile 모두 shortest와 다른 geometry를 선택했다.
- 이번 OD에서는 시각장애인/휠체어 `SAFE` 결과가 동일했다.
- 이 구간에서는 `crossing` penalty가 실제 분기 원인으로 작동했다고 보는 것이 타당하다.

### 3. 계단 대표 OD에서는 `wheelchair_shortest`가 shortest와 다른 경로를 선택했다

검증 OD:

- 시작: `35.1517986, 129.0665998`
- 종료: `35.1618369, 129.0700577`

결과:

- `visual_shortest`
  - 거리: `1498.925m`
  - 시간: `1098.764s`
- `visual_safe`
  - 거리: `1508.865m`
  - 시간: `1086.384s`
- `wheelchair_shortest`
  - 거리: `1508.865m`
  - 시간: `1086.384s`
- `wheelchair_safe`
  - 거리: `1508.865m`
  - 시간: `1086.384s`

해석:

- `wheelchair_shortest`가 `visual_shortest`보다 약 `9.94m` 우회했다.
- 이는 `road_class == STEPS` 금지가 실제 분기를 만들었다는 뜻이다.
- `visual_safe`도 계단 회피 규칙 때문에 같은 대체 경로를 선택했다.

## 한계

### 1. `average_slope`는 현재 graph에서 실효성이 낮다

이번 graph는 `elevation=false` 상태로 import됐다.

즉 `average_slope` EV는 schema에는 존재하지만, 현재 1차 검증에서는 경사 기반 penalty가 사실상 의미 있게 작동하지 않을 가능성이 높다.

따라서 `wheelchair_safe`의 slope 규칙은 “미래 대응 준비”에 가깝다.

### 2. `has_curb_gap`, `has_elevator`, `has_audio_signal`, `has_braille_block`은 아직 profile 규칙에 못 넣었다

이 값들은 built-in EV가 아니라서, 지금 단계의 config/custom model만으로는 사용할 수 없다.

즉 이번 1차 profile은 아래 범위까지만 반영한다.

- `road_class`
- `crossing`
- `footway`
- `surface`
- `average_slope`

## 실행 기록

```bash
java -Xms512m -Xmx512m \
  -Ddw.graphhopper.datareader.file=/Users/jangjooyoon/Desktop/JooYoon/ssafy/ieumgil-poc/ieumgil-osm-etl-poc/data/raw/busan.osm.pbf \
  -Ddw.graphhopper.graph.location=/Users/jangjooyoon/Desktop/JooYoon/ssafy/ieumgil-poc/ieumgil-osm-etl-poc/data/graphhopper/busan_profiles_v1 \
  -jar /Users/jangjooyoon/Desktop/JooYoon/ssafy/ieumgil-poc/infra/graphhopper/graphhopper-web-11.0.jar \
  server /Users/jangjooyoon/Desktop/JooYoon/ssafy/ieumgil-poc/infra/graphhopper/config-foot.yml

curl 'http://localhost:8989/info'

curl 'http://localhost:8989/route?profile=visual_shortest&point=35.1497707,129.0656452&point=35.1578066,129.0510036&points_encoded=false&instructions=false&calc_points=true'
curl 'http://localhost:8989/route?profile=visual_safe&point=35.1497707,129.0656452&point=35.1578066,129.0510036&points_encoded=false&instructions=false&calc_points=true'
curl 'http://localhost:8989/route?profile=wheelchair_shortest&point=35.1497707,129.0656452&point=35.1578066,129.0510036&points_encoded=false&instructions=false&calc_points=true'
curl 'http://localhost:8989/route?profile=wheelchair_safe&point=35.1497707,129.0656452&point=35.1578066,129.0510036&points_encoded=false&instructions=false&calc_points=true'

curl 'http://localhost:8989/route?profile=visual_shortest&point=35.1517986,129.0665998&point=35.1618369,129.0700577&points_encoded=false&instructions=false&calc_points=true'
curl 'http://localhost:8989/route?profile=visual_safe&point=35.1517986,129.0665998&point=35.1618369,129.0700577&points_encoded=false&instructions=false&calc_points=true'
curl 'http://localhost:8989/route?profile=wheelchair_shortest&point=35.1517986,129.0665998&point=35.1618369,129.0700577&points_encoded=false&instructions=false&calc_points=true'
curl 'http://localhost:8989/route?profile=wheelchair_safe&point=35.1517986,129.0665998&point=35.1618369,129.0700577&points_encoded=false&instructions=false&calc_points=true'
```

## 결론

이번 1차 설계 결과는 아래와 같다.

- 4개 profile이 GraphHopper에 정상 등록됐다.
- `SAFE` / `SHORTEST` 분기가 시각장애인, 휠체어 프로필 모두에서 실제 geometry 차이를 만들었다.
- `wheelchair_shortest`는 `SHORTEST` 단계부터 계단 금지를 반영하는 구조로 동작한다.
- 다만 경사도와 접근성 세부 속성은 아직 데이터/EV 한계가 있으므로, 운영 품질을 논하기 전에 추가 import 확장이 필요하다.
