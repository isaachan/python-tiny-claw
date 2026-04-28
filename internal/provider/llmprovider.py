from internal.context.context import Context
from internal.schema.message import Message, ToolDefinition

class LLMProvider:

    def generate(self, ctx: Context, context_history: list[Message], available_tools: list[ToolDefinition] | None) -> Message: 

        return None # type: ignore