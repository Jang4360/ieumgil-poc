# 11_RESULTS_SUMMARY_GUIDE.md

## 목적

각 단계의 PoC 결과를 같은 형식으로 정리하기 위한 기준 문서다.

## 기본 정리 형식

1. 목적
2. 입력 데이터
3. 실행 환경
4. 시도한 방법
5. 성공한 것
6. 안 된 것
7. 제약 사항
8. 다음 단계
9. ADR 반영 필요 사항

## 반드시 남길 항목

- 부산 OSM import 가능 여부
- GraphHopper 기본 보행 경로 성공 여부
- 스냅핑 성공 여부
- API 응답 변환 가능 여부
- `SAFE` / `SHORTEST` 분리 가능 여부
- 위험도 반영은 어디서부터 후처리가 필요한지

## 결과 문서 위치

- 단계별 결과는 `docs/reviews/`에 Markdown으로 남긴다.
- 파일명은 단계명과 검토 목적이 드러나도록 작성한다.

예시:
- `graphhopper-route-validation-compact.md`
- `response-mapping-review.md`
