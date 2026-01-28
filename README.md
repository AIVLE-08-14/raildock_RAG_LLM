# RAILDOCK - 철도 시설물 점검 AI 시스템

Vision AI 결과를 기반으로 철도 시설물 점검 보고서를 자동 생성하고, RAG 기반 챗봇으로 점검 결과를 조회하는 시스템입니다.

## 주요 기능

| 기능 | 설명 |
|------|------|
| 자동 문서 생성 | Vision AI 결과 → 점검 보고서 자동 생성 |
| RAG 기반 검토 | 규정 문서 참조하여 위험도 판정 및 조치방법 작성 |
| 환경정보 반영 | 온도/습도/날씨 기반 위험도 판정 |
| PDF 출력 | 폴더별(rail/insulator/nest) PDF 보고서 생성 |
| 챗봇 질의응답 | 규정 + 보고서 RAG + Google 웹검색 통합 챗봇 |

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RAILDOCK 시스템                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    문서 생성 파이프라인                        │   │
│  │                                                             │   │
│  │   Vision AI 결과 (JSON)                                     │   │
│  │          │                                                  │   │
│  │          ▼                                                  │   │
│  │   ┌──────────────┐      ┌──────────────┐                   │   │
│  │   │  generator   │◀────▶│  규정 RAG    │                   │   │
│  │   │  (문서 생성)  │      │  (ChromaDB)  │                   │   │
│  │   └──────────────┘      └──────────────┘                   │   │
│  │          │                                                  │   │
│  │          ▼                                                  │   │
│  │   ┌──────────────┐                                         │   │
│  │   │   reviewer   │                                         │   │
│  │   │  (문서 검토)  │                                         │   │
│  │   └──────────────┘                                         │   │
│  │          │                                                  │   │
│  │          ▼                                                  │   │
│  │   ┌──────────────┐                                         │   │
│  │   │pdf_generator │                                         │   │
│  │   │  (PDF 출력)  │                                         │   │
│  │   └──────────────┘                                         │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                       챗봇 서비스                             │   │
│  │                                                             │   │
│  │   사용자 질문                                                │   │
│  │        │                                                    │   │
│  │        ├──────────────┬──────────────┬──────────────┐      │   │
│  │        ▼              ▼              ▼              ▼      │   │
│  │   ┌─────────┐   ┌──────────┐   ┌──────────┐  ┌─────────┐  │   │
│  │   │ 규정 RAG │   │ 보고서   │   │  Google  │  │ Gemini  │  │   │
│  │   │ (1순위) │   │RAG(2순위)│   │웹검색    │  │2.5 Flash│  │   │
│  │   └─────────┘   └──────────┘   │ (3순위)  │  └─────────┘  │   │
│  │                                └──────────┘               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Backend | FastAPI |
| LLM | Google Gemini 2.5 Flash |
| Vector DB | ChromaDB |
| Embedding | Sentence-Transformers |
| Web Search | Google Search Retrieval |
| PDF | ReportLab (한글 지원) |
| Container | Docker |

---

## 폴더 구조

```
document_ai_system/
├── app/                          # 문서 생성 시스템
│   ├── main.py                   # FastAPI 앱
│   ├── config.py                 # 설정
│   ├── models/
│   │   └── schemas.py            # 데이터 스키마
│   ├── routers/
│   │   ├── document.py           # 문서 API
│   │   └── pipeline.py           # 파이프라인 API
│   ├── services/
│   │   ├── generator.py          # 문서 생성 (Gemini + RAG)
│   │   ├── reviewer.py           # 문서 검토 (Gemini)
│   │   ├── pdf_generator.py      # PDF 생성
│   │   ├── vector_service.py     # 규정 RAG (ChromaDB)
│   │   └── zip_processor.py      # ZIP 처리
│   └── utils/
│       ├── chunker.py            # 텍스트 청킹
│       └── pdf_loader.py         # PDF 로드
│
├── chatbot/                      # 챗봇 서비스
│   ├── config.py                 # 챗봇 설정
│   ├── routers/
│   │   └── chat.py               # 챗봇 API
│   └── services/
│       ├── chatbot_service.py    # 챗봇 로직 (규정+보고서 RAG+웹검색)
│       └── report_vector_service.py  # 보고서 RAG
│
├── data/
│   ├── regulations/              # 규정 PDF 원본
│   │   ├── scenario_document/    # 시나리오 규정
│   │   └── maintenance_document/ # 유지보수 규정
│   ├── chroma_db/                # 규정 Vector DB
│   ├── report_db/                # 보고서 Vector DB (챗봇용)
│   ├── reports/                  # 생성된 PDF (데이터셋별 통합)
│   └── json_reports/             # 생성된 JSON (데이터셋별 통합)
│
├── scripts/                      # 유틸리티 스크립트
│   ├── init_db.py                # DB 초기화
│   ├── embed_documents.py        # 문서 임베딩
│   ├── embed_regulations.py      # 규정 임베딩
│   └── test_api.py               # API 테스트
│
├── .env.example                  # 환경변수 예시
├── requirements.txt              # 의존성
├── run.py                        # 실행 스크립트
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 핵심 모듈 설명

### generator.py
- Vision AI 탐지 결과를 입력받아 점검 보고서 텍스트 생성
- 규정 RAG를 검색하여 프롬프트에 포함
- 결함 분석, 위험도 등급 판정(E/O/X1/X2/S), 조치방법 작성

### reviewer.py
- 생성된 보고서를 LLM이 검토하고 수정
- 등급 판정 적절성, 조치방법 타당성 검증
- 피드백과 함께 수정된 문서 반환

### pdf_generator.py
- 텍스트 보고서를 PDF 파일로 변환
- 문서 파싱 (필드별 추출)
- 테이블/이미지 배치, 줄바꿈 후처리

### chatbot_service.py
- 규정 RAG + 보고서 RAG + Google 웹검색 3단계 검색
- **정보 우선순위**: 규정(1순위) > 보고서(2순위) > 웹검색(3순위)
- 위험도 등급 판정은 규정만 참고 (웹검색 사용 금지)
- 웹검색 사용 시 "웹 검색 결과,"로 시작하여 구분
- 참조한 규정 ID 및 보고서 목록 반환

---

## 빠른 시작

```bash
# 1. 저장소 클론
git clone https://github.com/AIVLE-08-14/raildock_RAG_LLM.git
cd raildock_RAG_LLM

# 2. 환경변수 설정
cp .env.example .env
# .env 파일에 GOOGLE_API_KEY 입력

# 3. 규정 PDF 복사
# data/regulations/ 폴더에 scenario_document, maintenance_document 복사

# 4. 실행 (의존성 설치 + DB 초기화 + 서버 시작)
python run.py --setup --init-db

# 5. 접속
# http://localhost:8000/docs
```

---

## 실행 방법

### 로컬 실행

```bash
# 처음 실행 시
python run.py --setup --init-db

# 이후 실행 시
python run.py
```

- 포트: **8000**
- API 문서: http://localhost:8000/docs

### Docker 실행

```bash
# 빌드 + 실행
docker-compose up -d --build

# DB 초기화 (최초 1회)
curl -X POST "http://localhost:8888/regulations/load-pdfs"

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

- 포트: **8888**
- API 문서: http://localhost:8888/docs

---

## API 엔드포인트

### Pipeline (자동화)

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/pipeline/process-zip` | POST | ZIP 업로드 → 자동 처리 |
| `/pipeline/process-folder` | POST | 로컬 폴더 처리 |
| `/pipeline/list-pdfs` | GET | PDF 목록 |
| `/pipeline/download-pdf/{filename}` | GET | PDF 다운로드 |

### Document (개별 처리)

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/document/generate` | POST | 문서 생성 |
| `/document/review` | POST | 문서 검토 |
| `/document/query` | POST | RAG 질의 |
| `/document/regulations` | GET | 규정 목록 |
| `/document/regulations/add` | POST | 규정 추가 |

### Chatbot

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/chatbot/ask` | POST | 챗봇 질문 |
| `/chatbot/reports` | GET | 저장된 보고서 목록 |
| `/chatbot/stats` | GET | 보고서 통계 |
| `/chatbot/clear` | DELETE | 보고서 DB 초기화 |

### Regulations

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/regulations/load-pdfs` | POST | PDF 임베딩 |
| `/regulations/clear` | DELETE | DB 초기화 |

---

## 환경 변수

`.env.example`을 `.env`로 복사 후 수정:

```env
# Google Gemini API 키 (필수)
GOOGLE_API_KEY=your_api_key_here

# Gemini 모델
GEMINI_MODEL=gemini-2.5-flash

# ChromaDB 저장 경로
CHROMA_PERSIST_PATH=./data/chroma_db

# 규정 문서 경로
REGULATIONS_PATHS=./data/regulations/scenario_document,./data/regulations/maintenance_document

# RAG 설정
CHUNK_SIZE=500
CHUNK_OVERLAP=200
RAG_TOP_K=5
RAG_THRESHOLD=0.1
```

---

## 위험도 등급

| 등급 | 상태 | 권장 조치 |
|------|------|----------|
| E | 파손 진행 없음 | 교체 불필요, 정기 점검 유지 |
| O | 요주의 결함 | 지속 모니터링 |
| X1 | 중·장기 파손 발전 | 1개월 이내 교체 |
| X2 | 단기 파손 발전 | 10일 이내 교체 |
| S | 즉각 파손 위험 | 즉시 교체 (당일) |
