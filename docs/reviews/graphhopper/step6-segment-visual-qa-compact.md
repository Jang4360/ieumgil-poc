# Step 6 Segment Visual QA Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/06_SEGMENT_VISUAL_QA.md`, `docs/ARD/erd.md`
- 입력 파일: `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/road_segments_service.csv`
- 작업 일자: 2026-04-14

## 목적

Step 4에서 생성한 `road_segments`가 지도 선형 기준으로도 사용할 만한지 확인한다.

이번 단계의 목표는 UI 구현이 아니라, 샘플 네트워크를 실제로 그려보고 연결 이상, 과분할, 과소분할, 누락 가능성을 시각적으로 검토하는 것이다.

## 반영 내용

시각 검증용 스크립트를 추가했다.

- `ieumgil-osm-etl-poc/scripts/render_segment_visual_qa.py`

생성 산출물:

- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/visual_qa/segment_overview.png`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/visual_qa/segment_length_outliers.png`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/visual_qa/segment_visual_qa_summary.json`

## 시각 확인 결과

### 1. 메인 보행 네트워크는 중심부에서 일관성 있게 보인다

- 중심 상업지 구역은 격자형 도로와 보행 연결이 비교적 자연스럽게 이어진다.
- 가장 큰 연결 컴포넌트가 `2,069 / 2,190` edge를 차지해, 샘플 대부분은 하나의 메인 네트워크로 묶인다.

즉, Step 4에서 만든 기본 골격은 시각적으로도 완전히 깨진 상태는 아니다.

### 2. 다만 외곽에 고립된 조각 네트워크가 여럿 남아 있다

- 전체 연결 컴포넌트 수: `17`
- 메인 컴포넌트 외 나머지 `16`개는 모두 소규모 파편이다.
- 그중 `46-node / 45-edge`, `37-node / 47-edge`급 보조 컴포넌트 2개가 있고, 나머지는 대부분 `2-node / 1-edge` 수준이다.

시각적으로는 서남쪽 외곽과 동쪽 끝, 북동쪽 외곽에 분리된 선형이 보인다.

이 패턴은 아래 둘 중 하나일 가능성이 높다.

- 샘플 bbox 절단으로 인해 메인 네트워크와 연결점이 잘린 경우
- `conditional` 포함 규칙으로 잡힌 도로가 실제 보행 연결성과 다르게 남은 경우

### 3. 장거리 세그먼트는 일부 과소분할 의심이 있다

- `500m` 이상 세그먼트: `15`
- 최장 세그먼트:
  - `edgeId=1358`, `2044.83m`
  - `edgeId=272`, `1860.40m`
  - `edgeId=84`, `1858.99m`
  - `edgeId=2110`, `1139.52m`
  - `edgeId=1883`, `1101.36m`

시각화 기준으로 긴 세그먼트는 주로 외곽 장축 선형에 몰려 있다.

- bbox 경계에 닿는 세그먼트는 총 `5`건인데, 이들은 모두 장거리 outlier였다.
- 즉, 일부는 샘플 영역 절단 영향으로 보인다.
- 반면 `1101.36m`, `981.53m`, `736.75m`, `701.91m`처럼 경계에 직접 닿지 않는 장거리 세그먼트도 있어, anchor 분할 기준이 길게 남는 구간이 존재한다.

따라서 Step 4 로직은 동작하지만, GraphHopper 비교나 세부 품질 검증 전에는 장거리 구간을 한 번 더 점검하는 편이 안전하다.

### 4. 극단적으로 짧은 세그먼트는 중심부 교차점에 몰려 있다

- `5m` 이하 세그먼트: `53`
- 최단 세그먼트:
  - `edgeId=1439`, `1.29m`
  - `edgeId=1156`, `1.71m`
  - `edgeId=1349`, `1.75m`
  - `edgeId=1406`, `1.79m`

시각적으로는 짧은 구간이 중심부 교차점 밀집 지역에 주로 나타난다.

이 자체가 곧 오류는 아니지만, 아래 둘 중 하나일 가능성이 있다.

- 횡단보도, 좁은 연결부, 계단 입구처럼 실제로 짧은 세그먼트
- 과분할 또는 중복 생성

## 이상 케이스

### 1. 중복 세그먼트 후보가 남아 있다

- 동일 노드쌍 중복: `11`쌍
- exact geometry duplicate: `1`쌍
  - `edgeId=1938`, `edgeId=1998`
- reverse geometry duplicate: `1`쌍
  - `edgeId=1995 (1455 -> 1448)`
  - `edgeId=1999 (1448 -> 1455)`

즉, 현재 생성 결과에는 완전히 겹치거나 역방향으로 중복된 세그먼트가 일부 남아 있다.

### 2. 외곽 파편 네트워크는 다음 단계 전에 성격 구분이 필요하다

현 상태에서는 아래가 섞여 있을 가능성이 있다.

- 실제로 독립된 보행 경로
- bbox 절단으로 인한 고립
- 조건부 포함 도로의 연결성 부족

이 부분을 구분하지 않으면 GraphHopper import 후에도 예외 케이스가 계속 남을 수 있다.

## 핵심 판단

### 1. Step 4 결과는 시각적으로 “사용 불가” 수준은 아니다

중심부 메인 네트워크는 자연스럽게 이어지고, 큰 구조상 붕괴는 보이지 않는다.

즉, 샘플 `road_segments`를 다음 단계 검증 입력으로 사용하는 것은 가능하다.

### 2. 하지만 그대로 고정하기엔 세 가지 보완 포인트가 있다

- 장거리 outlier 세그먼트 점검
- 분리된 minor component 처리 기준 정리
- 중복 / 역방향 중복 세그먼트 제거 규칙 검토

### 3. `road_segments.vertexId` 제거 예정은 이번 단계에 영향이 없다

이번 시각 검증은 `geom`, `from_node_id`, `to_node_id`, `length_meter` 기준으로 수행했기 때문에, 추후 `road_segments.vertexId`가 제거되어도 Step 6 결론은 그대로 유지된다.

## 결론

샘플 세그먼트는 전체적으로 보행 네트워크 형태를 잘 보존하고 있으며, GraphHopper 검증의 입력으로 사용할 수 있다.

다만 현재 상태는 “품질 확인용 샘플 네트워크” 수준으로 보는 것이 맞다. 다음 단계 전에 아래 3가지는 보완 후보로 유지해야 한다.

- bbox 경계 영향이 큰 장거리 세그먼트 분리 여부 검토
- minor component 유지 / 제외 기준 정리
- 중복 세그먼트 제거 규칙 추가 여부 검토

## 실행 기록

```powershell
python ieumgil-osm-etl-poc\scripts\render_segment_visual_qa.py `
  --segments-csv ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\road_segments_service.csv `
  --output-dir ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\visual_qa
```

## 다음 단계

다음 작업은 `docs/plans/graphhopper/07_GRAPHHOPPER_ROUTE_VALIDATION.md`로 넘어가되, 최소한 아래 두 조건을 메모로 들고 가는 것이 안전하다.

- 장거리 outlier와 분리 컴포넌트가 경로 결과에 어떤 영향을 주는지 함께 본다.
- 중복 세그먼트가 경로 선택에 불필요한 왜곡을 만드는지 확인한다.
