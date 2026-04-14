# AGENT_CONTEXT.md

## 프로젝트 역할
이 프로젝트는 OSM 원천 데이터 검증 및 향후 ETL 작업을 위한 공간이다.

## 현재 단계 역할
현재 단계에서는 아래만 수행한다.

- 부산 OSM 원천 데이터 후보 조사
- 파일 확보
- `.osm.pbf` 포맷 확인
- 보행 관련 태그 샘플 확인
- 적재 대상 파일 확정

## 현재 단계에서 하지 않는 것
- road_nodes 생성
- road_segments 생성
- GraphHopper import
- 경사도 계산
- 공공데이터 매핑

## 참고 문서
- `../AGENTS.md`
- `../docs/plans/graphhopper/00_EXECUTION_ROADMAP.md`
- `../docs/plans/graphhopper/01_SCOPE_AND_GOALS.md`
- `../docs/plans/graphhopper/03_EXECUTION_ROADMAP.md`
- `../docs/plans/graphhopper/04_WALKABLE_SEGMENT_CRITERIA.md`
- `../docs/plans/graphhopper/05_ROAD_NETWORK_GENERATION_VALIDATION.md`
- `../docs/plans/graphhopper/06_SEGMENT_VISUAL_QA.md`
- `../docs/plans/graphhopper/07_GRAPHHOPPER_ROUTE_VALIDATION.md`
- `../docs/plans/graphhopper/08_COORDINATE_SNAPPING_VALIDATION.md`
- `../docs/plans/graphhopper/09_RESPONSE_MAPPING_VALIDATION.md`
- `../docs/plans/graphhopper/10_ROUTE_OPTION_VALIDATION.md`
- `../docs/plans/graphhopper/11_RESULTS_SUMMARY_GUIDE.md`
