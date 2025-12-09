#!/usr/bin/env python3
import asyncio
from droidrun import AdbTools, DroidAgent
from llama_index.llms.openai_like import OpenAILike
from droidrun.config_manager.config_manager import (
    DroidrunConfig,
    AgentConfig,
    CodeActConfig,
    ManagerConfig,
    ExecutorConfig,
)

async def main():
    # Load tools
    tools = AdbTools()
    # set up google gemini llm
    llm = OpenAILike(
        api_base="https://openrouter.ai/api/v1",
        api_key="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",  # Replace with your Gemini API key
        model="google/gemini-2.0-flash-001",  # or "gemini-2.5-pro" for enhanced reasoning
        is_chat_model=True, # droidrun requires chat model support
    )
    
    # Create agent
    config = DroidrunConfig(
        agent=AgentConfig(
            max_steps=200,
            reasoning=True,
            codeact=CodeActConfig(vision=True),     # CodeAct 使用截图
            manager=ManagerConfig(vision=True),     # 若 reasoning=True，Manager 也能看图
            executor=ExecutorConfig(vision=True),   # 同上
        )
    )
    agent = DroidAgent(
        timeout=7200,  # 2小时，适配 max_steps=200
        # goal="open dapp store and search&install 'save' dapp, use the phone wallet to login. Then explore its functions and tell me what it can do.",
        goal = """这是一台web3手机，你现在的任务是对这台手机进行一次深度的、长时间的用户体验测试。
请务必持续操作，不要提前结束任务，目标是至少进行 50 次以上的有效交互操作。

具体执行流：
1. 打开应用商店，搜索并下载 3-5 个不同类型的热门应用（如新闻、工具、游戏）。
2. 等待下载完成后，逐一打开这些应用。
3. 对每个应用进行深度的试用：点击内部的菜单，滑动浏览内容，模拟真实用户的浏览行为。
4. 如果遇到登录界面，尝试寻找“跳过”或“游客访问”，如果不行则退出换下一个应用。
5. 在操作过程中，不断检查通知栏和设置，调整一些显示或声音设置来测试系统反应。

重要原则：
- 即使你认为已经完成了上述步骤，也不要停止，请继续去发现手机里已安装的其他系统应用并进行试用。
- 只要步数允许，请保持持续探索，直到被系统强制停止。

注意：
- 它的所有下载软件功能都应该通过dapp商店进行，不要通过 play商店下载
- 所有碰到需要账号登陆（除非支持web3 wallet登录）的都应该退出换下一个应用。
""",
        llms=llm,
        tools=tools,
        config=config,
    )
    
    # Run agent
    result = await agent.run()
    print(f"Success: {result['success']}")
    if result.get('output'):
        print(f"Output: {result['output']}")

if __name__ == "__main__":
    asyncio.run(main())
