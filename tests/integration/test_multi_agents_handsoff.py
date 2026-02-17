import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.skill_service import SkillManager
from app.runtime.agents import Agent
from app.schemas.runtime import Message

# =======================
# 1. 模拟数据结构
# =======================

class MockRunResult:
    """模拟 Runner.run 的返回值"""
    def __init__(self, final_output):
        self.final_output = final_output

# =======================
# 2. 测试逻辑
# =======================

@pytest.mark.asyncio
async def test_handoff_workflow(tmp_path):
    """
    场景：User -> Analyst (Skill: Analysis) -> Handoff -> Writer (Skill: Writing) -> Result
    """
    
    # --- A. 环境准备 (Skills) ---
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    
    # 创建分析技能
    (skills_root / "data_analysis").mkdir()
    (skills_root / "data_analysis" / "Skill.md").write_text(
        "---\nname: data_analysis\ndescription: Data analysis\n---\n# Analysis Skill\nAnalyze data.", encoding="utf-8"
    )
    
    # 创建写作技能
    (skills_root / "report_writing").mkdir()
    (skills_root / "report_writing" / "Skill.md").write_text(
        "---\nname: report_writing\ndescription: Report writing\n---\n# Writing Skill\nWrite report.", encoding="utf-8"
    )

    skill_manager = SkillManager(skill_dir=str(skills_root))

    # --- B. Agent 初始化 ---
    # 我们需要模拟一个共享的消息队列，Runtime 通常用它来传递消息
    # 格式: list[tuple[sender, content, receiver]]
    message_queue = []

    # 1. Analyst Agent
    with patch("app.runtime.agents.skill_manager", skill_manager):
        # 假设 Agent 初始化时会读取 config 并加载 prompt (你需要根据实际 __init__ 调整)
        # 这里直接模拟构造好的 system_prompt
        agent_analyst = Agent(
            name="Analyst",
            system_prompt="You are an analyst. Skills: # Analysis Skill",
            tools=[], # 实际运行中这里会有 send_message 工具
            message_queue=message_queue
        )

    # 2. Writer Agent
    with patch("app.runtime.agents.skill_manager", skill_manager):
        agent_writer = Agent(
            name="Writer",
            system_prompt="You are a writer. Skills: # Writing Skill",
            tools=[],
            message_queue=message_queue
        )

    # --- C. 执行流程测试 ---
    
    # 这里的关键是 Patch 掉 `app.runtime.agents.Runner.run`
    # 因为 Agent.receive_message 内部调用了它
    with patch("app.runtime.agents.Runner.run", new_callable=AsyncMock) as mock_runner:
        
        # === Round 1: 发送任务给 Analyst ===
        print("\n[Step 1] User sends task to Analyst")
        
        # 1.1 设定 Mock LLM 的行为：Analyst 决定 Handoff
        # 在真实情况中，Runner 会执行 send_message 工具。
        # 在测试中，我们模拟 Runner 返回了 Handoff 的意图或工具调用的结果。
        # 假设 Runner 此时执行了 send_message("Writer", "Data is ready") 并返回了结果
        mock_runner.return_value = MockRunResult(
            final_output="Transferred to Writer: Data average is 42"
        )

        # 1.2 触发 Agent 接收消息
        user_msg = Message(sender="User", content="Analyze data [10, 20, 96]", role="user")
        await agent_analyst.receive_message(user_msg)

        # 1.3 验证 Analyst 确实调用了 Runner
        assert mock_runner.call_count == 1
        # 验证入参包含了发送者信息 (Agent类第83行逻辑)
        call_args = mock_runner.call_args[0]
        assert "[消息来自: User]" in call_args[1] 

        # 1.4 模拟 Handoff 的副作用
        # 在真实系统中，send_message 工具会向 message_queue 写入一条发给 Writer 的消息。
        # 我们这里手动模拟这个“消息路由”的过程，假设 Analyst 产出了给 Writer 的消息。
        handoff_msg = Message(
            sender="Analyst", 
            content="Context: Average is 42. Please write report.", 
            role="assistant"
        )
        print(f"[System] Message routed: {handoff_msg.sender} -> Writer")

        
        # === Round 2: Writer 接手任务 ===
        print("\n[Step 2] Writer receives context")

        # 2.1 更新 Mock LLM 的行为：Writer 产出最终报告
        mock_runner.reset_mock()
        mock_runner.return_value = MockRunResult(
            final_output="REPORT: The average is 42. Market is bullish."
        )

        # 2.2 触发 Writer 接收消息
        await agent_writer.receive_message(handoff_msg)

        # 2.3 验证 Writer 调用了 Runner
        assert mock_runner.call_count == 1
        call_args_2 = mock_runner.call_args[0]
        # 验证 Writer 看到的输入包含了 Analyst 的上下文
        assert "[消息来自: Analyst]" in call_args_2[1]
        assert "Average is 42" in call_args_2[1]

        # === Round 3: 验证结果 ===
        print("\n[Step 3] Verifying Output")
        
        # 验证 Writer 将最终结果放入了 message_queue (发给 SYSTEM)
        # Agent 代码第 96 行: self._enqueue_to_system(final_output)
        
        # 检查队列中是否有 Writer 发出的包含 REPORT 的消息
        found_report = False
        for sender, content, receiver in message_queue:
            if sender == "Writer" and "REPORT" in content:
                found_report = True
                print(f"✅ Found Report in Queue: {content}")
        
        assert found_report, "Writer did not output the report to system queue"