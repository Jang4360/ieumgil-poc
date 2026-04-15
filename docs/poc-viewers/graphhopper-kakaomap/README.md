# GraphHopper Hybrid Transit Viewer

정적 보행 viewer를 확장해, `1km` 이하에서는 GraphHopper 보행 경로를, `1km` 초과에서는 `도보 + 버스 + 지하철` 혼합 경로를 보여주는 PoC viewer다.

## 파일

- `index.html`
- `app.js`
- `styles.css`
- `config.local.example.js`
- `server.py`

## 동작 구조

- `WALK_ONLY`
  - GraphHopper만 사용
- `HYBRID_TRANSIT`
  - `ODsay`로 대중교통 후보 조회
  - `WALK` 구간은 GraphHopper로 재계산
  - `BUS` 구간은 `부산 BIMS` 실시간/저상버스 정보 보강
  - `SUBWAY` 구간은 `부산교통공사/odcloud` 매칭 상태 보강

## 준비

1. `config.local.example.js`를 복사해서 `config.local.js`를 만든다.
2. `config.local.js`에 최소한 아래 값을 넣는다.
   - `kakaoJavascriptKey`
   - `graphhopperBaseUrl`
   - `hybridTransitApiBaseUrl`
3. `.env`에 ODsay / BIMS / odcloud 키가 있어야 한다.
4. GraphHopper 서버를 먼저 띄운다.

예시:

```js
window.APP_CONFIG = {
  kakaoJavascriptKey: "YOUR_KAKAO_JAVASCRIPT_KEY",
  graphhopperBaseUrl: "http://localhost:8989",
  hybridTransitApiBaseUrl: "http://localhost:8080",
  initialCenter: { lat: 35.157, lng: 129.059 },
  initialLevel: 5
};
```

## 실행

### 1. GraphHopper 실행

GraphHopper는 `http://localhost:8989`에서 떠 있어야 한다.

### 2. viewer 서버 실행

```powershell
cd C:\Users\SSAFY\poc\docs\poc-viewers\graphhopper-kakaomap
Copy-Item .\config.local.example.js .\config.local.js
python .\server.py
```

### 3. 브라우저 열기

- [http://localhost:8080](http://localhost:8080)

## 주요 기능

- 출발지 / 도착지 좌표 입력 또는 지도 클릭 입력
- `1km` 이하 보행 경로 조회
- `1km` 초과 하이브리드 대중교통 경로 조회
- `WALK`, `BUS`, `SUBWAY` 구간별 색상 렌더링
- 경로 요약 패널
  - 총 거리
  - 총 시간
  - 총 요금
  - 데이터 소스
  - 구간별 거리 / 시간
- 구간 상세 패널
  - 도보 snap 상태
  - 버스 실시간 도착 / 저상버스 여부
  - 지하철 매칭 상태
- 보행 family shortest/safe 비교
  - 보행 전용 경로에서만 사용 권장

## 주의

- 이 viewer는 로컬 PoC 용도다.
- `server.py`는 `.env`의 API 키를 사용하므로, 반드시 로컬에서만 실행해야 한다.
- 브라우저가 직접 ODsay/BIMS/odcloud를 호출하지 않고, 같은 `localhost:8080`의 로컬 API를 통해 우회한다.
- 지하철 `동해선`처럼 현재 odcloud에 바로 매핑되지 않는 구간은 `UNMATCHED`로 표시될 수 있다.
