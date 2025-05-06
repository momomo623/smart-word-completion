from src.app.processor import DocumentProcessor
from loguru import logger

# 测试日志级别
logger.debug("这是DEBUG级别的日志消息")
logger.info("这是INFO级别的日志消息")
logger.warning("这是WARNING级别的日志消息")

processor = DocumentProcessor()
# result = processor.process("test.docx", "output.docx")
result = processor.process(
    "input/承诺书模板.docx",
    "output/承诺书模板.docx",
)

print(result.report)
