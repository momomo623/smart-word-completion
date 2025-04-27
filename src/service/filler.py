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
    
    def fill_document(
        self, doc: Document, placeholders: List[PlaceholderInfo], output_path: Union[str, Path]
    ) -> None:
        """填充文档并保存.
        
        Args:
            doc: 文档对象
            placeholders: 占位符列表
            output_path: 输出文件路径
        """
        if not placeholders:
            logger.info("没有找到占位符，直接保存文档")
            self.doc_io.save_document(doc, output_path)
            return
        
        # 处理每个占位符
        for placeholder in placeholders:
            try:
                # 对于表格占位符，直接使用表头作为内容
                if placeholder.placeholder_type == "table":
                    neutral_term = placeholder.text  # 使用表头作为内容
                    logger.info(f"表格占位符 '{placeholder.text}' 直接使用表头作为填充内容")
                else:
                    # 其他类型占位符使用大模型生成中性词
                    # neutral_term = self._get_neutral_term(placeholder)
                    continue

                # 填充中性词
                self.doc_filler.fill_neutral_term(doc, placeholder, neutral_term)
            except Exception as e:
                logger.error(f"处理占位符失败: {e}")
                placeholder.neutral_term = "???"
        
        # 保存文档
        self.doc_io.save_document(doc, output_path)
        
        # 生成报告
        report_path = Path(output_path).with_suffix(".md")
        self.report_generator.generate_report(placeholders, report_path)
        
        logger.info(f"文档填充完成，已保存至: {output_path}")
        logger.info(f"报告已保存至: {report_path}")
    
    def _get_neutral_term(self, placeholder: PlaceholderInfo) -> str:
        """获取中性词.
        
        Args:
            placeholder: 占位符信息
            
        Returns:
            中性词
        """
        if not placeholder.before_text and not placeholder.after_text:
            logger.warning(f"占位符 '{placeholder.text}' 没有上下文信息，无法获取中性词")
            return "???"
        
        # 准备请求
        request = LLMRequest(
            # context=f"文档中的占位符 '{placeholder.text}'",
            before_text=placeholder.before_text,
            after_text=placeholder.after_text,
            line_text=placeholder.line_text,
        )
        
        # 请求大模型生成中性词
        try:
            neutral_term = self.llm_client.get_neutral_term(request)
            if not neutral_term or neutral_term.strip() == "":
                logger.warning(f"占位符 '{placeholder.text}' 获取中性词失败，返回结果为空")
                return "???"
            
            logger.info(f"占位符 '{placeholder.text}' 获取中性词: {neutral_term}")
            return neutral_term
        except Exception as e:
            logger.error(f"获取中性词失败: {e}")
            return "???"
    
    def batch_fill_document(
        self, doc: Document, placeholders: List[PlaceholderInfo], output_path: Union[str, Path]
    ) -> None:
        """批量填充文档并保存.
        
        Args:
            doc: 文档对象
            placeholders: 占位符列表
            output_path: 输出文件路径
        """
        if not placeholders:
            logger.info("没有找到占位符，直接保存文档")
            self.doc_io.save_document(doc, output_path)
            return
        
        # 将占位符分为表格占位符和其他占位符
        table_placeholders = []
        other_placeholders = []
        
        for placeholder in placeholders:
            if placeholder.placeholder_type == "table":
                table_placeholders.append(placeholder)
            else:
                other_placeholders.append(placeholder)
        
        # 处理表格占位符 - 直接使用表头
        for placeholder in table_placeholders:
            try:
                neutral_term = placeholder.text  # 使用表头作为内容
                self.doc_filler.fill_neutral_term(doc, placeholder, neutral_term)
                logger.info(f"表格占位符 '{placeholder.text}' 直接使用表头作为填充内容")
            except Exception as e:
                logger.error(f"处理表格占位符失败: {e}")
                placeholder.neutral_term = "???"
        
        # 处理其他占位符 - 批量请求大模型
        if other_placeholders:
            self._batch_fill_placeholders(doc, other_placeholders)
        
        # 保存文档
        self.doc_io.save_document(doc, output_path)
        
        # 生成报告
        report_path = Path(output_path).with_suffix(".md")
        self.report_generator.generate_report(placeholders, report_path)
        
        logger.info(f"文档填充完成，已保存至: {output_path}")
        logger.info(f"报告已保存至: {report_path}")
    
    def _batch_fill_placeholders(self, doc: Document, placeholders: List[PlaceholderInfo]) -> None:
        """批量填充占位符.
        
        Args:
            doc: 文档对象
            placeholders: 占位符列表
        """
        # 准备批量请求
        requests = []
        valid_placeholders = []
        
        for placeholder in placeholders:
            if not placeholder.before_text and not placeholder.after_text:
                logger.warning(f"占位符 '{placeholder.text}' 没有上下文信息，无法获取中性词")
                placeholder.neutral_term = "???"
                continue
            
            request = LLMRequest(
                # context=f"文档中的占位符 '{placeholder.text}'",
                before_text=placeholder.before_text,
                after_text=placeholder.after_text,
                line_text=placeholder.line_text,
            )
            requests.append(request)
            valid_placeholders.append(placeholder)
        
        if not valid_placeholders:
            return
        
        # 批量请求大模型生成中性词
        try:
            neutral_terms = self.llm_client.get_neutral_term_batch(requests)
            
            # 处理结果
            for i, (placeholder, term) in enumerate(zip(valid_placeholders, neutral_terms)):
                if not term or term.strip() == "":
                    logger.warning(f"占位符 '{placeholder.text}' 获取中性词失败，返回结果为空")
                    placeholder.neutral_term = "???"
                else:
                    self.doc_filler.fill_neutral_term(doc, placeholder, term)
                    logger.info(f"占位符 '{placeholder.text}' 获取中性词: {term}")
        except Exception as e:
            logger.error(f"批量获取中性词失败: {e}")
            for placeholder in valid_placeholders:
                placeholder.neutral_term = "???" 