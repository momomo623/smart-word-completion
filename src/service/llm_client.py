"""大模型客户端服务."""

import json
import os
import yaml
from typing import Dict, List, Optional, Union, Any

from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field

from src.config.settings import settings


class LLMClient:
    """大模型客户端.
    
    负责与大模型API的基础通信，不包含特定业务逻辑。
    """
    
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
        
        logger.info(f"大模型客户端已初始化，使用模型: {self.model_name}, API基础URL: {self.api_base_url}")
    
    def chat_completion(
        self, 
        user_message: str, 
        system_message: str = "你是一个有帮助的AI助手。",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> str:
        """发送聊天请求到大模型.
        
        Args:
            user_message: 用户消息
            system_message: 系统消息
            temperature: 温度参数，控制生成的随机性
            max_tokens: 最大生成token数
            timeout: 超时时间(秒)
            
        Returns:
            大模型返回的文本
            
        Raises:
            Exception: 请求失败
        """
        try:
            logger.debug(f"发送聊天请求到LLM: {user_message}...")
            
            # 发送请求到LLM服务
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                timeout=timeout or self.timeout,
            )
            
            # 提取生成的文本
            if not response.choices:
                logger.warning("大模型未返回有效选项")
                return ""
                
            result = response.choices[0].message.content.strip()
            logger.info(f"大模型返回: {result[:200]}...")
            
            return result
        except Exception as e:
            logger.error(f"大模型请求失败: {e}")
            # 向上层抛出异常，让调用者决定如何处理
            raise
    
    def structured_completion(
        self, 
        user_message: str,
        system_message: str = "你是一个专业的数据分析助手，擅长将信息以结构化JSON格式返回。请确保返回有效的JSON数据。",
        response_format: str = "json_object",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """获取结构化响应数据.
        
        Args:
            user_message: 用户消息
            system_message: 系统消息
            response_format: 响应格式，默认为json_object
            temperature: 温度参数，控制生成的随机性
            max_tokens: 最大生成token数
            timeout: 超时时间(秒)
            
        Returns:
            结构化响应数据，通常是字典或列表
            
        Raises:
            Exception: 请求失败或结果解析失败
        """
        try:
            logger.debug(f"发送结构化数据请求到LLM: {user_message}...")
            
            # 使用JSON模式指导模型返回结构化数据
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": response_format},
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or 0.2,  # 降低温度以获得更确定的结构
                timeout=timeout or self.timeout,
            )
            
            # 提取响应内容
            if not response.choices:
                logger.warning("大模型未返回有效选项")
                return {}
                
            content = response.choices[0].message.content.strip()
            logger.info(f"大模型返回: {content[:200]}...")
            
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(f"结构化数据请求失败: {e}")
            raise
    
    # 提取####后的内容
    def extract_content_after_hash(self, content: str) -> str:
        """提取####后的内容.
        
        Args:
            content: 大模型返回的文本内容
        
        Returns:
            提取后的内容
        """
        try:
            # 查找####后的内容
            start = content.find("####")
            if start == -1:
                return ""
            # 提取####后的内容
            return content[start + 4:].strip()
        except Exception as e:
            logger.error(f"提取内容失败: {e}")
            return ""
    def _parse_json_response(self, content: str) -> Any:
        """解析JSON响应.
        
        Args:
            content: 大模型返回的文本内容
            
        Returns:
            解析后的JSON数据
            
        Raises:
            ValueError: 如果无法解析为JSON
        """
        try:
            # 尝试解析整个内容
            result = json.loads(content)
            logger.info(f"成功解析结构化数据，类型: {type(result).__name__}")
            return result
        except json.JSONDecodeError:
            # 如果整个内容不是JSON，尝试提取JSON部分
            logger.warning("无法直接解析为JSON，尝试提取JSON部分")
            try:
                # 查找可能的JSON数组
                start = content.find('[')
                end = content.rfind(']') + 1
                
                if start >= 0 and end > start:
                    json_part = content[start:end]
                    result = json.loads(json_part)
                    logger.info(f"从响应中提取到JSON数组，包含 {len(result)} 个元素")
                    return result
                
                # 尝试提取JSON对象
                start = content.find('{')
                end = content.rfind('}') + 1
                
                if start >= 0 and end > start:
                    json_part = content[start:end]
                    result = json.loads(json_part)
                    logger.info("从响应中提取到JSON对象")
                    return result
                
                # 如果都失败了，抛出异常
                raise ValueError("无法从响应中提取有效JSON")
                
            except Exception as e:
                logger.error(f"提取JSON失败: {e}")
                raise ValueError(f"无法解析响应为JSON: {e}") from e 
    
    
    # yaml_data = self.llm_client.parse_yaml(response)
    # # 业务逻辑判断：检查是否包含neutral_term字段
    # if not yaml_data or "neutral_term" not in yaml_data:
    #     logger.warning("解析结果中缺少neutral_term字段")
    #     neutral_term = "???"
    # else:
    #     neutral_term = yaml_data["neutral_term"]
        
    # logger.info(f"获取到中性词: {neutral_term}")
    def parse_yaml(self, response_text: str) -> Dict[str, Any]:
        """从LLM响应中解析YAML格式数据.
        
        Args:
            response_text: 大模型返回的文本响应
            
        Returns:
            解析后的YAML数据，如果解析失败则返回空字典
            
        Note:
            此方法期望响应中包含```yaml和```标记的YAML代码块
        """
        try:
            # 提取YAML代码块
            yaml_parts = response_text.split("```yaml")
            if len(yaml_parts) < 2:
                # 尝试其他可能的分隔符
                yaml_parts = response_text.split("```yml")
                
            if len(yaml_parts) < 2:
                logger.warning(f"响应中未找到YAML格式: {response_text[:100]}...")
                return {}
                
            yaml_str = yaml_parts[1].split("```")[0].strip()
            result = yaml.safe_load(yaml_str)
            
            if not isinstance(result, dict):
                logger.warning(f"解析的YAML不是字典格式: {result}")
                return {}
                
            logger.debug(f"成功解析YAML: {list(result.keys())}")
            return result
        except Exception as e:
            logger.error(f"解析YAML失败: {e}")
            return {} 