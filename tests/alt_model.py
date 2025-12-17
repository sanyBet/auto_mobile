import sys
from pathlib import Path

import os
from dotenv import load_dotenv
load_dotenv()

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.openai_client import create_client

# 创建兼容 PackyAPI 的客户端
client = create_client(    
    api_key=os.getenv("PACKYAPI_API_KEY"),    
    base_url=os.getenv("PACKYAPI_BASE_URL", "https://www.packyapi.com/v1"),
)

prompt = """You are an agent who can operate an Android phone on behalf of a user. Your goal is to track progress and devise high-level plans to achieve the user's requests.

**CRITICAL: OUTPUT FORMAT REQUIREMENT**
You MUST respond using ONLY the XML format shown below. Do NOT use any other format such as markdown, plain text, or numbered lists outside of XML tags.
Your response MUST contain these XML tags: <thought> and <plan> (or <request_accomplished> if task is complete).
Any response without proper XML tags will be rejected.

**Example of CORRECT response format:**
<thought>
The user wants to open the dApp Store. I can see the dApp Store icon on the home screen at index 5.
</thought>

<plan>
1. Click on the dApp Store icon to open the store
2. Browse available apps
</plan>

**Example of INCORRECT response (DO NOT do this):**
Here's my plan:
1. Open dApp Store
2. Browse apps
(This format is WRONG because it doesn't use XML tags)

<user_request>
测试 dApp Store 生态系统：打开 dApp Store，安装一个应用，体验后卸载。
</user_request>

<guidelines>
The following guidelines will help you plan this request.
General:
1. Use the `open_app` action whenever you want to open an app, do not use the app drawer to open an app.
2. Don't do more than what the user asks for.
</guidelines>

---
Assess the current status and screenshot. Update the plan if needed.
- If task is complete: use <request_accomplished success="true">message</request_accomplished>
- If task failed: use <request_accomplished success="false">reason</request_accomplished>
- If task is in progress: provide <thought> and <plan>

**REMEMBER: You MUST use XML tags. Plain text responses will be rejected.**

<thought>
Your reasoning about the current state and next steps.
</thought>

<plan>
Your numbered plan. Keep first item as the immediate next action.
</plan>
"""

response = client.chat.completions.create(
    model=os.getenv("PACKYAPI_MODEL", "gpt-5.1"),
    messages=[{"role": "user", "content": prompt}]
)

print(response.choices[0].message.content)