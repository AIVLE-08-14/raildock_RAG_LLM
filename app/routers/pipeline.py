"""자동화 파이프라인 API 라우터"""

import os
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
    2. 3개 폴더 (rail, insulator, nest) 읽기
    3. 각 JSON에 대해 문서 생성 + 검토(권장 조치내용 수정)
    4. 폴더별 PDF 보고서 생성 (rail, insulator, nest 각각)

    Args:
        file: ZIP 파일
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

        # 3. Vision 결과 읽기
        vision_results = zip_processor.read_vision_results(extract_dir)

        if not vision_results:
            raise HTTPException(status_code=400, detail="처리할 Vision 결과가 없습니다.")

        # 4. 각 결과 처리
        results = []
        pdf_reports_by_folder = {'rail': [], 'insulator': [], 'nest': []}
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
                # 문서 생성
                print(f"  → 문서 생성 중...")
                document, referenced_regs, rag_used = document_generator.generate(
                    vision_result=vision_result,
                    use_rag=True
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

                # PDF용 데이터 수집 (폴더별 분류)
                if generate_pdf and folder in pdf_reports_by_folder:
                    pdf_reports_by_folder[folder].append({
                        'document_content': document,
                        'vision_result': vision_result,
                        'review_result': None,
                        'image_path': image_path
                    })

                results.append(result)

            except Exception as e:
                # 개별 처리 실패 시 계속 진행
                results.append(ProcessResult(
                    filename=filename,
                    folder=folder,
                    document=f"처리 실패: {str(e)}"
                ))

        # 5. 폴더별 PDF 생성
        pdf_paths = {}
        if generate_pdf:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for folder_name, reports in pdf_reports_by_folder.items():
                if reports:
                    try:
                        pdf_filename = f"batch_report_{folder_name}_{timestamp}.pdf"
                        pdf_path = pdf_generator.generate_batch_report(reports, pdf_filename)
                        pdf_paths[folder_name] = pdf_path
                        print(f"  → {folder_name} PDF 생성: {pdf_path}")
                    except Exception as e:
                        print(f"  → {folder_name} PDF 생성 실패: {e}")

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
async def process_vision_folder(folder_path: str, generate_pdf: bool = True, skip_review: bool = False):
    """
    로컬 폴더에서 Vision 결과 처리 (테스트용)

    Args:
        folder_path: Vision 결과가 있는 폴더 경로 (예: result_1)
        generate_pdf: PDF 생성 여부
        skip_review: 검토 단계 건너뛰기 (기본: False)
    """
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail=f"폴더를 찾을 수 없습니다: {folder_path}")

    try:
        # Vision 결과 읽기
        vision_results = zip_processor.read_vision_results(folder_path)

        if not vision_results:
            raise HTTPException(status_code=400, detail="처리할 Vision 결과가 없습니다.")

        # 처리
        results = []
        pdf_reports_by_folder = {'rail': [], 'insulator': [], 'nest': []}

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
                # 문서 생성
                print(f"  → 문서 생성 중...")
                document, referenced_regs, rag_used = document_generator.generate(
                    vision_result=vision_result,
                    use_rag=True
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

                # PDF용 데이터 수집 (폴더별 분류)
                if generate_pdf and folder in pdf_reports_by_folder:
                    pdf_reports_by_folder[folder].append({
                        'document_content': document,
                        'vision_result': vision_result,
                        'review_result': None,
                        'image_path': image_path
                    })

                results.append(result)

            except Exception as e:
                results.append({
                    'filename': filename,
                    'folder': folder,
                    'error': str(e)
                })

        # 폴더별 PDF 생성
        pdf_paths = {}
        if generate_pdf:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for folder_name, reports in pdf_reports_by_folder.items():
                if reports:
                    try:
                        pdf_filename = f"{folder_name}_report_{timestamp}.pdf"
                        pdf_path = pdf_generator.generate_batch_report(reports, pdf_filename)
                        pdf_paths[folder_name] = pdf_path
                        print(f"  → {folder_name} PDF 생성: {pdf_path}")
                    except Exception as e:
                        print(f"  → {folder_name} PDF 생성 실패: {e}")

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
