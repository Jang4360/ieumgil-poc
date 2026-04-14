# 09_RESPONSE_MAPPING_VALIDATION.md

## 단계명

GraphHopper 응답 분석 및 API 응답 형태 변환 검증

## 목적

GraphHopper 결과에서 어떤 데이터를 꺼낼 수 있는지 파악하고, 현재 API 구조로 변환 가능한지 확인한다.

## 구현 접근

1. GraphHopper 원본 응답을 그대로 분석한다.
2. polyline, step, instruction, 거리, 시간, snapped point를 분리해 본다.
3. `routes[].segments[]` 구조를 만들 수 있는지 확인한다.
4. PoC 전용 DTO 초안을 만들고 샘플 경로 1건 이상 변환해 본다.
5. 현재 응답만으로 부족한 정보와 후처리 join이 필요한 지점을 기록한다.

## 확인할 것

- polyline 추출 가능 여부
- step / instruction 추출 가능 여부
- 거리, 시간, snapped point 추출 가능 여부
- `routes[].segments[]` 형태 매핑 가능 여부
- `guidanceMessage`를 instructions 기반으로 만들 수 있는지
- 위험 속성은 후처리 join이 필요한지

## 산출물

- GraphHopper 원본 응답 분석 문서
- PoC 응답 DTO 초안
- API 응답 매핑 표
- 샘플 경로 변환 결과
- 누락 필드 및 보완 필요 사항 기록

## 완료 기준

- PoC 응답 DTO 생성
- 샘플 경로 1건 이상 API 형태 변환 성공
- 변환 불가 또는 추가 규칙 필요 항목 문서화

## 범위 제한

- 메인 서비스 최종 API 명세 확정은 하지 않는다.
- 인증, 에러 코드 표준화는 포함하지 않는다.

## 다음 단계 입력값

- `SAFE` / `SHORTEST` 옵션 분리에 필요한 응답 차이 분석
- 후처리 대상 필드 목록
