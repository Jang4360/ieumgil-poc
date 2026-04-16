# Transportation PoC Results Summary Compact Review

## 목적
- `docs/plans/transportation/08_RESULTS_SUMMARY_GUIDE.md` 기준으로, 교통 PoC의 현재 결과를 다음 단계 입력값으로 쓸 수 있게 요약한다.
- 데이터 소스별 가용/불가 항목, 연결 가능 범위, 도보 구간 처리 범위, 접근성 반영 범위, MVP 투입 가능 범위를 구분한다.

## 검토 범위
- Step 1: 데이터 소스 스모크 테스트
- Step 2: 경로 후보 조회 검증
- Step 3: 데이터셋 연결 전략 및 매핑 검증
- Step 4~6: mixed path 도보 구간 추출 / 보행 입력 매핑 / 접근성 통합 검토
- Step 9: viewer hybrid transit 통합

참고 문서:
- [step1-transit-api-access-smoke-test-compact.md](C:/Users/SSAFY/poc/docs/reviews/transportation/step1-transit-api-access-smoke-test-compact.md)
- [step2-transit-smoke-test-script-bootstrap-compact.md](C:/Users/SSAFY/poc/docs/reviews/transportation/step2-transit-smoke-test-script-bootstrap-compact.md)
- [step3-dataset-linking-validation-compact.md](C:/Users/SSAFY/poc/docs/reviews/transportation/step3-dataset-linking-validation-compact.md)
- [step4-6-mixed-transit-walk-validation-compact.md](C:/Users/SSAFY/poc/docs/reviews/transportation/step4-6-mixed-transit-walk-validation-compact.md)
- [step9-viewer-hybrid-transit-integration-compact.md](C:/Users/SSAFY/poc/docs/reviews/transportation/step9-viewer-hybrid-transit-integration-compact.md)

## 한 줄 결론
- 현재 PoC 기준의 가장 현실적인 조합은 `ODsay + 부산 BIMS + 부산교통공사/odcloud + GraphHopper`다.
- 이 조합으로 `도보 + 버스 + 지하철` 혼합 경로를 viewer까지 연결할 수는 있었지만, `지하철 접근성`, 특히 `동해선` 커버리지는 아직 비어 있다.

## 데이터 소스별 판단

### 1. ODsay
- 가능:
  - 출발지 / 도착지 기준 대중교통 경로 후보 조회
  - 총 소요시간, 총 요금, 구간별 `WALK/BUS/SUBWAY` 분해
  - 버스 승하차 정류장, 지하철 승하차역, 환승 전후 WALK leg 추출
- 불가 또는 한계:
  - 버스 실시간 도착 정보 없음
  - 저상버스 실시간 여부 없음
  - 지하철 역사 엘리베이터 / 출입구 접근성 없음
- 역할:
  - 전체 경로 후보와 구간 시퀀스의 기준 앵커

### 2. 부산 BIMS
- 가능:
  - 버스 정류장명 / 정류장 ID / 좌표 조회
  - 실시간 버스 도착정보 조회
  - `lowplate` 기반 저상버스 여부 확인
- 불가 또는 한계:
  - 출발지-도착지 전체 경로 후보 생성 불가
  - 전체 이동시간 추천 엔진 역할 불가
- 역할:
  - 버스 구간의 실시간 운영 정보 보강

### 3. 부산교통공사 / odcloud
- 가능:
  - 일부 도시철도 노선의 노선명 / 노선번호 / 운행구간정거장 / 정거장 시각 정보 확인
  - 부산 1/2/3/4호선 계열은 노선/역명 매칭 가능
- 불가 또는 한계:
  - 실시간 지하철 도착 API로 보기 어려움
  - 역사 엘리베이터 / 출입구 접근성 데이터 없음
  - `동해선`은 현재 기준 데이터셋에서 매칭 실패 사례가 남음
- 역할:
  - 지하철 운영/노선 정보 보강

### 4. GraphHopper
- 가능:
  - 도보 leg를 실제 보행 네트워크 기준으로 재계산
  - snap 거리 확인
  - slope / width / elevator / curb gap / audio signal / braille block detail 요약
- 불가 또는 한계:
  - 대중교통 전체 경로 후보 생성 불가
  - 지하철/버스 자체 운영 정보 없음
- 역할:
  - ODsay가 준 WALK leg의 실제 보행 경로 검증과 재계산

## 데이터셋 연결 가능성

### 버스
- 전략:
  - `ODsay localStationID -> BIMS bstopid` 직접 확인
  - 부족하면 `이름 정규화 + 좌표 근접 + 노선 보조키` fallback
- 결과:
  - 대표 시나리오와 해운대구 확장 표본에서 최종적으로 `버스 미매핑 0건`
- 결론:
  - 버스는 현재 조합으로 MVP 투입 가능 수준

### 지하철
- 전략:
  - `노선명 정규화 + 출발역/도착역이 운행구간정거장에 함께 포함되는지`로 매핑
- 결과:
  - 부산 1/2/3/4호선 계열은 연결 가능
  - `동해선` 구간은 미매핑 사례가 남음
- 결론:
  - 지하철은 부분 가용
  - `도시철도 본선 일부는 가능`, `동해선과 역사 접근성은 보류`

## 도보 구간 처리 가능성

### 가능
- ODsay mixed path에서 `trafficType=3` 도보 leg 추출
- `ACCESS`, `TRANSFER`, `EGRESS` 역할 구분
- `startPoint/endPoint` 구조로 변환
- 지하철 구간은 `startExitX/Y`, `endExitX/Y`를 anchor로 우선 사용
- GraphHopper `wheelchair_safe / wheelchair_shortest`로 실제 재계산

### 확인된 점
- ODsay가 매우 짧게 준 도보 구간도 실제 보행 네트워크에서는 더 길 수 있다.
- 예시:
  - `반송시장 -> 오시리아역` mixed path의 마지막 egress leg는 ODsay상 `1m`
  - GraphHopper 재계산 결과 약 `44.9m`, 종료 snap `WARN`

### 결론
- 도보 leg는 `ODsay 원본 수치`보다 `GraphHopper 재계산 결과`를 우선 사용하는 편이 맞다.

## 접근성 정보 반영 범위

### 즉시 반영 가능
- 도보:
  - 거리
  - 시간
  - snap 상태
  - slope 범위
  - width 범위
  - elevator / curb gap / audio signal / braille block 존재 여부
- 버스:
  - 실시간 도착 시간
  - 정류장 전 수
  - 저상버스 여부 (`lowplate`)
- 지하철:
  - 노선명
  - 시작역 / 도착역
  - 운영 데이터 매칭 상태

### 아직 반영 불가 또는 보류
- 지하철 역사 엘리베이터 상세
- 지하철 출입구 접근성
- 역사 내부 환승 동선
- 동해선 접근성 데이터

## mixed path 가능 범위

### 확인 완료
- `도보 + 버스 + 지하철` 혼합 경로는 실제로 ODsay 응답에서 나온다.
- 대표 검증 시나리오 `반송시장 -> 오시리아역`은
  - `WALK -> BUS -> WALK -> SUBWAY -> WALK`
  로 추출됐다.
- 이 경로는 viewer까지 렌더링했다.

### viewer 반영 결과
- `1km 이하` 입력:
  - `WALK_ONLY`
- `1km 초과` 입력:
  - `HYBRID_TRANSIT`
- 요약 패널:
  - 총 거리
  - 총 시간
  - 총 요금
  - 데이터 소스
  - 구간별 거리 / 시간 / 교통수단
- 구간 상세:
  - 도보 detail
  - 버스 실시간 / 저상버스
  - 지하철 매칭 상태

## 가용 / 보류 / 불가

### 가용
- ODsay로 대중교통 후보 조회
- 버스 구간 BIMS 실시간 도착 / 저상버스 결합
- ODsay WALK leg 추출
- GraphHopper 보행 재계산
- hybrid viewer에서 `WALK_ONLY` / `HYBRID_TRANSIT` 분기

### 보류
- 동해선 구간 운영 데이터 매칭 안정화
- 지하철 역사 접근성 데이터 결합
- transit geometry 정밀 복원
- 복수 hybrid 후보 비교 UI

### 불가
- 현재 데이터셋만으로 지하철 역사 엘리베이터 / 출입구 상세 접근성 반영
- 현재 데이터셋만으로 모든 지하철 노선의 안정적인 운영 매칭 보장

## 실패 / 불일치 사례

### 1. odcloud와 동해선 불일치
- 사례:
  - `기장 -> 오시리아`
  - `센텀 -> 오시리아`
  - `재송 -> 벡스코`
- 의미:
  - 현재 연결한 부산교통공사/odcloud만으로는 동해선 커버리지가 부족하거나 운영 주체가 다를 가능성

### 2. 도보 거리 불일치
- 사례:
  - ODsay의 일부 WALK leg는 매우 짧게 나오지만, GraphHopper 재계산 결과는 더 길게 나옴
- 의미:
  - mixed path 응답에서 도보 구간은 재계산 후 결과를 우선 사용해야 함

### 3. direct ID만으로는 불충분
- 사례:
  - 정류장명 괄호 표기, 약칭, 방향 분리
- 대응:
  - `이름 정규화 + 좌표 근접 + 노선 보조키` fallback으로 해결

## MVP 투입 가능 범위
- 출발지 / 도착지 기준 hybrid path 조회
- 버스 / 지하철 / 도보 구간 분리
- 도보 leg GraphHopper 재계산
- 버스 실시간 / 저상버스 결합
- 지하철 노선 / 역명 / 매칭 상태 표시
- viewer에서 hybrid path 렌더링

## MVP 제외 또는 후속 과제
- 지하철 접근성 데이터 추가 확보
- 동해선 운영 데이터 보강
- 역사 내부 동선 모델링
- 사용자 선호 기반 경로 선택 정책
- 서비스용 API 정교화와 본 UX 반영

## 최종 판단
- 현재 PoC는 `교통정보 + 보행 재계산 + viewer 시각화`까지는 연결됐다.
- 버스는 MVP 수준에서 충분히 쓸 수 있다.
- 지하철은 `노선/역 정보 표시` 수준은 가능하지만, `접근성`과 `동해선 커버리지`는 아직 비어 있다.
- 따라서 다음 단계의 최우선 과제는 `지하철 접근성 데이터 보강`과 `동해선 보완 데이터셋 확인`이다.
