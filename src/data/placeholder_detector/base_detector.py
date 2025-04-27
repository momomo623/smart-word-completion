"""占位符检测器基类."""

from abc import ABC, abstractmethod
from typing import List

from docx import Document

from src.data.models import PlaceholderInfo


class PlaceholderDetector(ABC):
    """占位符检测器基类."""
    
    @abstractmethod
    def detect(self, doc: Document) -> List[PlaceholderInfo]:
        """检测文档中的占位符.
        
        Args:
            doc: Document对象
            
        Returns:
            占位符信息列表
        """
        pass