# tests/integration/test_agent_skill_integration.py

import pytest
from unittest.mock import patch
from app.services.skill_service import SkillManager

# 假设你的 Agent 类定义在 app.runtime.agents
from app.runtime.agents import Agent

# =======================
# 1. 准备测试数据与环境
# =======================

@pytest.fixture
def mock_skill_env(tmp_path):
    """
    在临时目录创建一个测试用的 Skill
    """
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    
    # 创建一个名为 'data_analysis' 的技能
    skill_name = "data_analysis"
    skill_dir = skills_dir / skill_name
    skill_dir.mkdir()
    
    skill_content = """---
name: data_analysis
description: 数据分析能力
---
# Data Analysis Protocol
1. Always check for null values.
2. Use pandas for verification.
    """
    (skill_dir / "Skill.md").write_text(skill_content, encoding="utf-8")
    
    return str(skills_dir)

# =======================
# 2. 测试逻辑
# =======================

def test_agent_initialization_with_skill(mock_skill_env):
    """
    测试：当 Agent 配置了 skill 时，Skill 的内容是否正确注入到了 System Prompt 中。
    """
    
    # 1. 初始化一个指向临时目录的 SkillManager
    test_manager = SkillManager(skill_dir=mock_skill_env)
    
    
    # 2. 验证 Manager 是否加载成功
    assert test_manager.get_skill("data_analysis") is not None


    # 4. 关键步骤：Mock 掉 app.runtime.agents 里的 skill_manager
    # 这样 Agent 运行时就会用我们的 test_manager，而不是去读项目真实的 skills 目录
    with patch("app.runtime.agents.skill_manager", test_manager):
        agent = Agent(name="Analyst_Bot", system_prompt="You are a helpful assistant.", skills=["data_analysis", "non_existent_skill"])

    # 5. 断言验证
    print("\n生成的 System Prompt:\n", agent.system_prompt)

    # A. 验证基础提示词还在
    assert "You are a helpful assistant." in agent.system_prompt
    
    # B. 验证 Skill 标题被注入
    assert "【能力: data_analysis】" in agent.system_prompt
    
    # C. 验证 Skill 正文被注入
    assert "# Data Analysis Protocol" in agent.system_prompt
    assert "Use pandas for verification" in agent.system_prompt
    
    # D. 验证不存在的 Skill 没有导致崩溃或乱入
    assert "non_existent_skill" not in agent.system_prompt 
    # (注意：如果你的代码逻辑是把找不到的skill名也打印进去，这里就要改断言，
    # 但通常设计是忽略找不到的skill)

def test_agent_without_skills():
    """测试没有配置 Skill 的普通 Agent"""

    # 即使不 mock manager，空列表也不应该触发调用
    agent = Agent(name="Chat_Bot", system_prompt="Just chat.")
    
    assert agent.system_prompt == "Just chat."
    assert "### 加载的能力" not in agent.system_prompt