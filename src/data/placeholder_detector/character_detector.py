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
            "colon_field": r"[\u4e00-\u9fa5A-Za-z0-9]{2,8}：\s*$",  # 新增：字段名+冒号+无内容
            # 新增：字段名+冒号+空格
            "colon_field_space": r"[\u4e00-\u9fa5A-Za-z0-9]{2,8}：\s+.+",  # 字段名+冒号+空格+内容，且不是行尾
# todo 
# 1. colon_field和colon_field_space的重复识别
# 2. colon_field_space插入位置不对

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
        # 记录已匹配的区间，避免所有类型的重复识别
        # 结构：[(paragraph_index, run_index, run_start, run_end)]
        matched_ranges = []
        
        # 遍历所有段落和文本块
        for para_idx, para in enumerate(doc.paragraphs):
            para_text = para.text
            
            # 跳过空段落
            if not para_text.strip():
                continue
            
            # 依次遍历所有pattern_type，优先顺序可调整
            for pattern_type, pattern in self.patterns.items():
                
                for match in pattern.finditer(para_text):
                    # 避免重复检测 --------------------------------------------
                    # 计算run_index和run内start/end
                    start_pos = match.start()
                    end_pos = match.end()
                    run_idx = self._find_run_index(para, start_pos, end_pos)
                    # 计算run内的start/end
                    run_start_in_para = 0
                    for i, run in enumerate(para.runs):
                        run_len = len(run.text)
                        if i < run_idx:
                            run_start_in_para += run_len
                    run_inner_start = start_pos - run_start_in_para if run_idx < len(para.runs) else 0
                    run_inner_end = end_pos - run_start_in_para if run_idx < len(para.runs) else 0
                    # 检查是否与已匹配区间重叠
                    overlap = False
                    for (pidx, ridx, rstart, rend) in matched_ranges:
                        if pidx == para_idx and ridx == run_idx:
                            # run内区间有重叠
                            if not (run_inner_end <= rstart or run_inner_start >= rend):
                                overlap = True
                                break
                    if overlap:
                        logger.info(f"跳过与已匹配区间重叠的占位符: {match.group(0)} (段落{para_idx}, run{run_idx}, 区间{run_inner_start}-{run_inner_end})")
                        continue
                    # 避免重复检测 --------------------------------------------
                    
                    
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
                    
                    display_text = self._get_display_text(pattern_type, placeholder_text)
                    # 记录已处理的位置
                    processed_positions.add(position_key)
                    # 新增：记录本次匹配区间，避免后续pattern重复
                    matched_ranges.append((para_idx, run_idx, run_inner_start, run_inner_end))
                    
                    # 确定文本块索引
                    start_pos = match.start()
                    end_pos = match.end()
                    
                    # 正则检测"字段名+冒号+无内容"时，正则的起始点不是要插入的位置（占位符的位置），需要调整
                    if pattern_type == "colon_field":
                        start_pos = start_pos + len(placeholder_text)
                        end_pos = end_pos + len("<neutral_term>")
                        placeholder_text = "<neutral_term>"
                        para_text = para_text + "<neutral_term>"
                    
                    # 正则检测"字段名+冒号+空格"时，正则的起始点不是要插入的位置（占位符的位置），需要调整
                    # 查询冒号的位置
                    if pattern_type == "colon_field_space":
                        colon_pos = para_text.find(":")
                        # 或者中文冒号
                        if colon_pos == -1:
                            colon_pos = para_text.find("：")
                        if colon_pos:
                            start_pos = colon_pos + 1
                            end_pos = end_pos + len("<neutral_term>")
                            placeholder_text = "<neutral_term>"
                            para_text = para_text + "<neutral_term>"
                    
                    run_idx = self._find_run_index(para, start_pos, end_pos)
                    
                    # 提取上下文（用段落内精确位置）
                    context_window = self.context_extractor.window_size if hasattr(self.context_extractor, 'window_size') else 100
                    before_text = para_text[max(0, start_pos-context_window):start_pos]
                    after_text = para_text[end_pos:end_pos+context_window]
                    
                    # 创建占位符信息对象
                    placeholder = PlaceholderInfo(
                        text=display_text,  # 用于显示的占位符文本（如"字段名：<neutral_term>"或"下划线占位符"）
                        raw_text=placeholder_text,  # 原始占位符文本（正则匹配到的原文）
                        paragraph_index=para_idx,  # 占位符所在段落的索引
                        run_index=run_idx,  # 占位符所在文本块（run）的索引
                        before_text=before_text,  # 占位符前的上下文文本
                        after_text=after_text,  # 占位符后的上下文文本
                        placeholder_type=pattern_type,  # 占位符类型（如colon_field、underline等）
                        line_text=para_text,  # 占位符所在的整行文本
                        start=start_pos,  # 占位符在段落中的起始位置
                        end=end_pos,  # 占位符在段落中的结束位置
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
        elif pattern_type == "colon_field":
            return "冒号字段（无内容）"
        elif pattern_type == "colon_field_space":
            return "冒号字段（有内容）"
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