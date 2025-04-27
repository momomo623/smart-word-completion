"""报告生成器."""

from pathlib import Path
from typing import List, Union

from loguru import logger

from src.data.models import PlaceholderInfo


class ReportGenerator:
    """报告生成器."""
    
    def generate_report(self, placeholders: List[PlaceholderInfo], output_path: Union[str, Path]) -> None:
        """生成处理报告.
        
        Args:
            placeholders: 占位符信息列表
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("# Word文档中性词处理报告\n\n")
                f.write(f"总共处理 {len(placeholders)} 个占位符\n\n")
                
                for i, ph in enumerate(placeholders, 1):
                    f.write(f"## 占位符 {i}: {ph.text}\n\n")
                    
                    # 根据占位符类型生成不同的报告内容
                    if ph.placeholder_type == "table":
                        table_idx = abs(ph.paragraph_index) - 1
                        row_idx = ph.run_index // 100
                        cell_idx = ph.run_index % 100
                        f.write(f"- 类型: 表格占位符\n")
                        f.write(f"- 表格索引: {table_idx}\n")
                        f.write(f"- 单元格位置: 第{row_idx}行 第{cell_idx}列\n")
                    else:
                        f.write(f"- 类型: {ph.placeholder_type}\n")
                        f.write(f"- 段落索引: {ph.paragraph_index}\n")
                        f.write(f"- 文本块索引: {ph.run_index}\n")
                    
                    f.write(f"- 生成的中性词: {ph.neutral_term or '未生成'}\n\n")
                    
                    f.write("### 上下文\n\n")
                    f.write(f"前文: {ph.before_text}\n\n")
                    f.write(f"后文: {ph.after_text}\n\n")
                    f.write("---\n\n")
            
            logger.info(f"已生成处理报告: {output_path}")
        except Exception as e:
            logger.error(f"生成处理报告失败: {e}")
            raise ValueError(f"生成处理报告失败: {e}")