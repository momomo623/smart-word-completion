"""文档读写操作."""

from pathlib import Path
from typing import Union

import docx
from docx import Document
from loguru import logger


class DocumentIO:
    """文档读写操作类."""
    
    @staticmethod
    def load_document(file_path: Union[str, Path]) -> Document:
        """加载Word文档.
        
        Args:
            file_path: 文档路径
            
        Returns:
            加载的Document对象
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不正确
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if file_path.suffix.lower() not in ['.docx']:
            raise ValueError(f"不支持的文件类型: {file_path.suffix}")
        
        try:
            doc = Document(file_path)
            logger.info(f"已加载文档: {file_path}")
            return doc
        except Exception as e:
            logger.error(f"加载文档失败: {e}")
            raise ValueError(f"加载文档失败: {e}")
    
    @staticmethod
    def save_document(doc: Document, output_path: Union[str, Path]) -> None:
        """保存Word文档.
        
        Args:
            doc: Document对象
            output_path: 输出文件路径
            
        Raises:
            ValueError: 保存失败
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            doc.save(output_path)
            logger.info(f"已保存文档: {output_path}")
        except Exception as e:
            logger.error(f"保存文档失败: {e}")
            raise ValueError(f"保存文档失败: {e}")
    
    @staticmethod
    def extract_document_text(doc: Document) -> str:
        """提取文档中的所有文本.
        
        Args:
            doc: Document对象
            
        Returns:
            文档中的所有文本
        """
        text = []
        for para in doc.paragraphs:
            # 输出段落的结构信息
            # print(f"段落文本: {para.text}")
            # print(f"段落样式: {para.style.name}")
            # print(f"段落对齐方式: {para.alignment}")
            # print(f"段落缩进: {para.paragraph_format.left_indent}")
            # print(f"段落间距: {para.paragraph_format.space_after}")
            # print(f"段落中的文本块数量: {len(para.runs)}")
            # print("-" * 50)
            text.append(para.text)
        return "\n".join(text)