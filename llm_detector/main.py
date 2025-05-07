import sys
import asyncio
from pathlib import Path
import typer
from loguru import logger
from config.settings import settings
from flow import create_llm_detector_flow

def setup_logger():
    logger.remove()
    logger.add(sys.stderr, level=settings.log.level, format=settings.log.format)
    if settings.log.log_file:
        logger.add(settings.log.log_file, rotation=settings.log.rotation, retention=settings.log.retention)

app = typer.Typer()

@app.command()
def main(
    doc_paths: list[str] = typer.Argument(..., help="输入Word文档路径（可多个）"),
    output_dir: str = typer.Option(None, help="输出目录，默认为config.output_dir")
):
    """批量处理Word文档，识别占位符并生成中性词。"""
    setup_logger()
    # 输出目录
    out_dir = Path(output_dir) if output_dir else settings.output_dir
    out_dir.mkdir(exist_ok=True, parents=True)
    # 生成输出路径
    output_paths = [str(out_dir / (Path(p).stem + "_filled.docx")) for p in doc_paths]
    shared = {
        "doc_paths": doc_paths,
        "output_paths": output_paths
    }
    logger.info(f"开始批量处理文档: {doc_paths}")
    flow = create_llm_detector_flow()
    asyncio.run(async_main(shared))
    logger.info("处理完成！输出文件:")
    for out_path in shared.get("output_paths", []):
        logger.info(out_path)
    # 输出解析日志
    if "parse_logs" in shared:
        for i, logs in enumerate(shared["parse_logs"]):
            logger.info(f"文档{i+1}解析日志：")
            for log in logs:
                logger.info(log)

async def async_main(shared):
    flow = create_llm_detector_flow()
    await flow.run_async(shared)

if __name__ == "__main__":
    app()
