"""内置工具集成测试（Orchestrator 中心调度 + 子 Agent 协作）。

任务：从 2025-07-09 到今天有多少个工作日（考虑中国法定节假日）？
     把结果写入 /data/workspace/ 下。

架构（Hub-and-Spoke）：
    alice(Human)
      ↕ send_message
    orchestrator (规划调度，无业务工具)
      ↕ send_message                        ↕ send_message
    search_agent                           calc_agent
    (datetime_now + bash/curl)             (python_exec)
      ↕ send_message                        ↕ send_message
    bash_agent                            writer_agent
    (bash)                                 (write_file)

所有 sub-agent 的 handsoff 都指向 orchestrator，
由 orchestrator 保存状态、规划下一步、选取 agent。
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.runtime.groupchat import GroupChat
from app.runtime.system import SYSTEM_PARTICIPANT_ID
from app.schemas.agent import AgentProfile, AgentStatus
from app.schemas.model import LLMModel
from app.services.agent_service import create_agent, get_agent

# 导入以触发内置工具注册
import app.tools  # noqa: F401
import app.tools.fs.write_file as _wf_mod  # 用于测试中放宽写入路径限制

import asyncio
from agents import Agent, Runner, set_trace_processors
from langsmith.integrations.openai_agents_sdk import OpenAIAgentsTracingProcessor


set_trace_processors([OpenAIAgentsTracingProcessor()])


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

WORKSPACE_DIR = "/data/workspace"
OUTPUT_FILE = os.path.join(WORKSPACE_DIR, "workdays_result.txt")


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


# ----------------------------------f-----------------------------------------
# Agent Profile 定义
# ---------------------------------------------------------------------------

def _build_profiles(llm: LLMModel) -> list[AgentProfile]:
    """构建 1 个 Orchestrator + 4 个子 Agent 的 Profile。

    所有 Sub-Agent 的 handsoff 都指向 orchestrator。
    Orchestrator 的 handsoff 包含所有 Sub-Agent + alice。
    """

    # =====================================================================
    # Orchestrator — 中央调度器
    # =====================================================================
    orchestrator = AgentProfile(
        agent_id="orchestrator",
        name="Orchestrator",
        role="orchestrator",
        system_prompt=(
            "你是任务编排调度器（Orchestrator）。你没有业务工具，只有 send_message。\n"
            "你的职责是：接收任务 → 拆解步骤 → 逐步调度子 Agent → 汇总结果 → 报告给用户。\n\n"
            "## 可用的子 Agent\n"
            "| agent_id      | 能力                      | 说明                                    |\n"
            "| ------------- | ------------------------- | --------------------------------------- |\n"
            "| search_agent  | datetime_now + bash (curl) | 获取当前时间，联网搜索并整理信息          |\n"
            "| calc_agent    | python_exec               | 执行 Python 代码进行计算                 |\n"
            "| bash_agent   | bash                      | 执行 Shell 命令（创建目录等）             |\n"
            "| writer_agent  | write_file                | 写入文件                                 |\n\n"
            "## 工作流程\n"
            "1. 收到任务后，先分析需要哪些步骤，确定调度顺序。\n"
            "2. 每次只调度一个子 Agent：用 send_message 发送明确的指令。\n"
            "   - 指令中必须包含子 Agent 完成任务所需的全部上下文信息。\n"
            "   - 指令中必须说明：'完成后请把结果发回给 orchestrator'。\n"
            "3. 收到子 Agent 的回复后，检查结果是否符合预期。\n"
            "   - 如果失败或不完整，可以重试或调度其他 Agent 补充。\n"
            "   - 如果两次重试或调度失败，直接放弃，向 alice 发送失败报告。\n"
            "4. 将上一步的结果作为上下文，传递给下一步的子 Agent。\n"
            "5. 所有步骤完成后，用 send_message 向 alice 发送最终汇总报告。\n\n"
            "## 重要规则\n"
            "- 每次 send_message 只发给一个目标。\n"
            "- 你自己不执行任何计算/搜索/文件操作，全部委托给子 Agent。\n"
            "- 保持对整体进度的追踪，在每次调度时说明当前是第几步。\n"
            "- 最终报告发给 alice 时，包含完整的任务结果。"
        ),
        tools=["runtime.send_message"],
        skills=[],
        handsoff=[
            "search_agent", "calc_agent",
            "bash_agent", "writer_agent", "alice",
        ],
        model=llm,
        status=AgentStatus.TESTING,
    )

    # =====================================================================
    # Sub-Agents — handsoff 仅指向 orchestrator
    # =====================================================================

    search_agent = AgentProfile(
        agent_id="search_agent",
        name="SearchAgent",
        role="search_utility",
        system_prompt = (
        "你是信息获取与整理工具人。你拥有 datetime_now 和 bash 两个工具。\n\n"
        "配置：\n"
        "- Tavily API Key: 从环境变量 $TAVILY_API_KEY 获取（用于 HTTP Authorization Header）\n"
        "- Tavily API Endpoint: https://api.tavily.com/search\n\n"
        "工作方式：\n"
        "### 第一步：获取当前时间\n"
        "调用 datetime_now(tz_offset_hours=8) 获取北京时间的当前日期。\n\n"
        "### 第二步：联网搜索\n"
        "根据指令构造 curl 命令调用 Tavily API 进行搜索，要求：\n"
        "- 使用 POST 方法\n"
        "- 设置 Header: Authorization: Bearer $TAVILY_API_KEY\n"
        "- 设置 Header: Content-Type: application/json\n"
        "- 请求体中不包含 api_key 字段\n"
        "- 请求体示例结构如下：\n"
        "{\n"
        "  \"query\": \"搜索关键词\",\n"
        "  \"search_depth\": \"advanced\",\n"
        "  \"max_results\": 5\n"
        "}\n\n"
        "### 第三步：整理信息\n"
        "从搜索结果返回的 JSON 中提取关键信息，整理成列表：\n"
        "- 去除无关内容和广告噪声\n"
        "- 列表的每一项标注具体日期，使用 YYYY-MM-DD 格式\n"
        "### 第四步：回报\n"
        "将【当前日期】和【整理后的信息列表】通过 send_message 发回给 orchestrator。\n\n"
        "注意：\n"
        "- 仅负责获取时间、联网搜索和信息整理\n"
        "- 不做任何推理、计算或最终判断\n"
    ),

        tools=["util.datetime_now", "shell.bash", "runtime.send_message"],
        skills=[],
        handsoff=["orchestrator"],
        model=llm,
        status=AgentStatus.TESTING,
    )

    calc_agent = AgentProfile(
        agent_id="calc_agent",
        name="CalcAgent",
        role="python_interpreter",
        system_prompt=(
            "你是 Python 计算工具人。你只有 python_exec 工具。\n\n"
            "工作方式：\n"
            "1. 收到计算指令后，根据指令中提供的数据编写 Python 代码。\n"
            "2. 代码必须使用 print() 输出结果。\n"
            "3. 只使用 Python 标准库，不要 import numpy 等第三方包。\n"
            "4. 将代码执行结果通过 send_message 发回给 orchestrator。\n"
            "5. 不要自己编造数据，只使用指令中提供的数据。"
        ),
        tools=["shell.python", "runtime.send_message"],
        skills=[],
        handsoff=["orchestrator"],
        model=llm,
        status=AgentStatus.TESTING,
    )

    bash_agent = AgentProfile(
        agent_id="bash_agent",
        name="BashAgent",
        role="shell_operator",
        system_prompt=(
            "你是 Shell 运维工具人。你通过 bash 工具执行系统命令。\n\n"
            "工作方式：\n"
            "1. 收到指令后，执行对应的 bash 命令。\n"
            "2. 将执行结果（成功/失败、输出信息）通过 send_message 发回给 orchestrator。\n"
            "3. 不要做任何超出指令范围的操作。"
        ),
        tools=["shell.bash", "runtime.send_message"],
        skills=[],
        handsoff=["orchestrator"],
        model=llm,
        status=AgentStatus.TESTING,
    )

    writer_agent = AgentProfile(
        agent_id="writer_agent",
        name="WriterAgent",
        role="file_io",
        system_prompt=(
            "你是文件写入工具人。你只有 write_file 工具。\n\n"
            "工作方式：\n"
            "1. 从收到的指令中提取目标文件路径 (path) 和写入内容 (content)。\n"
            "2. 调用 write_file 执行写入。\n"
            "3. 将写入结果（成功/失败、文件路径）通过 send_message 发回给 orchestrator。\n"
            "4. 不要修改需要写入的内容。"
        ),
        tools=["fs.write_file", "runtime.send_message"],
        skills=[],
        handsoff=["orchestrator"],
        model=llm,
        status=AgentStatus.TESTING,
    )

    return [orchestrator, search_agent, calc_agent, bash_agent, writer_agent]


# ---------------------------------------------------------------------------
# 测试：Orchestrator 调度多 Agent 协作
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_workdays_pipeline() -> None:
    """Orchestrator 中心调度 4 个子 Agent 完成工作日计算任务。

    调度流程（由 Orchestrator LLM 自主规划）：
        alice → orchestrator → search_agent → orchestrator
             → calc_agent → orchestrator → bash_agent → orchestrator
             → writer_agent → orchestrator → alice

    Orchestrator 负责：
    - 保存每步的中间状态
    - 根据子 Agent 返回结果决定下一步调度哪个 Agent
    - 将上下文信息传递给下一个子 Agent
    - 最终汇总结果报告给 Human
    """

    async_session = await _prepare_db()
    llm = _get_llm()
    profiles = _build_profiles(llm)

    # --- 放宽 fs.write_file 的写入路径限制（测试环境） ---
    original_root = _wf_mod._DEFAULT_ALLOWED_ROOT
    _wf_mod._DEFAULT_ALLOWED_ROOT = "/data"

    # 清理上次运行残留
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    try:
        # --- 持久化 Agent 到数据库 ---
        async with async_session() as session:
            for profile in profiles:
                await create_agent(session, profile)

        # --- 从数据库加载 Agent ---
        loaded_profiles: list[AgentProfile] = []
        async with async_session() as session:
            for profile in profiles:
                loaded = await get_agent(session, profile.agent_id)
                loaded_profiles.append(loaded)

        # --- 创建 GroupChat 运行时 ---
        # Orchestrator 模式下消息轮次更多（每个子 Agent 至少 2 轮来回）
        runtime = GroupChat(max_turns=80)

        for lp in loaded_profiles:
            runtime.create_agent_from_profile(lp)

        human = runtime.add_human("alice", display_name="Alice")

        # --- Human 向 Orchestrator 发起任务 ---
        task_msg = (
            "请帮我完成以下任务：\n"
            "1. 获取今天的日期，并搜索 2025年7月 到今天期间的中国法定节假日和调休安排\n"
            "2. 根据搜索到的节假日数据，计算从 2025-07-09 到今天的实际工作日数"
            "（排除周末和法定节假日，加上调休上班日）\n"
            f"3. 确保目录 {WORKSPACE_DIR} 存在\n"
            f"4. 将计算结果写入 {OUTPUT_FILE}\n\n"
            "请协调你的子 Agent 完成以上步骤。"
        )
        runtime.message_queue.append(("alice", task_msg, "orchestrator"))
        print(f"\n{'='*60}")
        print(f"[alice -> orchestrator] {task_msg}")
        print(f"{'='*60}")

        # --- 运行消息队列 ---
        await runtime.drain_queue()

        # -----------------------------------------------------------------
        # 验证结果
        # -----------------------------------------------------------------

        # 1. System 日志
        system_history = runtime.system.get_history()
        print(f"\n--- System 收到 {len(system_history)} 条消息 ---")
        for msg in system_history:
            print(f"  [SYSTEM] from {msg.sender}: {msg.content[:200]}")

        # 2. Human 收到的待处理消息（Orchestrator 最终汇报）
        pending = human.get_pending_requests()
        print(f"\n--- Human 待处理 {len(pending)} 条消息 ---")
        for req_id, req in pending.items():
            print(f"  [{req_id}] from {req.message.sender}: "
                  f"{req.message.content[:300]}")

        # 3. 输出文件
        print(f"\n--- 输出文件检查 ---")
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                file_content = f.read()
            print(f"  [OK] 文件存在: {OUTPUT_FILE}")
            print(f"  [OK] 内容:\n{file_content}")
            assert len(file_content) > 0, "输出文件不应为空"
            assert any(c.isdigit() for c in file_content), \
                "输出文件应包含数字（工作日数）"
        else:
            print(f"  [WARN] 文件未找到: {OUTPUT_FILE}")

        # 4. 消息流转历史
        print(f"\n--- 消息历史 ({len(runtime.message_history)} 条) ---")
        for i, msg in enumerate(runtime.message_history, 1):
            direction = f"{msg.sender} -> {msg.target}" if msg.target else msg.sender
            print(f"  {i}. [{msg.role.value}] {direction}: "
                  f"{msg.content[:120]}")

        # 5. 关键断言
        senders = {msg.sender for msg in runtime.message_history}
        targets = {msg.target for msg in runtime.message_history if msg.target}
        all_participants = senders | targets
        print(f"\n--- 参与者覆盖 ---")
        print(f"  发送者: {senders}")
        print(f"  接收者: {targets}")

        # Orchestrator 必须参与调度
        assert "orchestrator" in senders, \
            "orchestrator 应作为调度中心发送消息"
        assert "orchestrator" in targets, \
            "orchestrator 应作为调度中心接收消息"

        # 至少部分子 Agent 应被调度到
        sub_agents_involved = {"search_agent", "calc_agent"} & all_participants
        assert len(sub_agents_involved) >= 1, \
            "至少 search_agent 或 calc_agent 应被 orchestrator 调度"

    finally:
        # 恢复原始允许路径
        _wf_mod._DEFAULT_ALLOWED_ROOT = original_root


