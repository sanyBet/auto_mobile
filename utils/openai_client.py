"""
通用的 OpenAI 客户端工具，兼容 PackyAPI 等第三方 API 服务

本模块提供：
- CompatibleTransport: 自定义传输层，修改 User-Agent 以兼容第三方 API
- create_client(): 按需创建 OpenAI 客户端的工具函数

使用方法：
    from utils.openai_client import create_client

    client = create_client(
        api_key="your_key",
        base_url="https://api.example.com/v1",
        use_custom_transport=True
    )
    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": "Hello"}]
    )
"""
import os
import httpx
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class CompatibleTransport(httpx.HTTPTransport):
    """
    自定义传输层（同步），修改 User-Agent 以兼容第三方 API 服务
    """
    def handle_request(self, request):
        # 修改 User-Agent 为通用浏览器标识，避免被识别为 OpenAI SDK
        request.headers['user-agent'] = 'Mozilla/5.0 (compatible; APIClient/1.0)'
        return super().handle_request(request)


class CompatibleAsyncTransport(httpx.AsyncHTTPTransport):
    """
    自定义异步传输层，修改 User-Agent 以兼容第三方 API 服务
    用于异步环境（如 DroidRun 的 MultiDeviceRunner）
    """
    async def handle_async_request(self, request):
        # 修改 User-Agent 为通用浏览器标识，避免被识别为 OpenAI SDK
        request.headers['user-agent'] = 'Mozilla/5.0 (compatible; APIClient/1.0)'
        return await super().handle_async_request(request)


def create_client(
    api_key: str = None,
    base_url: str = None,
    use_custom_transport: bool = True
) -> OpenAI:
    """
    创建 OpenAI 客户端

    Args:
        api_key: API 密钥，默认从环境变量 OPENAI_API_KEY 读取
        base_url: API 基础 URL，默认从环境变量 OPENAI_BASE_URL 读取
        use_custom_transport: 是否使用自定义传输层（用于兼容第三方服务），默认 True

    Returns:
        OpenAI 客户端实例
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    base_url = base_url or os.getenv("OPENAI_BASE_URL")

    if use_custom_transport:
        http_client = httpx.Client(transport=CompatibleTransport())
        return OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
    else:
        return OpenAI(api_key=api_key, base_url=base_url)
