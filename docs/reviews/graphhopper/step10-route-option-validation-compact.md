# Step 10 Route Option Validation Compact Review

- 기준 문서: `AGENTS.md`, `docs/ARD/erd.md`, `docs/plans/graphhopper/10_ROUTE_OPTION_VALIDATION.md`
- 참고 산출물: `docs/reviews/graphhopper/step4-road-network-generation-compact.md`, `docs/reviews/graphhopper/step7-graphhopper-route-validation-compact.md`, `docs/reviews/graphhopper/step9-response-mapping-validation-compact.md`
- 작업 일자: 2026-04-14

## 목적

Step 7에서 확인한 기본 `foot` 경로를 `SHORTEST` 기준으로 두고, Step 4의 `road_segments` 속성을 이용해 `SAFE`를 별도 옵션으로 분리할 수 있는지 확인했다.

이번 단계의 핵심은 운영 품질 비교가 아니라, 어떤 제약은 실제 경로 선택 단계에서 분기 가능하고 어떤 속성은 현재 구조상 후처리 메타로만 남겨야 하는지 선을 긋는 것이다.

## 반영 내용

수정 문서:

- `docs/plans/graphhopper/10_ROUTE_OPTION_VALIDATION.md`

추가 스크립트:

- `ieumgil-osm-etl-poc/scripts/run_route_option_validation.py`

생성 산출물:

- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/route_options/route_option_validation_summary.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/route_options/avoid_stairs_candidate.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/route_options/avoid_unsignalized_crossing_candidate.json`

## 검증 방식

이번 단계는 GraphHopper 실제 custom model import를 추가로 돌리는 대신, Step 4에서 만든 서비스 기준 `road_segments` 그래프를 다시 사용해 분기 구조를 검증했다.

검증 기준:

- 분석 대상: `road_segments_service_cleaned.csv`의 메인 컴포넌트(`component_id = 1`)
- `SHORTEST`: `length_meter`만 비용으로 사용하는 기본 경로
- `SAFE / avoid_stairs`: `has_stairs = true` 세그먼트 금지
- `SAFE / avoid_unsignalized_crossing`: `has_crosswalk = true and has_signal = false` 세그먼트에 `80m` penalty 부여

대표 OD는 Step 10 탐색 과정에서 차이가 명확히 드러난 사례를 고정했다.

- 계단 회피 대표 OD: `1244 -> 1335`
- 비신호 횡단 회피 대표 OD: `322 -> 1218`

## 네트워크 기준 확인

메인 컴포넌트 기준 집계:

- 노드: `1,516`
- 세그먼트: `2,076`
- 계단 세그먼트: `6`
- 횡단 세그먼트: `68`
- 신호 횡단 세그먼트: `5`
- 비신호 횡단 세그먼트: `63`

즉, `SAFE` 후보 규칙을 시험할 최소 데이터는 이미 샘플 네트워크 안에 존재한다.

## 결과

### 1. `avoid_stairs`는 즉시 분기 후보로 쓸 수 있다

대표 OD:

- 시작: `1244` (`35.1517986, 129.0665998`)
- 종료: `1335` (`35.1618369, 129.0700577`)

비교 결과:

- `SHORTEST`
  - 거리: `1498.97m`
  - edge 수: `31`
  - 계단 노출: `1`
- `SAFE`
  - 거리: `1508.91m`
  - edge 수: `27`
  - 계단 노출: `0`
- 차이
  - 우회 거리: `9.94m`
  - 제거된 계단: `1`

즉, 작은 우회만으로 계단을 완전히 제거하는 경로 분기가 가능했다.

이번 규칙은 OSM 태그 기반 제약이고 Step 4에서도 `has_stairs`를 직접 매핑했으므로, 현재 PoC에서 가장 먼저 `SAFE` 후보로 채택할 수 있다.

### 2. `avoid_unsignalized_crossing`도 구조적으로는 가능하다

대표 OD:

- 시작: `322` (`35.1497707, 129.0656452`)
- 종료: `1218` (`35.1578066, 129.0510036`)

비교 결과:

- `SHORTEST`
  - 거리: `1853.74m`
  - edge 수: `31`
  - 비신호 횡단 노출: `10`
- `SAFE`
  - 거리: `1998.47m`
  - edge 수: `27`
  - 비신호 횡단 노출: `0`
- 차이
  - 우회 거리: `144.73m`
  - 감소한 비신호 횡단: `10`

즉, 비신호 횡단 회피도 경로 선택 자체를 바꾸는 규칙으로 만들 수 있다.

다만 이 규칙은 현재 GraphHopper 기본 응답만으로는 바로 구현하기 어렵다.

- Step 9 기준 현재 GraphHopper 응답에는 서비스 `road_segments` 식별자가 없다.
- Step 4의 `has_crosswalk`, `has_signal`은 서비스 ETL 결과에는 있지만 현재 GraphHopper 설정에는 직접 연결되어 있지 않다.

따라서 이 규칙은 아래 둘 중 하나가 필요하다.

- GraphHopper import 확장 또는 encoded value 추가
- 서비스 DB 기반 별도 라우팅 그래프 또는 후속 경로 재계산 계층

### 3. 후처리만으로는 `SAFE` 경로를 만들 수 없는 속성이 남아 있다

아래 속성은 이번 단계에서도 경로 선택 입력이 아니라 후처리 메타로 남는다.

- `riskLevel`
- `has_curb_gap`
- `has_audio_signal`
- `has_braille_block`

이유:

- Step 4 기준 OSM 단독으로 충분히 채워지지 않거나
- Step 9 기준 현재 GraphHopper 응답만으로 세그먼트 속성 join이 불가능하기 때문이다.

즉, 이런 값은 현재 단계에서는 경로 설명/경고에는 쓸 수 있어도, `SAFE` 경로 생성 규칙으로 바로 넣을 수는 없다.

## 핵심 판단

### 1. `SAFE` / `SHORTEST` 분기 구조는 가능하다

이번 단계 완료 기준인 “분기 구조 가능 여부 판단”은 충족했다.

- `SHORTEST`: Step 7 기본 `foot` 경로
- `SAFE`: 별도 비용 함수가 적용된 대안 경로

두 옵션은 실제로 서로 다른 edge 집합을 반환했다.

### 2. 1차 `SAFE` 규칙은 `avoid_stairs`가 가장 현실적이다

현재 PoC에서 가장 먼저 가져갈 수 있는 규칙은 계단 회피다.

이유:

- 데이터 존재가 확인됐다.
- 경로 변화가 실제로 발생했다.
- 우회 비용이 작았다.
- GraphHopper 내부 분기 후보로 설명 가능하다.

### 3. 횡단 안전 규칙은 “가능하지만 구현 위치가 다르다”

비신호 횡단 회피는 구조적으로 의미가 있지만, 현재 PoC GraphHopper 설정만으로 바로 넣는다고 보면 안 된다.

즉, 이번 단계의 결론은 아래처럼 나뉜다.

- 지금 바로 `SAFE` 1차 규칙 후보: `avoid_stairs`
- 다음 설계 검토가 필요한 규칙 후보: `avoid_unsignalized_crossing`
- 후처리 메타 전용: `riskLevel`, `has_curb_gap`, `has_audio_signal`, `has_braille_block`

## 결론

Step 10 결과는 아래와 같다.

- `SAFE` / `SHORTEST` 분기 구조는 가능하다.
- 최소 1개 이상 회피 규칙 후보 정리 완료:
  - `avoid_stairs`
  - `avoid_unsignalized_crossing`
- 후처리 필요 지점 문서화 완료

따라서 다음 구현 단계에서는 `routeOption = SHORTEST | SAFE` 자체를 먼저 열고, `SAFE`의 1차 규칙은 계단 회피부터 시작하는 것이 가장 안전하다.

## 실행 기록

```powershell
python ieumgil-osm-etl-poc\scripts\run_route_option_validation.py `
  --road-nodes-csv ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\road_nodes_service.csv `
  --cleaned-segments-csv ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\graphhopper_validation\road_segments_service_cleaned.csv `
  --output-dir ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\graphhopper_validation\route_options
```

## 다음 단계

다음 작업은 `docs/plans/graphhopper/11_RESULTS_SUMMARY_GUIDE.md` 기준으로 Step 1~10 결과를 묶어, 바로 구현할 범위와 후속 검토 범위를 명확히 구분한 종합 결과 문서를 만드는 것이다.
