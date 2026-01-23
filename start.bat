@echo off
chcp 65001 > nul
echo ========================================
echo   철도 문서 AI 시스템 시작
echo ========================================
echo.

REM 의존성 설치
echo [1/3] 의존성 설치 중...
pip install -r requirements.txt -q

REM 환경변수 확인
if not exist .env (
    echo [경고] .env 파일이 없습니다. .env.example을 복사하세요.
    copy .env.example .env
    echo .env 파일을 생성했습니다. GOOGLE_API_KEY를 설정하세요.
    pause
    exit /b
)

REM 데이터 폴더 생성
echo [2/3] 데이터 폴더 확인 중...
if not exist data\chroma_db mkdir data\chroma_db
if not exist data\reports mkdir data\reports

REM 서버 시작
echo [3/3] 서버 시작 중...
echo.
echo ========================================
echo   http://localhost:8000/docs 에서 API 테스트
echo   Ctrl+C로 종료
echo ========================================
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
