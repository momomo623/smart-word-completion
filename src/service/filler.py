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
from src.service.llm_client import LLMClient, LLMRequest


class DocumentFillerService:
    """文档填充服务."""
    
    def __init__(self):
        """初始化文档填充服务."""
        self.llm_client = LLMClient()
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
        # if not placeholders:
        #     logger.info("没有找到占位符，直接保存文档")
        #     self.doc_io.save_document(doc, output_path)
        #     return
        #
        # # 处理每个占位符
        # for placeholder in placeholders:
        #     try:
        #         # 对于表格占位符，直接使用表头作为内容
        #         if placeholder.placeholder_type == "table":
        #             neutral_term = placeholder.text  # 使用表头作为内容
        #             logger.debug(f"表格占位符 '{placeholder.text}' 直接使用表头作为填充内容")
        #         else:
        #             # 其他类型占位符使用大模型生成中性词
        #             # neutral_term = self._get_neutral_term(placeholder)
        #             continue
        #
        #         # 填充中性词
        #         self.doc_filler.fill_neutral_term(doc, placeholder, neutral_term)
        #     except Exception as e:
        #         logger.error(f"处理占位符失败: {e}")
        #         placeholder.neutral_term = "???"
        
        # 保存文档
        self.doc_io.save_document(doc, output_path)
        
        # 生成报告
        report_path = Path(output_path).with_suffix(".md")
        self.report_generator.generate_report(placeholders, report_path)
        
        logger.info(f"文档填充完成，已保存至: {output_path}")
        logger.info(f"报告已保存至: {report_path}")
    
