# 12_CUSTOM_EV_IMPORT_EXTENSION.md

- 기준 문서: `AGENTS.md`, `docs/ARD/erd.md`, `docs/plans/graphhopper/10_ROUTE_OPTION_VALIDATION.md`
- 참고 문서: `docs/reviews/graphhopper/step10-graphhopper-encoded-value-alignment-compact.md`, `docs/reviews/graphhopper/step11-profile-custom-model-compact.md`, `docs/reviews/graphhopper/step4-road-network-generation-compact.md`
- 작업 일자: 2026-04-14

## 목적

`has_curb_gap`, `has_elevator`, `has_audio_signal`, `has_braille_block`, `width_meter`를 GraphHopper 라우팅 입력으로 반영하기 위한 custom encoded value 확장 설계를 정리한다.

이번 문서의 목표는 바로 구현에 들어갈 수 있도록 아래를 한 번에 명확히 하는 것이다.

- custom EV 5개 정의 방식
- 값 출처와 기본값 정책
- GraphHopper import 확장 순서
- 구현 후 검증 항목

## 전제

현재 GraphHopper graph에 이미 반영된 항목:

- `road_class`
- `crossing`
- `footway`
- `surface`
- `average_slope`
- `osm_way_id`

현재 GraphHopper graph에 없는 항목:

- `has_curb_gap`
- `has_elevator`
- `has_audio_signal`
- `has_braille_block`
- `width_meter`

즉 이 네 값은 PostgreSQL `road_segments`나 ETL 산출물에는 있을 수 있지만, 현재 GraphHopper는 라우팅 시 직접 읽지 못한다.

## 핵심 판단

### 1. 이 5개는 built-in EV가 아니라 custom EV가 맞다

현재 GraphHopper 11 built-in import registry로는 아래 5개를 서비스 의미 그대로 직접 지원하지 않는다.

- `has_curb_gap`
- `has_elevator`
- `has_audio_signal`
- `has_braille_block`
- `width_meter`

따라서 라우팅에 쓰려면 아래 둘이 함께 필요하다.

- custom encoded value 정의
- import 시 edge에 값을 채우는 custom parser 또는 import hook

### 2. 1차는 boolean 4개 + numeric 1개로 두는 것이 가장 안전하다

1차 설계 기준 권장 타입:

- `has_curb_gap`: boolean
- `has_elevator`: boolean
- `has_audio_signal`: boolean
- `has_braille_block`: boolean
- `width_meter`: decimal

이유:

- 서비스 ERD와 의미가 맞다.
- custom model 조건식이 단순해진다.
- `width_meter`는 threshold 기반 규칙에 바로 쓸 수 있다.
- 향후 품질 점수나 enum으로 확장하더라도 backward migration이 비교적 쉽다.

### 3. 기본값은 무조건 `false` 또는 `0`으로 확정하면 안 된다

가장 중요한 설계 포인트다.

서비스 DB나 ETL 산출물에서는 `false` 또는 `NULL`이 들어갈 수 있지만, GraphHopper 라우팅용 EV에서는 아래 둘을 구분해야 한다.

- 실제로 없음
- 정보가 없음

특히 아래 속성은 OSM 단독 커버리지가 낮다.

- `has_curb_gap`
- `has_audio_signal`
- `has_braille_block`
- `width_meter`

따라서 라우팅 엔진에서 `false`를 “안전하지 않음” 또는 “없음”으로 강하게 쓰면 오판정이 발생할 수 있다.

또한 `width_meter`는 source 단계에서 `NULL`이 정상값일 수 있으므로, 미측정 폭을 좁은 폭으로 오인하면 안 된다.

## 추천 설계안

### 안 A. 1차 구현 추천안

1차 구현에서는 아래처럼 간다.

- GraphHopper EV:
  - `has_curb_gap`
  - `has_elevator`
  - `has_audio_signal`
  - `has_braille_block`
  - `width_meter`
- 값 출처:
  - OSM에서 직접 판정 가능한 경우만 `true`
  - 그 외는 모두 `false`
  - `width_meter`는 실제 폭 데이터가 있으면 meter 단위 숫자, 없으면 source 단계에서는 `NULL`
- custom model 사용 방식:
  - `true`일 때 선호
  - `false`라고 해서 강한 불이익은 주지 않음
  - `width_meter`는 측정값이 있는 경우에만 threshold 규칙 적용

의미:

- `true`는 신뢰 가능한 positive evidence
- `false`는 “없음 또는 모름”으로 취급
- `width_meter = NULL`은 “미측정”으로 취급

장점:

- 현재 ETL/OSM 품질에 잘 맞는다.
- 잘못된 회피를 줄일 수 있다.
- 바로 구현 가능하다.

단점:

- 데이터가 부족한 구간은 큰 분기 효과가 안 날 수 있다.

### 안 B. 2차 확장안

후속 단계에서 품질이 올라가면 tri-state 또는 quality enum으로 확장한다.

예시:

- `curb_gap_status = MISSING | YES | NO`
- `audio_signal_status = MISSING | YES | NO`
- `width_quality = MISSING | NARROW | PASSABLE | COMFORTABLE`

하지만 이건 1차 구현 난도를 크게 올리므로 지금 권장하지 않는다.

## EV 정의 초안

### 1. `has_curb_gap`

의미:

- 휠체어/유모차/보행약자가 경계석 단차 없이 통과 가능한 구간 여부

권장 타입:

- boolean

권장 해석:

- `true`: curb gap 존재가 명시적으로 확인됨
- `false`: 없음 또는 정보 없음

1차 custom model 사용 방향:

- `wheelchair_safe`: `has_curb_gap == true` 선호
- `wheelchair_shortest`: 아직 미사용 또는 약한 선호

### 2. `has_elevator`

의미:

- 계단 대체 수단으로 elevator를 사용할 수 있는 연결 구간 여부

권장 타입:

- boolean

권장 해석:

- `true`: elevator 존재가 확인됨
- `false`: 없음 또는 정보 없음

1차 custom model 사용 방향:

- `wheelchair_safe`: `has_elevator == true` 선호
- `visual_safe`: 필요 시 약한 선호 가능

주의:

- elevator는 edge 자체보다 연결 지점(node) 속성에 더 가까운 경우가 많다.
- 그래도 1차는 segment/edge 기준 boolean으로 시작하고, 추후 node EV 또는 connector 개념으로 재검토한다.

### 3. `has_audio_signal`

의미:

- 시각장애인을 위한 음향 신호기 존재 여부

권장 타입:

- boolean

권장 해석:

- `true`: 음향 신호 존재가 확인됨
- `false`: 없음 또는 정보 없음

1차 custom model 사용 방향:

- `visual_safe`: `has_audio_signal == true` 선호

주의:

- `false`에 강한 penalty를 주면 데이터 누락 구간을 과도하게 불리하게 만들 수 있다.
- 1차에서는 positive preference만 부여한다.

### 4. `has_braille_block`

의미:

- 점자블록/유도블록 존재 여부

권장 타입:

- boolean

권장 해석:

- `true`: tactile paving 존재가 확인됨
- `false`: 없음 또는 정보 없음

1차 custom model 사용 방향:

- `visual_safe`: `has_braille_block == true` 선호

### 5. `width_meter`

의미:

- 보행 세그먼트의 유효 통행 폭(m)

권장 타입:

- decimal

권장 source 기본값:

- `NULL`

GraphHopper 저장 방식:

- EV에는 SQL `NULL`을 그대로 저장하지 않고 sentinel 값으로 변환
- 1차 권장 sentinel: `0.0`

권장 해석:

- `width_meter > 0`: 실제 측정값 있음
- `width_meter == 0`: 미측정 또는 미확인

1차 custom model 사용 방향:

- `wheelchair_shortest`: `width_meter > 0 && width_meter < 0.8` 이면 하드 금지 또는 거의 0에 가까운 priority
- `wheelchair_safe`: `width_meter > 0 && width_meter < 1.0` 강한 회피
- `wheelchair_safe`: `width_meter > 0 && width_meter >= 1.2` 약한 선호 가능

중요:

- 미측정 폭(`width_meter == 0`)은 경로탐색 알고리즘에서 반영하지 않는다.
- 즉 모든 width 조건식은 반드시 `width_meter > 0` guard를 먼저 둔다.

## 값 출처 설계

### 우선순위 1. OSM 직접 태그

1차 기본값은 OSM/원천 태그 직접 판정이다.

권장 매핑:

- `has_elevator`
  - `elevator=yes`
  - `highway=elevator`
- `has_braille_block`
  - `tactile_paving=yes|contrasted`

1차 구현 판단:

- OSM parser로 직접 넣는 대상은 `has_elevator`, `has_braille_block` 두 개로 한정한다.
- `has_audio_signal`, `has_curb_gap`, `width_meter`는 OSM 태그 후보가 있더라도 1차 구현에서는 OSM parser 대상으로 잡지 않는다.

### 우선순위 2. 서비스 ETL 보정

OSM 직접 태그만으로 부족한 경우 ETL에서 보정한다.

권장 방식:

- OSM raw + 후처리 규칙을 거쳐 `road_segments_service.csv`를 만든다.
- GraphHopper import 직전, 이 CSV 또는 중간 산출물에서 EV 값을 읽어 edge에 주입한다.

적합한 속성:

- `has_curb_gap`
- `has_audio_signal`
- `width_meter`

1차 구현 판단:

- ETL join 대상은 `has_curb_gap`, `has_audio_signal`, `width_meter` 세 개로 고정한다.
- `width_meter`는 ETL source에서 `NULL` 허용, GraphHopper EV에서는 sentinel `0.0`으로 저장한다.
- `width_meter == 0`은 미측정으로 간주하고 경로탐색 알고리즘에 반영하지 않는다.

### 우선순위 3. 공공데이터 / 수동 보정

후속 단계에서는 외부 접근성 데이터나 수동 보정 데이터를 조인할 수 있다.

권장 대상:

- `has_audio_signal`
- `has_curb_gap`
- `has_elevator`
- `width_meter`

## 기본값 정책

### 1차 권장 정책

| 속성 | 기본값 | custom model 기본 해석 |
| --- | --- | --- |
| `has_curb_gap` | `false` | `true`만 선호 |
| `has_elevator` | `false` | `true`만 선호 |
| `has_audio_signal` | `false` | `true`만 선호 |
| `has_braille_block` | `false` | `true`만 선호 |
| `width_meter` | source는 `NULL`, EV는 sentinel `0.0` | `width_meter > 0`일 때만 평가 |

중요:

- `false`에 즉시 penalty를 주지 않는다.
- 먼저 `true` positive evidence만 reward한다.
- 데이터 품질이 올라간 뒤에만 `false` penalty를 검토한다.
- `width_meter == 0`은 미측정으로 보고 어떤 penalty도 주지 않는다.

## GraphHopper import 확장 순서

### Step 1. custom EV 정의

GraphHopper Java 코드에 boolean EV 4개와 numeric EV 1개를 추가한다.

필요 작업:

- `has_curb_gap`
- `has_elevator`
- `has_audio_signal`
- `has_braille_block`
- `width_meter`

형태:

- `SimpleBooleanEncodedValue` 기반
- `width_meter`는 `DecimalEncodedValue` 기반

### Step 2. import registry 등록

GraphHopper import 초기화 과정에서 새 EV가 인식되도록 registry에 등록한다.

필요 결과:

- `graph.encoded_values`에 위 4개 이름을 적으면 import가 가능해야 한다.

### Step 3. parser 또는 import hook 구현

OSM / ETL 입력으로부터 edge별 값을 계산해 EV에 저장한다.

구현 선택지는 두 가지다.

#### 3-A. OSM 태그 직접 parser

장점:

- GraphHopper 기본 OSM import 흐름에 가장 자연스럽게 맞는다.

단점:

- ETL 보정값을 쓰기 어렵다.

#### 3-B. 외부 매핑 파일 join parser

장점:

- 서비스 ETL 결과를 그대로 재사용할 수 있다.
- OSM 단독 한계를 보완할 수 있다.

단점:

- import 시 외부 파일 로딩 규칙을 따로 설계해야 한다.

권장:

- `has_elevator`, `has_braille_block`: OSM 직접 parser
- `has_curb_gap`, `has_audio_signal`, `width_meter`: 외부 매핑 파일 join parser

### Step 4. config 반영

`infra/graphhopper/config-foot.yml`의 `graph.encoded_values`에 아래를 추가한다.

- `has_curb_gap`
- `has_elevator`
- `has_audio_signal`
- `has_braille_block`
- `width_meter`

### Step 5. custom model 반영

profile별 custom model에 긍정 선호 규칙부터 추가한다.

예시:

- `wheelchair_safe`
  - `has_curb_gap == true` 선호
  - `has_elevator == true` 선호
  - `width_meter > 0 && width_meter < 0.8` 금지
  - `width_meter > 0 && width_meter < 1.0` 강한 회피
- `visual_safe`
  - `has_audio_signal == true` 선호
  - `has_braille_block == true` 선호

### Step 6. graph 재import/build

새 EV는 기존 graph에 없으므로 반드시 graph를 새로 만든다.

권장 출력 디렉터리:

- `ieumgil-osm-etl-poc/data/graphhopper/busan_profiles_v2_custom_ev`

## 구현 파일 초안

아래 파일/영역을 수정 대상으로 본다.

- GraphHopper fork 또는 custom source
  - EV 정의 클래스
  - import registry
  - parser / external mapping loader
- 저장소 설정
  - `infra/graphhopper/config-foot.yml`
  - `infra/graphhopper/*.json`

추가 산출물 권장:

- `ieumgil-osm-etl-poc/scripts/build_graphhopper_custom_ev_join.py`
- `ieumgil-osm-etl-poc/data/derived/.../graphhopper_ev_mapping/*.csv`
- `docs/reviews/graphhopper/step13-custom-ev-implementation-compact.md`

## 검증 체크리스트

### 1. import 성공 검증

- `/info`에 EV 4개가 노출되는가
- `/info`에 EV 5개가 노출되는가
- `properties.txt`에 EV 5개가 저장되는가

### 2. 데이터 채움 검증

- EV별 `true` edge 수가 0이 아닌가
- 예상보다 과도하게 많은 `true`가 찍히지 않는가
- `width_meter > 0` edge 수가 0이 아닌가
- `width_meter == 0` edge가 미측정 구간으로만 남는가

### 3. profile 반영 검증

- `visual_safe`에서 `has_audio_signal`, `has_braille_block` 선호가 weight에 반영되는가
- `wheelchair_safe`에서 `has_curb_gap`, `has_elevator` 선호가 weight에 반영되는가
- `wheelchair_shortest`/`wheelchair_safe`에서 `width_meter > 0 && width_meter < 0.8` 조건이 실제 회피를 만드는가
- `width_meter == 0` 구간이 오탐으로 배제되지 않는가

### 4. 회귀 검증

- 기존 `visual_shortest`, `visual_safe`, `wheelchair_shortest`, `wheelchair_safe` 모두 여전히 응답하는가
- Step 11 대표 OD 결과가 과도하게 깨지지 않는가

## 구현 권장 순서

1. `has_elevator`, `has_braille_block` OSM parser 구현
2. `has_curb_gap`, `has_audio_signal`, `width_meter` ETL join parser 구현
3. `build_graphhopper_custom_ev_join.py`로 `way_id + segment_ordinal` 기준 join CSV 생성
4. custom model에는 positive preference와 width threshold만 먼저 추가
5. 라우팅 차이 검증 후 `false` penalty 여부를 별도 판단

## 바로 구현할 때의 결정사항

구현 전에 아래 3가지는 확정해야 한다.

1. GraphHopper fork를 저장소 안에 둘지, 별도 커스텀 jar 빌드 파이프라인으로 관리할지
2. ETL 보정값을 import 시 어떤 파일 포맷으로 넘길지
3. `false`를 “없음”으로 볼지, “모름”으로 볼지

현재 추천 답:

1. 별도 custom GraphHopper source 또는 patch 관리
2. edge 매핑 CSV 또는 OSM way/node 기반 lookup 파일
3. 1차는 “모름 포함”으로 해석

## 결론

이 5개 속성을 GraphHopper 경로 계산에 직접 쓰려면 custom EV가 맞다.

다만 1차 구현은 아래 원칙으로 가는 것이 가장 안전하다.

- boolean EV 4개 + numeric EV 1개(`width_meter`)
- `true` positive evidence만 우선 활용
- `false` penalty는 보류
- `width_meter`는 source `NULL`, graph sentinel `0.0`, custom model guard `width_meter > 0`
- `has_elevator`, `has_braille_block`는 OSM parser
- `has_curb_gap`, `has_audio_signal`, `width_meter`는 ETL join

즉 다음 실제 구현 단계는 “custom EV 정의”부터가 아니라, “값 주입 전략을 OSM 직접 parser와 ETL join 중 어디로 갈지 확정”하는 것까지 포함한다.
