import os
import re

from internal.context.context import Context
from internal.schema.message import ToolDefinition
from internal.tools.registry import BaseTool
import json


class EditfileTool(BaseTool):

    def __init__(self, work_dir: str):
        self.name = "edit_file"
        self.definition = ToolDefinition(
            name=self.name,
            description="对现有文件进行局部的字符串替换。这比重写整个文件更安全、更快速。请提供足够的 old_text 上下文以确保匹配的唯一性。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要修改的文件路径，如 cmd/claw/main.py",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "文件中原有的文本。必须包含足够的上下文（建议上下各多包含几行），以确保在文件中的唯一性。",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "要替换的新文本",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            }
        )
        self.work_dir = work_dir


    # 支持的替换场景：
    # 1. 精确字符串替换 — old_text / new_text 为不带换行的词或句子，前后无空格。
    # 2. 带空白替换 — old_text / new_text 前后可以包含空格（缩进、尾随空格等）。
    # 3. 跨行替换 — old_text / new_text 包含换行符，假设文件与参数的换行符一致。
    # 4. 换行符不一致 — old_text / new_text 的换行符与文件不一致（\r\n vs \n），自动规范化为文件的换行风格。
    # 5. 缩进无关模糊匹配 — 前几种精确匹配失败后，忽略绝对缩进量，按相对缩进匹配。
    def execute(self, ctx: Context, args: str) -> str:
        input = json.loads(args)
        full_path = os.path.join(self.work_dir, input["path"])

        if not os.path.isfile(full_path):
            return f"Error: 文件 {input['path']} 不存在。"

        try:
            with open(full_path, "r", newline="") as f:
                content = f.read()
        except Exception as e:
            return f"Error: 无法读取文件 {input['path']}，异常信息: {str(e)}"

        old_text = input["old_text"]
        new_text = input["new_text"]

        # 检测文件的换行风格，并将 old_text / new_text 规范化为与文件一致
        file_newline = "\r\n" if "\r\n" in content else "\n"
        old_text = _normalize_newlines(old_text, file_newline)
        new_text = _normalize_newlines(new_text, file_newline)

        count = content.count(old_text)
        if count == 1:
            new_content = content.replace(old_text, new_text)
        elif count > 1:
            return f"Error: 要替换的文本在文件中出现了 {count} 次，请提供更多上下文以确保唯一性。"
        else:
            # 精确匹配失败，尝试缩进无关的模糊匹配
            new_content, fuzzy_count = _fuzzy_replace(content, old_text, new_text, file_newline)
            if new_content is None:
                if fuzzy_count == 0:
                    return f"Error: 在文件 {input['path']} 中未找到要替换的文本。"
                else:
                    return f"Error: 要替换的文本在文件中出现了 {fuzzy_count} 次（模糊匹配），请提供更多上下文以确保唯一性。"

        try:
            with open(full_path, "w", newline="") as f:
                f.write(new_content)
            return f"文件 {input['path']} 替换成功。"
        except Exception as e:
            return f"Error: 无法写入文件 {input['path']}，异常信息: {str(e)}"


def _normalize_newlines(text: str, target: str) -> str:
    """将 text 中的换行符规范化为 target 风格（\n 或 \r\n）。"""
    text = text.replace("\r\n", "\n")
    if target == "\r\n":
        text = text.replace("\n", "\r\n")
    return text


def _min_indent(lines: list[str]) -> int:
    """计算非空行的最小前导空格数。"""
    min_val = None
    for line in lines:
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip())
        if min_val is None or indent < min_val:
            min_val = indent
    return 0 if min_val is None else min_val


def _strip_indents(lines: list[str], indent: int) -> list[str]:
    """从每行去除 indent 个前导空格，空行保持不变。"""
    result = []
    for line in lines:
        if line.strip() == "":
            result.append(line)
        else:
            result.append(line[indent:])
    return result


def _add_indent(lines: list[str], indent: int) -> list[str]:
    """给每行添加 indent 个前导空格，空行保持不变。"""
    result = []
    for line in lines:
        if line.strip() == "":
            result.append(line)
        else:
            result.append(" " * indent + line)
    return result


def _fuzzy_replace(content: str, old_text: str, new_text: str, file_newline: str) -> tuple:
    """缩进无关的模糊匹配替换。返回 (new_content, None) 成功，或 (None, error_count) 失败。"""
    sep = file_newline
    old_lines = old_text.split(sep)
    new_lines = new_text.split(sep)
    content_lines = content.split(sep)

    old_min = _min_indent(old_lines)
    old_stripped = _strip_indents(old_lines, old_min)

    new_min = _min_indent(new_lines)
    new_stripped = _strip_indents(new_lines, new_min)

    matches = []
    for i in range(len(content_lines) - len(old_lines) + 1):
        window = content_lines[i:i + len(old_lines)]
        window_min = _min_indent(window)
        window_stripped = _strip_indents(window, window_min)
        if window_stripped == old_stripped:
            matches.append((i, window_min))

    if not matches:
        return None, 0
    if len(matches) > 1:
        return None, len(matches)

    match_idx, file_indent = matches[0]
    indented_new = _add_indent(new_stripped, file_indent)

    before = content_lines[:match_idx]
    after = content_lines[match_idx + len(old_lines):]
    return sep.join(before + indented_new + after), None