"""数据模型定义."""

from typing import Optional


class DocumentSection:
    """文档区域类，用于大模型分析."""
    
    def __init__(self, text: str, paragraph_index: int, section_type: str = "paragraph"):
        """初始化文档区域.
        
        Args:
            text: 区域文本
            paragraph_index: 起始段落索引
            section_type: 区域类型 (paragraph, table, etc.)
        """
        self.text = text
        self.paragraph_index = paragraph_index
        self.section_type = section_type


class PlaceholderInfo:
    """占位符信息类."""
    
    def __init__(
        self,
        text: str,
        paragraph_index: int,
        run_index: int,
        before_text: str = "",
        after_text: str = "",
        placeholder_type: str = "auto",
        line_text: str = "",
        raw_text: str = "",
        start: int = -1,
        end: int = -1,
        table_index: Optional[int] = None,
        row_index: Optional[int] = None,
        col_index: Optional[int] = None,
    ) -> None:
        """初始化占位符信息.
        
        Args:
            text: 占位符文本
            paragraph_index: 段落索引
            run_index: 文本块索引
            before_text: 占位符前文本
            after_text: 占位符后文本
            placeholder_type: 占位符类型（underline, table, llm_detected, auto）
            line_text: 占位符所在行的完整文本
            raw_text: 原始占位符字符串
            start: 占位符在段落中的起始位置
            end: 占位符在段落中的结束位置
            table_index: 表格索引（可选）
            row_index: 行索引（可选）
            col_index: 列索引（可选）
        """
        self.text = text
        self.paragraph_index = paragraph_index
        self.run_index = run_index
        self.before_text = before_text
        self.after_text = after_text
        self.placeholder_type = placeholder_type
        self.neutral_term: Optional[str] = None
        self.line_text = line_text
        self.raw_text = raw_text
        self.start = start
        self.end = end
        self.table_index = table_index
        self.row_index = row_index
        self.col_index = col_index
    
    def __repr__(self) -> str:
        """返回占位符信息的字符串表示.
        
        Returns:
            占位符信息的字符串表示
        """
        return (
            f"PlaceholderInfo(text='{self.text}', "
            f"paragraph_index={self.paragraph_index}, "
            f"run_index={self.run_index}, "
            f"type='{self.placeholder_type}', "
            f"neutral_term='{self.neutral_term or 'None'}', "
            f"line_text='{self.line_text}', "
            f"raw_text='{self.raw_text}', "
            f"table_index={self.table_index}, row_index={self.row_index}, col_index={self.col_index}"
            f")"
        )