import os
import json
from openai import OpenAI

from internal.context.context import Context
from internal.schema.message import Message, ToolDefinition, ToolCall, Role
from internal.provider.llmprovider import LLMProvider


class OpenAIProvider(LLMProvider):

    def __init__(self, api_key: str, base_url: str, model: str, enable_thinking: bool = False):
        print(f"[OpenAIProvider] 正在初始化，连接 {base_url}，模型 {model}...")
        self.client = OpenAI(api_key=api_key, base_url=base_url or None)
        self.model = model
        self.enable_thinking = enable_thinking

    @classmethod
    def create_deepseek_provider(cls):
        return cls(
            api_key=os.environ['DEEPSEEK_API_KEY'],
            base_url=os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'),
            model=os.environ.get('DEEPSEEK_MODEL', 'deepseek-v4-flash'),
            enable_thinking=True,
        )

    def _convert_message(self, msg: Message) -> dict:
        if msg.role == Role.SYS:
            return {"role": "system", "content": msg.content or ""}
        if msg.role == Role.USER and msg.toolcall_id:
            return {"role": "tool", "tool_call_id": msg.toolcall_id, "content": msg.content or ""}
        if msg.role == Role.ASSISTANT:
            d = {"role": "assistant", "content": msg.content or None}
            if msg.reasoning_content:
                d["reasoning_content"] = msg.reasoning_content
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
        return {"role": "user", "content": msg.content or ""}

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

    def generate(self, ctx: Context | None, context_history: list[Message], available_tools: list[ToolDefinition] | None, stream: bool = False) -> Message:
        openai_messages = [self._convert_message(m) for m in context_history]

        kwargs = {
            "model": self.model,
            "messages": openai_messages,
        }
        if self.enable_thinking:
            kwargs["reasoning_effort"] = "high"
            kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
        if available_tools is not None:
            kwargs["tools"] = [self._convert_tool(t) for t in available_tools]

        if not stream:
            return self._generate_nonstream(kwargs)

        return self._generate_stream(kwargs)

    def _generate_nonstream(self, kwargs: dict) -> Message:
        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        msg = choice.message

        content = msg.content or ""
        reasoning_content = getattr(msg, 'reasoning_content', None) or ""

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                ))

        return Message(Role.ASSISTANT, content, tool_calls, reasoning_content=reasoning_content)

    def _generate_stream(self, kwargs: dict) -> Message:
        stream_resp = self.client.chat.completions.create(
            **kwargs, stream=True, stream_options={"include_usage": True},
        )

        content = ""
        reasoning_content = ""
        tool_calls_acc = {}

        for chunk in stream_resp:
            if len(chunk.choices) == 0:
                continue

            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason

            if hasattr(delta, 'reasoning_content') and delta.reasoning_content: # type: ignore
                reasoning_content += delta.reasoning_content # type: ignore

            if delta.content:
                content += delta.content
                print(delta.content, end="", flush=True)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"id": None, "function": {"name": None, "arguments": ""}}
                    if tc.id:
                        tool_calls_acc[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_acc[idx]["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_acc[idx]["function"]["arguments"] += tc.function.arguments

        if content:
            print()

        tool_calls = []
        for idx, tc_data in tool_calls_acc.items():
            tool_calls.append(ToolCall(
                id=tc_data["id"],
                name=tc_data["function"]["name"],
                arguments=tc_data["function"]["arguments"],
            ))

        return Message(Role.ASSISTANT, content, tool_calls, reasoning_content=reasoning_content)
