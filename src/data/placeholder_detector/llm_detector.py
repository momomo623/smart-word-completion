"""大模型占位符检测器."""

import json
from typing import List, Any, Dict

from docx import Document
from loguru import logger

from src.data.models import PlaceholderInfo, DocumentSection
from src.data.placeholder_detector.base_detector import PlaceholderDetector
from src.service.llm_client import LLMClient

class LLMDetector(PlaceholderDetector):
    """大模型占位符检测器."""
    
    def __init__(self):
        """初始化大模型占位符检测器."""
        self.llm_client = LLMClient()
    
    def detect(self, doc: Document) -> List[PlaceholderInfo]:
        """检测文档中的占位符并回填中性词。
        适配新版大模型输出YAML格式：
        need_fill: false/true
        fill_list:
          run_index: neutral_term
        """
        from src.config.settings import settings
        results = []
        for i, para in enumerate(doc.paragraphs):
            paragraph_text = para.text
            runs_text = "\n".join([f'  run{j}: "{run.text.strip()}"' for j, run in enumerate(para.runs)])
            prompt = settings.llm.placeholder_detect_prompt.format(
                paragraph_text=paragraph_text,
                paragraph_runs=runs_text
            )
            # 调用大模型
            response = self.llm_client.chat_completion(user_message=prompt, system_message="You are a helpful assistant.")
            # 用llm_client的parse_yaml解析
            yaml_data = self.llm_client.parse_yaml(response)
            if yaml_data.get("need_fill"):
                fill_list = yaml_data.get("fill_list") or {}
                for run_idx, neutral_term in fill_list.items():
                    try:
                        idx = int(run_idx)
                        # 回填中性词
                        doc.paragraphs[i].runs[idx].text = neutral_term
                        # 可选：构造 PlaceholderInfo
                        # results.append(PlaceholderInfo(...))
                    except Exception as e:
                        logger.warning(f"回填失败: 段落{i} run{run_idx} - {e}")
        return results