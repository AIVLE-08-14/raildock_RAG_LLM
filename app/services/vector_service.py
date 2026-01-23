"""ChromaDB 벡터 저장소 서비스"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
from pathlib import Path

from app.config import settings
from app.utils.chunker import RegulationChunker


class VectorService:
    """ChromaDB 기반 RAG 서비스"""

    def __init__(self):
        persist_path = Path(settings.chroma_persist_path)
        persist_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(persist_path),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # 규정 문서 컬렉션
        self.collection = self.client.get_or_create_collection(
            name="regulations",
            metadata={"description": "철도 규정 문서"}
        )

        self.chunker = RegulationChunker(
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap
        )

    def add_regulation_document(self, document_text: str, source: str = "unknown") -> int:
        """
        규정 문서 추가 (청킹 → 임베딩 → 저장)

        Args:
            document_text: 전체 규정 문서 텍스트
            source: 문서 출처

        Returns:
            추가된 청크 수
        """
        # 청킹
        chunks = self.chunker.chunk(document_text)

        if not chunks:
            return 0

        # ChromaDB에 추가
        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            chunk_id = f"{chunk['regulation_id']}_chunk_{chunk['chunk_index']}"

            # 메타데이터 추출
            metadata = self.chunker.extract_metadata(chunk['content'])
            metadata['regulation_id'] = chunk['regulation_id']
            metadata['chunk_index'] = chunk['chunk_index']
            metadata['total_chunks'] = chunk['total_chunks']
            metadata['source'] = source
            metadata['doc_type'] = 'scenario'

            ids.append(chunk_id)
            documents.append(chunk['content'])
            metadatas.append(metadata)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        return len(chunks)

    def add_whole_document(self, document_text: str, source: str = "unknown", doc_id: str = None) -> int:
        """
        전체 문서를 청킹 없이 통째로 저장 (maintenance_document용)

        Args:
            document_text: 전체 문서 텍스트
            source: 문서 출처 (파일명)
            doc_id: 문서 ID (없으면 파일명에서 생성)

        Returns:
            추가된 문서 수 (1)
        """
        if not document_text.strip():
            return 0

        # 문서 ID 생성
        if not doc_id:
            # 파일명에서 ID 생성 (확장자 제거)
            doc_id = source.replace('.pdf', '').replace('.hwp', '').replace(' ', '_')

        chunk_id = f"WHOLE_{doc_id}"

        metadata = {
            'regulation_id': doc_id,
            'source': source,
            'doc_type': 'maintenance',
            'chunk_index': 0,
            'total_chunks': 1,
            'is_whole_document': True,
            'content_length': len(document_text)
        }

        self.collection.add(
            ids=[chunk_id],
            documents=[document_text],
            metadatas=[metadata]
        )

        return 1

    def search(
        self,
        query: str,
        top_k: int = None,
        filter_regulation_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        쿼리로 관련 규정 검색

        Args:
            query: 검색 쿼리 (결함 정보 등)
            top_k: 반환할 청크 수
            filter_regulation_id: 특정 규정 ID로 필터링

        Returns:
            관련 청크 리스트
        """
        if top_k is None:
            top_k = settings.rag_top_k

        where_filter = None
        if filter_regulation_id:
            where_filter = {"regulation_id": filter_regulation_id}

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # 결과 정리
        chunks = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                chunks.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else None,
                    'regulation_id': results['metadatas'][0][i].get('regulation_id') if results['metadatas'] else None
                })

        return chunks

    def get_all_regulation_ids(self) -> List[str]:
        """저장된 모든 규정 ID 목록 조회"""
        results = self.collection.get(include=["metadatas"])

        regulation_ids = set()
        for metadata in results.get('metadatas', []):
            if metadata and 'regulation_id' in metadata:
                regulation_ids.add(metadata['regulation_id'])

        return sorted(list(regulation_ids))

    def delete_regulation(self, regulation_id: str):
        """특정 규정 삭제"""
        # 해당 규정의 모든 청크 ID 조회
        results = self.collection.get(
            where={"regulation_id": regulation_id},
            include=["metadatas"]
        )

        if results['ids']:
            self.collection.delete(ids=results['ids'])

    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계"""
        count = self.collection.count()
        regulation_ids = self.get_all_regulation_ids()

        # doc_type별 카운트
        results = self.collection.get(include=["metadatas"])
        scenario_count = 0
        maintenance_count = 0
        for meta in results.get('metadatas', []):
            if meta and meta.get('doc_type') == 'maintenance':
                maintenance_count += 1
            else:
                scenario_count += 1

        return {
            'total_chunks': count,
            'total_regulations': len(regulation_ids),
            'scenario_chunks': scenario_count,
            'maintenance_docs': maintenance_count,
            'regulation_ids': regulation_ids
        }

    def clear_collection(self):
        """컬렉션 초기화 (모든 데이터 삭제)"""
        # 기존 컬렉션 삭제 후 재생성
        self.client.delete_collection("regulations")
        self.collection = self.client.get_or_create_collection(
            name="regulations",
            metadata={"description": "철도 규정 문서"}
        )
        return {"message": "컬렉션 초기화 완료"}


# 싱글톤 인스턴스
vector_service = VectorService()
