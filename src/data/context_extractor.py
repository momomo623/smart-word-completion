"""上下文提取器."""

from typing import Tuple


class ContextExtractor:
    """上下文提取器."""
    
    def __init__(self, context_window: int = 100):
        """初始化上下文提取器.
        
        Args:
            context_window: 上下文窗口大小
        """
        self.context_window = context_window
    
    def extract_context(self, full_text: str, placeholder: str) -> Tuple[str, str]:
        """提取占位符的上下文.
        
        Args:
            full_text: 文档全文
            placeholder: 占位符文本
            
        Returns:
            占位符前文本和后文本的元组
        """
        placeholder_pos = full_text.find(placeholder)
        if placeholder_pos == -1:
            return "", ""
        
        # 提取前文
        start_pos = max(0, placeholder_pos - self.context_window)
        before_text = full_text[start_pos:placeholder_pos].strip()
        
        # 提取后文
        end_pos = min(len(full_text), placeholder_pos + len(placeholder) + self.context_window)
        after_text = full_text[placeholder_pos + len(placeholder):end_pos].strip()
        
        return before_text, after_text