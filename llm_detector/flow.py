import os
import re
from typing import List, Dict, Any
from docx import Document
from pocketflow import AsyncFlow, Node, AsyncParallelBatchNode
from utils.llm_client import LLMClient
from utils.document_io import read_docx, save_docx

# 注意：本流程包含异步节点，必须用await flow.run_async(shared)调用。

class BatchReadDocNode(Node):
    def prep(self, shared):
        return shared["doc_paths"]
    def exec(self, doc_paths: List[str]):
        docs = [read_docx(path) for path in doc_paths]
        return docs
    def post(self, shared, prep_res, exec_res):
        shared["docs"] = exec_res
        return "default"

class DispatchNode(Node):
    """
    类型分发节点，将所有段落、单列表格单元格、多列表格行分发为任务列表。
    """
    def prep(self, shared):
        return shared["docs"]
    def exec(self, docs):
        tasks_para = []
        tasks_table_row = []
        for doc_idx, doc in enumerate(docs):
            # 段落
            for para_idx, para in enumerate(doc["paragraphs"]):
                if para.text.strip() == "":
                    continue
                tasks_para.append({
                    "doc_idx": doc_idx,
                    "para_idx": para_idx,
                    "para": para,
                    "type": "paragraph"
                })
            # 表格
            for table_idx, table in enumerate(doc["tables"]):
                n_cols = len(table.columns)
                if n_cols == 1:
                    # 单列表格，逐格处理
                    for row_idx, row in enumerate(table.rows):
                        cell = row.cells[0]
                        for cell_para_idx, para in enumerate(cell.paragraphs):
                            if para.text.strip() == "":
                                continue
                            tasks_para.append({
                                "doc_idx": doc_idx,
                                "table_id": table_idx,
                                "row_id": row_idx,
                                "col_id": 0,
                                "para_id": cell_para_idx,
                                "para": para,
                                "type": "table_cell"
                            })
                else:
                    # 多列表格，按行整体处理，去重cell_text，只保留第一次出现
                    for row_idx, row in enumerate(table.rows):
                        row_cells = []
                        seen = set()
                        for col_idx, cell in enumerate(row.cells):
                            cell_text = "\n".join([p.text for p in cell.paragraphs if p.text.strip()])
                            # 跳过全空cell
                            if cell_text.strip() == "":
                                continue
                            if cell_text in seen:
                                continue  # 跳过重复cell_text
                            seen.add(cell_text)
                            row_cells.append({
                                "col_id": col_idx,
                                "cell_text": cell_text,
                                "cell": cell
                            })
                        # 跳过全空行
                        if not row_cells:
                            continue
                        tasks_table_row.append({
                            "doc_idx": doc_idx,
                            "table_id": table_idx,
                            "row_id": row_idx,
                            "row_cells": row_cells,
                            "type": "table_row"
                        })
        return {"para_tasks": tasks_para, "table_row_tasks": tasks_table_row}
    def post(self, shared, prep_res, exec_res):
        shared["para_tasks"] = exec_res["para_tasks"]
        shared["table_row_tasks"] = exec_res["table_row_tasks"]
        # 按任务类型分发action
        actions = []
        # if exec_res["para_tasks"]:
        #     actions.append("para")
        # if exec_res["table_row_tasks"]:
        #     actions.append("table_row")
        # 如果都有，优先para，PocketFlow会依次分支
        # return actions[0] if actions else None
        return "default"

class ParaLLMFillNode(AsyncParallelBatchNode):
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
    @staticmethod
    def extract_neutral_term(text):
        match = re.search(r"\{\{([^{}]+)\}\}", text)
        if match:
            return match.group(1)
        match = re.search(r"\{([^{}]+)\}", text)
        if match:
            return match.group(1)
        return ""
    async def prep_async(self, shared):
        return shared.get("para_tasks", [])
    async def exec_async(self, item):
        para = item["para"]
        paragraph_text = para.text
        runs_text = "\n".join([f'  run{j}: "{run.text.strip()}"' for j, run in enumerate(para.runs)])
        prompt = f"""
你是一名专业的内容分析助手。你的任务是审查下方Word文档的段落结构，判断每个run是否包含占位符或需要人工填写的内容（如姓名、日期、专业等字段）。

**任务要求**
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

**输出格式**
思考1:（不超过10个字）
思考2:（不超过10个字）
####
```yaml
need_fill: false/true
fill_list:
  run_index: run_filled_text
```

**输入示例**
完整段落：
由 (xxxxxx公司) 申在我院xxx专业申请开展的一项名为"（xxxxxx临床试验） "的临床研究。
每个run：
  run0: "由 ("
  run1: "xxxxxx"
  run2: "公司) 申在我院xxx专业申请开展的一项名为"（"
  run3: "xxxxxx"
  run4: "临床试验） "的临床研究。"

**输出示例**
思考1:（不超过10个字）
思考2:（不超过10个字）
####
```yaml
need_fill: true
fill_list:
  1: "{{公司名称}}"
  2: "公司) 申在我院{{专业名称}}专业申请开展的一项名为"（"
  3: "{{临床试验名称}}"
  
**错误示例**
原始run0: '联系电话/传真/手机：'
错误输出: "{{联系电话}}/{{传真}}/{{手机}}："
正确输出: "联系电话/传真/手机：{{联系电话/传真/手机}}"
```

## 现在，请分析下方段落：
完整段落：
{paragraph_text}
每个run：
{runs_text}
"""
        response = self.llm_client.chat_completion(user_message=prompt)
        yaml_data = self.llm_client.parse_yaml(response)
        logs = []
        if yaml_data.get("need_fill"):
            fill_list = yaml_data.get("fill_list") or {}
            for run_idx, run_filled_text in fill_list.items():
                try:
                    idx = int(run_idx)
                    para.runs[idx].text = run_filled_text
                    neutral = self.extract_neutral_term(run_filled_text)
                    log = {
                        "type": item["type"],
                        "doc_idx": item["doc_idx"],
                        "para_idx": item.get("para_idx"),
                        "table_id": item.get("table_id"),
                        "row_id": item.get("row_id"),
                        "col_id": item.get("col_id"),
                        "cell_para_id": item.get("para_id"),
                        "run_id": idx,
                        "neutral_term": neutral
                    }
                    logs.append(log)
                except Exception as e:
                    logs.append({"error": str(e), **item})
        return {
            "type": item["type"],
            "doc_idx": item["doc_idx"],
            "para_idx": item.get("para_idx"),
            "table_id": item.get("table_id"),
            "row_id": item.get("row_id"),
            "col_id": item.get("col_id"),
            "cell_para_id": item.get("para_id"),
            "filled_text": para.text,
            "logs": logs
        }
    async def post_async(self, shared, prep_res, exec_res_list):
        shared["para_results"] = exec_res_list
        return "default"

class TableRowLLMFillNode(AsyncParallelBatchNode):
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
    async def prep_async(self, shared):
        return shared.get("table_row_tasks", [])
    async def exec_async(self, item):
        # 优化prompt，参考段落提示词，强调每列内容、上下文和依赖关系
        row_cells = item["row_cells"]
        virtual2real = {}
        row_texts = []
        for v_idx, cell in enumerate(row_cells):
            virtual2real[str(v_idx)] = cell["col_id"]
            row_texts.append(f"列{v_idx}: {cell['cell_text']}")
        prompt = f"""
你是一名专业的内容分析助手。你的任务是分析下方Word表格的一行内容，判断每一列（格）是否包含占位符或需要人工填写的内容（如姓名、日期、专业等字段），并输出结构化结果。

**任务要求**
- 你需要结合本行所有列的内容，判断每一列是否需要填写中性词。
- 某一列的填写可以依赖前一列的内容，也可以不依赖。
- 如果某列不需要填写，need_fill设为false，neutral_term设为""。
- 如果某列需要填写，need_fill设为true，neutral_term为中性词（如{{公司名称}}、{{日期}}等）。
- 不要修改原始文本，只能替换占位符或者添加中性词。
- 输出格式为YAML，每列一个字段，内容为：need_fill: true/false, neutral_term: "..."
- 在分析过程中，请逐步思考，但每个步骤的描述尽量简洁（不超过10个字）。
- 使用分隔符"####"来区分思考过程与最终答案，"####"后直接输出YAML。

**输入示例**
{chr(10).join(row_texts)}

**输出示例**
思考1:（不超过10个字）
思考2:（不超过10个字）
####
```yaml
0:
  need_fill: true
  neutral_term: "{{公司名称}}"
1:
  need_fill: false
  neutral_term: ""
2:
  need_fill: true
  neutral_term: "{{日期}}"
```

## 现在，请分析下方表格行：
{chr(10).join(row_texts)}
"""
        response = self.llm_client.chat_completion(user_message=prompt)
        yaml_data = self.llm_client.parse_yaml(response)
        logs = []
        # 只处理第一次出现的cell（已去重）
        for v_idx_str, cell_info in yaml_data.items():
            real_col_id = virtual2real.get(v_idx_str)
            if real_col_id is None:
                continue
            if cell_info.get("need_fill"):
                neutral = cell_info.get("neutral_term", "")
                log = {
                    "type": "table_row",
                    "doc_idx": item["doc_idx"],
                    "table_id": item["table_id"],
                    "row_id": item["row_id"],
                    "col_id": real_col_id,
                    "neutral_term": neutral
                }
                logs.append(log)
        return {
            "type": "table_row",
            "doc_idx": item["doc_idx"],
            "table_id": item["table_id"],
            "row_id": item["row_id"],
            "logs": logs
        }
    async def post_async(self, shared, prep_res, exec_res_list):
        shared["table_row_results"] = exec_res_list
        return "default"

class MergeResultNode(Node):
    def prep(self, shared):
        return {
            "docs": shared["docs"],
            "para_results": shared.get("para_results", []),
            "table_row_results": shared.get("table_row_results", [])
        }
    def exec(self, data):
        # 此处可实现回填合并、日志合并等
        parse_logs = []
        for res in data["para_results"]:
            if res.get("logs"):
                parse_logs.extend(res["logs"])
        for res in data["table_row_results"]:
            if res.get("logs"):
                parse_logs.extend(res["logs"])
        return {"parse_logs": parse_logs}
    def post(self, shared, prep_res, exec_res):
        shared["parse_logs"] = exec_res["parse_logs"]
        return "default"

class OutputDocNode(Node):
    def prep(self, shared):
        return {
            "docs": shared["docs"],
            "output_paths": shared["output_paths"] if "output_paths" in shared else []
        }
    def exec(self, data):
        docs = data["docs"]
        output_paths = data["output_paths"]
        result_paths = []
        for i, doc_info in enumerate(docs):
            doc = doc_info["doc_obj"]
            out_path = output_paths[i] if i < len(output_paths) else doc_info["doc_path"].replace(".docx", "_filled.docx")
            save_docx(doc, out_path)
            result_paths.append(out_path)
        return result_paths
    def post(self, shared, prep_res, exec_res):
        shared["output_paths"] = exec_res
        return None

# PocketFlow流程组装
def create_llm_detector_flow():
    read_node = BatchReadDocNode()
    dispatch_node = DispatchNode()
    para_node = ParaLLMFillNode()
    table_row_node = TableRowLLMFillNode()
    merge_node = MergeResultNode()
    output_node = OutputDocNode()
    # 串联处理：para_node处理完后再处理table_row_node
    read_node >> dispatch_node >> para_node >> table_row_node >> merge_node >> output_node
    return AsyncFlow(start=read_node)
