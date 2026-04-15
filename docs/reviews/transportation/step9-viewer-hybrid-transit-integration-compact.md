# Step 9 Viewer Hybrid Transit Integration Compact Review

## 목적
- `docs/plans/transportation/09_VIEWER_HYBRID_TRANSIT_INTEGRATION_PLAN.md`를 기준으로, 기존 GraphHopper KakaoMap viewer를 `보행 전용 + 대중교통 혼합` viewer로 확장한다.
- `http://localhost:8080/`에서 출발지 / 도착지 조회 시
  - `1km 이하`는 `WALK_ONLY`
  - `1km 초과`는 `HYBRID_TRANSIT`
  로 분기되도록 구현한다.

## 구현 범위
- static viewer에 로컬 API 서버를 붙였다.
- viewer는 `1km 기준 분기`, `경로 요약 패널`, `구간 상세 패널`, `지도 구간 렌더링`을 처리한다.
- 로컬 API 서버는 아래 역할을 맡는다.
  - `ODsay` 대중교통 후보 조회
  - `WALK` 구간 GraphHopper 재계산
  - `BUS` 구간 BIMS 실시간/저상버스 정보 결합
  - `SUBWAY` 구간 odcloud 매칭 상태 결합

## 수정 파일
- viewer 서버: [server.py](C:/Users/SSAFY/poc/docs/poc-viewers/graphhopper-kakaomap/server.py)
- viewer 클라이언트: [app.js](C:/Users/SSAFY/poc/docs/poc-viewers/graphhopper-kakaomap/app.js)
- 화면 구조: [index.html](C:/Users/SSAFY/poc/docs/poc-viewers/graphhopper-kakaomap/index.html)
- 스타일: [styles.css](C:/Users/SSAFY/poc/docs/poc-viewers/graphhopper-kakaomap/styles.css)
- 설정 예시: [config.local.example.js](C:/Users/SSAFY/poc/docs/poc-viewers/graphhopper-kakaomap/config.local.example.js)
- 실행 문서: [README.md](C:/Users/SSAFY/poc/docs/poc-viewers/graphhopper-kakaomap/README.md)

## 구현 내용

### 1. `localhost:8080` 로컬 API 서버 추가
- `python -m http.server` 대신 `server.py`를 추가했다.
- 이 서버는 정적 파일과 `/api/hybrid-route`를 같은 포트에서 제공한다.
- 브라우저가 ODsay/BIMS/odcloud를 직접 호출하지 않도록 해서
  - API 키 노출
  - CORS
  문제를 피했다.

### 2. 1km 기준 모드 분기
- `straightDistanceMeter <= 1000`이면 `WALK_ONLY`
- `straightDistanceMeter > 1000`이면 `HYBRID_TRANSIT`
- `WALK_ONLY`에서는 GraphHopper 단일 도보 segment를 반환한다.
- `HYBRID_TRANSIT`에서는 ODsay path를 기반으로 `WALK`, `BUS`, `SUBWAY` 구간을 구성한다.

### 3. 혼합 경로 응답 조합
- `WALK`
  - GraphHopper profile로 실제 geometry 재계산
  - snap distance / snap status 포함
  - slope, width, elevator, curb gap, audio signal, braille block detail 요약 포함
- `BUS`
  - ODsay 구간 거리 / 시간 사용
  - BIMS `stopArrByBstopid` 결과를 붙여 `min1`, `station1`, `lowplate1` 등 제공
- `SUBWAY`
  - ODsay 구간 거리 / 시간 사용
  - odcloud 매칭 상태와 사유 포함

### 4. viewer UI 변경
- 요약 패널:
  - 모드
  - 총 거리
  - 총 시간
  - 총 요금
  - 데이터 소스
  - 구간별 카드
- 상세 패널:
  - 도보 detail summary
  - 버스 실시간/저상버스
  - 지하철 매칭 상태
- 지도:
  - `WALK`, `BUS`, `SUBWAY`를 타입별 색상으로 렌더링
  - 각 구간의 시작/끝 anchor marker 표시

## 실행 테스트

### 테스트 1. hybrid 경로
- 요청:
  - `반송시장 -> 오시리아역`
  - `profile=wheelchair_safe`
- 호출:

```powershell
python C:\Users\SSAFY\poc\docs\poc-viewers\graphhopper-kakaomap\server.py
Invoke-WebRequest "http://127.0.0.1:8080/api/hybrid-route?startLat=35.2269086&startLng=129.1486268&endLat=35.1962560&endLng=129.2082910&profile=wheelchair_safe"
```

- 결과:
  - `mode = HYBRID_TRANSIT`
  - 구간 시퀀스 = `WALK -> BUS -> WALK -> SUBWAY -> WALK`
  - 요금 = `1600`
  - 버스 구간 실시간 정보 결합 성공
  - 지하철 구간은 `동해선`으로 odcloud 기준 `UNMATCHED`

### 테스트 2. walk-only 경로
- 요청:
  - `서면역.롯데호텔백화점` 인근 짧은 좌표쌍
- 결과:
  - `straightDistanceMeter ≈ 75.9m`
  - `mode = WALK_ONLY`
  - segment 1개, 타입 `WALK`

### 테스트 3. 정적 viewer 응답
- `http://127.0.0.1:8080/` HTML 응답 정상 확인
- viewer 서버 기동 후 정적 페이지와 hybrid API가 같은 포트에서 함께 동작함을 확인

## 확인된 동작
- `1km` 기준 분기 동작
- hybrid route API 응답 동작
- ODsay 기반 mixed path 조합 동작
- BIMS 실시간 / 저상버스 필드 결합 동작
- odcloud 매칭 상태 반영 동작
- viewer용 통합 응답 구조 생성 동작

## 남은 제약
- 실제 브라우저 상의 시각적 UI는 자동화로 확인하지 못했고, 이번 단계는 HTML/API 응답과 로컬 실행 기반 검증이다.
- `BUS`, `SUBWAY` geometry는 ODsay `passStopList` 좌표 기반 요약선이며, 정밀 선형 복원은 아니다.
- `동해선`은 현재 연결된 odcloud 데이터셋 기준으로 여전히 `UNMATCHED`가 발생할 수 있다.
- hybrid 모드에서는 `family shortest/safe 비교`를 지원하지 않고, 비교 버튼은 보행 전용 쿼리에서만 유의미하다.
- GraphHopper 서버는 별도로 떠 있어야 한다.

## 결론
- 계획 문서 09 기준의 핵심 요구였던
  - `1km 이하 보행`
  - `1km 초과 대중교통 혼합`
  - 요약 패널에 `도보/교통정보`, `거리`, `소요시간`, `사용 데이터셋` 표시
  는 구현됐다.
- 현재 viewer는 PoC 수준에서 `GraphHopper + ODsay + BIMS + odcloud`를 하나의 조회 흐름으로 통합해 보여줄 수 있다.
- 실질적인 후속 과제는 `동해선 지하철 데이터 보강`, `UI polish`, `transit geometry 정밀화`다.
