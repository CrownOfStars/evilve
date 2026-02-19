# tests/e2e/test_agents_handoff.py

"""E2E 测试：Agent 之间的 Handoff 协作流程。

通过 GroupChat + AgentProfile 的正规路径创建 Agent，
验证 Searcher → Analyst 的完整 handoff 链路。

前置条件：
- skills/ 目录存在且包含 tavily_web_search / python_sandbox_exec
- LLM API 可访问（通过 .env 或环境变量配置）
- TAVILY_API_KEY 已设置（tavily_web_search 需要）
"""

import os

import pytest

# 触发所有内置工具的 @register_tool 注册（shell.bash, python.sandbox_exec 等）
import app.tools  # noqa: F401

from app.core.config import get_settings
from app.runtime.groupchat import GroupChat
from app.runtime.system import SYSTEM_PARTICIPANT_ID
from app.schemas.agent import AgentProfile, AgentStatus
from app.models.llm_meta import LLMModel
from app.services.skill_service import SkillManager

from agents import Agent, Runner, set_trace_processors
from langsmith.integrations.openai_agents_sdk import OpenAIAgentsTracingProcessor

set_trace_processors([OpenAIAgentsTracingProcessor()])


def _get_llm() -> LLMModel:
    """获取测试用 LLMModel（从环境变量/配置读取）。"""

    settings = get_settings()
    return LLMModel(
        model_id=settings.llm_model_name,
        provider="openai",
        display_name="Test LLM",
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_search_and_analyze_flow():
    """
    场景:
    1. User 问: "搜索一下过去5天微软的股价，并计算平均值"
    2. Searcher (Agent A): 使用 tavily_web_search 技能搜索数据 -> Handoff 给 Analyst
    3. Analyst (Agent B): 使用 python_sandbox_exec 技能计算平均值 -> 返回结果

    验证点:
    - Searcher 通过 send_message 工具将数据 handoff 给 Analyst
    - Analyst 处理数据后将结果输出到 SYSTEM
    - SYSTEM 收到包含数字的最终计算结果
    """

    # 1. 准备环境 —— 检查 skills 目录
    real_skill_dir = os.path.join(os.getcwd(), "skills")
    if not os.path.exists(real_skill_dir):
        pytest.skip("Skills directory not found")

    skill_manager = SkillManager()
    llm = _get_llm()

    # 加载技能（用于注入 AgentProfile）
    tavily_skill = skill_manager.get_skill("tavily_web_search")
    search_summary_skill = skill_manager.get_skill("search_result_refinement")
    python_skill = skill_manager.get_skill("python_sandbox_exec")
    if not tavily_skill:
        pytest.skip("Skill 'tavily_web_search' not found")
    if not python_skill:
        pytest.skip("Skill 'python_sandbox_exec' not found")

    # 2. 定义 AgentProfile（配置层，使用字符串标识工具和技能）
    searcher_profile = AgentProfile(
        agent_id="Searcher",
        name="Searcher",
        role="searcher",
        system_prompt=(
            "You are a Search Specialist. ...\n\n"
            
            "1. **Action: Search**\n"
            "   Use 'tavily_web_search' to retrieve raw data.\n\n"
            
            "2. **Action: Refine & Handoff (The Critical Step)**\n"
            "   Upon receiving search results, DO NOT output raw text or explanations. "
            "   Immediately call the 'send_message' tool and send the result to the Analyst.\n"
            "   **CRITICAL**: The 'content' argument of this tool must NOT be the raw search dump. "
            "   You must apply the [Refinement Guidelines] on the fly to construct a perfectly structured JSON string "
            "   (containing 'refined_summary', 'key_facts', 'sources') and pass that CLEARED data into the tool."
        ),
        tools=["shell.bash", "runtime.send_message"],
        skills=[tavily_skill, search_summary_skill],
        handsoff=["Analyst"],
        model=llm,
        status=AgentStatus.TESTING,
    )

    analyst_profile = AgentProfile(
        agent_id="Analyst",
        name="Analyst",
        role="analyst",
        system_prompt=(
            "You are a Data Analyst. Use 'python_sandbox_exec' skill to calculate statistics. "
            "After calculation, present the final result clearly."
        ),
        tools=["python.sandbox_exec", "runtime.send_message"],
        skills=[python_skill],
        handsoff=["Searcher"],
        model=llm,
        status=AgentStatus.TESTING,
    )

    # 3. 创建 GroupChat 运行时，通过 create_agent_from_profile 注入工具
    runtime = GroupChat(max_turns=30)
    runtime.create_agent_from_profile(searcher_profile)
    runtime.create_agent_from_profile(analyst_profile)

    # 验证参与者已注册
    assert "Searcher" in runtime.participants
    assert "Analyst" in runtime.participants
    assert SYSTEM_PARTICIPANT_ID in runtime.participants

    # 4. 开始执行流程
    query = "Search for Microsoft stock price history for last 5 days."
    print(f"\n[User] {query}")

    

    # 将用户消息入队给 Searcher，然后 drain_queue 自动驱动整个 handoff 链路
    runtime.message_queue.append(("User", query, "Searcher"))
    await runtime.drain_queue()

    # 5. 验证结果
    # 检查消息历史中是否有 Searcher -> Analyst 的 handoff
    handoff_found = False
    for msg in runtime.message_history:
        if msg.sender == "Searcher" and msg.target == "Analyst":
            handoff_found = True
            print(f"\n[Handoff] Searcher -> Analyst. Data Length: {len(msg.content)}")
            break

    if not handoff_found:
        # 输出调试信息
        print("\n--- 消息历史 ---")
        for msg in runtime.message_history:
            print(f"  [{msg.role.value}] {msg.sender} -> {msg.target}: {msg.content[:120]}")
        print("\n--- System messages ---")
        for msg in runtime.system.get_history():
            print(f"  [SYSTEM] from {msg.sender}: {msg.content[:200]}")
        pytest.fail("Searcher failed to handoff data to Analyst")

    # 检查 SYSTEM 是否收到了 Analyst 的最终输出
    system_messages = runtime.system.get_history()
    analyst_output = None
    for msg in system_messages:
        if msg.sender == "Analyst":
            analyst_output = msg.content
            break

    print(f"\n[Result] Analyst Output: {analyst_output}")

    assert analyst_output is not None, "Analyst should produce output to SYSTEM"
    # 验证是否真的执行了 python（结果里通常会有计算出的数字）
    assert any(char.isdigit() for char in analyst_output), (
        "Output should contain calculation numbers"
    )

    # 输出完整消息历史（方便调试）
    print("\n--- 完整消息历史 ---")
    for msg in runtime.message_history:
        print(f"  [{msg.role.value}] {msg.sender} -> {msg.target}: {msg.content[:120]}")
