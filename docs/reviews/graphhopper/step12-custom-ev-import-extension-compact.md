# step12-custom-ev-import-extension-compact.md

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/12_CUSTOM_EV_IMPORT_EXTENSION.md`
- 작업 일자: 2026-04-15

## 목적

`has_curb_gap`, `has_elevator`, `has_audio_signal`, `has_braille_block`, `width_meter`를 GraphHopper graph에 custom EV로 실제 반영하고, 4개 profile이 이를 읽을 수 있는 상태까지 연결한다.

## 이번 변경

### 1. Step 12 계획 문서를 구현 기준과 일치시켰다

`docs/plans/graphhopper/12_CUSTOM_EV_IMPORT_EXTENSION.md`를 아래 기준으로 정리했다.

- OSM parser 대상:
  - `has_elevator`
  - `has_braille_block`
- ETL join 대상:
  - `has_curb_gap`
  - `has_audio_signal`
  - `width_meter`
- `width_meter`
  - source 기본값은 `NULL`
  - GraphHopper EV 저장값은 sentinel `0.0`
  - custom model에서는 `width_meter > 0` guard가 있을 때만 평가

### 2. ETL join 입력 CSV 생성 스크립트를 추가했다

추가 파일:

- `ieumgil-osm-etl-poc/scripts/build_graphhopper_custom_ev_join.py`

역할:

- `road_segments.csv`의 `source_way_id + segment_ordinal`과
- `road_segments_service.csv`의 접근성 속성을
- geometry 기준으로 매칭해서
- GraphHopper import용 `graphhopper_custom_ev_join.csv`를 생성한다.

생성 결과:

- 입력: `2190` rows
- 출력: `2190` rows
- unmatched road rows: `0`
- remaining service rows: `0`

출력 파일:

- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/graphhopper_custom_ev_join.csv`

### 3. GraphHopper custom extension jar를 추가했다

추가 위치:

- `infra/graphhopper/custom-ev-extension`

핵심 구현:

- custom EV 정의
  - `has_curb_gap`
  - `has_elevator`
  - `has_audio_signal`
  - `has_braille_block`
  - `width_meter`
- custom import registry
  - `IeumgilImportRegistry`
- OSM parser
  - `AccessibilityOsmTagParser`
- ETL join parser
  - `AccessibilityJoinTagParser`
- GraphHopper boot override
  - `com.graphhopper.http.GraphHopperManaged`

구현 방식:

- GraphHopper 본체 jar를 포크하지 않았다.
- 대신 boot 시점에 `setImportRegistry(new IeumgilImportRegistry())`를 주입하는 `GraphHopperManaged` override jar를 classpath 앞에 두는 방식으로 확장했다.

### 4. profile과 runtime 설정을 연결했다

변경 파일:

- `infra/graphhopper/config-foot.yml`
- `infra/graphhopper/docker-entrypoint.sh`
- `infra/graphhopper/visual-safe.json`
- `infra/graphhopper/wheelchair-shortest.json`
- `infra/graphhopper/wheelchair-safe.json`

적용 내용:

- `graph.encoded_values`에 custom EV 5개 추가
- entrypoint에서 extension jar classpath와 ETL join system property 지원
- `visual_safe`
  - `has_audio_signal`
  - `has_braille_block`
  positive preference 추가
- `wheelchair_shortest`
  - `width_meter > 0 && width_meter < 0.8` 금지 추가
- `wheelchair_safe`
  - `has_curb_gap`
  - `has_elevator`
  positive preference 추가
  - `width_meter` threshold rule 추가

## 빌드 및 import 검증

### 1. extension jar 빌드

실행:

```bash
sh ieumgil-routing-poc/gradlew -p infra/graphhopper/custom-ev-extension clean build
```

결과:

- `BUILD SUCCESSFUL`
- 산출물:
  - `infra/graphhopper/custom-ev-extension/build/libs/ieumgil-graphhopper-custom-ev.jar`

### 2. GraphHopper import

실행 방식:

- classpath 앞에 extension jar 배치
- system property로 join CSV 전달
- 새 graph location에 재import

출력 graph:

- `ieumgil-osm-etl-poc/data/graphhopper/busan_custom_ev_v1`

로그 확인:

- join loader가 `1012` OSM ways에 대한 ETL rows를 로드
- import 성공
- 4개 profile 모두 서버 기동 성공

### 3. `/info` 검증

확인 결과:

- profiles:
  - `visual_shortest`
  - `visual_safe`
  - `wheelchair_shortest`
  - `wheelchair_safe`
- custom EV 노출 확인:
  - `has_curb_gap`
  - `has_elevator`
  - `has_audio_signal`
  - `has_braille_block`
  - `width_meter`

### 4. `properties.txt` 검증

`ieumgil-osm-etl-poc/data/graphhopper/busan_custom_ev_v1/properties.txt`에서 custom EV 5개가 모두 저장된 것을 확인했다.

### 5. route details 검증

테스트 OD:

- start: `35.1497707,129.0656452`
- end: `35.1578066,129.0510036`
- profile: `wheelchair_safe`

요청 details:

- `has_curb_gap`
- `has_elevator`
- `has_audio_signal`
- `has_braille_block`
- `width_meter`

응답 결과:

- `details`에 위 5개 key가 모두 포함됐다.
- 샘플 route에서는 값이 아래처럼 확인됐다.
  - `has_curb_gap = false`
  - `has_elevator = false`
  - `has_audio_signal = false`
  - `has_braille_block = false`
  - `width_meter = 0.0`

즉 custom EV가 route API path details까지 연결된 것은 확인됐다.

## 경로 결과 비교

동일 OD에서 4개 profile 결과:

- `visual_shortest`: `1914.875m`, `1378.711s`
- `visual_safe`: `2044.669m`, `1472.162s`
- `wheelchair_shortest`: `1914.875m`, `1378.711s`
- `wheelchair_safe`: `2044.669m`, `1472.162s`

해석:

- Step 11에서 확인한 기본 분기 구조는 유지됐다.
- 이번 custom EV 반영으로 route 실패나 profile 로딩 문제는 생기지 않았다.
- 다만 현재 sample join 데이터에는
  - `has_curb_gap = true`
  - `has_audio_signal = true`
  - `width_meter` 측정값
  이 하나도 없어서, 새 EV 기반 추가 분기 효과는 아직 관측되지 않았다.

## 한계

### 1. ETL join 데이터가 아직 거의 비어 있다

현재 생성된 join CSV 기준:

- `has_curb_gap_true = 0`
- `has_audio_signal_true = 0`
- `width_meter_present = 0`

즉 parser와 graph wiring은 끝났지만, 실제 서비스 효과는 ETL 값 채움 이후에야 본격 검증 가능하다.

### 2. OSM parser 대상도 현재 샘플 경로에서는 효과가 드러나지 않았다

`has_elevator`, `has_braille_block`는 OSM 태그가 있는 edge에서만 `true`가 된다. 이번 대표 OD에서는 detail 값이 모두 `false`였다.

### 3. ETL join 키는 현재 `way_id + segment_ordinal` 전략이다

이 방식은 현재 PoC 산출물 구조에는 맞지만, 향후 ETL 세그먼트 분할 규칙이 바뀌면 join 입력 생성 스크립트도 함께 재검토해야 한다.

## 결론

이번 단계에서 확인한 것은 아래다.

- custom EV 5개를 GraphHopper import에 실제 등록할 수 있다.
- OSM parser 2개와 ETL join 3개를 한 graph에 함께 반영할 수 있다.
- 기존 4개 profile과 custom model이 새 EV를 읽는 상태로 서버 기동 가능하다.
- route API `details`까지 새 EV가 노출된다.

즉 구현 관점의 “GraphHopper custom EV import 확장 가능성”은 검증됐다.

다음 단계는 data quality 쪽이다.

- ETL에서 `width_meter`, `has_curb_gap`, `has_audio_signal` 실제 값 채우기
- 값이 채워진 join CSV로 재import
- `wheelchair_*`, `visual_safe` profile의 실제 분기 효과 재검증
