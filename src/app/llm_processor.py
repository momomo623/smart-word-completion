"""基于大模型的Word占位符检测与回填应用."""

from pathlib import Path
from typing import Optional
import typer
from docx import Document
from loguru import logger

from src.data.placeholder_detector.llm_detector import LLMDetector

app = typer.Typer()

def generate_report(doc: Document, changed_runs: list, output_path: str) -> str:
    """生成检测和回填结果报告."""
    report_lines = [
        f"# LLM占位符检测与回填报告",
        f"输出文件: {output_path}",
        f"共检测到 {len(changed_runs)} 处需要回填的内容\n"
    ]
    for item in changed_runs:
        para_idx, run_idx, old_text, new_text = item
        report_lines.append(f"- 段落{para_idx} run{run_idx}: '{old_text}' → '{new_text}'")
    return "\n".join(report_lines)

@app.command()
def process_document(
    input_path: str = typer.Argument(..., help="输入Word文档路径"),
    output_path: Optional[str] = typer.Option(None, help="输出Word文档路径，默认为'input_llmfilled.docx'"),
    report_path: Optional[str] = typer.Option(None, help="检测报告路径，默认为'input_llmfilled_report.md'"),
):
    """使用大模型检测并回填Word文档中的占位符."""
    input_file = Path(input_path)
    if not output_path:
        output_path = str(input_file.parent / f"{input_file.stem}_llmfilled{input_file.suffix}")
    if not report_path:
        report_path = str(input_file.parent / f"{input_file.stem}_llmfilled_report.md")

    logger.info(f"读取文档: {input_path}")
    doc = Document(input_path)
    detector = LLMDetector()
    changed_runs = []
    for i, para in enumerate(doc.paragraphs):
        old_runs = [run.text for run in para.runs]
        # 检测并回填（detect会直接修改doc）
        detector.detect(doc)
        new_runs = [run.text for run in para.runs]
        for j, (old, new) in enumerate(zip(old_runs, new_runs)):
            if old != new:
                changed_runs.append((i, j, old, new))
    doc.save(output_path)
    logger.info(f"已保存回填后的文档: {output_path}")
    report = generate_report(doc, changed_runs, output_path)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"已生成检测报告: {report_path}")
    typer.echo(report)

if __name__ == "__main__":
    app()
