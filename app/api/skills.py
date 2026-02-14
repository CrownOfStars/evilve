# app/api/skill.py (新建文件)

from fastapi import APIRouter, HTTPException, Depends
from app.schemas.skill import SkillSchema
from app.services.skill_service import skill_manager, SkillManager

router = APIRouter(prefix="/skills", tags=["Skills"])

def get_manager() -> SkillManager:
    return skill_manager

@router.get("/", response_model=list[SkillSchema])
async def list_skills(
    manager: SkillManager = Depends(get_manager)
):
    """获取所有可用技能列表"""
    return manager.list_skills()

@router.get("/{skill_name}", response_model=SkillSchema)
async def get_skill(
    skill_name: str,
    manager: SkillManager = Depends(get_manager)
):
    """获取指定技能的详细内容"""
    skill = manager.get_skill(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    return skill

@router.post("/reload")
async def reload_skills(
    manager: SkillManager = Depends(get_manager)
):
    """强制重新加载技能（用于开发调试）"""
    manager.reload_skills()
    return {"message": "Skills reloaded", "count": len(manager.list_skills())}