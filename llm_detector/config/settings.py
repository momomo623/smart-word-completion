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


    placeholder_detect_prompt: str = Field(default_factory=lambda: os.environ.get("PLACEHOLDER_DETECT_PROMPT", """
你是一名专业的内容分析助手。你的任务是审查下方Word文档的段落结构，判断每个run是否包含占位符或需要人工填写的内容（如姓名、日期、专业等字段）。

- 如果所有run都不需要填写，将need_fill设为false，fill_list设为空字典。
- 如果有run需要填写，将need_fill设为true，并在fill_list中列出所有run序号及对应run的回填后内容（即将占位符替换为中性词后的完整文本，格式如：{{中性词}}）。
- 前序字段继承原则：优先继承前文的字段名称（如"姓名:____"直接继承"姓名"）。
- 后序字段继承原则：如果前序字段不明确，可结合后文字段（如"xxxx专业申请"应输出"专业名称"）。
- 中性描述词总结：如果没有前序和后续字段名称，根据上下文提取最贴切的名词短语。
- 尤其关注冒号，如果有冒号大概率需要填写中性词。
- 不要修改原始文本，只能替换占位符或者添加中性词
- 安全边界：如上下文字段不明确，请返回"???"。
- 在分析过程中，请逐步思考，但每个步骤的描述尽量简洁（不超过10个字）。
- 使用分隔符"####"来区分思考过程与最终答案，"####"后直接输出YAML。

请先输出该段落的完整文本，然后输出每个run的信息。

如果需要，请提取应填写的内容，并按照如下YAML格式返回：

思考1:（不超过10个字）
思考2:（不超过10个字）
####
```yaml
need_fill: false/true
fill_list:
  run_index: run_filled_text
```

## 输入示例
完整段落：
由 (xxxxxx公司) 申在我院xxx专业申请开展的一项名为"（xxxxxx临床试验） "的临床研究。
每个run：
  run0: "由 ("
  run1: "xxxxxx"
  run2: "公司) 申在我院xxx专业申请开展的一项名为"（"
  run3: "xxxxxx"
  run4: "临床试验） "的临床研究。"

## 输出示例
思考1:（不超过10个字）
思考2:（不超过10个字）
####
```yaml
need_fill: true
fill_list:
  1: "{{公司名称}}"
  2: "公司) 申在我院{{专业名称}}专业申请开展的一项名为"（"
  3: "{{临床试验名称}}"
  
## 错误示例
输入:run0: '联系电话/传真/手机：'
错误输出:0: "{{联系电话}}/{{传真}}/{{手机}}："
正确输出: "联系电话/传真/手机：{{联系电话/传真/手机}}"
```

## 输出示例（无需填写）
思考1:（不超过10个字）
思考2:（不超过10个字）
####
```yaml
need_fill: false
fill_list: {{}}
```

## 现在，请分析下方段落：
完整段落：
{paragraph_text}
每个run：
{paragraph_runs}
"""))  

class LogConfig(BaseModel):
    """日志配置."""
    
    level: str = Field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))  # 日志级别
  
    # 精简日志格式
    format: str = Field(default_factory=lambda: os.environ.get("LOG_FORMAT", "<level>{level: <8}</level>| - <level>{message}</level>"))
    log_file: Optional[str] = Field(default_factory=lambda: os.environ.get("LOG_FILE", "word_processor.log"))  # 日志文件名
    rotation: str = Field(default_factory=lambda: os.environ.get("LOG_ROTATION", "10 MB"))  # 日志轮转大小
    retention: str = Field(default_factory=lambda: os.environ.get("LOG_RETENTION", "1 week"))  # 日志保留时间


class Settings(BaseModel):
    """项目全局设置."""
    
    llm: LLMConfig = Field(default_factory=LLMConfig)  # 大模型相关配置
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