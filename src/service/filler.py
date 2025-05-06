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
        # 下面的在之前已经处理了，可以暂时放这里，未来需要处理其他类型占位符时，可以参考
        # 针对colon_field类型，演示如何在冒号后插入内容
        # for ph in placeholders:
        #     if hasattr(ph, 'placeholder_type') and ph.placeholder_type == 'colon_field':
        #         para = doc.paragraphs[ph.paragraph_index]
        #         # 在冒号后插入内容（此处以<neutral_term>为例，实际可替换为目标内容）
        #         new_text = para.text[:ph.end] + '<neutral_term>' + para.text[ph.end:]
        #         # 直接修改段落文本（注意：docx的text属性只读，需重建runs或用更细致的API，简化演示如下）
        #         for run in para.runs:
        #             run.text = ''
        #         para.add_run(new_text)
        # 保存文档
        self.doc_io.save_document(doc, output_path)
        
        # 生成报告
        report_path = Path(output_path).with_suffix(".md")
        self.report_generator.generate_report(placeholders, report_path)
        
        logger.info(f"文档填充完成，已保存至: {output_path}")
        logger.info(f"报告已保存至: {report_path}")
    
