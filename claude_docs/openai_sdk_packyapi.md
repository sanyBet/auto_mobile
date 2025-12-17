# OpenAI SDK 兼容 PackyAPI 使用指南

## 问题背景

PackyAPI 会拦截带有 `OpenAI/Python` User-Agent 的请求，导致标准 OpenAI SDK 无法直接使用。

## 解决方案

通过自定义 HTTP Transport 修改 User-Agent，使 OpenAI SDK 可以正常使用。

## 使用方法

### 方法1: 使用封装好的工具（推荐）

```python
from utils.openai_client import create_client

# 创建客户端（自动从 .env 读取配置）
client = create_client()

# 正常使用 OpenAI SDK
response = client.chat.completions.create(
    model="gpt-5.1",
    messages=[{"role": "user", "content": "Hello"}]
)

print(response.choices[0].message.content)
```

### 方法2: 在其他项目中使用

如果你的其他程序也需要这个功能，有两种方式：

#### 2.1 复制 utils/openai_client.py

将 `utils/openai_client.py` 复制到你的项目中，然后：

```python
from your_utils.openai_client import create_client

client = create_client(
    api_key="your-api-key",
    base_url="https://www.packyapi.com/v1"
)
```

#### 2.2 手动创建兼容客户端

```python
import httpx
from openai import OpenAI

class CompatibleTransport(httpx.HTTPTransport):
    def handle_request(self, request):
        request.headers['user-agent'] = 'Mozilla/5.0 (compatible; APIClient/1.0)'
        return super().handle_request(request)

http_client = httpx.Client(transport=CompatibleTransport())
client = OpenAI(
    api_key="your-api-key",
    base_url="https://www.packyapi.com/v1",
    http_client=http_client
)
```

## 技术原理

1. **问题原因**: PackyAPI 通过检测 `User-Agent: OpenAI/Python x.x.x` 来识别并拦截 OpenAI SDK 的请求
2. **解决方法**: 使用自定义 HTTP Transport 将 User-Agent 修改为通用浏览器标识
3. **关键代码**: 只需修改 User-Agent 即可，无需移除其他请求头

## 测试结果

✅ 方案1: 修改 User-Agent + 移除 x-stainless-* → 成功
✅ 方案2: 仅修改 User-Agent → 成功（推荐）
❌ 方案3: 仅移除 x-stainless-* → 失败

## 注意事项

1. 此方案仅适用于第三方 API 服务（如 PackyAPI）
2. 官方 OpenAI API 不需要此修改
3. 确保 `.env` 文件中正确配置了 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`
4. `OPENAI_BASE_URL` 应该是 `https://www.packyapi.com/v1`，不包含 `/chat/completions`

## 环境配置示例

```bash
# .env
OPENAI_BASE_URL="https://www.packyapi.com/v1"
OPENAI_API_KEY="sk-your-api-key"
```
