# Step 10 GraphHopper Encoded Value Alignment Compact Review

- 기준 문서: `AGENTS.md`, `docs/ARD/erd.md`, `docs/plans/graphhopper/10_ROUTE_OPTION_VALIDATION.md`
- 참고 문서: `docs/reviews/graphhopper/step4-road-network-generation-compact.md`, `docs/reviews/graphhopper/step9-response-mapping-validation-compact.md`
- 작업 일자: 2026-04-14

## 목적

`road_segments` ERD 컬럼 중 현재 GraphHopper 그래프에 직접 반영 가능한 항목과 불가능한 항목을 구분하고, 1차 `SAFE` profile 설계 전에 즉시 사용할 수 있는 built-in encoded value를 graph import 설정에 반영한다.

이번 단계의 목표는 서비스 ERD 전체를 GraphHopper edge 속성으로 완전히 복제하는 것이 아니라, GraphHopper 11 built-in 기능만으로 바로 활용할 수 있는 속성을 먼저 graph에 싣는 것이다.

## 반영 내용

수정 파일:

- `infra/graphhopper/config-foot.yml`
- `infra/graphhopper/ieumgil-foot-base.json`

생성 산출물:

- `ieumgil-osm-etl-poc/data/graphhopper/busan_ev_alignment_v2`

## 핵심 판단

### 1. `road_segments` 전체 컬럼이 GraphHopper encoded value와 1:1 대응되지는 않는다

ERD 기준 컬럼별 판단은 아래와 같다.

| `road_segments` 컬럼 | 현재 GraphHopper 대응 | 판단 |
| --- | --- | --- |
| `edgeId` | GraphHopper 내부 edge id는 있으나 서비스 `edgeId`와 별개 | 직접 대응 불가 |
| `from_node_id` | GraphHopper 내부 node id는 있으나 서비스 FK와 별개 | 직접 대응 불가 |
| `to_node_id` | GraphHopper 내부 node id는 있으나 서비스 FK와 별개 | 직접 대응 불가 |
| `geom` | route geometry로는 사용 가능하나 encoded value 아님 | 직접 대응 불가 |
| `length_meter` | route distance/weight 계산에 사용되나 encoded value 아님 | 직접 대응 불가 |
| `avg_slope_percent` | built-in `average_slope` 존재 | 1차 대응 가능 |
| `width_meter` | built-in `max_width`는 있으나 차량 제한 성격이 강하고 서비스 의미와 다름 | 현재 대응 보류 |
| `has_stairs` | built-in `road_class=steps`로 부분 대응 가능 | 1차 대응 가능 |
| `has_curb_gap` | built-in 없음 | custom EV 필요 |
| `has_elevator` | built-in 없음 | custom EV 필요 |
| `has_crosswalk` | built-in `crossing` enum으로 대응 가능 | 1차 대응 가능 |
| `has_signal` | built-in `crossing=traffic_signals`로 대응 가능 | 1차 대응 가능 |
| `has_audio_signal` | built-in 없음 | custom EV 필요 |
| `has_braille_block` | built-in 없음 | custom EV 필요 |
| `surface_type` | built-in `surface` 존재 | 1차 대응 가능 |
| `vertexId` | 서비스 보조 FK 개념이며 GraphHopper 그래프에는 대응 개념 없음 | 직접 대응 불가 |

즉, 지금 바로 GraphHopper에 반영 가능한 핵심 속성은 아래와 같다.

- `road_class` 기반 `has_stairs`
- `crossing` 기반 `has_crosswalk`, `has_signal`
- `surface`
- `average_slope`

### 2. `has_crosswalk`, `has_signal`은 커스텀 boolean보다 `crossing` enum이 1차 구현에 적합하다

GraphHopper 11에는 built-in `OSMCrossingParser`와 `crossing` encoded value가 이미 있다.

따라서 1차에서는 아래처럼 해석하는 것이 가장 안전하다.

- `has_signal = true` 상당: `crossing == TRAFFIC_SIGNALS`
- `has_crosswalk = true` 상당: `crossing in {TRAFFIC_SIGNALS, UNCONTROLLED, MARKED, UNMARKED}`

즉, 지금 필요한 것은 `has_crosswalk`, `has_signal` boolean을 새로 만드는 것이 아니라 `crossing` EV를 graph에 포함시키는 것이다.

### 3. `has_curb_gap`, `has_elevator`, `has_audio_signal`, `has_braille_block`은 이번 변경만으로는 못 넣는다

이 속성들은 GraphHopper 11 built-in import registry에서 바로 쓸 수 있는 encoded value가 확인되지 않았다.

따라서 이 값들을 GraphHopper edge 비용 함수에 직접 쓰려면 아래가 추가로 필요하다.

- custom encoded value 정의
- custom tag parser 또는 외부 데이터 결합 import 확장
- custom build된 GraphHopper 실행 아티팩트

즉, 이번 1차 범위에서는 config 변경만으로 해결되지 않는다.

## 설정 반영

이번에 `graph.encoded_values`에 아래를 추가했다.

- `crossing`
- `footway`
- `surface`
- `average_slope`
- `osm_way_id`

기존 유지:

- `foot_access`
- `foot_priority`
- `foot_average_speed`
- `foot_road_access`
- `hike_rating`
- `mtb_rating`
- `country`
- `road_class`

선택 이유:

- `crossing`: `has_crosswalk`, `has_signal` 1차 대응
- `surface`: `surface_type` 대응
- `average_slope`: `avg_slope_percent` 1차 대응
- `footway`: `sidewalk`, `crossing`, `traffic_island` 등 footway 세분화 보조
- `osm_way_id`: route 결과 해석과 후속 join/debug 보조

## 구현 전 해석 기준

향후 `SAFE` custom model에서 우선 사용할 수 있는 해석 기준은 아래와 같다.

- `road_class == STEPS`: 계단 회피
- `crossing == TRAFFIC_SIGNALS`: 신호 횡단
- `crossing == UNCONTROLLED || crossing == UNMARKED`: 비신호/저통제 횡단 회피 후보
- `surface` 계열: 휠체어 불리 surface 회피 후보
- `average_slope`: 경사 회피 후보

## 범위 밖 항목

이번 변경에서는 아래를 아직 하지 않는다.

- `visual_safe`, `wheelchair_safe` profile 추가
- profile별 custom model 구현
- custom GraphHopper Java parser 작성
- 외부 데이터 기반 custom encoded value 주입

## 실행 기록

```bash
java -Xms512m -Xmx512m \
  -Ddw.graphhopper.datareader.file=/Users/jangjooyoon/Desktop/JooYoon/ssafy/ieumgil-poc/ieumgil-osm-etl-poc/data/raw/busan.osm.pbf \
  -Ddw.graphhopper.graph.location=/Users/jangjooyoon/Desktop/JooYoon/ssafy/ieumgil-poc/ieumgil-osm-etl-poc/data/graphhopper/busan_ev_alignment_v2 \
  -jar /Users/jangjooyoon/Desktop/JooYoon/ssafy/ieumgil-poc/infra/graphhopper/graphhopper-web-11.0.jar \
  server /Users/jangjooyoon/Desktop/JooYoon/ssafy/ieumgil-poc/infra/graphhopper/config-foot.yml
```

## 결론

이번 단계 결론은 아래와 같다.

- `road_segments` 전체 컬럼을 GraphHopper EV로 바로 옮길 수는 없다.
- 하지만 `crossing`, `surface`, `average_slope`, `road_class`만으로도 1차 `SAFE` 설계에 필요한 핵심 재료는 graph에 넣을 수 있다.
- `has_curb_gap`, `has_elevator`, `has_audio_signal`, `has_braille_block`은 다음 단계의 custom import 확장 대상이다.
