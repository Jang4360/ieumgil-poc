# 13_KAKAOMAP_ROUTE_VISUAL_VALIDATION.md

## 단계명

카카오맵 기반 GraphHopper 경로 시각 검증

## 목적

지금까지 검증한 GraphHopper profile과 custom EV 결과를 실제 지도 위에 올려 보고, 최소한의 프론트 코드로 경로 geometry가 정상적으로 보이는지 확인한다.

이번 단계의 핵심은 운영용 프론트엔드를 만드는 것이 아니라, 아래 3가지를 빠르게 검증하는 것이다.

- GraphHopper route 응답 geometry가 카카오맵 위에 올바르게 그려지는가
- `visual_*`, `wheelchair_*` profile 차이가 실제 지도상 경로선으로 구분되는가
- 향후 API/프론트 연동 전에 좌표계, snapped point, details 시각화 방식에 구조 문제가 없는가

## 구현 원칙

1. 메인 서비스 프론트 구조를 먼저 만들지 않는다.
2. 최소 정적 HTML + JavaScript만으로 검증한다.
3. 카카오맵 지도 위에 GraphHopper 결과를 오버레이하는 것만 목표로 둔다.
4. 프로필 선택, 시작/도착 선택, 경로선 표시, 핵심 details 확인까지만 구현한다.
5. 인증, 사용자 상태, 저장 기능, 반응형 UI 고도화는 범위에서 제외한다.

## 왜 지금 필요한가

ETL 값 채움 이전에도 아래는 먼저 확인할 수 있다.

- GraphHopper geometry와 실제 도로 시각 위치가 크게 어긋나지 않는지
- `visual_safe`와 `wheelchair_safe`가 우회할 때 사용자가 지도에서 차이를 체감할 수 있는지
- path details를 어떤 방식으로 지도에 붙여야 읽기 쉬운지
- 향후 카카오맵 기반 서비스 프론트가 GraphHopper 응답을 그대로 소비할 수 있는지

즉 이 단계는 “추천 품질”보다 “지도 위 검증 가능성”을 확인하는 단계다.

## ETL 외 추가로 확인할 GraphHopper PoC 항목

ETL 값 채움 외에도 아래는 PoC로 별도 확인할 가치가 있다.

### 1. geometry 시각 정합성

- route polyline이 실제 보행 가능한 도로와 크게 어긋나지 않는가
- snapped 시작점/종료점이 사용자가 이해 가능한 위치에 찍히는가

### 2. profile 체감 가능성

- `visual_shortest` vs `visual_safe`
- `wheelchair_shortest` vs `wheelchair_safe`

이 2쌍이 지도 위에서 실제로 다른 선형으로 보이는가

### 3. details 시각화 가능성

- `crossing`
- `surface`
- `has_elevator`
- `has_braille_block`
- `width_meter`

같은 details를 지도 위 하이라이트 또는 범례로 보여줄 수 있는가

### 4. snapped point UX

- 입력 좌표가 도로 밖이어도 경로가 안정적으로 시작되는가
- 사용자가 입력한 점과 실제 경로 시작점 차이를 시각적으로 설명할 수 있는가

### 5. profile 요청 방식 안정성

- `profile`만으로 충분한가
- 추후 `routeOption`과 `profile`을 함께 노출해야 하는가

### 6. route response 후처리 최소 필요량

- 프론트가 GraphHopper raw response를 직접 써도 되는가
- 아니면 백엔드가 DTO로 감싸야 지도 UI가 단순해지는가

## 검증 대상 범위

### 지도

- 카카오맵 JavaScript SDK

### 데이터 입력

- GraphHopper `/route`
- GraphHopper `/info`

### profile

- `visual_shortest`
- `visual_safe`
- `wheelchair_shortest`
- `wheelchair_safe`

### 최소 시각 요소

- 지도
- 시작점 marker
- 도착점 marker
- snapped point marker
- 경로 polyline
- profile 선택 UI
- 대표 details 요약 패널

## 구현 방식

### 1. 프론트 구조

운영 프론트가 아니라 standalone viewer로 만든다.

권장 위치:

- `docs/poc-viewers/graphhopper-kakaomap/`

권장 파일:

- `index.html`
- `app.js`
- `styles.css`
- `README.md`

이유:

- 메인 서비스 코드를 건드리지 않는다.
- `python3 -m http.server` 같은 단순 정적 서버로 바로 띄울 수 있다.
- GraphHopper와 카카오맵 검증만 분리해서 반복 가능하다.

### 2. 환경값

필요 환경값:

- 카카오맵 JavaScript app key
- GraphHopper base URL

권장 방식:

- `config.local.js` 또는 `env.js` 같은 별도 ignore 파일
- 예:
  - `window.APP_CONFIG = { kakaoJavascriptKey: '...', graphhopperBaseUrl: 'http://localhost:8989' }`

주의:

- `.env`를 브라우저에서 직접 읽지 않는다.
- app key는 정적 viewer에서 주입 가능한 형태로만 둔다.

### 3. 지도 초기화

초기 지도는 서면역 1km 샘플 영역에 맞춘다.

권장 초기 중심:

- `35.1570, 129.0590`

초기 동작:

- 카카오맵 로드
- 기본 중심/줌 설정
- 시작/도착 marker 기본값 표시

### 4. 경로 요청 방식

프론트는 GraphHopper `/route`를 직접 호출한다.

권장 요청 파라미터:

- `profile`
- `point` x 2
- `points_encoded=false`
- `details=crossing`
- `details=surface`
- `details=has_curb_gap`
- `details=has_elevator`
- `details=has_audio_signal`
- `details=has_braille_block`
- `details=width_meter`

이유:

- geometry와 details를 한 번에 받아 지도와 요약 패널에서 같이 쓸 수 있다.

### 5. 최소 UI

필수 UI:

- profile dropdown
- 시작점/도착점 preset 선택 또는 지도 클릭 2점 입력
- “경로 조회” 버튼
- 거리/시간 요약
- details 요약 패널

선택 UI:

- `shortest`와 `safe`를 동시에 조회해 2개 선을 겹쳐 보기
- details toggle

### 6. 지도 오버레이 방식

Polyline 색상 기준 권장:

- `visual_shortest`: 파랑
- `visual_safe`: 초록
- `wheelchair_shortest`: 주황
- `wheelchair_safe`: 빨강

Marker 기준 권장:

- 입력 시작점/도착점
- snapped 시작점/종료점

details 시각화 1차 권장:

- 지도 전체 구간 하이라이트는 하지 않는다.
- 우선 우측 패널에 route details summary만 보여준다.

이유:

- custom EV 값이 아직 sparse해서 segment별 과한 시각화는 노이즈가 크다.
- 1차는 선형과 profile 차이 확인이 우선이다.

## 구현 계획

1. standalone viewer 폴더 생성
2. 카카오맵 SDK 로드 가능한 정적 HTML 작성
3. GraphHopper `/info` 호출로 profile 목록 확인
4. preset OD 2건을 코드에 넣고 버튼으로 선택 가능하게 구성
5. `/route` 호출 결과를 카카오맵 polyline으로 렌더링
6. 거리/시간/snapped point를 패널에 표시
7. `details` 응답을 요약해 패널에 표시
8. 동일 OD에서 `shortest`/`safe`를 번갈아 호출해 시각 차이 확인
9. 결과와 한계를 `docs/reviews/graphhopper`에 기록

## 대표 검증 시나리오

### 시나리오 1. visual shortest vs safe

- 동일 OD에 대해 `visual_shortest`, `visual_safe`를 각각 조회
- 지도 위 선형 차이 확인
- 거리/시간 차이 표시
- crossing 관련 detail 요약 확인

### 시나리오 2. wheelchair shortest vs safe

- 동일 OD에 대해 `wheelchair_shortest`, `wheelchair_safe`를 각각 조회
- 지도 위 선형 차이 확인
- `width_meter`, `has_elevator`, `has_curb_gap` detail 요약 확인

### 시나리오 3. snapped point 확인

- 도로 밖 좌표를 일부러 넣어 경로 조회
- 입력 marker와 snapped marker 차이 확인

## 확인할 것

- 카카오맵 위 polyline 표시가 정상 동작하는가
- GraphHopper 응답 geometry를 별도 변환 없이 바로 쓸 수 있는가
- 4개 profile이 지도 위에서 구분 가능한가
- details를 최소 패널 형태로 읽을 수 있는가
- snapped point를 UI로 설명할 수 있는가
- 이후 백엔드 DTO가 꼭 필요한지 판단 가능한가

## 산출물

- 최소 static viewer 코드
- 실행 방법 문서
- preset OD 목록
- 시각 검증 스크린샷
- 검증 결과 문서

## 완료 기준

- 카카오맵 위에 GraphHopper 경로 1건 이상 표시 성공
- 4개 profile 중 최소 2개 이상 비교 시각화 성공
- 시작/도착점과 snapped point 표시 성공
- details 최소 요약 표시 성공
- 결과 문서 작성 완료

## 범위 제한

- 운영용 프론트 프로젝트 생성은 하지 않는다.
- 카카오 장소 검색, 주소 검색, 현위치 권한 요청은 이번 단계 범위에서 제외한다.
- 백엔드 API DTO 신규 설계는 하지 않는다.
- 다중 경유지, 대안 경로, turn-by-turn UI는 하지 않는다.
- 접근성 속성 segment별 정교한 지도 하이라이트는 후속으로 넘긴다.

## 다음 단계 입력값

- 실제 서비스 프론트에 필요한 최소 route DTO 구조
- profile 선택 UX 방향
- snapped point 설명 UI 방향
- details 시각화 우선순위
- ETL 값 채움 이후 재검증할 시나리오 목록
