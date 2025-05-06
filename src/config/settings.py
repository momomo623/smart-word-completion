"""项目配置设置."""

from dotenv import load_dotenv
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

# 先加载.env.example（最低优先级），再加载.env（覆盖前者），最后环境变量最高
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / '.env.example', override=False)
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / '.env', override=True)

class LLMConfig(BaseModel):
    """大模型配置."""
    
    model_name: str = Field(default_factory=lambda: os.environ.get("LLM_MODEL_NAME", "qwen-max"))  # 使用的大模型名称
    api_key: Optional[str] = Field(default_factory=lambda: os.environ.get("DASHSCOPE_API_KEY"))  # 大模型API密钥
    api_base_url: Optional[str] = Field(default_factory=lambda: os.environ.get("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"))  # API基础URL
    max_tokens: int = Field(default_factory=lambda: int(os.environ.get("MAX_TOKENS", "100")))  # 生成的最大token数
    temperature: float = Field(default_factory=lambda: float(os.environ.get("TEMPERATURE", "0.7")))  # 生成多样性（温度）
    timeout: int = Field(default_factory=lambda: int(os.environ.get("TIMEOUT", "30")))  # API请求超时时间（秒）

    
    """
    当前行:{line_text}
占位符前序内容:{before_text}  
占位符后序内容:{after_text}  
    """
    # 提示词相关配置
    prompt_template: str = Field(default_factory=lambda: os.environ.get("PROMPT_TEMPLATE", """
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
1. 生成中性描述词，作为<neutral_term>的内容。
2. 前序字段继承原则：优先继承前文的字段名称（如"姓名:____"直接继承"姓名"）。
3. 后序字段继承原则：如果前序字段不明确，可结合后文字段（如“xxxx专业申请”应输出“专业名称”）。
4. 中性描述词总结：如果没有前序和后续字段名称，根据上下文提取最贴切的名词短语。
5. 安全边界：如上下文字段不明确，请返回"???"。
6. 在分析过程中，请逐步思考，但每个步骤的描述尽量简洁（不超过10个字）。
7. 使用分隔符"####"来区分思考过程与最终答案，"####"后直接输出中性词。

思考1:（不超过10个字）
思考2:（不超过10个字）
####
<neutral_term>

"""))  # 大模型提示词模板

# ```yaml
# neutral_term: "提取的中性词，如果不确定则为???"
# ```

class DocumentConfig(BaseModel):
    """文档处理配置."""
    
    placeholder_pattern: str = Field(default_factory=lambda: os.environ.get("PLACEHOLDER_PATTERN", r"{{(.*?)}}"))  # 占位符正则表达式
    context_window: int = Field(default_factory=lambda: int(os.environ.get("CONTEXT_WINDOW", "100")))  # 上下文窗口大小（字符数）
    highlight_color: str = Field(default_factory=lambda: os.environ.get("HIGHLIGHT_COLOR", "FFFF00"))  # 高亮颜色（默认黄色）
    output_format: str = Field(default_factory=lambda: os.environ.get("OUTPUT_FORMAT", "{{{{{}}}}}"))  # 中性词输出格式
    unknown_format: str = Field(default_factory=lambda: os.environ.get("UNKNOWN_FORMAT", "{{{{{}}}}}"))  # 未知中性词输出格式


class LogConfig(BaseModel):
    """日志配置."""
    
    level: str = Field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))  # 日志级别
    # format: str = Field(
    #     os.environ.get("LOG_FORMAT", 
    #     "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"),
    #     description="日志格式",
    # )
    # 精简日志格式
    format: str = Field(default_factory=lambda: os.environ.get("LOG_FORMAT", "<level>{level: <8}</level>| - <level>{message}</level>"))
    log_file: Optional[str] = Field(default_factory=lambda: os.environ.get("LOG_FILE", "word_processor.log"))  # 日志文件名
    rotation: str = Field(default_factory=lambda: os.environ.get("LOG_ROTATION", "10 MB"))  # 日志轮转大小
    retention: str = Field(default_factory=lambda: os.environ.get("LOG_RETENTION", "1 week"))  # 日志保留时间


class Settings(BaseModel):
    """项目全局设置."""
    
    llm: LLMConfig = Field(default_factory=LLMConfig)  # 大模型相关配置
    document: DocumentConfig = Field(default_factory=DocumentConfig)  # 文档处理相关配置
    log: LogConfig = Field(default_factory=LogConfig)  # 日志相关配置
    
    # 项目路径配置
    project_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)  # 项目根目录
    output_dir: Path = Field(default_factory=lambda: Path(os.environ.get("OUTPUT_DIR", str(Path(__file__).parent.parent.parent / "output"))))  # 输出目录


# 单例模式，避免多次实例化
_settings = None
def get_settings():
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

settings = get_settings()

# 确保输出目录存在
settings.output_dir.mkdir(exist_ok=True, parents=True) 