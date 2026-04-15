# accessible_navigation_web 라우팅/경사도 분석

## 목적
- 외부 저장소 `solv1209/accessible_navigation_web`의 길찾기 방식과 경사도 반영 여부를 PoC 참고용으로 정리한다.

## 분석 대상
- 저장소: `https://github.com/solv1209/accessible_navigation_web.git`
- 확인 커밋: `22f1a850907e997774ed5d85d88c5decfe2e1934`
- 로컬 확인 경로: `C:\Users\SSAFY\poc\.tmp\accessible_navigation_web`

## 결론 요약
- 이 저장소는 자체 보행 그래프를 구축해 최단경로를 계산하는 구조가 아니다.
- 핵심 경로 계산은 `SK Open API Tmap`의 대중교통/보행 경로 API에 위임한다.
- 자체 구현은 `지하철역 엘리베이터 마커`를 DB에서 조회한 뒤, Tmap이 준 대중교통 경로의 보행 구간을 엘리베이터 경유 보행 경로로 재계산해 덮어쓰는 후처리 로직이다.
- README에는 `경사로 가중치 1.5`, `계단/에스컬레이터 제외` 같은 정책 설명이 있으나, 현재 커밋의 실제 코드에는 경사도 계산이나 경사로 기반 가중치 평가 로직이 없다.

## 길찾기 방식

### 1. 외부 API 호출이 실제 경로 엔진
- `TmapServiceImpl`은 대중교통 경로와 보행자 경로를 각각 Tmap API로 직접 요청한다.
- 근거:
  - `back/hatw/src/main/java/com/HATW/service/TmapServiceImpl.java:21-26`
  - `back/hatw/src/main/java/com/HATW/service/TmapServiceImpl.java:31-61`
  - `back/hatw/src/main/java/com/HATW/service/TmapServiceImpl.java:64-94`
  - `back/hatw/src/main/resources/application.properties:28-31`

### 2. 서버 엔드포인트 흐름
- `/api/map/forPram`:
  1. Tmap 대중교통 경로 조회
  2. 지하철 전후 WALK leg를 엘리베이터 경유로 강제 보정
  3. 후처리된 보행 경로를 응답
- `/api/map/forOld`:
  - Tmap 대중교통 경로를 받은 뒤 모든 WALK leg에 대해 추가 보행 경로를 계산
- 근거:
  - `back/hatw/src/main/java/com/HATW/controller/MapController.java:39-64`

### 3. 자체 구현된 핵심 후처리 알고리즘
- `TransitServiceImpl.getRouteWithElevator()`는 itinerary에서 `SUBWAY` 구간의 앞뒤 `WALK` leg만 골라 수정한다.
- 각 역명으로 엘리베이터 후보를 DB에서 찾고, 후보마다 Tmap 보행 경로를 다시 호출한다.
- 후보 중 `총 거리(distance)`가 가장 짧은 엘리베이터를 선택해 기존 WALK leg의 `walkRouteJson`과 `steps`를 덮어쓴다.
- 근거:
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:30-74`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:76-142`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:145-210`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:320-332`

### 4. 엘리베이터 후보 데이터 소스
- 엘리베이터는 그래프 탐색으로 찾는 것이 아니라 DB `marker` 테이블에서 가져온다.
- SQL 조건은 `type = 3` 그리고 `weight = 0` 이다.
- 즉, 현재 구현상 접근성 판단의 핵심 데이터는 경사도나 도로 속성이 아니라 `엘리베이터 마커 좌표`다.
- 근거:
  - `back/hatw/src/main/resources/mapper/MarkerMapper.xml:14-28`

### 5. 보행 구간 연결 방식
- 보행 구간은 직접 그래프를 탐색하지 않고 Tmap 보행 API를 다시 부르는 방식이다.
- 일부 매우 가까운 구간은 API 호출 대신 직선 `LineString`을 생성한다.
- 버스 연계 WALK에서는 `passList`를 만들어 Tmap 보행 API에 전달한다.
- 근거:
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:338-445`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:466-484`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:503-598`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:602-744`

### 6. 구현상 중요한 제한
- `TransitServiceImpl`는 여러 곳에서 `searchOption`과 `passList`를 파라미터에 넣지만, 실제 HTTP body를 만드는 `TmapServiceImpl.getPedestrianRoute()`는 `startX/startY/endX/endY/startName/endName/좌표계`만 전송한다.
- 따라서 코드 작성 의도와 달리 `searchOption=4`, `searchOption=30`, `passList`는 현재 커밋 기준 실제 Tmap 보행 경로 요청에 반영되지 않는다.
- 이 점 때문에 “우회 옵션”이나 “경유 제약”이 동작한다고 단정하면 안 된다.
- 근거:
  - `back/hatw/src/main/java/com/HATW/service/TmapServiceImpl.java:34-50`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:155-156`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:189-190`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:411-412`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:429-430`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:548-549`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:677-678`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:710-711`

## 경사도 반영 여부

### 코드 기준 판단
- 현재 커밋에는 `slope`, `elevation`, `grade`, `incline`, `DEM` 같은 경사도 계산/저장/평가 로직이 없다.
- `build.gradle`에도 지형/고도 분석용 라이브러리나 라우팅 엔진 의존성이 없다.
- 실제 선택 기준은 엘리베이터 후보별 `distance` 비교뿐이다.
- 근거:
  - `back/hatw/build.gradle:26-52`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:113-131`
  - 저장소 전체 키워드 검색 결과 기준 `slope|elevation|grade|incline|DEM` 관련 구현 부재

### README와 코드의 차이
- README는 다음 정책을 서술한다.
  - 엘리베이터 구간 가중치 1.0
  - 경사로 구간 가중치 1.5
  - 계단/에스컬레이터 제외
- 하지만 현재 코드/SQL에서는 이 정책을 실제로 계산하는 부분이 확인되지 않는다.
- 따라서 경사도 반영은 “구상 또는 설명” 수준이고, 구현 완료 상태로 보기는 어렵다.
- 근거:
  - `README.md:263-279`
  - `back/hatw/src/main/resources/mapper/MarkerMapper.xml:14-28`
  - `back/hatw/src/main/java/com/HATW/service/TransitServiceImpl.java:76-142`

## 사용 라이브러리/외부 서비스

### 실제 사용 외부 서비스
- `Tmap POI API`
- `Tmap Pedestrian Route API`
- `Tmap Transit Route API`
- `OpenAI Chat Completions API` (경로 안내 문장 생성용, 경로 계산용 아님)
- `Nurigo` SMS API

### 코드에 보이는 주요 라이브러리
- Spring Boot Web
- MyBatis
- Gson
- Java `HttpClient`
- OkHttp
- Lombok
- JJWT
- jBCrypt

### 확인되지 않은 것
- GraphHopper
- OSRM
- OpenRouteService
- Mapbox Directions
- Google Directions
- JGraphT / 자체 A* / Dijkstra 구현
- 지형 고도 처리 라이브러리

## PoC 관점 해석
- 이 저장소는 “접근성 데이터를 반영한 독자 라우팅 엔진”이라기보다, “Tmap 결과를 엘리베이터 정보로 보정하는 접근성 후처리 서비스”에 가깝다.
- 특히 경사도는 현재 코드상 반영되지 않았으므로, 부산 이음길 PoC에서 참고할 때는 `외부 경로 엔진 위 후처리` 사례로만 보는 것이 적절하다.
- GraphHopper 기반 자체 프로파일/커스텀 모델 검증과는 접근 방식이 다르다.

## 추가 관찰
- README에는 React 프런트 구조가 설명되지만, 현재 확인한 저장소 체크아웃에는 프런트엔드 소스가 보이지 않았다.
- `application.properties`에 실사용 API 키로 보이는 값이 평문 포함되어 있어 운영/공개 저장소 기준으로는 보안 위험이 있다. 라우팅 분석과 직접 관계는 없지만 참고 필요.
