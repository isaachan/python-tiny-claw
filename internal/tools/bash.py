import subprocess
import json

from internal.context.context import Context
from internal.schema.message import ToolDefinition
from internal.tools.registry import BaseTool

MAX_OUTPUT_LENGTH = 8000
DEFAULT_TIMEOUT = 60  # seconds


class BashTool(BaseTool):

    def __init__(self, work_dir: str):
        self.name = "bash"
        self.definition = ToolDefinition(
            name=self.name,
            description="在当前工作区执行任意的 bash 命令。支持管道、重定向、环境变量、链式命令(&&/||)等完整 Shell 语法。返回标准输出(stdout)和标准错误(stderr)。",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 bash 命令，例如: ls -la 或 FOO=bar pytest tests/ -v 2>&1",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "命令超时秒数，默认 60 秒。超时后进程被强制终止。",
                    },
                },
                "required": ["command"],
            }
        )
        self.work_dir = work_dir

    def _truncate(self, text: str) -> str:
        if len(text) > MAX_OUTPUT_LENGTH:
            return text[:MAX_OUTPUT_LENGTH] + f"\n... [truncated, {len(text) - MAX_OUTPUT_LENGTH} more bytes]"
        return text

    def execute(self, ctx: Context, args: str) -> str:
        input_args = json.loads(args)
        command = input_args["command"]
        timeout = input_args.get("timeout", DEFAULT_TIMEOUT)

        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                executable="/bin/bash",
            )
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {timeout}s\n[timeout] {command}"

        stdout = self._truncate(completed.stdout)
        stderr = self._truncate(completed.stderr)

        parts: list[str] = []
        if stdout:
            parts.append(stdout)
        if stderr:
            parts.append(f"[stderr]\n{stderr}")

        if completed.returncode != 0:
            parts.append(f"[exit code: {completed.returncode}]")

        if not parts:
            return f"Command executed successfully (no output).\n[exit code: 0]"

        return "\n".join(parts)
    