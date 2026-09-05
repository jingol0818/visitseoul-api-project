# Visit Seoul API Project

2026 서울관광재단 「비짓서울 API 데이터·AI 활용 아이디어 공모전」 참가를 위한
비짓서울 API 데이터 분석 및 AI 관광서비스 프로토타입 연구 저장소입니다.

- 프로젝트 사이트: https://jingol0818.github.io/visitseoul-api-project/
- 데이터 출처: [비짓서울 API 센터](https://api.visitseoul.net/) (서울관광재단)
- 현재 단계: **Research / Prototype**

## Purpose

- 비짓서울 관광 콘텐츠 데이터 구조 및 활용 가능성 분석
- 외부 데이터와의 결합 가능성 조사
- AI 기술을 활용한 신규 관광서비스 아이디어 및 프로토타입 연구

## 구조

```
index.html            프로젝트 소개 페이지 (GitHub Pages 루트)
census/               비짓서울 API 전수조사 코드
  config.py           엔드포인트·카테고리·언어·필드 정의 (비밀값 없음)
  client.py           API 클라이언트 — 키는 환경변수 VISITSEOUL_API_KEY 로만 읽음
  fetch_all.py        카테고리·언어코드·목록·상세 전수 수집 (원본 JSON 보존, 재개 가능)
  analyze.py          전수 분석 → reports/census_report.md
data/raw/             원본 응답 JSON (gitignore, 로컬 전용)
data/processed/       정제 CSV/JSONL
reports/              분석 리포트
.env.example          환경변수 예시 (.env 는 커밋 금지)
```

## 전수조사 항목 (API 키 발급 후 실행)

1. 모든 API 엔드포인트 2. 요청 파라미터 3. 응답 필드 전체
4. 8개 카테고리별 데이터 수 5. 7개 언어별 데이터 수
6. 필드별 값 존재율(null/빈값) 7. 좌표·운영시간·휴무일·행사기간·장애인 편의시설·교통·태그 충실도
8. 등록일/수정일 및 갱신 특성 9. 서울 외 지역 콘텐츠 10. 중복·오래된 정보·언어 간 불일치

```bash
pip install -r requirements.txt
cp .env.example .env        # VISITSEOUL_API_KEY 입력
python -m census.fetch_all  # 수집 (원본 → data/raw)
python -m census.analyze    # 분석 (→ reports/census_report.md)
```

## 보안

- API Key·토큰·비밀번호는 코드와 저장소에 넣지 않습니다. `.env`·`*.key`·`secrets/` 는 `.gitignore` 로 제외됩니다.
- 키가 실수로 커밋되면 즉시 비짓서울 API 센터에서 키를 삭제·재발급하고 커밋 이력에서 제거합니다.
- 본 사이트·저장소는 서울관광재단의 공식 사이트가 아니며, 공모전 참가자의 연구용입니다.
