"""PDF 파일 로딩 유틸리티"""

from pathlib import Path
from typing import Dict, List
from pypdf import PdfReader


class PDFLoader:
    """PDF 파일에서 텍스트를 추출하는 클래스"""

    def load(self, file_path: str) -> str:
        """
        PDF 파일에서 텍스트 추출

        Args:
            file_path: PDF 파일 경로

        Returns:
            추출된 텍스트
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        if path.suffix.lower() != '.pdf':
            raise ValueError(f"PDF 파일이 아닙니다: {file_path}")

        reader = PdfReader(str(path))
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        return "\n\n".join(text_parts)

    def load_directory(self, directory_path: str) -> List[Dict[str, str]]:
        """
        디렉토리 내 모든 PDF 파일 로드

        Args:
            directory_path: PDF 파일이 있는 디렉토리 경로

        Returns:
            [{"filename": "xxx.pdf", "content": "..."}, ...]
        """
        path = Path(directory_path)
        if not path.exists():
            raise FileNotFoundError(f"디렉토리를 찾을 수 없습니다: {directory_path}")

        results = []
        for pdf_file in path.glob("*.pdf"):
            try:
                content = self.load(str(pdf_file))
                results.append({
                    "filename": pdf_file.name,
                    "filepath": str(pdf_file),
                    "content": content
                })
            except Exception as e:
                print(f"PDF 로드 실패 ({pdf_file.name}): {e}")

        return results


# 싱글톤 인스턴스
pdf_loader = PDFLoader()
