# 철도 문서 AI 시스템 (LLM + RAG)

Vision AI 결과를 기반으로 철도 시설물 점검 보고서를 자동 생성하고 검토하는 시스템입니다.

## 주요 기능

- **자동 문서 생성**: Vision AI 결과 → 점검 보고서 자동 생성
- **RAG 기반 검토**: 규정 문서 참조하여 권장 조치내용 보완
- **PDF 출력**: 폴더별(rail/insulator/nest) PDF 보고서 생성
- **ZIP 업로드**: ZIP 파일 업로드 → 자동 처리 → PDF 다운로드

## 시스템 구성

```
┌─────────────────────────────────────────────────────────────┐
│                    철도 문서 AI 시스템                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Vision AI 결과 (JSON)                                     │
│         │                                                   │
│         ▼                                                   │
│   ┌─────────────┐     ┌─────────────┐                      │
│   │  문서 생성   │────▶│  ChromaDB   │                      │
│   │  (Gemini)   │◀────│   (RAG)     │                      │
│   └─────────────┘     └─────────────┘                      │
│         │                    │                              │
│         ▼                    │                              │
│   ┌─────────────┐           │                              │
│   │  문서 검토   │◀──────────┘                              │
│   │  (Gemini)   │                                          │
│   └─────────────┘                                          │
│         │                                                   │
│         ▼                                                   │
│   PDF 보고서 출력 (rail/insulator/nest 별도)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 기술 스택

- **Backend**: FastAPI
- **LLM**: Google Gemini 2.5 Flash
- **Vector DB**: ChromaDB
- **PDF**: ReportLab (한글 지원)
- **Container**: Docker

## 사전 요구사항

- Python 3.9 이상
- Google Gemini API 키 ([발급 링크](https://aistudio.google.com/app/apikey))
- Docker (서버 배포 시)

---

## 실행 순서도

```
┌─────────────────────────────────────────────────────────────┐
│                      실행 순서                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 저장소 clone                                            │
│         │                                                   │
│         ▼                                                   │
│  2. 규정 PDF 복사 (data/regulations/)                       │
│         │                                                   │
│         ▼                                                   │
│  3. 환경변수 설정 (.env)                                    │
│         │                                                   │
│         ▼                                                   │
│  ┌──────┴──────┐                                           │
│  │             │                                            │
│  ▼             ▼                                            │
│ [로컬]      [Docker]                                        │
│  │             │                                            │
│  ▼             ▼                                            │
│ pip install   docker-compose                                │
│ python run.py  up --build                                   │
│         │             │                                     │
│         └──────┬──────┘                                     │
│                ▼                                            │
│  4. DB 초기화 (규정 벡터화)                                 │
│         │                                                   │
│         ▼                                                   │
│  5. http://localhost:8888/docs 접속                         │
│         │                                                   │
│         ▼                                                   │
│  6. ZIP 업로드 → PDF 생성 완료                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. 환경 설정

### 1.1 저장소 다운로드

```bash
git clone https://github.com/AIVLE-08-14/raildock_RAG_LLM.git
cd raildock_RAG_LLM
```

### 1.2 규정 PDF 다운로드 (S3)

```bash
# AWS CLI 설치 (없는 경우)
# https://aws.amazon.com/cli/

# AWS 자격 증명 설정
aws configure

# S3에서 규정 문서 다운로드
aws s3 cp s3://버킷명/scenario_document/ ./data/regulations/ --recursive
aws s3 cp s3://버킷명/maintenance_document/ ./data/regulations/ --recursive
```

또는 로컬 파일이 있는 경우:
```bash
cp -r /path/to/scenario_document/*.pdf ./data/regulations/
cp -r /path/to/maintenance_document/*.pdf ./data/regulations/
```

### 1.3 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 수정:

```bash
cp .env.example .env
```

`.env` 파일 열어서 API 키 입력:

```env
# Google Gemini API 키 (필수)
GOOGLE_API_KEY=your_api_key_here

# 나머지는 기본값 사용 가능
GEMINI_MODEL=gemini-2.5-flash
CHROMA_PERSIST_PATH=./data/chroma_db
REGULATIONS_PATHS=./data/regulations
```

---

## 2. 실행 방법

### 방법 1: Docker (권장)

```bash
# 빌드 + 실행
docker-compose up -d --build

# DB 초기화 (최초 1회)
curl -X POST "http://localhost:8888/documents/init-db"

# 로그 확인
docker-compose logs -f
```

### 방법 2: 로컬 실행

**처음 실행 시 (의존성 설치 + DB 초기화):**

```bash
python run.py --setup --init-db
```

**이후 실행 시:**

```bash
python run.py
```

### 방법 3: 수동 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 서버 실행
uvicorn app.main:app --reload --host 127.0.0.1 --port 8888

# 3. DB 초기화 (별도 터미널에서)
curl -X POST "http://localhost:8888/documents/init-db"
```

---

## 3. 서버 접속

서버 실행 후 브라우저에서:

```
http://127.0.0.1:8888/docs
```

Swagger UI에서 모든 API를 테스트할 수 있습니다.

---

## 4. 사용 방법

### 4.1 규정 PDF 임베딩 (최초 1회)

`python run.py --init-db` 사용 시 자동으로 수행됩니다.

수동으로 하려면 Swagger UI에서:
1. `DELETE /regulations/clear` - 기존 데이터 초기화
2. `POST /regulations/load-pdfs` - PDF 임베딩

### 4.2 Vision 결과 처리

**로컬 폴더 처리:**

1. Swagger UI에서 `POST /pipeline/process-folder` 클릭
2. `folder_path`에 Vision 결과 폴더 경로 입력:
   ```
   C:\Users\사용자명\Downloads\result_1
   ```
3. Execute 클릭

**ZIP 파일 업로드:**

1. Swagger UI에서 `POST /pipeline/process-zip` 클릭
2. ZIP 파일 선택 후 업로드
3. Execute 클릭

### 4.3 결과 확인

- 터미널에서 진행 상황 확인:
  ```
  [1/30] 처리 중: rail/rail_고속철도_frame_000000.jpg
    → 문서 생성 중...
    → 문서 검토 중...
    ✓ 완료 (적합: True)
  ```

- 생성된 PDF 확인:
  - `GET /pipeline/list-pdfs` - PDF 목록 조회
  - `GET /pipeline/download-pdf/{filename}` - PDF 다운로드
  - 또는 `data/reports/` 폴더에서 직접 확인

---

## 5. 폴더 구조

```
document_ai_system/
├── app/
│   ├── main.py              # FastAPI 앱
│   ├── config.py            # 설정
│   ├── models/
│   │   └── schemas.py       # 데이터 스키마
│   ├── routers/
│   │   ├── document.py      # 문서 API
│   │   └── pipeline.py      # 파이프라인 API
│   ├── services/
│   │   ├── generator.py     # 문서 생성 (Gemini)
│   │   ├── reviewer.py      # 문서 검토 (Gemini)
│   │   ├── vector_service.py # ChromaDB
│   │   ├── zip_processor.py # ZIP 처리
│   │   └── pdf_generator.py # PDF 생성
│   └── utils/
│       ├── chunker.py       # 텍스트 청킹
│       └── pdf_loader.py    # PDF 로드
├── data/
│   ├── chroma_db/           # 벡터 DB 저장소
│   └── reports/             # 생성된 PDF
├── .env                     # 환경 변수
├── requirements.txt         # 의존성
├── run.py                   # 실행 스크립트
└── README.md                # 이 파일
```

---

## 6. API 목록

### Pipeline (자동화)

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/pipeline/process-zip` | POST | ZIP 파일 업로드 → 자동 처리 |
| `/pipeline/process-folder` | POST | 로컬 폴더 처리 |
| `/pipeline/list-pdfs` | GET | 생성된 PDF 목록 |
| `/pipeline/download-pdf/{filename}` | GET | PDF 다운로드 |

### Document (개별 처리)

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/document/generate` | POST | 문서 생성 |
| `/document/review` | POST | 문서 검토 |
| `/document/query` | POST | RAG 질의 |
| `/document/regulations` | GET | 규정 목록 |

### Regulations (규정 관리)

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/regulations/load-pdfs` | POST | PDF 임베딩 |
| `/regulations/clear` | DELETE | DB 초기화 |

---

## 7. Vision 결과 폴더 구조

시스템이 처리하는 Vision AI 결과 폴더 구조:

```
result_1/
├── rail/              # 레일 결함
│   ├── frames/        # 이미지 파일 (.jpg)
│   └── json/          # Vision 결과 (.json)
├── insulator/         # 애자 결함
│   ├── frames/
│   └── json/
└── nest/              # 둥지 탐지
    ├── frames/
    └── json/
```

### JSON 파일 형식

```json
{
  "source_mp4": "rail_input.mp4",
  "frame_index": 0,
  "timestamp_ms": 0.0,
  "image_file": "rail_고속철도_220916_영암1_frame_000000.jpg",
  "detections": [
    {
      "cls_id": 7,
      "rail_type": "고속철도",
      "cls_name": "레일",
      "detail": "마모",
      "confidence": 0.95,
      "bbox_xyxy": [100, 100, 200, 200]
    }
  ],
  "is_anomaly": true
}
```

---

## 8. 규정 문서

시스템이 참조하는 규정 문서:

### scenario_document/ (시나리오별 규정)
- `철도_선로_유지보수_규정_시나리오.pdf` - 120개 청크
- `애자_규정_유지보수_시나리오.pdf` - 120개 청크
- `둥지류_규정_시나리오_권장조치추가본.pdf` - 15개 청크

### maintenance_document/ (핵심 참조 문서)
- `선로유지관리지침.pdf` - 전체 문서 저장
- `선로유지관리지침_별표6.pdf` - 전체 문서 저장

---

## 9. 설정 변경

`.env` 파일에서 설정 변경 가능:

```env
# Gemini 모델 변경
GEMINI_MODEL=gemini-2.5-flash

# RAG 검색 결과 개수
RAG_TOP_K=5

# 청크 크기 (글자 수)
CHUNK_SIZE=500
CHUNK_OVERLAP=200
```

---

## 10. Docker 배포

### 10.1 서버에 파일 전송

```bash
# git clone
git clone https://github.com/AIVLE-08-14/raildock_RAG_LLM.git
cd raildock_RAG_LLM
```

### 10.2 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# API 키 입력
nano .env
# GOOGLE_API_KEY=실제_API_키_입력
```

### 10.3 규정 PDF 복사

```bash
# 규정 문서를 data/regulations 폴더에 복사
cp -r /path/to/scenario_document/* ./data/regulations/
cp -r /path/to/maintenance_document/* ./data/regulations/
```

### 10.4 Docker 실행

```bash
# 빌드 + 실행 (한 번에)
docker-compose up -d --build

# 로그 확인
docker-compose logs -f
```

### 10.5 DB 초기화

```bash
# 규정 문서 벡터화 (최초 1회)
curl -X POST "http://localhost:8888/documents/init-db"
```

### 10.6 Docker 명령어

| 명령어 | 설명 |
|--------|------|
| `docker-compose up -d --build` | 빌드 + 백그라운드 실행 |
| `docker-compose down` | 중지 |
| `docker-compose restart` | 재시작 |
| `docker-compose logs -f` | 로그 실시간 확인 |
| `docker ps` | 실행 중인 컨테이너 확인 |

---

## 11. 라이선스

이 프로젝트는 내부 사용 목적으로 제작되었습니다.
