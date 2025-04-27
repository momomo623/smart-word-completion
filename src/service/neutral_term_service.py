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
        # 构建内容文本
        # content_txt = request.before_text + "<neutral_term>" + request.after_text
        
        # 格式化提示词
        try:
            prompt = self.prompt_template.format(
                line_text=request.line_text,
                before_text=request.before_text,
                after_text=request.after_text,
                # content=content_txt,
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
            yaml_data = self.llm_client.parse_yaml(response)
            
            # 业务逻辑判断：检查是否包含neutral_term字段
            if not yaml_data or "neutral_term" not in yaml_data:
                logger.warning("解析结果中缺少neutral_term字段")
                neutral_term = "???"
            else:
                neutral_term = yaml_data["neutral_term"]
                
            logger.info(f"获取到中性词: {neutral_term}")
            return neutral_term
        except Exception as e:
            logger.error(f"解析中性词失败: {e}")
            return "???"
    
    def get_neutral_term_batch(self, requests: List[NeutralTermRequest]) -> List[str]:
        """批量获取中性词.
        
        Args:
            requests: 中性词请求模型列表
            
        Returns:
            中性词列表
        """
        results = []
        for req in requests:
            neutral_term = self.get_neutral_term(req)
            results.append(neutral_term)
        return results 