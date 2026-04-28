from context.context import Context
from schema.message import Message, ToolDefinition

class LLMProvider:

    def generate(self, ctx: Context, context_history: list[Message], available_tools: list[ToolDefinition] | None) -> Message: 

        return None # type: ignore