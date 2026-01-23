"""API 테스트 스크립트"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_health():
    """헬스 체크"""
    print("\n=== 1. 헬스 체크 ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_init_database():
    """DB 초기화"""
    print("\n=== 2. DB 초기화 ===")
    response = requests.post(f"{BASE_URL}/init/database")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_load_regulations():
    """규정 PDF 로드"""
    print("\n=== 3. 규정 PDF 로드 ===")
    response = requests.post(f"{BASE_URL}/regulations/load-pdfs")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return response.status_code == 200


def test_upload_status():
    """업로드 상태 확인"""
    print("\n=== 4. 업로드 상태 확인 ===")
    response = requests.get(f"{BASE_URL}/upload/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_upload_zip():
    """ZIP 파일 업로드 테스트"""
    print("\n=== 5. ZIP 파일 업로드 ===")

    # result_1 폴더를 ZIP으로 압축하여 업로드
    import zipfile
    import tempfile

    result_path = Path(__file__).parent.parent.parent / "result_1"

    if not result_path.exists():
        print(f"테스트 데이터 폴더가 없습니다: {result_path}")
        return False

    # 임시 ZIP 파일 생성
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name

    with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in result_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(result_path)
                zf.write(file_path, arcname)

    # 업로드
    with open(tmp_path, 'rb') as f:
        files = {'file': ('test_result.zip', f, 'application/zip')}
        response = requests.post(f"{BASE_URL}/upload/vision-result", files=files)

    # 임시 파일 삭제
    Path(tmp_path).unlink()

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return response.status_code == 200


def test_metadata():
    """메타데이터 조회"""
    print("\n=== 6. 메타데이터 조회 ===")

    for data_type in ['rail', 'insulator', 'nest']:
        response = requests.get(f"{BASE_URL}/metadata/{data_type}?limit=2")
        print(f"\n[{data_type}] Status: {response.status_code}")
        result = response.json()
        print(f"Count: {result.get('count', 0)}")

    # 통계
    response = requests.get(f"{BASE_URL}/metadata/stats/summary")
    print(f"\n[통계] {response.json()}")

    return True


def test_regulations():
    """규정 목록 조회"""
    print("\n=== 7. 규정 목록 조회 ===")
    response = requests.get(f"{BASE_URL}/document/regulations")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return response.status_code == 200


def test_rag_query():
    """RAG 쿼리 테스트"""
    print("\n=== 8. RAG 쿼리 테스트 ===")

    query_data = {
        "query": "레일 결함 마모 조치",
        "top_k": 3
    }

    response = requests.post(
        f"{BASE_URL}/document/query",
        json=query_data
    )
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return response.status_code == 200


def test_document_generate():
    """문서 생성 테스트"""
    print("\n=== 9. 문서 생성 테스트 ===")

    # 샘플 Vision 결과
    vision_result = {
        "image_id": "test_001",
        "file_name": "rail_test_frame_001.jpg",
        "defects": [
            {
                "category": "레일",
                "status": "abnormal",
                "status_detail": "마모",
                "confidence": 0.92,
                "bbox": [100, 200, 150, 80]
            }
        ],
        "metadata": {
            "datetime": "2024-01-15 14:30:00",
            "region_name": "서울역",
            "weather": "맑음",
            "temperature": 5,
            "humidity": 40
        }
    }

    request_data = {
        "vision_result": vision_result,
        "use_rag": True
    }

    response = requests.post(
        f"{BASE_URL}/document/generate",
        json=request_data
    )
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"RAG 사용: {result.get('rag_used')}")
        print(f"참조 규정: {result.get('referenced_regulations')}")
        print(f"\n--- 생성된 문서 (앞부분) ---")
        print(result.get('draft', '')[:500] + "...")
    else:
        print(f"Error: {response.json()}")

    return response.status_code == 200


def main():
    print("=" * 60)
    print("철도 문서 AI 시스템 - API 테스트")
    print("=" * 60)

    tests = [
        ("헬스 체크", test_health),
        ("DB 초기화", test_init_database),
        ("규정 PDF 로드", test_load_regulations),
        ("업로드 상태", test_upload_status),
        ("ZIP 업로드", test_upload_zip),
        ("메타데이터 조회", test_metadata),
        ("규정 목록", test_regulations),
        ("RAG 쿼리", test_rag_query),
        ("문서 생성", test_document_generate),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✓" if success else "✗"))
        except Exception as e:
            print(f"Error: {e}")
            results.append((name, "✗"))

    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    for name, status in results:
        print(f"  {status} {name}")


if __name__ == "__main__":
    main()
