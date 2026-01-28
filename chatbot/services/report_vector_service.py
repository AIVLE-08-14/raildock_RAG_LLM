"""점검 보고서 Vector DB 서비스"""

import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import re

from chatbot.config import chatbot_settings


class ReportVectorService:
    """점검 보고서 저장 및 검색 서비스"""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=chatbot_settings.report_db_path)

        # 임베딩 함수 (Google 기본 임베딩)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        # 컬렉션 생성/로드
        self.collection = self.client.get_or_create_collection(
            name="inspection_reports",
            embedding_function=self.embedding_fn,
            metadata={"description": "철도 시설물 점검 보고서"}
        )

    def add_report(
        self,
        document_content: str,
        folder: str,
        filename: str,
        vision_result: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> str:
        """
        점검 보고서 저장

        Args:
            document_content: 생성된 보고서 전체 내용
            folder: 폴더 타입 (rail, insulator, nest)
            filename: 원본 이미지 파일명
            vision_result: Vision AI 결과
            metadata: 환경 메타데이터

        Returns:
            저장된 보고서 ID
        """
        report_id = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

        # 메타데이터 추출
        env_metadata = metadata.get('metadata', {}) if metadata else {}

        # Vision 결과에서 주요 정보 추출
        detections = vision_result.get('detections', [])
        defect_types = list(set(d.get('cls_name', '') for d in detections))
        risk_grades = self._extract_risk_grade(document_content)

        # 저장할 메타데이터
        doc_metadata = {
            "report_id": report_id,
            "folder": folder,
            "filename": filename,
            "created_at": datetime.now().isoformat(),
            "defect_types": ", ".join(defect_types),
            "risk_grade": risk_grades,
            "region": env_metadata.get('region_name', ''),
            "datetime": env_metadata.get('datetime', ''),
            "detection_count": len(detections)
        }

        # ChromaDB에 저장
        self.collection.add(
            ids=[report_id],
            documents=[document_content],
            metadatas=[doc_metadata]
        )

        return report_id

    def _extract_risk_grade(self, document: str) -> str:
        """문서에서 위험도 등급 추출"""
        # "위험도 등급: X2" 패턴 찾기
        match = re.search(r'위험도\s*등급[:\s]*([EOXS][12]?)', document)
        if match:
            return match.group(1)
        return "Unknown"

    def search(
        self,
        query: str,
        top_k: int = None,
        folder_filter: str = None
    ) -> List[Dict[str, Any]]:
        """
        보고서 검색

        Args:
            query: 검색 질의
            top_k: 반환할 결과 수
            folder_filter: 폴더 필터 (rail, insulator, nest)

        Returns:
            검색된 보고서 목록
        """
        top_k = top_k or chatbot_settings.report_top_k

        # 필터 조건
        where_filter = None
        if folder_filter:
            where_filter = {"folder": folder_filter}

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter
        )

        # 결과 포맷팅
        reports = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                reports.append({
                    "report_id": doc_id,
                    "content": results['documents'][0][i] if results['documents'] else "",
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None
                })

        return reports

    def get_all_reports(self, limit: int = 100) -> List[Dict[str, Any]]:
        """저장된 모든 보고서 목록 조회"""
        results = self.collection.get(
            limit=limit,
            include=["metadatas"]
        )

        reports = []
        if results['ids']:
            for i, doc_id in enumerate(results['ids']):
                meta = results['metadatas'][i] if results['metadatas'] else {}
                reports.append({
                    "report_id": doc_id,
                    "folder": meta.get('folder', ''),
                    "filename": meta.get('filename', ''),
                    "risk_grade": meta.get('risk_grade', ''),
                    "created_at": meta.get('created_at', ''),
                    "defect_types": meta.get('defect_types', '')
                })

        return reports

    def get_stats(self) -> Dict[str, Any]:
        """보고서 DB 통계"""
        count = self.collection.count()

        # 폴더별 통계
        folder_stats = {"rail": 0, "insulator": 0, "nest": 0}
        if count > 0:
            all_reports = self.get_all_reports(limit=1000)
            for report in all_reports:
                folder = report.get('folder', '')
                if folder in folder_stats:
                    folder_stats[folder] += 1

        return {
            "total_reports": count,
            "by_folder": folder_stats
        }

    def clear(self) -> Dict[str, Any]:
        """보고서 DB 초기화"""
        count = self.collection.count()

        # 컬렉션 삭제 후 재생성
        self.client.delete_collection("inspection_reports")
        self.collection = self.client.get_or_create_collection(
            name="inspection_reports",
            embedding_function=self.embedding_fn,
            metadata={"description": "철도 시설물 점검 보고서"}
        )

        return {
            "message": "보고서 DB 초기화 완료",
            "deleted_count": count
        }


# 싱글톤 인스턴스
report_vector_service = ReportVectorService()
