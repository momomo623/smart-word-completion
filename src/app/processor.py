"""Word文档处理应用."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

import typer
from loguru import logger

from src.data.document_handler import PlaceholderInfo
from src.service.filler import DocumentFillerService
from src.service.parser import DocumentParser


@dataclass
class ProcessResult:
    """处理结果."""
    
    output_path: str
    report_path: str
    placeholder_count: int
    success: bool
    error_message: Optional[str] = None
    
    @property
    def report(self) -> str:
        """生成结果报告.
        
        Returns:
            结果报告字符串
        """
        if not self.success:
            return f"处理失败: {self.error_message}"
        
        return (
            f"处理成功!\n"
            f"- 总共处理了 {self.placeholder_count} 个占位符\n"
            f"- 输出文件: {self.output_path}\n"
            f"- 报告文件: {self.report_path}"
        )


class DocumentProcessor:
    """Word文档处理器."""
    
    def __init__(self) -> None:
        """初始化Word文档处理器."""
        self.parser = DocumentParser()
        self.filler = DocumentFillerService()
        logger.info("文档处理器已初始化")
    
    def process(self, input_path: str, output_path: str) -> ProcessResult:
        """处理Word文档.
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            
        Returns:
            处理结果
        """
        try:
            logger.info(f"开始处理文档: {input_path}")
            
            # 解析文档
            doc, placeholders = self.parser.parse_document(input_path)
            logger.info(f"文档解析完成，找到 {len(placeholders)} 个占位符")
            
            if not placeholders:
                logger.warning("未找到任何占位符，将直接保存文档")
            else:
                # 处理占位符，同时进行填充
                placeholders = self.parser.process_placeholders(doc, placeholders)
                logger.info("占位符处理完成")
            
            # 填充文档
            self.filler.fill_document(doc, placeholders, output_path)
            
            # 准备结果
            report_path = Path(output_path).with_suffix(".md")
            result = ProcessResult(
                output_path=output_path,
                report_path=str(report_path),
                placeholder_count=len(placeholders),
                success=True,
            )
            
            logger.info("文档处理完成")
            return result
            
        except Exception as e:
            logger.error(f"处理文档时发生错误: {e}")
            return ProcessResult(
                output_path=output_path,
                report_path="",
                placeholder_count=0,
                success=False,
                error_message=str(e),
            )


# 命令行接口
app = typer.Typer()


@app.command()
def process_document(
    input_path: str = typer.Argument(..., help="输入Word文档路径"),
    output_path: str = typer.Option(None, help="输出Word文档路径，默认为'input_processed.docx'"),
) -> None:
    """处理Word文档，识别占位符并生成中性词."""
    # 如果未指定输出路径，则使用默认路径
    if not output_path:
        input_file = Path(input_path)
        output_path = str(input_file.parent / f"{input_file.stem}_processed{input_file.suffix}")
    
    processor = DocumentProcessor()
    result = processor.process(input_path, output_path)
    
    if result.success:
        typer.echo(typer.style(result.report, fg=typer.colors.GREEN))
    else:
        typer.echo(typer.style(result.report, fg=typer.colors.RED))
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app() 