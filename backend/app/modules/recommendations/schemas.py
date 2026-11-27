from typing import Literal

from pydantic import BaseModel, Field

from app.modules.projects.schemas import ProjectResponse

ProfileField = Literal["skills", "interests", "availability_hours", "experience_years"]


class ProjectRecommendation(BaseModel):
    project: ProjectResponse
    score: int = Field(ge=0, le=100)
    reasons: list[str]
    cautions: list[str]


class RecommendedProjects(BaseModel):
    items: list[ProjectRecommendation]
    missing_fields: list[ProfileField]
