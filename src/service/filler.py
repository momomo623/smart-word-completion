"""文档填充服务."""

import time
from pathlib import Path
from typing import Dict, List, Union

from docx import Document
from loguru import logger

from src.data.document_io import DocumentIO
from src.data.document_filler import DocumentFiller
from src.data.models import PlaceholderInfo
from src.data.report_generator import ReportGenerator


class DocumentFillerService:
    """文档填充服务."""
    
    def __init__(self):
        """初始化文档填充服务."""
        self.doc_filler = DocumentFiller()
        self.report_generator = ReportGenerator()
        self.doc_io = DocumentIO()
    
    def save_document(
        self, doc: Document, placeholders: List[PlaceholderInfo], output_path: Union[str, Path]
    ) -> None:
        """填充文档并保存.
        
        Args:
            doc: 文档对象
            placeholders: 占位符列表
            output_path: 输出文件路径
        """
        # 保存文档
        self.doc_io.save_document(doc, output_path)
        
        # 生成报告
        report_path = Path(output_path).with_suffix(".md")
        self.report_generator.generate_report(placeholders, report_path)
        
        logger.info(f"文档填充完成，已保存至: {output_path}")
        logger.info(f"报告已保存至: {report_path}")
    
