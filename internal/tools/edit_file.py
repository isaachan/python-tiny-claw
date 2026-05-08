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


    def execute(self, ctx: Context, args: str) -> str:
        return ''