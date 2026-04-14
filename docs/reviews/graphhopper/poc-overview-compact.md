# PoC Overview Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/00_EXECUTION_ROADMAP.md`, `docs/plans/graphhopper/01_SCOPE_AND_GOALS.md`, `ieumgil-osm-etl-poc/AGENT_CONTEXT.md`
- 검토 대상 파일: `ieumgil-osm-etl-poc/data/raw/busan.osm.pbf`
- 검토 일자: 2026-04-14

## 결론

현재 단계 범위에 맞는 작업을 수행했다.

- 부산 범위 OSM 원천 파일 1건 확보 확인
- `.osm.pbf` 포맷 확인
- 보행 관련 태그 존재 확인
- 파일 크기와 로컬 처리 가능성 확인
- 현재 적재 대상 원천 파일 후보로 `busan.osm.pbf` 사용 가능

## 확인 결과

### 1. 파일 확보

- 파일 경로: `ieumgil-osm-etl-poc/data/raw/busan.osm.pbf`
- 파일 크기: 12,115,959 bytes, 약 11.55 MB

### 2. 파일 포맷 확인

다음 근거로 `.osm.pbf` 포맷으로 판단했다.

- 파일 확장자가 `.osm.pbf`
- 파일 시작부 바이너리에서 `OSMHeader`, `DenseNodes`, `OSMData` 문자열 확인
- `python + osmium`으로 실제 헤더와 객체를 정상 파싱

추출 확인값:

- header box: `(128.6550000/34.7860000 129.5900000/35.3280000)`
- header generator: `https://download.BBBike.org`

### 3. 보행 관련 태그 확인

전체 스캔 결과:

- nodes: 1,256,524
- ways: 161,648
- relations: 2,530
- `highway=*` ways: 72,108
- `highway=footway`: 9,162
- `highway=pedestrian`: 648
- `highway=path`: 6,667
- `highway=steps`: 797
- `sidewalk=*`: 787
- `foot=*`: 1,216
- `crossing=*`: 2,165

샘플:

- `way_id=26005519`: `highway=secondary`, `sidewalk=both`
- `way_id=26398657`: `highway=tertiary`, `foot=designated`
- `way_id=34567996`: `highway=secondary`, `foot=yes`
- `way_id=37374522`: `highway=primary`, `foot=no`
- `way_id=37396775`: `highway=tertiary`, `sidewalk=both`

## 판단

`busan.osm.pbf`는 현재 Step 1 검증 범위의 원천 파일로 적절하다.

- 부산 범위를 포함하는 PBF 파일로 읽힘
- 보행 네트워크 검토에 필요한 보행 관련 태그가 실제 포함됨
- 11.55 MB 규모라 샘플 검증과 후속 실험에 부담이 크지 않음

## 실행 기록

```powershell
Get-ChildItem -Recurse -File -Filter busan.osm.pbf
rg -a -o -m 20 "OSMHeader|OSMData|DenseNodes|highway|footway|sidewalk|pedestrian|crossing|steps|path" "C:\Users\SSAFY\poc\ieumgil-osm-etl-poc\data\raw\busan.osm.pbf"
python -m pip install --user osmium
```
