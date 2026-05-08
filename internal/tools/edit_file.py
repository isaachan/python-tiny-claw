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
    def execute(self, ctx: Context, args: str) -> str:
        input = json.loads(args)
        full_path = os.path.join(self.work_dir, input["path"])

        if not os.path.isfile(full_path):
            return f"Error: 文件 {input['path']} 不存在。"

        try:
            with open(full_path, "r") as f:
                content = f.read()
        except Exception as e:
            return f"Error: 无法读取文件 {input['path']}，异常信息: {str(e)}"

        old_text = input["old_text"]
        new_text = input["new_text"]

        count = content.count(old_text)
        if count == 0:
            return f"Error: 在文件 {input['path']} 中未找到要替换的文本。"
        if count > 1:
            return f"Error: 要替换的文本在文件中出现了 {count} 次，请提供更多上下文以确保唯一性。"

        new_content = content.replace(old_text, new_text)

        try:
            with open(full_path, "w") as f:
                f.write(new_content)
            return f"文件 {input['path']} 替换成功。"
        except Exception as e:
            return f"Error: 无法写入文件 {input['path']}，异常信息: {str(e)}"