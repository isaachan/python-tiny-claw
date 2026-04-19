from provider.llmprovider import LLMProvider
from tools.registry import Registry
from schema.message import Message, Role
from context.context import Context

class AgentEngine:

    def __init__(self, llmprovider: LLMProvider, registry: Registry, workdir: str):
        self.provider = llmprovider
        self.registry = registry
        self.workDir = workdir
    

    def run(self, ctx: Context, user_prompt: str):
        print(f"[Engine] 引擎启动，锁定工作区: {self.workDir}")

        context_history = [
            Message(Role.SYS, "You are python-tiny-claw, an expert coding assistant. You have full access to tools in the workspace."),
            Message(Role.USER, user_prompt)
        ]

        turn_count = 0

        while(True):
            turn_count += 1
            print(f"========== [Turn {turn_count}] 开始 ==========")

            available_tools = self.registry.get_available_tools()

            print("[Engine] 正在思考 (Reasoning)...")

            # TODO check exception
            repsone_msg = self.provider.generate(ctx, context_history, available_tools)

            if len(repsone_msg.toolcalls) == 0:
                print("[Engine] 任务完成，退出循环。")
                break
            
            print(f"[Engine] 模型请求调用 {len(repsone_msg.toolcalls)} 个工具...")

            # for _, toolCall := range responseMsg.ToolCalls { 

            for toolcall in repsone_msg.toolcalls:
                print(f" -> 🛠️ 执行工具: {toolcall.name}, 参数: {toolcall.arguments}")
                result = self.registry.execute(ctx, toolcall)

                if result.is_error:
                    print(f" -> ❌ 工具执行报错: {result.output}")
                else:
                    print(f" -> ✅ 工具执行成功 (返回 {len(result.output)} 字节)")

                observation_msg = Message(Role.USER, result.output, toolcall_id=toolcall.id)
                context_history.append(observation_msg)
            
            return None
