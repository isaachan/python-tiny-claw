from context.context import Context
from schema.message import Message

class LLMProvider:

    #TODO type of available_tools
    def generate(self, ctx: Context, context_history: list[Message], available_tools) -> Message: 

        return None # type: ignore