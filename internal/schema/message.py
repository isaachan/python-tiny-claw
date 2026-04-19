
class ToolCall():

    def __init__(self, id, name, arguments):
        self.id = id
        self.name = name
        self.arguments = arguments


class ToolResult():

    def __init__(self, toolcall_id: str, output: str, is_error: bool):
        self.toolcall_id = toolcall_id
        self.output = output
        self.is_error = is_error


class ToolDefinition:

    def __init__(self, name: str, description: str, input_schema: str):
        self.name = name
        self.description = description
        self.input_schema = input_schema


from enum import Enum, auto

class Role(Enum):
    SYS = auto()
    USER = auto()
    ASSISTANT = auto()


class Message:

    def __init__(self, role, content, toolcalls: list[ToolCall] = [], toolcall_id=None):
        self.role = role
        self.content = content
        self.toolcalls = toolcalls
        self.toolcall_id = toolcall_id

