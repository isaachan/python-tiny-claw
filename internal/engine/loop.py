from internal.provider.llmprovider import LLMProvider
from internal.tools.registry import Registry
from internal.schema.message import Message, Role
from internal.context.context import Context

class AgentEngine:

    def __init__(self, llmprovider: LLMProvider, registry: Registry, workdir: str, stream: bool, enableThinking: bool):
        self.provider = llmprovider
        self.registry = registry
        self.workDir = workdir
        self.stream = stream
        self.enableThinking = enableThinking
    

    def run(self, ctx: Context, user_prompt: str):
        print(f"[Engine] 引擎启动，锁定工作区: {self.workDir}")
        print(f"[Engine] 慢思考模式 (Thinking Phase): {self.enableThinking}")

        context_history = [
            Message(Role.SYS, "You are python-tiny-claw, an expert coding assistant. You have full access to tools in the workspace."),
            Message(Role.USER, user_prompt)
        ]

        turn_count = 0

        while(True):
            turn_count += 1
            print(f"========== [Turn {turn_count}] 开始 ==========")

            available_tools = self.registry.get_available_tools()
            
            if self.enableThinking:
                print("[Engine][Phase 1] 剥夺工具访问权，强制进入慢思考与规划阶段...")
                # TODO check exception
                think_resp = self.provider.generate(ctx, context_history, None, stream=self.stream)
                trace = think_resp.reasoning_content or think_resp.content
                if trace:
                    if not self.stream:
                        print(f"🧠 [内部思考 Trace]: {trace}")
                    context_history.append(think_resp)


            #print("[Engine] 正在思考 (Reasoning)...")
            print("[Engine][Phase 2] 恢复工具挂载，等待模型采取行动... ")
            # TODO check exception
            action_resp = self.provider.generate(ctx, context_history, available_tools, stream=self.stream)
            context_history.append(action_resp)
            if action_resp.content:
                if not self.stream:
                    print(f"🤖 [对外回复]: {action_resp.content}")

            if len(action_resp.toolcalls) == 0:
                print("[Engine] 模型未请求调用工具，任务宣告完成。")
                break
            
            print(f"[Engine] 模型请求调用 {len(action_resp.toolcalls)} 个工具...")

            # for _, toolCall := range responseMsg.ToolCalls { 

            for toolcall in action_resp.toolcalls:
                print(f" -> 🛠️ 执行工具: {toolcall.name}, 参数: {toolcall.arguments}")
                result = self.registry.execute(ctx, toolcall)

                if result.is_error:
                    print(f" -> ❌ 工具执行报错: {result.output}")
                else:
                    print(f" -> ✅ 工具执行成功 (返回 {len(result.output)} 字节)")

                observation_msg = Message(Role.USER, result.output, toolcall_id=toolcall.id)
                context_history.append(observation_msg)
            
