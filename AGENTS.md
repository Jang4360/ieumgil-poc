# AGENTS.md

## 목적
이 저장소는 부산 이음길 PoC 전용 작업 공간이다.
현재 목표는 OSM 원천 데이터 확보, 보행 네트워크 구축 가능성 검증, GraphHopper 기반 경로 탐색 가능성 검증이다.

메인 서비스 구현이 아니라 기술 검증이 목적이므로, 실험 코드와 결과 문서를 명확히 남기는 것을 우선한다.

---

## 작업 원칙

1. 메인 프로젝트 코드는 수정하지 않는다.
2. PoC는 재현 가능해야 한다.
3. 모든 판단은 문서로 남긴다.
4. 현재 단계에서 확정되지 않은 설계를 성급히 일반화하지 않는다.
5. 실패한 시도도 기록한다.
6. 문서, 코드, 스크립트의 역할을 분리한다.

---

## 현재 단계

현재 진행 단계는 아래와 같다.

### Step 1
부산 OSM 원천 데이터 확보 및 범위 검증

### 현재 검증 목표
- 부산 범위 데이터 확보 가능 여부 확인
- 파일 포맷이 `.osm.pbf`인지 확인
- 보행 관련 태그 포함 여부 확인
- 데이터 크기와 처리 가능성 확인
- 적재 대상 원천 파일 확정

---

## 폴더별 역할

### `/docs`
PoC 공통 규칙, 범위, 제약사항, 완료 기준, 의사결정 템플릿을 둔다.

### `/ieumgil-routing-poc`
Spring Boot 기반 PoC 프로젝트.
현재 단계에서는 직접 구현보다 향후 GraphHopper 연동과 Postgres 연결을 위한 준비 역할이 크다.

### `/ieumgil-osm-etl-poc`
OSM 원천 데이터 검증 및 향후 전처리 작업 공간.
현재 단계에서는 데이터 확보, 포맷 검증, 태그 샘플 확인이 목적이다.

---

## 문서 우선순위

작업 시작 전 아래 순서로 읽는다.

1. `AGENTS.md`
2. `docs/plans/graphhopper/00_EXECUTION_ROADMAP.md`
3. `docs/plans/graphhopper/01_SCOPE_AND_GOALS.md`
4. `docs/plans/graphhopper/02_CONSTRAINTS.md`
5. 해당 프로젝트의 `AGENT_CONTEXT.md`

---

## 작업별 참고 문서

### 원천 데이터 확보 작업
반드시 아래 문서를 참고한다.
- `docs/plans/graphhopper/00_EXECUTION_ROADMAP.md`
- `docs/plans/graphhopper/01_SCOPE_AND_GOALS.md`
- `docs/plans/graphhopper/03_EXECUTION_ROADMAP.md`
- `docs/plans/graphhopper/04_WALKABLE_SEGMENT_CRITERIA.md`
- `ieumgil-osm-etl-poc/AGENT_CONTEXT.md`

### Spring Boot 프로젝트 초기화 작업
반드시 아래 문서를 참고한다.
- `docs/plans/graphhopper/00_EXECUTION_ROADMAP.md`
- `docs/plans/graphhopper/02_CONSTRAINTS.md`
- `ieumgil-routing-poc/AGENT_CONTEXT.md`

### 완료 기준 검토 작업
반드시 아래 문서를 참고한다.
- 해당 단계 계획 문서의 `완료 기준` 섹션

### PoC 결과 정리 작업
반드시 아래 문서를 참고한다.
- 해당 단계 계획 문서
- `docs/reviews/`

---

## 산출물 규칙

작업 결과는 아래 중 하나 이상으로 남겨야 한다.

- Markdown 문서
- 실행 명령어
- 샘플 파일 경로
- 확인한 데이터셋 정보
- 의사결정 기록

---

## 금지 사항

1. 현재 단계에서 메인 서비스 구조를 확정된 구현처럼 작성하지 않는다.
2. 검증되지 않은 데이터를 운영 기준 데이터로 가정하지 않는다.
3. 문서 없는 임의 판단을 하지 않는다.
4. 현재 단계에서 경사도 계산, 공공데이터 매핑, Slack 반영 자동화까지 한 번에 확장하지 않는다.

---

## 현재 단계 종료 조건

아래가 모두 충족되면 Step 1 완료로 본다.

- 부산 범위 OSM 원천 파일 1개 이상 확보
- `.osm.pbf` 포맷 확인
- 보행 태그 샘플 확인
- 적재 대상으로 사용할 원천 파일 확정
- 결과 문서 작성 완료
