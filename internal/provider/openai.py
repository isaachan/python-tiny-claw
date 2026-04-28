import os
import json
from openai import OpenAI

from context.context import Context
from schema.message import Message, ToolDefinition, ToolCall, Role
from provider.llmprovider import LLMProvider


class OpenAIProvider(LLMProvider):

    def __init__(self):
        print("[OpenAIProvider] 正在初始化 OpenAIProvider，连接 OpenAI API...")
        self.client = OpenAI(
            api_key=os.environ.get('DEEPSEEK_API_KEY'),
            base_url=os.environ.get('DEEPSEEK_BASE_URL'),
        )
        self.model = os.environ.get('OPENAI_MODEL', 'deepseek-v4-flash')

    def _convert_message(self, msg: Message) -> dict:
        if msg.role == Role.SYS:
            return {"role": "system", "content": msg.content or ""}
        if msg.role == Role.USER and msg.toolcall_id:
            return {"role": "tool", "tool_call_id": msg.toolcall_id, "content": msg.content or ""}
        if msg.role == Role.USER:
            return {"role": "user", "content": msg.content or ""}
        if msg.role == Role.ASSISTANT:
            d = {"role": "assistant", "content": msg.content or None}
            if msg.toolcalls:
                d["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in msg.toolcalls
                ]
            return d
        return {"role": "user", "content": str(msg.content)}

    def _convert_tool(self, tool: ToolDefinition) -> dict:
        schema = tool.input_schema
        if isinstance(schema, str):
            schema = json.loads(schema)
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": schema,
            }
        }

    def generate(self, ctx: Context, context_history: list[Message], available_tools: list[ToolDefinition] | None) -> Message:
        openai_messages = [self._convert_message(m) for m in context_history]

        kwargs = {
            "model": self.model,
            "messages": openai_messages,
            "reasoning_effort": "high",
            "extra_body": {"thinking": {"type": "enabled"}},
        }
        if available_tools is not None:
            kwargs["tools"] = [self._convert_tool(t) for t in available_tools]

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        msg = choice.message

        content = msg.content or ""
        reasoning_content = getattr(msg, 'reasoning_content', None) or ""

        # In thinking phase (no tools passed), prefer reasoning_content as trace
        if available_tools is None and reasoning_content:
            content = reasoning_content

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                ))

        return Message(Role.ASSISTANT, content, tool_calls)
