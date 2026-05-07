import os

from internal.context.context import Context
from internal.schema.message import ToolDefinition
from internal.tools.registry import BaseTool
import json

class ReadfileTool(BaseTool):

    def __init__(self, work_dir: str):
        self.name = "read_file"
        self.definition = ToolDefinition(
            name=self.name,
            description="读取指定路径的文件内容。请提供相对工作区的路径。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径，如 cmd/claw/main.py",
                    },
                },
                "required": ["path"],
            }
        )   
        self.work_dir = work_dir


    def execute(self, ctx: Context, args: str) -> str:
        input = json.loads(args) 
        full_path = os.path.join(self.work_dir, input["path"])
        if not os.path.isfile(full_path):
            return f"Error: 文件 {input['path']} 不存在。"
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            max_len = 8000
            if len(content) > max_len:
                print(f"[ReadfileTool] 文件内容过长 ({len(content)} 字节)，将被截断至前 {max_len} 字节返回。")
                content = content[:max_len]
            return content
        except Exception as e:
            return f"Error: 无法读取文件 {input['path']}，异常信息: {str(e)}"   
        
