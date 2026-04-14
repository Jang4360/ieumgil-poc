# Constraints Implementation Compact Review

- 기준 문서: `AGENTS.md`, `docs/plans/graphhopper/02_CONSTRAINTS.md`, `ieumgil-routing-poc/AGENT_CONTEXT.md`
- 검토 일자: 2026-04-14

## 문서 보강 내용

`docs/plans/graphhopper/02_CONSTRAINTS.md`의 `## 작업 제약` 아래에 현재 단계에서 허용하는 준비 작업과 구현하지 않는 작업을 추가했다.

추가 목적은 아래와 같다.

- 현재 단계에서 허용되는 구현 범위를 문서로 고정
- Dockerfile, docker-compose, 환경 설정 같은 준비 작업만 허용
- ETL 확장, 비즈니스 코드 확장, GraphHopper import 자동화는 계속 제외

## 구현 결과

현재 제약에 맞춰 아래 파일을 추가 또는 수정했다.

### 1. 컨테이너 구성

- `docker-compose.yml`
  - `backend`, `postgres`, `graphhopper` 3개 컨테이너만 정의
- `.env.example`
  - 포트와 Postgres 계정 예시 제공

### 2. backend 준비

- `ieumgil-routing-poc/Dockerfile`
  - Spring Boot `bootJar` 기반 이미지 빌드
- `ieumgil-routing-poc/.dockerignore`
  - 불필요 파일 제외
- `ieumgil-routing-poc/src/main/resources/application-docker.yaml`
  - Postgres/GraphHopper 연결용 Docker 프로필 설정
- `ieumgil-routing-poc/build.gradle`
  - Actuator 추가
- `ieumgil-routing-poc/src/test/resources/application-test.yaml`
- `ieumgil-routing-poc/src/test/java/com/example/ieumgil_routing_poc/IeumgilRoutingPocApplicationTests.java`
  - 외부 DB 없이 테스트 가능하도록 `test` 프로필 적용

### 3. postgres 준비

- `infra/postgres/init/01-enable-postgis.sql`
  - `postgis` extension 초기화 추가

### 4. graphhopper 준비

- `infra/graphhopper/Dockerfile`
  - GraphHopper 11.0 web jar와 config 다운로드
- `infra/graphhopper/docker-entrypoint.sh`
  - 기본 모드를 `standby`로 두어 현재 단계에서 import 자동 실행 방지

## 제약 준수 판단

이번 구현은 `02_CONSTRAINTS.md` 제약을 벗어나지 않는다.

- 3개 컨테이너 구조만 사용함
- ETL 전용 컨테이너를 추가하지 않음
- Python 대량 ETL을 작성하지 않음
- GraphHopper import 자동화와 실제 경로 API 구현을 넣지 않음
- 엔티티, 리포지토리, 서비스 같은 비즈니스 코드 확장을 하지 않음
- 문서와 설정 중심 산출물로 남김

## 검증 결과

실행 또는 확인한 항목:

- `.\gradlew.bat test` 성공
- `.\gradlew.bat bootJar` 성공
- `docker compose config` 성공
- `docker compose build` 성공
  - `poc-backend` 이미지 빌드 완료
  - `poc-graphhopper` 이미지 빌드 완료

## 결론

현재 Step 1 제약 안에서 허용 가능한 인프라 준비 작업은 문서화했고, 그 문서 기준으로 최소 구현도 반영했다. 설정 검증, Spring Boot 빌드, Docker Compose 이미지 빌드까지 완료되어 현재 단계의 최소 인프라 준비 상태는 확보됐다.
