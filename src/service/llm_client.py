"""大模型客户端服务."""

import json
import os
from typing import Dict, List, Optional, Union, Any

import yaml
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field

from src.config.settings import settings


class LLMRequest(BaseModel):
    """LLM请求模型."""
    
    context: str= Field(default="", description="上下文信息")
    before_text: str = Field(..., description="待填入位置的前文")
    after_text: str = Field(..., description="待填入位置的后文")
    line_text: str = Field(..., description="当前行文本")


class LLMClient:
    """大模型客户端."""
    
    def __init__(self) -> None:
        """初始化大模型客户端."""
        # 从环境变量或设置获取API密钥
        self.api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY", settings.llm.api_key)
        if not self.api_key:
            logger.warning("未设置API密钥，请在环境变量或配置中设置DASHSCOPE_API_KEY或OPENAI_API_KEY")
        
        # 从环境变量或设置获取API基础URL
        self.api_base_url = os.environ.get("DASHSCOPE_API_BASE") or os.environ.get("OPENAI_API_BASE", settings.llm.api_base_url)
        
        # 创建OpenAI客户端
        client_kwargs = {"api_key": self.api_key}
        if self.api_base_url:
            client_kwargs["base_url"] = self.api_base_url
        
        self.client = OpenAI(**client_kwargs)
        
        # 模型设置
        self.model_name = os.environ.get("LLM_MODEL_NAME", settings.llm.model_name)
        self.max_tokens = settings.llm.max_tokens
        self.temperature = settings.llm.temperature
        self.timeout = settings.llm.timeout
        
        # 提示词模板
        self.prompt_template = settings.llm.prompt_template
        
        logger.info(f"大模型客户端已初始化，使用模型: {self.model_name}, API基础URL: {self.api_base_url}")
    
    def get_neutral_term(self, request: LLMRequest) -> str:
        """获取中性词.
        
        Args:
            request: LLM请求模型
            
        Returns:
            生成的中性词
            
        Raises:
            ValueError: 请求失败
        """

        # content_txt = request.before_text + "<neutral_term>" + request.after_text
        # 格式化提示词
        prompt = self.prompt_template.format(
            line_text=request.line_text,
            before_text=request.before_text,
            after_text=request.after_text,
            # content = content_txt,
        )
        
        try:
            print('-'*50)
            logger.debug(f"发送请求到LLM:\n {prompt}")
            
            # 发送请求到LLM服务
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的内容分析助手，擅长根据上下文生成精准的描述词。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=self.timeout,
            )

            # 提取生成的中性词
            resp = response.choices[0].message.content
            # 解析中性词yaml
            neutral_term = self.parse_neutral_term(resp).get("neutral_term", "???")

            logger.debug(f"大模型结果: {resp}")
            logger.info(f"获取到中性词: {neutral_term}")
            
            return neutral_term
        except Exception as e:
            logger.error(f"LLM请求失败: {e}")
            # 如果请求失败，返回"???"
            return "???"

    def   parse_neutral_term(self, resp: str) -> Dict[str, str]:
        """解析中性词yaml.

        Args:
            llm_out: LLM输出内容
            例如：
            ```
            思考1: 思考内容
            思考2： 思考内容
            ####

            ```yaml
            neutral_term: "提取的中性词"
            ```
            ```

        Returns:
            提取的中性词
        """
        yaml_str = resp.split("```yaml")[1].split("```")[0].strip()
        result = yaml.safe_load(yaml_str)

        assert isinstance(result, dict)
        assert "neutral_term" in result

        return result


    def get_neutral_term_batch(self, requests: List[LLMRequest]) -> List[str]:
        """批量获取中性词.

        Args:
            requests: LLM请求模型列表

        Returns:
            生成的中性词列表
        """
        results = []
        for req in requests:
            neutral_term = self.get_neutral_term(req)
            results.append(neutral_term)
        return results

    def get_structured_response(self, prompt: str) -> Any:
        """获取结构化响应数据（例如JSON）.
        
        Args:
            prompt: 提示词
            
        Returns:
            结构化响应数据，通常是字典或列表
            
        Raises:
            ValueError: 请求失败或结果解析失败
        """
        try:
            logger.debug(f"发送结构化数据请求到LLM: {prompt[:100]}...")
            
            # 使用JSON模式指导模型返回结构化数据
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的数据分析助手，擅长将信息以结构化JSON格式返回。请确保返回有效的JSON数据。"},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=self.max_tokens,
                temperature=0.2,  # 降低温度以获得更确定的结构
                timeout=self.timeout,
            )
            
            # 提取响应内容
            content = response.choices[0].message.content.strip()
            # logger.debug(f"LLM返回原始内容: {content[:200]}...")
            
            # 解析JSON
            try:
                # 尝试解析整个内容
                result = json.loads(content)
                logger.info(f"成功解析结构化数据，类型: {type(result).__name__}")
                return result
            except json.JSONDecodeError:
                # 如果整个内容不是JSON，尝试提取JSON部分
                logger.warning("无法直接解析为JSON，尝试提取JSON部分")
                try:
                    # 查找可能的JSON部分
                    start = content.find('[')
                    end = content.rfind(']') + 1
                    
                    if start >= 0 and end > start:
                        json_part = content[start:end]
                        result = json.loads(json_part)
                        logger.info(f"从响应中提取到JSON数组，包含 {len(result)} 个元素")
                        return result
                    
                    # 尝试提取对象
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    
                    if start >= 0 and end > start:
                        json_part = content[start:end]
                        result = json.loads(json_part)
                        logger.info("从响应中提取到JSON对象")
                        return result
                    
                    # 如果都失败了，返回空列表
                    logger.warning("无法从响应中提取有效JSON，返回空列表")
                    return []
                    
                except Exception as e:
                    logger.error(f"提取JSON失败: {e}")
                    return []
                
        except Exception as e:
            logger.error(f"结构化数据请求失败: {e}")
            return [] 