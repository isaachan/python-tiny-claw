from internal.context.context import Context
from internal.schema.message import ToolCall, ToolResult, ToolDefinition
from internal.context.context import Context
from internal.schema.message import ToolDefinition


class BaseTool:

    def __init__(self, name: str, definition: ToolDefinition):
        self.name = name
        self.definition = definition
    
    def execute(self, ctx: Context, args: str) -> str:
        raise NotImplementedError("Tool call method not implemented.")


class Registry:
    
    def __init__(self):
        self.tools = {}


    def register(self, tool: BaseTool) -> None:
        if self.tools.get(tool.name, None):
            print(f"[Warning] Tool {tool.name} already registered in registry, will be overwritten.")

        self.tools[tool.name] = tool
        print(f"[Registry] Tool {tool.name} registered successfully.")

    
    def get_available_tools(self) -> list[ToolDefinition]:
        return [t.definition for t in self.tools.values()]

    def execute(self, ctx: Context, toolcall: ToolCall) -> ToolResult:
        if toolcall.name not in self.tools:
            return ToolResult(toolcall.id, f"Tool {toolcall.name} not found in registry.", True)
        
        tool = self.tools[toolcall.name]
        try:
            output = tool.execute(ctx, toolcall.arguments)
            return ToolResult(toolcall.id, output, False)
        except Exception as e:
            return ToolResult(toolcall.id, str(e), True)



