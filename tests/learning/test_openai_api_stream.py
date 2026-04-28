import os
import json
from openai import OpenAI
from datetime import datetime

# The definition of the tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "Get the current date",
            "parameters": { "type": "object", "properties": {} },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather of a location, the user should supply the location and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": { "type": "string", "description": "The city name, in form of Pinyin without space, lower case." },
                    "date": { "type": "string", "description": "The date in format YYYY-mm-dd" },
                },
                "required": ["location", "date"]
            },
        }
    },
]

# The mocked version of the tool calls
def get_date_mock():
    return datetime.now().strftime("%Y-%m-%d")

def get_weather_mock(location, date):
    return "Cloudy 7~13°C"

TOOL_CALL_MAP = {
    "get_date": get_date_mock,
    "get_weather": get_weather_mock
}

def run_turn(turn, messages):
    sub_turn = 1
    while True:
        stream = client.chat.completions.create(
            model='deepseek-v4-flash',
            messages=messages,
            tools=tools, # type: ignore
            reasoning_effort="high",
            stream=True,
            stream_options={"include_usage": True},
            extra_body={ "thinking": { "type": "enabled" } },
        )

        content = ""
        reasoning_content = ""
        tool_calls = {}  # index -> {id, function: {name, arguments}}

        for chunk in stream:
            if len(chunk.choices) == 0:
                continue

            delta = chunk.choices[0].delta

            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                reasoning_content += delta.reasoning_content

            if delta.content:
                content += delta.content

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {"id": None, "function": {"name": None, "arguments": ""}}
                    if tc.id:
                        tool_calls[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls[idx]["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls[idx]["function"]["arguments"] += tc.function.arguments

        print(f"Turn {turn}.{sub_turn}\n{reasoning_content=}\n{content=}\n{tool_calls=}")

        if not tool_calls:
            break

        # Append the assistant message with tool_calls before adding tool results
        assistant_msg = {"role": "assistant", "content": content or None}
        if reasoning_content:
            assistant_msg["reasoning_content"] = reasoning_content
        assistant_msg["tool_calls"] = [
            {
                "id": tc_data["id"],
                "type": "function",
                "function": {
                    "name": tc_data["function"]["name"],
                    "arguments": tc_data["function"]["arguments"],
                },
            }
            for tc_data in tool_calls.values()
        ]
        messages.append(assistant_msg)

        for tc_data in tool_calls.values():
            tool_function = TOOL_CALL_MAP[tc_data["function"]["name"]] # type: ignore
            args = json.loads(tc_data["function"]["arguments"]) if tc_data["function"]["arguments"] else {}
            tool_result = tool_function(**args)
            print(f"tool result for {tc_data['function']['name']}: {tool_result}\n") # type: ignore
            messages.append({
                "role": "tool",
                "tool_call_id": tc_data["id"],
                "content": tool_result,
            })
        sub_turn += 1
    print()

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url=os.environ.get('DEEPSEEK_BASE_URL'),
)

# The user starts a question
turn = 1
messages = [{
    "role": "user",
    "content": "How's the weather in 广州 Tomorrow"
}]
run_turn(turn, messages)

# The user starts a new question
turn = 2
messages.append({
    "role": "user",
    "content": "How's the weather in Guangzhou Tomorrow"
})
run_turn(turn, messages)
