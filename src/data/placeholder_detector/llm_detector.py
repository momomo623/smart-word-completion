"""大模型占位符检测器."""

import json
from typing import List, Any, Dict

from docx import Document
from loguru import logger

from src.data.models import PlaceholderInfo, DocumentSection
from src.data.placeholder_detector.base_detector import PlaceholderDetector


class LLMDetector(PlaceholderDetector):
    """大模型占位符检测器."""
    
    def __init__(self):
        """初始化大模型占位符检测器."""
        self.llm_client = None  # 将在需要时初始化
    
    def detect(self, doc: Document) -> List[PlaceholderInfo]:
        """使用大模型检测文档中的占位符.
        
        Args:
            doc: Document对象
            
        Returns:
            占位符信息列表
        """
        if self.llm_client is None:
            from src.service.llm_client import LLMClient
            self.llm_client = LLMClient()
        
        placeholders = []
        # 文档分段处理
        sections = self._split_document_into_sections(doc)
        
        for section in sections:
            # 准备向大模型提问
            prompt = f"""
分析以下文档片段，找出所有可能需要填写的占位符位置。
占位符可能是空白、下划线或其他明显需要填写的位置。

文档片段：
{section.text}

请返回JSON格式的数组，每个占位符包含以下字段：
[
  {{"位置描述": "在第几段第几句", "前文": "占位符前的内容最多50个字符）", "后文": "占位符后的内容最多50个字符）"}}
]

如果没有找到占位符，请返回空数组 []。
"""
            
            # 调用大模型
            try:
                # 使用新的 structured_completion 方法
                system_message = "你是一个专业的文档分析助手，能够识别文档中需要填写的占位符位置。"
                try:
                    response_data = self.llm_client.structured_completion(
                        user_message=prompt,
                        system_message=system_message
                    )
                    # 直接使用返回的结构化数据
                    response = response_data
                except Exception as e:
                    logger.error(f"LLM结构化响应请求失败: {e}")
                    response = []
                    
                logger.debug(f"LLM返回占位符检测结果: {response}")
                
                # 处理响应，转换为PlaceholderInfo对象
                if response:
                    # 尝试处理不同格式的响应
                    placeholder_list = []
                    if isinstance(response, list):
                        placeholder_list = response  # 已经是列表
                    else:
                        logger.error(f"LLM返回的响应格式不正确: {response}")
                        placeholder_list = []
                    
                    # 处理每个占位符
                    for placeholder_data in placeholder_list:
                        # 尝试提取前文和后文，考虑不同的键名
                        before_text = ""
                        after_text = ""
                        
                        # 前文可能的键名
                        for key in ["前文", "before_text", "beforeText", "context_before", "前置文本"]:
                            if key in placeholder_data:
                                before_text = placeholder_data[key]
                                break
                        
                        # 后文可能的键名
                        for key in ["后文", "after_text", "afterText", "context_after", "后置文本"]:
                            if key in placeholder_data:
                                after_text = placeholder_data[key]
                                break
                        
                        # 如果前文后文都未找到，尝试提取位置描述
                        position_desc = ""
                        for key in ["位置描述", "position", "location", "description"]:
                            if key in placeholder_data:
                                position_desc = placeholder_data[key]
                                break
                        
                        # 处理段落和表格的不同索引方式
                        paragraph_index = section.paragraph_index
                        run_index = 0  # 默认为0
                        
                        # 创建占位符信息
                        if before_text or after_text or position_desc:
                            placeholder = PlaceholderInfo(
                                text=f"LLM检测占位符: {position_desc}" if position_desc else "LLM检测占位符",
                                paragraph_index=paragraph_index,
                                run_index=run_index,
                                before_text=before_text,
                                after_text=after_text,
                                placeholder_type="llm_detected",
                                line_text=section.text,
                            )
                            placeholders.append(placeholder)
                            logger.debug(f"LLM检测到占位符: {placeholder}")
            except Exception as e:
                logger.error(f"处理LLM响应时出错: {e}")
                continue
        
        logger.info(f"LLMDetector 共检测到 {len(placeholders)} 个占位符")
        return placeholders
    
    def _split_document_into_sections(self, doc: Document, max_section_length: int = 1000) -> List[DocumentSection]:
        """将文档分割为较小的区域进行分析.
        
        Args:
            doc: Document对象
            max_section_length: 每个区域的最大字符数
            
        Returns:
            文档区域列表
        """
        sections = []
        
        # 处理段落
        current_section = ""
        section_start_idx = 0
        
        for idx, para in enumerate(doc.paragraphs):
            para_text = para.text.strip()
            if not para_text:
                continue
            
            # 如果添加当前段落会超过最大长度，创建新区域
            if len(current_section) + len(para_text) > max_section_length and current_section:
                sections.append(DocumentSection(current_section, section_start_idx, "paragraph"))
                current_section = para_text
                section_start_idx = idx
            else:
                current_section += "\n" + para_text if current_section else para_text
                if not current_section:
                    section_start_idx = idx
        
        # 添加最后一个段落区域
        if current_section:
            sections.append(DocumentSection(current_section, section_start_idx, "paragraph"))
        
        # 处理表格
        for table_idx, table in enumerate(doc.tables):
            table_text = ""
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells)
                table_text += row_text + "\n"
            
            if table_text.strip():
                # 使用负索引标记表格区域
                sections.append(DocumentSection(table_text, -(table_idx + 1), "table"))
        
        return sections