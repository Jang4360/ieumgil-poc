# Step 13 KakaoMap Route Visual Validation Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/13_KAKAOMAP_ROUTE_VISUAL_VALIDATION.md`
- 작업 일자: 2026-04-15

## 목적

GraphHopper route geometry와 snapped point를 KakaoMap 위에 올려 볼 수 있는 최소 viewer를 만들고, 브라우저에서 직접 GraphHopper `/info`, `/route`를 호출할 수 있는지 확인했다.

이번 단계는 운영 화면 구현이 아니라 아래 3가지를 빠르게 검증하는 단계로 진행했다.

- KakaoMap 기반 standalone viewer를 메인 서비스와 분리해서 만들 수 있는가
- GraphHopper custom profile 4종과 details 응답을 브라우저 직결 방식으로 받을 수 있는가
- snapped point와 profile별 geometry 차이를 지도 UI에서 표현할 준비가 되었는가

## 반영 내용

추가 파일:

- `docs/poc-viewers/graphhopper-kakaomap/index.html`
- `docs/poc-viewers/graphhopper-kakaomap/app.js`
- `docs/poc-viewers/graphhopper-kakaomap/styles.css`
- `docs/poc-viewers/graphhopper-kakaomap/README.md`
- `docs/poc-viewers/graphhopper-kakaomap/config.local.example.js`
- `docs/poc-viewers/graphhopper-kakaomap/config.local.js`
- `ieumgil-osm-etl-poc/scripts/run_kakaomap_route_visual_validation.py`

수정 파일:

- `.gitignore`

생성 산출물:

- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/kakaomap_visual/graphhopper_info.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/kakaomap_visual/kakaomap_visual_validation_summary.json`
- `ieumgil-osm-etl-poc/data/derived/seomyeon_station_1km_service_mapping/graphhopper_validation/kakaomap_visual/*.json`

## 구현 내용

### 1. standalone viewer 추가

viewer는 `docs/poc-viewers/graphhopper-kakaomap` 아래에 정적 파일로 분리했다.

주요 기능:

- `visual_shortest`, `visual_safe`, `wheelchair_shortest`, `wheelchair_safe` 단일 조회
- `visual`, `wheelchair` family shortest/safe 비교 조회
- 입력 출발/도착 marker와 snapped marker 표시
- 거리, 시간, instruction 수, geometry point 수 요약
- `crossing`, `surface`, `has_curb_gap`, `has_elevator`, `has_audio_signal`, `has_braille_block`, `width_meter` details 요약

### 2. viewer 실행성 보완

- `config.local.js`를 ignore 대상으로 두고 placeholder 파일도 같이 생성했다.
- 정적 서버 기준으로 `index.html`, `config.local.js`는 모두 `200` 응답을 확인했다.

### 3. Step 13 지원 검증 스크립트 추가

`run_kakaomap_route_visual_validation.py`는 아래를 자동 확인한다.

- GraphHopper `/info`
- 브라우저 origin 기준 CORS 허용 여부
- preset 3개에 대한 shortest/safe route 응답
- details key 존재 여부
- snapped waypoint 개수

## 검증 결과

### 1. 브라우저 직결 전제는 충족됐다

`kakaomap_visual_validation_summary.json` 기준:

- GraphHopper profiles 확인:
  - `visual_shortest`
  - `visual_safe`
  - `wheelchair_shortest`
  - `wheelchair_safe`
- CORS probe:
  - origin: `http://localhost:8080`
  - `Access-Control-Allow-Origin: *`
  - `corsEnabled = true`

즉 static viewer가 GraphHopper를 브라우저에서 직접 호출하는 구조 자체는 성립한다.

### 2. visual family는 실제 geometry 차이가 다시 확인됐다

시나리오: `visual_crossing_compare`

- `visual_shortest`
  - `1914.875m`
  - `22.98분`
  - geometry `49점`
  - instruction `16개`
- `visual_safe`
  - `2044.669m`
  - `24.54분`
  - geometry `68점`
  - instruction `22개`
- 차이:
  - 거리 `+129.794m`
  - 시간 `+1.56분`

즉 KakaoMap 위에 shortest/safe를 동시에 그리면 사용자가 실제 우회 차이를 시각적으로 볼 수 있는 데이터가 나온다.

### 3. wheelchair family는 현재 sample data 기준으로 차이가 없었다

시나리오: `wheelchair_stairs_compare`

- `wheelchair_shortest = wheelchair_safe`
  - 거리 `1508.865m`
  - 시간 `18.11분`
  - geometry `27점`
  - instruction `9개`

이건 viewer 문제가 아니라 현재 custom EV sample 값이 sparse해서 `wheelchair_safe` 추가 선호가 실제 분기를 만들지 못한 결과로 보는 것이 맞다.

### 4. snapped point 표시용 데이터는 충분하다

시나리오: `snapped_offset_demo`

- route 성공
- `visual_shortest`, `visual_safe` 모두 snapped waypoint `2개`
- Step 8과 같은 off-road 입력 좌표 기준에서도 route geometry와 snapped point를 같이 받을 수 있었다

즉 viewer에서

- 입력 marker
- snapped marker
- route polyline

를 동시에 그릴 수 있는 응답 구조는 이미 확보됐다.

### 5. details 요약도 최소 수준으로는 가능하다

세 시나리오 모두 아래 details key를 응답에서 확인했다.

- `crossing`
- `surface`
- `has_curb_gap`
- `has_elevator`
- `has_audio_signal`
- `has_braille_block`
- `width_meter`

현재 sample route 값은 대부분 아래처럼 sparse했다.

- `has_curb_gap = false`
- `has_elevator = false`
- `has_audio_signal = false`
- `has_braille_block = false`
- `width_meter = 0.0`

따라서 Step 13의 details 표시는 “segment 시각화”보다 “요약 표시”로 두는 현재 계획이 맞다.

## 한계

### 1. 실제 KakaoMap 렌더링은 자동 확인하지 못했다

현재 작업 환경에는 `kakaoJavascriptKey`가 없어서 지도 SDK 로드까지는 검증하지 못했다.

즉 이번 단계에서 자동으로 확인한 것은 아래까지다.

- viewer 코드 생성
- 정적 서버 응답
- GraphHopper direct fetch 가능 여부
- route geometry/details/snapped payload 확보

아직 수동 확인이 필요한 것은 아래다.

- Kakao SDK 실제 로드
- polyline/marker가 지도 위에 정상 렌더링되는지
- 색상 구분이 시각적으로 충분한지

### 2. wheelchair safe 시각 차이는 데이터가 더 채워져야 선명해진다

현재 sample custom EV 값은 `false` 또는 `0.0`이 대부분이라 `wheelchair_shortest`와 `wheelchair_safe`가 같은 경로를 반환하는 케이스가 남아 있다.

## 결론

이번 Step 13에서 확인된 것은 아래다.

- KakaoMap 기반 standalone viewer 구조는 구현 가능하다.
- 브라우저에서 GraphHopper `/info`, `/route`를 직접 호출하는 방식은 CORS 기준으로도 가능하다.
- visual profile은 shortest/safe 차이를 실제 geometry로 보여줄 수 있다.
- snapped point marker와 route polyline을 함께 표현할 데이터는 이미 확보됐다.
- details는 최소 요약 UI로 붙이는 방향이 맞다.

다만 “실제 지도 위 렌더링 완료”는 Kakao JavaScript key가 필요하므로 아직 수동 최종 확인 전 단계다.

## 실행 기록

```powershell
python -m py_compile ieumgil-osm-etl-poc/scripts/run_kakaomap_route_visual_validation.py
node --check docs/poc-viewers/graphhopper-kakaomap/app.js

C:\Users\SSAFY\java\temurin21\bin\java.exe `
  -Xms512m -Xmx512m `
  -Ddw.graphhopper.datareader.file=C:\Users\SSAFY\poc\ieumgil-osm-etl-poc\data\raw\busan.osm.pbf `
  -Ddw.graphhopper.graph.location=C:\Users\SSAFY\poc\ieumgil-osm-etl-poc\data\graphhopper\busan_custom_ev_v1 `
  -cp "C:\Users\SSAFY\poc\infra\graphhopper\custom-ev-extension\build\libs\ieumgil-graphhopper-custom-ev.jar;C:\Users\SSAFY\poc\infra\graphhopper\graphhopper-web-11.0.jar" `
  com.graphhopper.application.GraphHopperApplication `
  server C:\Users\SSAFY\poc\infra\graphhopper\config-foot.yml

python ieumgil-osm-etl-poc\scripts\run_kakaomap_route_visual_validation.py `
  --base-url http://localhost:8989 `
  --output-dir ieumgil-osm-etl-poc\data\derived\seomyeon_station_1km_service_mapping\graphhopper_validation\kakaomap_visual

python -m http.server 8080 --directory C:\Users\SSAFY\poc\docs\poc-viewers\graphhopper-kakaomap
```
