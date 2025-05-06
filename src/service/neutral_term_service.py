"""中性词处理服务."""

from typing import Dict, List, Optional
from loguru import logger
from pydantic import BaseModel, Field

from src.config.settings import settings


class NeutralTermRequest(BaseModel):
    """中性词请求模型."""
    
    line_text: str = Field(..., description="当前行文本")
    before_text: str = Field(..., description="待填入位置的前文")
    after_text: str = Field(..., description="待填入位置的后文")
    context: str = Field(default="", description="上下文信息")
    raw_text: str = Field(default="", description="待填入位置的原始文本")
    start: int = Field(default=-1, description="占位符在段落中的起始位置")
    end: int = Field(default=-1, description="占位符在段落中的结束位置")
    placeholder_type: str = Field(default="", description="占位符类型")
    


class NeutralTermService:
    """中性词处理服务."""
    
    def __init__(self, llm_client=None):
        """初始化中性词处理服务.
        
        Args:
            llm_client: 大模型客户端，如果为None则自动创建
        """
        if llm_client is None:
            from src.service.llm_client import LLMClient
            self.llm_client = LLMClient()
        else:
            self.llm_client = llm_client
        
        # 提示词模板
        self.prompt_template = settings.llm.prompt_template
    
    def get_neutral_term(self, request: NeutralTermRequest) -> str:
        """获取中性词.
        
        Args:
            request: 中性词请求模型
            
        Returns:
            生成的中性词
        """
        # 用<neutral_term>精准替换line_text中的占位符
        masked_line_text = request.line_text
        if hasattr(request, 'placeholder_type') and request.placeholder_type == 'colon_field' and request.end != -1:
            # 在冒号后插入<neutral_term>
            masked_line_text = masked_line_text[:request.end] + '<neutral_term>' + masked_line_text[request.end:]
        elif request.start != -1 and request.end != -1 and request.start < request.end:
            masked_line_text = (
                masked_line_text[:request.start] + "<neutral_term>" + masked_line_text[request.end:]
            )
        elif hasattr(request, 'raw_text') and request.raw_text:
            masked_line_text = masked_line_text.replace(request.raw_text, "<neutral_term>", 1)
        
        # 格式化提示词
        try:
            prompt = self.prompt_template.format(
                line_text=masked_line_text,
                before_text=request.before_text,
                after_text=request.after_text,
            )
        except KeyError as ke:
            logger.error(f"提示词模板格式化错误: 缺少参数 {ke}，请检查prompt_template配置")
            return "???"
        
        # 调用大模型获取回复
        response = self.llm_client.chat_completion(
            system_message="你是一个专业的内容分析助手，擅长根据上下文生成精准的描述词。",
            user_message=prompt
        )
        
        if not response:
            logger.warning("大模型未返回有效响应")
            return "???"
            
        # 解析中性词
        try:
            # 使用LLMClient解析YAML
            neutral_term = self.llm_client.extract_content_after_hash(response)
            logger.info(f"获取到中性词: {neutral_term}")
            return neutral_term
        except Exception as e:
            logger.error(f"解析中性词失败: {e}")
            return "???"
    
