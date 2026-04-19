from internal.context.context import Context
from internal.schema.message import Message, Role, ToolCall, ToolResult
from internal.engine.loop import AgentEngine
from internal.provider.llmprovider import LLMProvider
from internal.tools.registry import Registry

class Mock_Provider(LLMProvider):

    def __init__(self):
        self.turn = 0
    
    def generate(self, ctx: Context, context_history: list[Message], available_tools): 
        self.turn += 1
        if self.turn == 1:
            return Message(Role.ASSISTANT, "让我来看看当前目录下有什么文件。", [
                ToolCall("call_123", "bash", '{"command": "ls -la"}')
            ])
        
        return Message(Role.ASSISTANT, "我看到了文件列表，里面包含 main.go，任务完成！")

class Mock_Registry(Registry):

    def get_available_tools(self):
        pass

    def execute(self, ctx: Context, toolcall: ToolCall):
        return ToolResult(toolcall.id, "-rw-r--r-- 1 user group 234 Oct 24 10:00 main.go\n", False)


def launch():
    print("🚀 欢迎来到 python-tiny-claw 引擎启动序列")
    print("架构蓝图搭建完毕，等待各核心模块注入！")

    # eng := engine.NewAgentEngine(p, r, workDir)
    engine = AgentEngine(Mock_Provider(), Mock_Registry(), "./")
    engine.run(Context(), "帮我检查当前目录的文件")




if __name__ == "__main__":
    launch()