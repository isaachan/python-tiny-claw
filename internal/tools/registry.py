from context.context import Context
from schema.message import ToolCall, ToolResult

class Registry:

    def get_available_tools(self):
        pass

    def execute(self, ctx: Context, toolcall: ToolCall) -> ToolResult:
        
        return None # type: ignore