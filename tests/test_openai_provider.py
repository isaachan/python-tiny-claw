import sys
import os
_project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, _project_root)

import unittest
from unittest.mock import MagicMock
import json

from internal.schema.message import Message, Role, ToolCall, ToolDefinition
from internal.provider.openai import OpenAIProvider


class TestConvertMessage(unittest.TestCase):

    def setUp(self):
        self.provider = OpenAIProvider(
            api_key="test-key",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
        )

    def test_system_message(self):
        msg = Message(Role.SYS, "You are a helpful assistant.")
        result = self.provider._convert_message(msg)
        self.assertEqual(result, {"role": "system", "content": "You are a helpful assistant."})

    def test_user_message(self):
        msg = Message(Role.USER, "Hello")
        result = self.provider._convert_message(msg)
        self.assertEqual(result, {"role": "user", "content": "Hello"})

    def test_user_message_empty_content(self):
        msg = Message(Role.USER, "")
        result = self.provider._convert_message(msg)
        self.assertEqual(result, {"role": "user", "content": ""})

    def test_tool_result_message(self):
        msg = Message(Role.USER, '{"files": []}', toolcall_id="call_1")
        result = self.provider._convert_message(msg)
        self.assertEqual(result, {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": '{"files": []}',
        })

    def test_assistant_message(self):
        msg = Message(Role.ASSISTANT, "I'll help you.")
        result = self.provider._convert_message(msg)
        self.assertEqual(result, {"role": "assistant", "content": "I'll help you."})

    def test_assistant_message_none_content(self):
        msg = Message(Role.ASSISTANT, None)
        result = self.provider._convert_message(msg)
        self.assertEqual(result, {"role": "assistant", "content": None})

    def test_assistant_with_tool_calls(self):
        msg = Message(Role.ASSISTANT, "", toolcalls=[
            ToolCall("call_1", "bash", '{"command": "ls -la"}'),
            ToolCall("call_2", "bash", '{"command": "pwd"}'),
        ])
        result = self.provider._convert_message(msg)
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(len(result["tool_calls"]), 2)
        self.assertEqual(result["tool_calls"][0], {
            "id": "call_1",
            "type": "function",
            "function": {"name": "bash", "arguments": '{"command": "ls -la"}'},
        })
        self.assertEqual(result["tool_calls"][1], {
            "id": "call_2",
            "type": "function",
            "function": {"name": "bash", "arguments": '{"command": "pwd"}'},
        })

    def test_assistant_with_reasoning_content(self):
        msg = Message(Role.ASSISTANT, "Final answer", reasoning_content="Thinking step by step")
        result = self.provider._convert_message(msg)
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["content"], "Final answer")
        self.assertEqual(result["reasoning_content"], "Thinking step by step")


class TestConvertTool(unittest.TestCase):

    def setUp(self):
        self.provider = OpenAIProvider(
            api_key="test-key",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
        )

    def test_tool_with_string_schema(self):
        tool = ToolDefinition("bash", "Execute bash commands", '{"type": "object", "properties": {"cmd": {"type": "string"}}}')
        result = self.provider._convert_tool(tool)
        self.assertEqual(result, {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "Execute bash commands",
                "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}},
            }
        })

    def test_tool_with_dict_schema(self):
        tool = ToolDefinition("get_weather", "Get weather", {"type": "object", "properties": {}})
        result = self.provider._convert_tool(tool)
        self.assertEqual(result["function"]["parameters"], {"type": "object", "properties": {}})


class TestGenerate(unittest.TestCase):

    def setUp(self):
        self.provider = OpenAIProvider(
            api_key="test-key",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
        )
        self.provider.client = MagicMock()
        self.mock_client = self.provider.client

    def _make_response(self, content=None, tool_calls=None, reasoning_content=None):
        mock_choice = MagicMock()
        mock_choice.message.content = content
        mock_choice.message.tool_calls = tool_calls
        mock_choice.message.reasoning_content = reasoning_content
        return MagicMock(choices=[mock_choice])

    def test_generate_without_tools(self):
        self.mock_client.chat.completions.create.return_value = self._make_response(
            content="Thinking about the problem"
        )

        result = self.provider.generate(None, [
            Message(Role.SYS, "You are an assistant."),
            Message(Role.USER, "Help me."),
        ], None)

        self.mock_client.chat.completions.create.assert_called_once()
        kwargs = self.mock_client.chat.completions.create.call_args[1]
        self.assertNotIn("tools", kwargs)
        self.assertEqual(len(kwargs["messages"]), 2)
        self.assertEqual(result.content, "Thinking about the problem")
        self.assertEqual(len(result.toolcalls), 0)

    def test_generate_with_tools(self):
        self.mock_client.chat.completions.create.return_value = self._make_response(
            content="I'll use bash"
        )

        tools = [ToolDefinition("bash", "Execute bash", '{"type": "object", "properties": {}}')]
        result = self.provider.generate(None, [
            Message(Role.SYS, "You are an assistant."),
            Message(Role.USER, "List files."),
        ], tools)

        kwargs = self.mock_client.chat.completions.create.call_args[1]
        self.assertIn("tools", kwargs)
        self.assertEqual(len(kwargs["tools"]), 1)
        self.assertEqual(kwargs["tools"][0]["function"]["name"], "bash")
        self.assertEqual(result.content, "I'll use bash")

    def test_generate_with_tool_calls_in_response(self):
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_abc"
        mock_tool_call.function.name = "bash"
        mock_tool_call.function.arguments = '{"command": "ls"}'
        self.mock_client.chat.completions.create.return_value = self._make_response(
            tool_calls=[mock_tool_call]
        )

        tools = [ToolDefinition("bash", "Execute bash", '{"type": "object", "properties": {}}')]
        result = self.provider.generate(None, [
            Message(Role.USER, "List files."),
        ], tools)

        self.assertEqual(len(result.toolcalls), 1)
        self.assertEqual(result.toolcalls[0].id, "call_abc")
        self.assertEqual(result.toolcalls[0].name, "bash")
        self.assertEqual(result.toolcalls[0].arguments, '{"command": "ls"}')
        self.assertEqual(result.content, "")

    def test_generate_captures_reasoning_content(self):
        self.mock_client.chat.completions.create.return_value = self._make_response(
            reasoning_content="Let me think about this step by step..."
        )

        result = self.provider.generate(None, [
            Message(Role.USER, "Solve this."),
        ], None)

        self.assertEqual(result.reasoning_content, "Let me think about this step by step...")
        self.assertEqual(result.content, "")

    def test_generate_with_thinking_params(self):
        provider = OpenAIProvider(
            api_key="test-key",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            enable_thinking=True,
        )
        provider.client = MagicMock()
        mock_client = provider.client
        mock_client.chat.completions.create.return_value = self._make_response(
            content="Answer", reasoning_content="Thinking..."
        )

        provider.generate(None, [
            Message(Role.USER, "Hi"),
        ], None)

        kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(kwargs["reasoning_effort"], "high")
        self.assertEqual(kwargs["extra_body"], {"thinking": {"type": "enabled"}})

    def test_generate_without_thinking_params(self):
        provider = OpenAIProvider(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
            enable_thinking=False,
        )
        provider.client = MagicMock()
        mock_client = provider.client
        mock_client.chat.completions.create.return_value = self._make_response(content="Answer")

        provider.generate(None, [
            Message(Role.USER, "Hi"),
        ], None)

        kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertNotIn("reasoning_effort", kwargs)
        self.assertNotIn("extra_body", kwargs)


if __name__ == "__main__":
    unittest.main()
