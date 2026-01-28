"""ZIP 파일 처리 서비스"""

import zipfile
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime


class ZipProcessor:
    """Vision AI 결과 ZIP 파일 처리"""

    def __init__(self):
        # 임시 디렉토리 기본 경로
        self.temp_base = Path(tempfile.gettempdir()) / "document_ai_temp"
        self.temp_base.mkdir(parents=True, exist_ok=True)

    def extract_zip(self, zip_path: str) -> Tuple[str, List[str]]:
        """
        ZIP 파일 압축 해제

        Args:
            zip_path: ZIP 파일 경로

        Returns:
            (압축 해제 경로, 폴더 목록)
        """
        # 타임스탬프로 고유 폴더 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extract_dir = self.temp_base / f"result_{timestamp}"
        extract_dir.mkdir(parents=True, exist_ok=True)

        # ZIP 압축 해제 (한글 인코딩 처리)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for info in zip_ref.infolist():
                # 한글 파일명 인코딩 처리
                try:
                    decoded_name = info.filename.encode('cp437').decode('euc-kr')
                except (UnicodeDecodeError, UnicodeEncodeError):
                    try:
                        decoded_name = info.filename.encode('cp437').decode('utf-8')
                    except:
                        decoded_name = info.filename

                # 경로 생성 및 추출
                target_path = extract_dir / decoded_name
                if info.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zip_ref.open(info) as source, open(target_path, 'wb') as target:
                        target.write(source.read())

        # 폴더 목록 (rail, insulator, nest 등)
        folders = [f.name for f in extract_dir.iterdir() if f.is_dir()]

        return str(extract_dir), folders

    def extract_zip_from_bytes(self, zip_bytes: bytes, filename: str = "upload.zip") -> Tuple[str, List[str]]:
        """
        바이트 데이터에서 ZIP 압축 해제

        Args:
            zip_bytes: ZIP 파일 바이트 데이터
            filename: 원본 파일명

        Returns:
            (압축 해제 경로, 폴더 목록)
        """
        # 임시 파일로 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_zip = self.temp_base / f"temp_{timestamp}.zip"

        with open(temp_zip, 'wb') as f:
            f.write(zip_bytes)

        # 압축 해제
        extract_dir, folders = self.extract_zip(str(temp_zip))

        # 임시 ZIP 파일 삭제
        temp_zip.unlink()

        return extract_dir, folders

    def read_vision_results(self, extract_dir: str) -> List[Dict[str, Any]]:
        """
        압축 해제된 폴더에서 모든 Vision 결과 JSON 읽기

        Args:
            extract_dir: 압축 해제된 경로

        Returns:
            Vision 결과 리스트 (폴더별 그룹화)
        """
        results = []
        extract_path = Path(extract_dir)

        # 각 폴더 순회 (rail, insulator, nest)
        for folder in extract_path.iterdir():
            if not folder.is_dir():
                continue

            folder_name = folder.name
            json_dir = folder / "json"

            # 이미지 폴더 찾기 (detect > frames 우선순위)
            frames_dir = None
            for img_folder in ['detect', 'frames']:
                candidate = folder / img_folder
                if candidate.exists():
                    frames_dir = candidate
                    break

            if not json_dir.exists():
                continue

            # JSON 파일 읽기
            for json_file in sorted(json_dir.glob("*.json")):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        vision_result = json.load(f)

                    # 매칭되는 이미지 경로 추가
                    image_name = vision_result.get('image_file', '')
                    image_path = frames_dir / image_name if (frames_dir and image_name) else None

                    results.append({
                        'folder': folder_name,
                        'json_file': str(json_file),
                        'image_path': str(image_path) if image_path and image_path.exists() else None,
                        'vision_result': vision_result
                    })

                except json.JSONDecodeError as e:
                    print(f"JSON 파싱 오류 ({json_file}): {e}")
                except Exception as e:
                    print(f"파일 읽기 오류 ({json_file}): {e}")

        return results

    def get_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        처리 결과 요약

        Args:
            results: Vision 결과 리스트

        Returns:
            요약 정보
        """
        folder_counts = {}
        anomaly_counts = {}
        total_detections = 0

        for result in results:
            folder = result['folder']
            vision = result['vision_result']

            # 폴더별 카운트
            folder_counts[folder] = folder_counts.get(folder, 0) + 1

            # 이상 탐지 카운트
            if vision.get('is_anomaly', False):
                anomaly_counts[folder] = anomaly_counts.get(folder, 0) + 1

            # 탐지 객체 수
            total_detections += len(vision.get('detections', []))

        return {
            'total_files': len(results),
            'folder_counts': folder_counts,
            'anomaly_counts': anomaly_counts,
            'total_detections': total_detections
        }

    def cleanup(self, extract_dir: str):
        """임시 폴더 정리"""
        try:
            shutil.rmtree(extract_dir)
        except Exception as e:
            print(f"정리 실패: {e}")


# 싱글톤 인스턴스
zip_processor = ZipProcessor()
