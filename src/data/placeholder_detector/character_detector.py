"""字符占位符检测器."""

import re
from typing import Dict, List, Pattern, Tuple, Union, Set

from docx import Document
from loguru import logger

from src.data.models import PlaceholderInfo
from src.data.placeholder_detector.base_detector import PlaceholderDetector
from src.data.context_extractor import ContextExtractor


class CharacterPlaceholderDetector(PlaceholderDetector):
    """字符占位符检测器.
    
    可检测多种类型的字符占位符，包括但不限于：
    - 下划线占位符（如 _____）
    - 重复星号占位符（如 *****）
    - 方括号占位符（如 [____]、[填写内容]）
    - 花括号占位符（如 {____}、{请填写}）
    - 重复符号占位符（如 ---、###、===）
    """
    
    def __init__(
        self, 
        context_window: int = 100,
        patterns: Dict[str, str] = None,
        min_repetition: int = 3  # 调整为默认5个字符，减少误检
    ):
        """初始化字符占位符检测器.
        
        Args:
            context_window: 上下文窗口大小
            patterns: 自定义占位符模式字典，格式为 {占位符类型: 正则表达式}
            min_repetition: 重复字符的最小重复次数
        """
        self.context_extractor = ContextExtractor(context_window)
        self.min_repetition = min_repetition
        
        # 默认占位符模式
        default_patterns = {
            "underline": rf"_{{{min_repetition},}}",  # 如 ___、_____
            # "asterisk": rf"\*{{{min_repetition},}}",  # 如 ***、*****
            # "dash": rf"-{{{min_repetition},}}",  # 如 ---、-----
            # "equal": rf"={{{min_repetition},}}",  # 如 ===、=====
            # "hash": rf"#{{{min_repetition},}}",  # 如 ###、#####
            # "bracket_empty": r"\[\s*_*\s*\]",  # 如 []、[___]、[ ]
            # "bracket_text": r"\[([^]]+)\]",  # 如 [填写]、[请输入]
            # "brace_empty": r"\{\s*_*\s*\}",  # 如 {}、{___}、{ }
            # "brace_text": r"\{([^}]+)\}",  # 如 {填写}、{请输入}
            "xxx_placeholder": r"x{2,10}",  # 识别连续出现的x，如 xxx、xxxxxx
            # "bracket_xxx": r"[（(]\s*x{2,10}[^）)]*[）)]",  # 识别括号中的xxx，如 (xxx) 或 （xxx公司）
        }
        
        # 合并自定义模式与默认模式
        if patterns:
            default_patterns.update(patterns)
        
        # 编译正则表达式
        self.patterns = {}
        for pattern_type, pattern in default_patterns.items():
            self.patterns[pattern_type] = re.compile(pattern)
    
    def detect(self, doc: Document) -> List[PlaceholderInfo]:
        """检测文档中的字符占位符.
        
        Args:
            doc: Document对象
            
        Returns:
            占位符信息列表
        """
        placeholders = []
        full_text = "\n".join(para.text for para in doc.paragraphs)
        
        # 使用集合记录已处理的占位符位置，避免重复
        processed_positions = set()
        
        # 遍历所有段落和文本块
        for para_idx, para in enumerate(doc.paragraphs):
            para_text = para.text
            
            # 跳过空段落
            if not para_text.strip():
                continue
            
            # 在段落中查找各种占位符模式
            for pattern_type, pattern in self.patterns.items():
                for match in pattern.finditer(para_text):
                    placeholder_text = match.group(0)  # 匹配的占位符文本
                    
                    # 创建唯一标识，避免重复检测同一位置
                    position_key = (para_idx, match.start(), match.end(), pattern_type)
                    
                    # 如果已经处理过该位置，则跳过
                    if position_key in processed_positions:
                        continue
                    
                    # 对于方括号和花括号占位符，检查内容是否有效
                    if pattern_type in ["bracket_text", "brace_text"]:
                        content = placeholder_text[1:-1].strip()
                        # 跳过过短或明显不是占位符的内容
                        if len(content) < 2 or content in ["的", "和", "与", "或"]:
                            continue
                    
                    # 记录已处理的位置
                    processed_positions.add(position_key)
                    
                    # 确定文本块索引
                    run_idx = self._find_run_index(para, match.start(), match.end())
                    
                    # 提取上下文
                    before_text, after_text = self.context_extractor.extract_context(
                        full_text, placeholder_text
                    )
                    
                    # 创建占位符显示文本
                    display_text = self._get_display_text(pattern_type, placeholder_text)
                    
                    # 创建占位符信息对象
                    placeholder = PlaceholderInfo(
                        text=display_text,
                        raw_text=placeholder_text,
                        paragraph_index=para_idx,
                        run_index=run_idx,
                        before_text=before_text,
                        after_text=after_text,
                        placeholder_type=pattern_type,
                        line_text=para_text,
                    )
                    
                    placeholders.append(placeholder)
                    # logger.debug(f"找到{pattern_type}占位符: 段落={para_idx}, 位置={match.start()}-{match.end()}, 文本='{placeholder_text}'")
        
        logger.info(f"CharacterPlaceholderDetector 共检测到 {len(placeholders)} 个占位符")
        return placeholders
    
    def _get_display_text(self, pattern_type: str, placeholder_text: str) -> str:
        """根据占位符类型和文本生成显示文本.
        
        Args:
            pattern_type: 占位符类型
            placeholder_text: 原始占位符文本
            
        Returns:
            用于显示的占位符文本
        """
        if pattern_type == "bracket_text":
            # 提取方括号中的内容
            content = placeholder_text[1:-1].strip()
            return f"方括号占位符: {content}" if content else "空方括号占位符"
        elif pattern_type == "brace_text":
            # 提取花括号中的内容
            content = placeholder_text[1:-1].strip()
            return f"花括号占位符: {content}" if content else "空花括号占位符"
        elif pattern_type == "underline":
            return "下划线占位符"
        elif pattern_type == "xxx_placeholder":
            return "xxx占位符"
        elif pattern_type == "bracket_xxx":
            return "括号xxx占位符"
        elif pattern_type == "asterisk":
            return "星号占位符"
        elif pattern_type == "dash":
            return "短横线占位符"
        elif pattern_type == "equal":
            return "等号占位符"
        elif pattern_type == "hash":
            return "井号占位符"
        elif pattern_type == "bracket_empty":
            return "空方括号占位符"
        elif pattern_type == "brace_empty":
            return "空花括号占位符"
        else:
            return f"{pattern_type}占位符"
    
    def add_pattern(self, pattern_type: str, pattern: Union[str, Pattern]) -> None:
        """添加新的占位符模式.
        
        Args:
            pattern_type: 占位符类型
            pattern: 正则表达式或已编译的Pattern对象
        """
        if isinstance(pattern, str):
            self.patterns[pattern_type] = re.compile(pattern)
        else:
            self.patterns[pattern_type] = pattern
        logger.info(f"添加了新的占位符模式: {pattern_type}")
    
    @staticmethod
    def _find_run_index(paragraph, start_pos: int, end_pos: int) -> int:
        """查找占位符所在的文本块索引.
        
        Args:
            paragraph: 段落对象
            start_pos: 占位符开始位置
            end_pos: 占位符结束位置
            
        Returns:
            文本块索引，如果未找到则返回0
        """
        pos = 0
        for i, run in enumerate(paragraph.runs):
            pos_next = pos + len(run.text)
            if pos <= start_pos < pos_next:
                return i
            pos = pos_next
        return 0