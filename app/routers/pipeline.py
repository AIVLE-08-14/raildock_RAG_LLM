"""자동화 파이프라인 API 라우터"""

import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.zip_processor import zip_processor
from app.services.generator import document_generator
from app.services.reviewer import document_reviewer
from app.services.pdf_generator import pdf_generator
from chatbot.services.report_vector_service import report_vector_service


# PDF 파일명 한글 매핑
FOLDER_NAME_MAP = {
    'rail': '선로_탐지_보고서',
    'insulator': '애자_탐지_보고서',
    'nest': '새둥지_탐지_보고서'
}

# JSON 결과 저장 경로
JSON_REPORTS_DIR = Path("./data/json_reports")


def save_batch_json_report(
    folder: str,
    reports: List[Dict],
    metadata: dict = None,
    timestamp: str = None
) -> str:
    """폴더별 통합 JSON 파일 저장 (PDF와 동일한 방식)"""
    import hashlib

    # 디렉토리 생성
    JSON_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 타임스탬프
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    created_at = datetime.now().isoformat()

    # 리포트 ID 생성
    hash_input = f"{folder}_{timestamp}"
    report_id = f"RPT-{datetime.now().strftime('%Y%m%d')}-{hashlib.md5(hash_input.encode()).hexdigest()[:6].upper()}"

    # 개별 리포트 데이터 구성
    report_items = []
    for idx, report in enumerate(reports, 1):
        report_items.append({
            "index": idx,
            "source_file": report.get("filename", ""),
            "image_file": report.get("vision_result", {}).get("image_file", ""),
            "vision_result": report.get("vision_result", {}),
            "document_content": report.get("document_content", ""),
            "review_result": report.get("review_result", None)
        })

    # 통합 JSON 데이터 구성
    json_data = {
        "report_id": report_id,
        "dataset_type": folder,
        "dataset_name": FOLDER_NAME_MAP.get(folder, folder),
        "created_at": created_at,
        "total_count": len(reports),
        "metadata": metadata,
        "reports": report_items
    }

    # 파일 저장
    report_name = FOLDER_NAME_MAP.get(folder, folder)
    json_filename = f"{report_name}_{timestamp}.json"
    json_path = JSON_REPORTS_DIR / json_filename

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    return str(json_path)


def load_metadata(metadata_path: str) -> Optional[Dict]:
    """메타데이터 JSON 파일 로드"""
    if not metadata_path or not os.path.exists(metadata_path):
        return None
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"메타데이터 로드 실패: {e}")
        return None


router = APIRouter()


class ProcessResult(BaseModel):
    """처리 결과"""
    filename: str
    folder: str
    document: str
    pdf_path: Optional[str] = None


class PipelineResponse(BaseModel):
    """파이프라인 응답"""
    message: str
    total_processed: int
    summary: dict
    results: List[ProcessResult]
    pdf_paths: Optional[Dict[str, str]] = None  # 폴더별 PDF 경로


@router.post("/process-zip", response_model=PipelineResponse)
async def process_vision_zip(
    file: UploadFile = File(...),
    generate_pdf: bool = True,
    skip_review: bool = False
):
    """
    Vision AI 결과 ZIP 파일 처리

    1. ZIP 압축 해제
    2. ZIP 내 metadata.json 자동 인식
    3. 3개 폴더 (rail, insulator, nest) 읽기
    4. 각 JSON에 대해 문서 생성 + 검토(권장 조치내용 수정)
    5. 폴더별 PDF 보고서 생성 (rail, insulator, nest 각각)

    Args:
        file: ZIP 파일 (metadata.json 포함 가능)
        generate_pdf: PDF 생성 여부 (기본: True)
        skip_review: 검토 단계 건너뛰기 (기본: False)
    """
    # 파일 확장자 확인
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="ZIP 파일만 업로드 가능합니다.")

    try:
        # 1. ZIP 파일 읽기
        zip_bytes = await file.read()

        # 2. 압축 해제
        extract_dir, folders = zip_processor.extract_zip_from_bytes(zip_bytes, file.filename)

        # 3. ZIP 내 metadata.json 자동 인식
        metadata = None
        metadata_candidates = ['metadata.json', 'meta.json']
        for candidate in metadata_candidates:
            metadata_file = os.path.join(extract_dir, candidate)
            if os.path.exists(metadata_file):
                metadata = load_metadata(metadata_file)
                if metadata:
                    print(f"ZIP 내 메타데이터 자동 인식: {candidate}")
                    break

        # 4. Vision 결과 읽기
        vision_results = zip_processor.read_vision_results(extract_dir)

        if not vision_results:
            raise HTTPException(status_code=400, detail="처리할 Vision 결과가 없습니다.")

        # 4. 각 결과 처리
        results = []
        pdf_reports_by_folder = {'rail': [], 'insulator': [], 'nest': []}
        json_reports_by_folder = {'rail': [], 'insulator': [], 'nest': []}
        total = len(vision_results)

        print(f"\n{'='*50}")
        print(f"  총 {total}개 파일 처리 시작")
        print(f"{'='*50}\n")

        for idx, item in enumerate(vision_results, 1):
            vision_result = item['vision_result']
            folder = item['folder']
            image_path = item.get('image_path')
            filename = vision_result.get('image_file', 'unknown')

            print(f"[{idx}/{total}] 처리 중: {folder}/{filename}")

            try:
                # 문서 생성 (메타데이터 + folder 포함)
                print(f"  → 문서 생성 중...")
                document, referenced_regs, rag_used = document_generator.generate(
                    vision_result=vision_result,
                    use_rag=True,
                    metadata=metadata,
                    folder=folder
                )

                # 문서 검토 (권장 조치내용 직접 수정)
                if not skip_review:
                    print(f"  → 문서 검토 및 수정 중...")
                    revised_document = document_reviewer.review(
                        document=document,
                        vision_result=vision_result
                    )
                    document = revised_document
                    print(f"  ✓ 완료")
                else:
                    print(f"  ✓ 완료 (검토 생략)")

                # 결과 저장
                result = ProcessResult(
                    filename=filename,
                    folder=folder,
                    document=document
                )

                # JSON용 데이터 수집 (폴더별 분류)
                if folder in json_reports_by_folder:
                    json_reports_by_folder[folder].append({
                        'filename': filename,
                        'vision_result': vision_result,
                        'document_content': document,
                        'review_result': {"revised": not skip_review}
                    })

                # PDF용 데이터 수집 (폴더별 분류)
                if generate_pdf and folder in pdf_reports_by_folder:
                    pdf_reports_by_folder[folder].append({
                        'document_content': document,
                        'vision_result': vision_result,
                        'review_result': None,
                        'image_path': image_path,
                        'metadata': metadata
                    })

                # 챗봇용 보고서 Vector DB 저장
                try:
                    report_id = report_vector_service.add_report(
                        document_content=document,
                        folder=folder,
                        filename=filename,
                        vision_result=vision_result,
                        metadata=metadata
                    )
                    print(f"  → 보고서 저장: {report_id}")
                except Exception as e:
                    print(f"  → 보고서 저장 실패: {e}")

                results.append(result)

            except Exception as e:
                # 개별 처리 실패 시 계속 진행
                results.append(ProcessResult(
                    filename=filename,
                    folder=folder,
                    document=f"처리 실패: {str(e)}"
                ))

        # 5. 폴더별 PDF 및 JSON 생성
        pdf_paths = {}
        json_paths = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # PDF 생성
        if generate_pdf:
            for folder_name, reports in pdf_reports_by_folder.items():
                if reports:
                    try:
                        report_name = FOLDER_NAME_MAP.get(folder_name, folder_name)
                        pdf_filename = f"{report_name}_{timestamp}.pdf"
                        pdf_path = pdf_generator.generate_batch_report(reports, pdf_filename)
                        pdf_paths[folder_name] = pdf_path
                        print(f"  → {folder_name} PDF 생성: {pdf_path}")
                    except Exception as e:
                        print(f"  → {folder_name} PDF 생성 실패: {e}")

        # JSON 생성 (폴더별 통합)
        for folder_name, reports in json_reports_by_folder.items():
            if reports:
                try:
                    json_path = save_batch_json_report(
                        folder=folder_name,
                        reports=reports,
                        metadata=metadata,
                        timestamp=timestamp
                    )
                    json_paths[folder_name] = json_path
                    print(f"  → {folder_name} JSON 생성: {json_path}")
                except Exception as e:
                    print(f"  → {folder_name} JSON 생성 실패: {e}")

        # 6. 요약 정보
        summary = zip_processor.get_summary(vision_results)

        # 7. 임시 폴더 정리
        zip_processor.cleanup(extract_dir)

        return PipelineResponse(
            message=f"처리 완료: {len(results)}개 파일",
            total_processed=len(results),
            summary=summary,
            results=results,
            pdf_paths=pdf_paths
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 실패: {str(e)}")


@router.post("/process-folder")
async def process_vision_folder(
    folder_path: str,
    metadata_path: str = "",
    generate_pdf: bool = True,
    skip_review: bool = False
):
    """
    로컬 폴더에서 Vision 결과 처리 (테스트용)

    Args:
        folder_path: Vision 결과가 있는 폴더 경로 (예: result_1)
        metadata_path: 메타데이터 JSON 파일 경로 (선택)
        generate_pdf: PDF 생성 여부
        skip_review: 검토 단계 건너뛰기 (기본: False)
    """
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail=f"폴더를 찾을 수 없습니다: {folder_path}")

    # 메타데이터 로드
    metadata = load_metadata(metadata_path) if metadata_path else None
    if metadata:
        print(f"메타데이터 로드 완료: {metadata_path}")

    try:
        # Vision 결과 읽기
        vision_results = zip_processor.read_vision_results(folder_path)

        if not vision_results:
            raise HTTPException(status_code=400, detail="처리할 Vision 결과가 없습니다.")

        # 처리
        results = []
        pdf_reports_by_folder = {'rail': [], 'insulator': [], 'nest': []}
        json_reports_by_folder = {'rail': [], 'insulator': [], 'nest': []}

        total = len(vision_results)
        print(f"\n{'='*50}")
        print(f"  총 {total}개 파일 처리 시작")
        print(f"{'='*50}\n")

        for idx, item in enumerate(vision_results, 1):
            vision_result = item['vision_result']
            folder = item['folder']
            image_path = item.get('image_path')
            filename = vision_result.get('image_file', 'unknown')

            print(f"[{idx}/{total}] 처리 중: {folder}/{filename}")

            try:
                # 문서 생성 (메타데이터 + folder 포함)
                print(f"  → 문서 생성 중...")
                document, referenced_regs, rag_used = document_generator.generate(
                    vision_result=vision_result,
                    use_rag=True,
                    metadata=metadata,
                    folder=folder
                )

                # 문서 검토 (권장 조치내용 직접 수정)
                if not skip_review:
                    print(f"  → 문서 검토 및 수정 중...")
                    revised_document = document_reviewer.review(
                        document=document,
                        vision_result=vision_result
                    )
                    document = revised_document
                    print(f"  ✓ 완료")
                else:
                    print(f"  ✓ 완료 (검토 생략)")

                result = {
                    'filename': filename,
                    'folder': folder,
                    'document': document
                }

                # JSON용 데이터 수집 (폴더별 분류)
                if folder in json_reports_by_folder:
                    json_reports_by_folder[folder].append({
                        'filename': filename,
                        'vision_result': vision_result,
                        'document_content': document,
                        'review_result': {"revised": not skip_review}
                    })

                # PDF용 데이터 수집 (폴더별 분류)
                if generate_pdf and folder in pdf_reports_by_folder:
                    pdf_reports_by_folder[folder].append({
                        'document_content': document,
                        'vision_result': vision_result,
                        'review_result': None,
                        'image_path': image_path,
                        'metadata': metadata
                    })

                # 챗봇용 보고서 Vector DB 저장
                try:
                    report_id = report_vector_service.add_report(
                        document_content=document,
                        folder=folder,
                        filename=filename,
                        vision_result=vision_result,
                        metadata=metadata
                    )
                    print(f"  → 보고서 저장: {report_id}")
                except Exception as e:
                    print(f"  → 보고서 저장 실패: {e}")

                results.append(result)

            except Exception as e:
                results.append({
                    'filename': filename,
                    'folder': folder,
                    'error': str(e)
                })

        # 폴더별 PDF 및 JSON 생성
        pdf_paths = {}
        json_paths = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # PDF 생성
        if generate_pdf:
            for folder_name, reports in pdf_reports_by_folder.items():
                if reports:
                    try:
                        report_name = FOLDER_NAME_MAP.get(folder_name, folder_name)
                        pdf_filename = f"{report_name}_{timestamp}.pdf"
                        pdf_path = pdf_generator.generate_batch_report(reports, pdf_filename)
                        pdf_paths[folder_name] = pdf_path
                        print(f"  → {folder_name} PDF 생성: {pdf_path}")
                    except Exception as e:
                        print(f"  → {folder_name} PDF 생성 실패: {e}")

        # JSON 생성 (폴더별 통합)
        for folder_name, reports in json_reports_by_folder.items():
            if reports:
                try:
                    json_path = save_batch_json_report(
                        folder=folder_name,
                        reports=reports,
                        metadata=metadata,
                        timestamp=timestamp
                    )
                    json_paths[folder_name] = json_path
                    print(f"  → {folder_name} JSON 생성: {json_path}")
                except Exception as e:
                    print(f"  → {folder_name} JSON 생성 실패: {e}")

        # 요약
        summary = zip_processor.get_summary(vision_results)

        return {
            'message': f'처리 완료: {len(results)}개 파일',
            'total_processed': len(results),
            'summary': summary,
            'results': results,
            'pdf_paths': pdf_paths
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 실패: {str(e)}")


@router.get("/download-pdf/{filename}")
async def download_pdf(filename: str):
    """생성된 PDF 다운로드"""
    pdf_path = Path("./data/reports") / filename

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF 파일을 찾을 수 없습니다.")

    return FileResponse(
        path=str(pdf_path),
        filename=filename,
        media_type='application/pdf'
    )


@router.get("/list-pdfs")
async def list_generated_pdfs():
    """생성된 PDF 목록 조회"""
    reports_dir = Path("./data/reports")

    if not reports_dir.exists():
        return {"pdfs": []}

    pdfs = []
    for pdf_file in reports_dir.glob("*.pdf"):
        pdfs.append({
            "filename": pdf_file.name,
            "size": pdf_file.stat().st_size,
            "created": pdf_file.stat().st_mtime
        })

    return {"pdfs": sorted(pdfs, key=lambda x: x['created'], reverse=True)}
