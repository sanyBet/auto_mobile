"""
Unit tests for Manager response parsing and LLM response validation.

This test file helps diagnose why Manager response validation fails.
"""

import sys
import asyncio
from pathlib import Path

# Add project root and droidrun to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "droidrun"))

from droidrun.agent.manager.prompts import parse_manager_response


class TestParseManagerResponse:
    """Test the parse_manager_response function."""

    def test_valid_response_with_plan(self):
        """Test parsing a valid response with plan."""
        response = """
<thought>
I need to open the dApp Store first.
</thought>

<plan>
1. Open dApp Store
2. Select an app to install
3. Experience the app
</plan>
"""
        result = parse_manager_response(response)

        print("\n=== Test: valid_response_with_plan ===")
        print(f"Input response:\n{response}")
        print(f"Parsed result: {result}")

        assert result["thought"] == "I need to open the dApp Store first."
        assert "Open dApp Store" in result["plan"]
        assert result["current_subgoal"] == "Open dApp Store"
        assert result["answer"] == ""
        assert result["success"] is None
        print("PASSED")

    def test_valid_response_with_request_accomplished(self):
        """Test parsing a valid response with request_accomplished."""
        response = """
<thought>
Task completed successfully.
</thought>

<request_accomplished success="true">
All dApps have been tested.
</request_accomplished>
"""
        result = parse_manager_response(response)

        print("\n=== Test: valid_response_with_request_accomplished ===")
        print(f"Input response:\n{response}")
        print(f"Parsed result: {result}")

        assert result["answer"] == "All dApps have been tested."
        assert result["success"] is True
        assert result["plan"] == ""
        print("PASSED")

    def test_response_without_plan_or_answer(self):
        """Test response that has neither plan nor request_accomplished."""
        response = """
<thought>
I'm thinking about what to do next.
</thought>
"""
        result = parse_manager_response(response)

        print("\n=== Test: response_without_plan_or_answer ===")
        print(f"Input response:\n{response}")
        print(f"Parsed result: {result}")

        # This should be invalid - no plan and no answer
        assert result["plan"] == ""
        assert result["answer"] == ""
        print("PARSED (but validation should fail)")

    def test_chinese_response(self):
        """Test parsing a response in Chinese."""
        response = """
<thought>
我需要先打开 dApp Store。
</thought>

<plan>
1. 打开 dApp Store
2. 选择一个应用安装
3. 体验应用
</plan>
"""
        result = parse_manager_response(response)

        print("\n=== Test: chinese_response ===")
        print(f"Input response:\n{response}")
        print(f"Parsed result: {result}")

        assert "打开 dApp Store" in result["plan"]
        assert result["current_subgoal"] == "打开 dApp Store"
        print("PASSED")

    def test_response_with_extra_text(self):
        """Test response with extra text outside tags."""
        response = """
Let me analyze the current state.

<thought>
I need to open the dApp Store.
</thought>

Based on my analysis:

<plan>
1. Open dApp Store
2. Install an app
</plan>

This should work well.
"""
        result = parse_manager_response(response)

        print("\n=== Test: response_with_extra_text ===")
        print(f"Input response:\n{response}")
        print(f"Parsed result: {result}")

        assert result["thought"] == "I need to open the dApp Store."
        assert "Open dApp Store" in result["plan"]
        print("PASSED")

    def test_response_with_markdown_formatting(self):
        """Test response where LLM wraps content in markdown code blocks."""
        response = """
```xml
<thought>
I need to open the dApp Store.
</thought>

<plan>
1. Open dApp Store
</plan>
```
"""
        result = parse_manager_response(response)

        print("\n=== Test: response_with_markdown_formatting ===")
        print(f"Input response:\n{response}")
        print(f"Parsed result: {result}")

        # This might fail if LLM wraps in code blocks
        print(f"Plan found: '{result['plan']}'")
        print(f"Thought found: '{result['thought']}'")

    def test_response_without_xml_tags(self):
        """Test response that doesn't use XML tags at all."""
        response = """
I'll help you test the dApp Store.

My plan is:
1. Open dApp Store
2. Install an app
3. Test it

Let me start by clicking on the dApp Store icon.
"""
        result = parse_manager_response(response)

        print("\n=== Test: response_without_xml_tags ===")
        print(f"Input response:\n{response}")
        print(f"Parsed result: {result}")

        # This should fail - no XML tags at all
        assert result["plan"] == ""
        assert result["thought"] == ""
        print("PARSED (no XML tags found)")


def run_parse_tests():
    """Run all parsing tests."""
    print("=" * 60)
    print("Testing parse_manager_response function")
    print("=" * 60)

    test = TestParseManagerResponse()

    try:
        test.test_valid_response_with_plan()
    except AssertionError as e:
        print(f"FAILED: {e}")

    try:
        test.test_valid_response_with_request_accomplished()
    except AssertionError as e:
        print(f"FAILED: {e}")

    try:
        test.test_response_without_plan_or_answer()
    except AssertionError as e:
        print(f"FAILED: {e}")

    try:
        test.test_chinese_response()
    except AssertionError as e:
        print(f"FAILED: {e}")

    try:
        test.test_response_with_extra_text()
    except AssertionError as e:
        print(f"FAILED: {e}")

    try:
        test.test_response_with_markdown_formatting()
    except AssertionError as e:
        print(f"FAILED: {e}")

    try:
        test.test_response_without_xml_tags()
    except AssertionError as e:
        print(f"FAILED: {e}")


async def test_llm_response():
    """Test actual LLM response to see what format it returns."""
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv(project_root / ".env")

    print("\n" + "=" * 60)
    print("Testing actual LLM response with FULL Manager prompt")
    print("=" * 60)

    # Get API config
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower()

    if provider == "packyapi":
        api_base = os.getenv("PACKYAPI_BASE_URL")
        api_key = os.getenv("PACKYAPI_API_KEY")
        model = os.getenv("PACKYAPI_MODEL", "gpt-5.1")
    else:
        api_base = "https://openrouter.ai/api/v1"
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

    print(f"Provider: {provider}")
    print(f"API Base: {api_base}")
    print(f"Model: {model}")

    # Use the UPDATED Manager system prompt with stronger format emphasis
    system_prompt = """You are an agent who can operate an Android phone on behalf of a user. Your goal is to track progress and devise high-level plans to achieve the user's requests.

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

    user_prompt = """<device_state>
App: Quickstep (com.android.launcher3)
Keyboard: hidden

Clickable Elements:
[0] ImageButton: "Search" - (84,189,228,333)
[1] TextView: "Mon, Dec 16" - (84,387,339,456)
[2] TextView: "Camera" - (24,1332,312,1830)
[3] TextView: "Phone" - (312,1332,600,1830)
[4] TextView: "Wallet" - (600,1332,888,1830)
[5] TextView: "dApp Store" - (888,1332,1176,1830)
[6] TextView: "Messages" - (1176,1332,1464,1830)
</device_state>

This is the first step. Please analyze the current state and provide your plan."""

    try:
        from llama_index.llms.openai_like import OpenAILike
        import httpx

        # Check if we need custom transport
        if provider == "packyapi":
            from utils.openai_client import CompatibleAsyncTransport
            async_http_client = httpx.AsyncClient(transport=CompatibleAsyncTransport())
            llm = OpenAILike(
                api_base=api_base,
                api_key=api_key,
                model=model,
                is_chat_model=True,
                async_http_client=async_http_client,
            )
        else:
            llm = OpenAILike(
                api_base=api_base,
                api_key=api_key,
                model=model,
                is_chat_model=True,
            )

        from llama_index.core.llms import ChatMessage, MessageRole

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_prompt),
        ]

        print("\nSending request to LLM...")
        response = await llm.achat(messages)

        raw_response = response.message.content

        print("\n" + "=" * 60)
        print("RAW LLM RESPONSE:")
        print("=" * 60)
        print(raw_response)
        print("=" * 60)

        # Parse the response
        parsed = parse_manager_response(raw_response)

        print("\n" + "=" * 60)
        print("PARSED RESULT:")
        print("=" * 60)
        print(f"thought: '{parsed['thought']}'")
        print(f"plan: '{parsed['plan']}'")
        print(f"current_subgoal: '{parsed['current_subgoal']}'")
        print(f"answer: '{parsed['answer']}'")
        print(f"success: {parsed['success']}")

        # Validate
        print("\n" + "=" * 60)
        print("VALIDATION:")
        print("=" * 60)

        if parsed["answer"] and not parsed["plan"]:
            if parsed["success"] is None:
                print("INVALID: request_accomplished without success attribute")
            else:
                print("VALID: Task completed")
        elif parsed["plan"] and parsed["answer"]:
            print("INVALID: Both plan and request_accomplished present")
        elif not parsed["plan"]:
            print("INVALID: No plan provided (this is the error you're seeing)")
        else:
            print("VALID: Plan provided without request_accomplished")

    except Exception as e:
        print(f"Error testing LLM: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run parsing tests first
    run_parse_tests()

    # Then test actual LLM response
    asyncio.run(test_llm_response())
