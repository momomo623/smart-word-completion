"""文档填充器."""

import docx
from docx import Document
from loguru import logger

from src.data.models import PlaceholderInfo


class DocumentFiller:
    """文档填充器."""
    
    def __init__(self):
        """初始化文档填充器."""
    
    def fill_neutral_term(
        self, doc: Document, placeholder: PlaceholderInfo, neutral_term: str
    ) -> None:
        """用中性词填充占位符.
        
        Args:
            doc: Document对象
            placeholder: 占位符信息
            neutral_term: 中性词
        """
        try:
            # 根据占位符类型选择不同的填充方法
            if placeholder.placeholder_type == "table":
                self._fill_table_placeholder(doc, placeholder, neutral_term)
            else:
                self._fill_text_placeholder(doc, placeholder, neutral_term)
            
            # 更新占位符的中性词
            placeholder.neutral_term = neutral_term
            
        except Exception as e:
            logger.error(f"填充中性词失败: {e}")
            raise ValueError(f"填充中性词失败: {e}")
    
    def _fill_text_placeholder(
        self, doc: Document, placeholder: PlaceholderInfo, neutral_term: str
    ) -> None:
        """填充文本类型占位符（段落中）.
        
        Args:
            doc: Document对象
            placeholder: 占位符信息
            neutral_term: 中性词
        """
        # 获取段落
        para = doc.paragraphs[placeholder.paragraph_index]
        
        # 确保文本块索引有效
        if placeholder.run_index >= len(para.runs):
            logger.warning(
                f"文本块索引超出范围: {placeholder.run_index} >= {len(para.runs)}, "
                f"将使用第一个文本块"
            )
            run_idx = 0
        else:
            run_idx = placeholder.run_index
        
        run = para.runs[run_idx]
        
        # 根据占位符类型确定要替换的文本
        if placeholder.placeholder_type == "underline":
            # 查找下划线
            import re
            underline_match = re.search(r"_{5,}", run.text)
            if underline_match:
                original_text = underline_match.group(0)
            else:
                original_text = run.text
        elif placeholder.placeholder_type == "underline_space":
            # 对于下划线空格，我们直接替换整个文本块
            # 因为空格较难定位，替换整个文本块更安全
            original_text = run.text
        elif placeholder.placeholder_type == "llm_detected":
            # 对于LLM检测的占位符，直接使用前后文定位
            original_text = run.text
        else:
            original_text = run.text
        
        # 准备替换文本
        if neutral_term == "???":
            # 未知中性词，使用黄色高亮
            replacement = ('{{' + neutral_term + '}}')
            highlighted = True
        else:
            # 正常中性词
            replacement = ('{{' + neutral_term + '}}')
            highlighted = False
        
        # 替换文本
        new_text = run.text.replace(original_text, replacement)
        
        # 应用替换
        run.text = new_text
        
        # 如果需要高亮
        if highlighted:
            # 设置黄色高亮背景
            run.font.highlight_color = docx.enum.text.WD_COLOR_INDEX.YELLOW
        
        logger.info(f"已将 '{original_text}' 替换为 '{replacement}'")
    
    def _fill_table_placeholder(
        self, doc: Document, placeholder: PlaceholderInfo, neutral_term: str
    ) -> None:
        """填充表格中的占位符.
        
        对于表格占位符，不使用大模型生成中性词，直接使用表头作为占位符内容。
        为了区分同一列的不同行，在占位符中添加行号作为索引，例如 {{访视时间1}}、{{访视时间2}}。
        
        Args:
            doc: Document对象
            placeholder: 占位符信息
            neutral_term: 中性词（对于表格，这个参数会被忽略）
        """
        # 解析表格索引（使用负值表示）
        table_idx = abs(placeholder.paragraph_index) - 1
        if table_idx >= len(doc.tables):
            logger.error(f"表格索引超出范围: {table_idx} >= {len(doc.tables)}")
            return
        
        table = doc.tables[table_idx]
        
        # 从run_index解析行列信息
        row_idx = placeholder.run_index // 100
        cell_idx = placeholder.run_index % 100
        
        if row_idx >= len(table.rows) or cell_idx >= len(table.rows[0].cells):
            logger.error(f"表格单元格索引超出范围: [{row_idx}, {cell_idx}]")
            return
        
        # 获取单元格
        cell = table.rows[row_idx].cells[cell_idx]
        
        # 对于表格占位符，直接使用占位符的text（即表头）作为内容
        header_text = placeholder.text
        
        # 准备替换文本 - 使用双花括号包裹表头，并添加行号索引
        # 行索引从1开始，更符合用户习惯
        replacement = "{{" + header_text + str(row_idx) + "}}"
        
        # 设置单元格文本
        cell.text = replacement
        
        # 记录使用的表头作为中性词，包含行号
        placeholder.neutral_term = header_text + str(row_idx)
        
        logger.info(f"已在表格[{table_idx}]的单元格[{row_idx}, {cell_idx}]填入表头占位符: '{replacement}'")