from internal.context.context import Context
from internal.schema.message import Message, Role, ToolCall, ToolResult, ToolDefinition
from internal.engine.loop import AgentEngine
from internal.provider.llmprovider import LLMProvider
from internal.tools.registry import Registry
from internal.provider.openai import OpenAIProvider

class One_Stage_Mock_Provider(LLMProvider):

    def __init__(self):
        self.turn = 0
    
    def generate(self, ctx: Context, context_history: list[Message], available_tools): 
        self.turn += 1
        if self.turn == 1:
            return Message(Role.ASSISTANT, "让我来看看当前目录下有什么文件。", [
                ToolCall("call_123", "bash", '{"command": "ls -la"}')
            ])
        
        return Message(Role.ASSISTANT, "我看到了文件列表，里面包含 main.go，任务完成！")


class Two_Stage_Mock_Provider(LLMProvider):

    def __init__(self):
        self.turn = 0
    
    def generate(self, ctx: Context, context_history: list[Message], available_tools): 
        if not available_tools or len(available_tools) == 0:
            return Message(Role.ASSISTANT, "【推理中】目标是检查文件。我不能直接盲猜，我需要先调用 bash 工具执行 ls 命令，看看当前目录下有什么，然后再做定夺。", [])

        self.turn += 1
        if self.turn == 1:
            return Message(Role.ASSISTANT, "我要执行我刚才计划的步骤了。", [
                ToolCall("call_123", "bash", '{"command": "ls -la"}')
            ])
        
        return Message(Role.ASSISTANT, "根据工具返回的结果，我看到了 main.go，任务圆满完成！")


class Mock_Registry(Registry):

    def get_available_tools(self) -> list[ToolDefinition]:
        # return []schema.ToolDefinition{{Name: "bash"}}
        return [ToolDefinition("bash", "Execute bash commands in the current workspace", None)] # type: ignore

    def execute(self, ctx: Context, toolcall: ToolCall):
        return ToolResult(toolcall.id, "-rw-r--r-- 1 user group 234 Oct 24 10:00 main.go\n", False)


def launch():
    print("🚀 欢迎来到 python-tiny-claw 引擎启动序列")
    print("架构蓝图搭建完毕，等待各核心模块注入！")

    # eng := engine.NewAgentEngine(p, r, workDir)
    # engine = AgentEngine(One_Stage_Mock_Provider(), Mock_Registry(), "./", False)
    # engine = AgentEngine(Two_Stage_Mock_Provider(), Mock_Registry(), "./", True)
    engine = AgentEngine(OpenAIProvider(), Mock_Registry(), "./", True)
    engine.run(Context(), "我的mac系统下当前目录下有什么文件？")




if __name__ == "__main__":
    launch()