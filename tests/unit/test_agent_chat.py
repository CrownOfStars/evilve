"""Agent 之间聊天与工具协作测试（基于 OpenAI Agents SDK）。

核心架构：
- 所有 receive_message 返回 None
- Agent 通过 send_message 工具通信（受 handsoff 约束）
- Human 通过 submit_reply 通信
- System 接收 final_output 和错误信息

测试场景：
1. test_agents_chat_with_tools — Agent 之间通过 LLM 驱动协作
2. test_human_agent_interaction — Human 与 Agent 的完整交互流程
3. test_system_receives_final_output — SYSTEM 接收 Agent 的 final_output
4. test_handsoff_validation — send_message 的 handsoff 校验
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from agents import function_tool

from app.core.config import get_settings
from app.runtime.groupchat import GroupChat
from app.runtime.human import HumanParticipant
from app.runtime.system import SYSTEM_PARTICIPANT_ID, SystemParticipant
from app.schemas.agent import AgentProfile, AgentStatus
from app.schemas.model import LLMModel
from app.schemas.tool import ToolSchema
from app.services.agent_service import create_agent, get_agent
from app.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# 业务工具定义 + 注册到 Registry（使用命名空间）
# ---------------------------------------------------------------------------

@function_tool
def add(a: int, b: int) -> str:
    """Add two integers and return the result."""
    print(f"🔧 [add] {a} + {b} = {a + b}")
    return str(a + b)


@function_tool
def format_reply(topic: str, value: str) -> str:
    """Format a reply message with topic and value."""
    print(f"🔧 [format_reply] {topic}: {value}")
    return f"{topic}: {value}"


# 注册到 ToolRegistry，使 profile.tools 中的 namespace.name 能被解析
ToolRegistry.register(
    ToolSchema(
        tool_id="math.add",
        namespace="math",
        name="Add",
        docstring="Add two integers and return the result.",
    ),
    add,
)

ToolRegistry.register(
    ToolSchema(
        tool_id="text.format_reply",
        namespace="text",
        name="FormatReply",
        docstring="Format a reply message with topic and value.",
    ),
    format_reply,
)


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

async def _prepare_db() -> async_sessionmaker:
    """创建内存数据库并初始化表。"""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    return session_factory


def _get_llm() -> LLMModel:
    """获取测试用 LLMModel。"""

    settings = get_settings()
    return LLMModel(
        model_id=settings.llm_model_name,
        provider="openai",
        display_name="Custom LLM",
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )


# ---------------------------------------------------------------------------
# 测试 1: Agent 之间协作
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agents_chat_with_tools() -> None:
    """两个 Agent 通过 LLM 驱动完成一次对话。

    流程：
    1. Human 发消息给 AgentB（计算 7+5）
    2. AgentB 使用 add 工具计算，通过 send_message 把结果发给 AgentA
    3. AgentA 使用 format_reply 格式化，通过 send_message 把结果发给 Human
    4. Human 收到结果，存入 pending
    5. drain_queue 受 max_turns 保护，不会无限循环
    """

    async_session = await _prepare_db()
    llm = _get_llm()

    agent_a = AgentProfile(
        agent_id="agent_a",
        name="AgentA",
        role="coordinator",
        system_prompt=(
            "你是输出员。当收到计算结果后，使用 format_reply 工具格式化结果，"
            "然后使用 send_message 把格式化后的结果发给 human_user。"
            "你只能给 handsoff 列表中的参与者发消息。"
        ),
        tools=["text.format_reply", "runtime.send_message"],
        skills=[],
        handsoff=["agent_b", "human_user"],
        model=llm,
        status=AgentStatus.TESTING,
    )
    agent_b = AgentProfile(
        agent_id="agent_b",
        name="AgentB",
        role="calculator",
        system_prompt=(
            "你是计算器。收到数学计算请求后，使用 add 工具计算并得到结果。"
            "然后使用 send_message 工具把计算结果发给 agent_a。"
            "你只能给 handsoff 列表中的参与者发消息。"
        ),
        tools=["math.add", "runtime.send_message"],
        skills=[],
        handsoff=["agent_a", "human_user"],
        model=llm,
        status=AgentStatus.TESTING,
    )

    async with async_session() as session:
        await create_agent(session, agent_a)
        await create_agent(session, agent_b)
        loaded_a = await get_agent(session, "agent_a")
        loaded_b = await get_agent(session, "agent_b")

    assert "agent_b" in loaded_a.handsoff
    assert "agent_a" in loaded_b.handsoff

    # 创建运行时（max_turns 保护）
    runtime = GroupChat(max_turns=20)
    runtime.create_agent_from_profile(loaded_a)
    runtime.create_agent_from_profile(loaded_b)

    # SYSTEM 自动注册
    assert SYSTEM_PARTICIPANT_ID in runtime.participants
    assert isinstance(runtime.participants[SYSTEM_PARTICIPANT_ID], SystemParticipant)

    # Human 作为一等参与者加入群聊
    runtime.add_human("human_user", display_name="Alice")
    assert isinstance(runtime.participants["human_user"], HumanParticipant)

    # 人发消息给 AgentB
    runtime.message_queue.append(("human_user", "请帮我计算 7 + 5", loaded_b.agent_id))
    print("[human_user -> AgentB] 请帮我计算 7 + 5")

    # drain_queue 处理所有消息（受 max_turns 保护）
    await runtime.drain_queue()

    # 输出 SYSTEM 收到的消息（final_output / error）
    print("\n--- System messages ---")
    for msg in runtime.system.get_history():
        print(f"  [SYSTEM] from {msg.sender}: {msg.content[:100]}")

    # 输出完整历史
    print("\n--- 消息历史 ---")
    for msg in runtime.message_history:
        print(f"  [{msg.role.value}] {msg.sender} -> {msg.target}: {msg.content[:100]}")

    # 检查 Human 的 pending（Agent 应该通过 send_message 给 human_user 发了结果）
    human = runtime.get_human("human_user")
    pending = human.get_pending_requests()
    print(f"\n--- Human pending: {len(pending)} ---")
    for req_id, req in pending.items():
        print(f"  [{req_id}] from {req.message.sender}: {req.message.content[:100]}")


# ---------------------------------------------------------------------------
# 测试 2: Human ↔ Agent 交互
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_human_agent_interaction() -> None:
    """Human 与 Agent 的完整交互流程。

    1. Human 发消息给 Agent
    2. Agent 处理后通过 send_message 回复 Human → 存入 pending
    3. Human 通过 submit_reply 提交回复 → 入队给 Agent
    4. Agent 再次处理
    """

    async_session = await _prepare_db()
    llm = _get_llm()

    calculator = AgentProfile(
        agent_id="calc_agent",
        name="Calculator",
        role="calculator",
        system_prompt=(
            "你是计算器。收到数学计算请求后，使用 add 工具计算。"
            "计算完成后，使用 send_message 把结果发回给消息的发送者。"
            "你只能给 handsoff 列表中的参与者发消息。"
        ),
        tools=["math.add", "runtime.send_message"],
        skills=[],
        handsoff=["alice"],
        model=llm,
        status=AgentStatus.TESTING,
    )

    async with async_session() as session:
        await create_agent(session, calculator)
        loaded_calc = await get_agent(session, "calc_agent")

    # 创建运行时
    runtime = GroupChat(max_turns=20)
    runtime.create_agent_from_profile(loaded_calc)
    human = runtime.add_human("alice", display_name="Alice")

    # 验证 participants 包含 agent、human、system
    assert "calc_agent" in runtime.participants
    assert "alice" in runtime.participants
    assert SYSTEM_PARTICIPANT_ID in runtime.participants

    # Step 1: Human 发消息给 Agent
    runtime.message_queue.append(("alice", "请计算 3 + 4", "calc_agent"))
    print("[alice -> calc_agent] 请计算 3 + 4")

    # Step 2: drain_queue — Agent 通过 send_message 把结果发给 alice
    await runtime.drain_queue()

    # Step 3: 检查 Human pending
    pending = human.get_pending_requests()
    print(f"\n--- Human pending requests: {len(pending)} ---")
    for req_id, req in pending.items():
        print(f"  [{req_id}] from {req.message.sender}: {req.message.content}")

    # Step 4: Human 提交回复
    if pending:
        first_req_id = next(iter(pending))
        runtime.submit_human_reply("alice", first_req_id, "收到，谢谢！")
        print("[alice] 提交回复: 收到，谢谢！")

        # Step 5: 继续处理队列
        await runtime.drain_queue()

    # 输出完整历史
    print("\n--- 完整消息历史 ---")
    for msg in runtime.message_history:
        print(f"  [{msg.role.value}] {msg.sender} -> {msg.target}: {msg.content[:100]}")

    # SYSTEM 应该收到 Agent 的 final_output
    print(f"\n--- System received: {len(runtime.system.get_history())} messages ---")


# ---------------------------------------------------------------------------
# 测试 3: SYSTEM 接收 final_output
# ---------------------------------------------------------------------------

def test_system_auto_registered() -> None:
    """GroupChat 初始化时自动注册 SYSTEM 参与者。"""

    runtime = GroupChat()
    assert SYSTEM_PARTICIPANT_ID in runtime.participants
    assert isinstance(runtime.system, SystemParticipant)
    assert runtime.system.name == SYSTEM_PARTICIPANT_ID


# ---------------------------------------------------------------------------
# 测试 4: handsoff 校验
# ---------------------------------------------------------------------------

def test_max_turns_configured() -> None:
    """max_turns 参数正确配置。"""

    runtime = GroupChat(max_turns=10)
    assert runtime.max_turns == 10

    runtime_default = GroupChat()
    assert runtime_default.max_turns == 50
