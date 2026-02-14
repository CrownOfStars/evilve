# tests/unit/test_skill_management.py

import os
import shutil
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.skill_service import SkillManager
from app.api.skills import get_manager  # 假设你按照建议在 api/skill.py 中定义了这个依赖

# =======================
# Fixtures (测试准备)
# =======================

@pytest.fixture
def mock_skill_dir(tmp_path):
    """
    创建一个临时的 skills 目录结构，包含两个测试 Skill。
    结构:
    /tmp/skills/
      ├── skill_a/
      │   └── Skill.md
      └── skill_b/
          └── Skill.md
    """
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    # 创建 Skill A
    skill_a_dir = skills_root / "skill_a"
    skill_a_dir.mkdir()
    (skill_a_dir / "Skill.md").write_text(
        "---\nname: skill_a\ndescription: Description for A\n---\n# Body A",
        encoding="utf-8"
    )

    # 创建 Skill B
    skill_b_dir = skills_root / "skill_b"
    skill_b_dir.mkdir()
    (skill_b_dir / "Skill.md").write_text(
        "---\nname: skill_b\ndescription: Description for B\n---\n# Body B",
        encoding="utf-8"
    )

    return str(skills_root)

@pytest.fixture
def manager(mock_skill_dir):
    """基于临时目录初始化 SkillManager"""
    return SkillManager(skill_dir=mock_skill_dir)

@pytest.fixture
def client(manager):
    """
    创建一个 TestClient，并覆盖 get_manager 依赖。
    这样 API 测试时会使用我们基于临时目录创建的 manager。
    """
    app.dependency_overrides[get_manager] = lambda: manager
    with TestClient(app) as c:
        yield c
    # 清理 override，避免影响其他测试
    app.dependency_overrides.clear()

# =======================
# Service 层测试
# =======================

def test_manager_load_skills(manager):
    """测试 Manager 初始化时是否正确加载了所有 Skills"""
    skills = manager.list_skills()
    assert len(skills) == 2
    
    # 验证名称是否正确加载
    names = {s.metadata.name for s in skills}
    assert "skill_a" in names
    assert "skill_b" in names

def test_manager_get_skill(manager):
    """测试获取单个 Skill"""
    skill = manager.get_skill("skill_a")
    assert skill is not None
    assert skill.metadata.name == "skill_a"
    assert skill.metadata.description == "Description for A"
    assert "Body A" in skill.body_markdown

def test_manager_get_non_existent_skill(manager):
    """测试获取不存在的 Skill"""
    skill = manager.get_skill("skill_ghost")
    assert skill is None

def test_manager_reload(manager, mock_skill_dir):
    """测试热重载功能"""
    # 初始状态有 2 个
    assert len(manager.list_skills()) == 2
    
    # 在运行时动态添加一个新的 Skill C
    skill_c_dir = os.path.join(mock_skill_dir, "skill_c")
    os.makedirs(skill_c_dir)
    with open(os.path.join(skill_c_dir, "Skill.md"), "w", encoding="utf-8") as f:
        f.write("---\nname: skill_c\ndescription: C\n---\n# Body C")
    
    # 调用重载
    manager.reload_skills()
    
    # 验证现在有 3 个
    assert len(manager.list_skills()) == 3
    assert manager.get_skill("skill_c") is not None

# =======================
# API 层测试
# =======================

def test_api_list_skills(client):
    """测试 GET /skills"""
    print("client 类型:", type(client))
    print("client.base_url:", getattr(client, "base_url", "N/A"))
    print("client.app:", getattr(client, "app", "N/A"))
    # 如果想看路由表
    print("注册的路由:")
    for r in client.app.routes:
        print(" ", r.name, r.path, r.methods)
    response = client.get("/api/v1/skills")   # 确保这里与 router 的 prefix 完全一致
    print("GET /skills -> status:", response.status_code)
    if response.status_code != 200:
        print("response.text:", response.text)
    assert response.status_code == 200

def test_api_get_skill_detail(client):
    """测试 GET /skills/{name}"""
    response = client.get("/api/v1/skills/skill_a")
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["name"] == "skill_a"
    assert data["body_markdown"].strip() == "# Body A"

def test_api_get_skill_not_found(client):
    """测试 GET /skills/{name} 404 情况"""
    response = client.get("/api/v1/skills/skill_unknown")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_api_reload(client):
    """测试 POST /skills/reload"""
    response = client.post("/api/v1/skills/reload")
    assert response.status_code == 200
    assert response.json()["message"] == "Skills reloaded"