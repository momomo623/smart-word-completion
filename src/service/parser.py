"""文档解析服务."""

from typing import Dict, List, Optional, Tuple, Union

from docx import Document
from loguru import logger

from src.data.document_handler import DocumentHandler, PlaceholderInfo
from src.service.llm_client import LLMClient
from src.service.neutral_term_service import NeutralTermService, NeutralTermRequest


class DocumentParser:
    """文档解析器."""
    
    def __init__(self) -> None:
        """初始化文档解析器."""
        self.document_handler = DocumentHandler()
        self.llm_client = LLMClient()
        self.neutral_term_service = NeutralTermService(self.llm_client)
    
    def parse_document(self, doc_path: str) -> Tuple[Document, List[PlaceholderInfo]]:
        """解析文档.
        
        Args:
            doc_path: 文档路径
            
        Returns:
            文档对象和占位符信息列表的元组
        """
        # 加载文档
        doc = self.document_handler.load_document(doc_path)

        # 输出doc的文本
        doc_text = self.document_handler.extract_document_text(doc)
        logger.debug(f"文档文本长度: {len(doc_text)} 字符")
        
        # 查找占位符
        placeholders = self.document_handler.find_placeholders(doc)
        
        return doc, placeholders
    
    def process_placeholders(
        self, doc: Document, placeholders: List[PlaceholderInfo]
    ) -> List[PlaceholderInfo]:
        """处理占位符.
        
        Args:
            doc: 文档对象
            placeholders: 占位符信息列表
            
        Returns:
            更新后的占位符信息列表
        """        
        for placeholder in placeholders:
            if placeholder.placeholder_type == 'table':
                # 对于表格占位符，直接使用表头作为内容
                neutral_term = placeholder.text
                self.document_handler.filler.fill_neutral_term(doc, placeholder, neutral_term)
                continue
                
            try:
                # 对于其他类型的占位符，使用中性词服务生成中性词
                request = NeutralTermRequest(
                    line_text=placeholder.line_text,
                    before_text=placeholder.before_text,
                    after_text=placeholder.after_text,
                )
                
                # 获取中性词
                neutral_term = self.neutral_term_service.get_neutral_term(request)
                
                # 填充中性词
                self.document_handler.filler.fill_neutral_term(doc, placeholder, neutral_term)
            except Exception as e:
                logger.error(f"处理占位符失败: {e}")
                # 处理失败时，填入默认值
                self.document_handler.filler.fill_neutral_term(doc, placeholder, "???")

        return placeholders 