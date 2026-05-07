import os

from internal.context.context import Context
from internal.schema.message import ToolDefinition
from internal.tools.registry import BaseTool
import json

class WritefileTool(BaseTool):

    def __init__(self, work_dir: str):
        self.name = "write_file"
        self.definition = ToolDefinition(
            name=self.name,
            description="创建或覆盖写入一个文件。如果目录不存在会自动创建。请提供相对于工作区的相对路径。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要写入的文件路径，如 cmd/claw/main.py",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的完整文件内容",
                    },
                },
                "required": ["path", "content"],
            }
        )   
        self.work_dir = work_dir


    def execute(self, ctx: Context, args: str) -> str:
        input = json.loads(args)
        full_path = os.path.join(self.work_dir, input["path"])
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            with open(full_path, 'w') as f:
                f.write(input["content"])
            return f"文件 {input['path']} 写入成功。"
        except Exception as e:
            return f"Error: 无法写入文件 {input['path']}，异常信息: {str(e)}"
