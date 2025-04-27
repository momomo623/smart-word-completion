"""项目配置设置."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """大模型配置."""
    
    model_name: str = Field(
        os.environ.get("LLM_MODEL_NAME", "qwen-max"), 
        description="使用的大模型名称"
    )
    api_key: Optional[str] = Field(
        os.environ.get("DASHSCOPE_API_KEY", 'sk-5b758fbcb3ca4c9ab039d8a68e9f0db6'), 
        description="API密钥"
    )
    api_base_url: Optional[str] = Field(
        os.environ.get(
            "DASHSCOPE_API_BASE", 
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ), 
        description="API基础URL"
    )
    max_tokens: int = Field(
        int(os.environ.get("MAX_TOKENS", "100")), 
        description="生成的最大token数"
    )
    temperature: float = Field(
        float(os.environ.get("TEMPERATURE", "0.7")), 
        description="生成的多样性程度"
    )
    timeout: int = Field(
        int(os.environ.get("TIMEOUT", "30")), 
        description="API请求超时时间(秒)"
    )
    
    # 提示词相关配置
    prompt_template: str = Field(
        os.environ.get("PROMPT_TEMPLATE", 
        """
你是一个专业的内容分析助手，擅长根据上下文生成精准的描述词。
**当前行**  
<current_line>
{line_text}  
</current_line>
**前序内容**  
<before_text>
{before_text}  
</before_text>
**后序内容**  
<after_text>
{after_text}  
</after_text>

**任务要求**  
1.字段继承原则：优先继承前文的字段名称（如"姓名:____"直接继承"姓名"）
2.短语压缩：对复合字段（如"入院日期"）保持完整名词短语
3.格式过滤：忽略换行符、空格等非语义符号
4.中性描述词总结：如果没有前序字段名称，根据上下文提取
5.安全边界：如上下文字段不明确，请返回"???"。
6.在分析过程中，请逐步思考，但每个步骤的描述尽量简洁（不超过10个字）。
7.使用分隔符"####"来区分思考过程与最终答案。

思考1:（不超过10个字）
思考2:（不超过10个字）
...
使用分隔符“####”来区分思考过程与最终答案。

```yaml
neutral_term: "提取的中性词，如果不确定则为???"
```


        """.strip()),
        description="提示词模板",
    )


class DocumentConfig(BaseModel):
    """文档处理配置."""
    
    placeholder_pattern: str = Field(
        os.environ.get("PLACEHOLDER_PATTERN", r"{{(.*?)}}"), 
        description="占位符正则表达式"
    )
    context_window: int = Field(
        int(os.environ.get("CONTEXT_WINDOW", "100")), 
        description="提取上下文的窗口大小(字符数)"
    )
    highlight_color: str = Field(
        os.environ.get("HIGHLIGHT_COLOR", "FFFF00"), 
        description="高亮颜色(黄色)"
    )
    output_format: str = Field(
        os.environ.get("OUTPUT_FORMAT", "{{{{{}}}}}"), 
        description="中性词输出格式"
    )
    unknown_format: str = Field(
        os.environ.get("UNKNOWN_FORMAT", "{{{{{}}}}}"), 
        description="未知中性词输出格式"
    )


class LogConfig(BaseModel):
    """日志配置."""
    
    level: str = Field(
        os.environ.get("LOG_LEVEL", "INFO"), 
        description="日志级别"
    )
    format: str = Field(
        os.environ.get("LOG_FORMAT", 
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"),
        description="日志格式",
    )
    log_file: Optional[str] = Field(
        os.environ.get("LOG_FILE", "word_processor.log"), 
        description="日志文件"
    )
    rotation: str = Field(
        os.environ.get("LOG_ROTATION", "10 MB"), 
        description="日志轮转大小"
    )
    retention: str = Field(
        os.environ.get("LOG_RETENTION", "1 week"), 
        description="日志保留时间"
    )


class Settings(BaseModel):
    """项目全局设置."""
    
    llm: LLMConfig = Field(default_factory=LLMConfig, description="大模型配置")
    document: DocumentConfig = Field(default_factory=DocumentConfig, description="文档处理配置")
    log: LogConfig = Field(default_factory=LogConfig, description="日志配置")
    
    # 项目路径配置
    project_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent, description="项目根目录")
    output_dir: Path = Field(
        default_factory=lambda: Path(os.environ.get("OUTPUT_DIR", str(Path(__file__).parent.parent.parent / "output"))), 
        description="输出目录"
    )


# 创建全局设置实例
settings = Settings()

# 确保输出目录存在
settings.output_dir.mkdir(exist_ok=True, parents=True) 