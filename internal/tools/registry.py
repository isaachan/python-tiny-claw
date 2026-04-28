from internal.context.context import Context
from internal.schema.message import ToolCall, ToolResult, ToolDefinition

class Registry:

    def get_available_tools(self) -> list[ToolDefinition]:
        return []

    def execute(self, ctx: Context, toolcall: ToolCall) -> ToolResult:
        return None # type: ignore