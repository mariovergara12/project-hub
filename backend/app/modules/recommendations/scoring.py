from dataclasses import dataclass
from fractions import Fraction
from uuid import UUID

from app.models import Project
from app.modules.recommendations.schemas import ProfileField

# Fixed points, not a probability. Unknown values earn no points.
SKILL_POINTS = 50
INTEREST_POINTS = 25
AVAILABILITY_POINTS = 15
EXPERIENCE_POINTS = 10


@dataclass(frozen=True)
class Preferences:
    skills: frozenset[UUID]
    interests: frozenset[UUID]
    availability_hours: int | None
    experience_years: int | None

    def missing_fields(self) -> list[ProfileField]:
        missing: list[ProfileField] = []
        if not self.skills:
            missing.append("skills")
        if not self.interests:
            missing.append("interests")
        if self.availability_hours is None:
            missing.append("availability_hours")
        if self.experience_years is None:
            missing.append("experience_years")
        return missing


@dataclass(frozen=True)
class Match:
    score: int
    reasons: list[str]
    cautions: list[str]


def names(values: list[str]) -> str:
    ordered = sorted(values)
    return ", ".join(ordered[:3]) + (f" (+{len(ordered) - 3} more)" if len(ordered) > 3 else "")


def score_project(project: Project, preferences: Preferences) -> Match:
    points = Fraction(0)
    reasons, cautions = [], []
    skills = project.skills
    if skills:
        weight = sum(2 if item.required else 1 for item in skills)
        shared = [item for item in skills if item.skill_id in preferences.skills]
        matched_weight = sum(2 if item.required else 1 for item in shared)
        points += Fraction(SKILL_POINTS * matched_weight, weight)
        if shared:
            reasons.append("Shared skills: " + names([item.skill.name for item in shared]))
        missing = [
            item.skill.name
            for item in skills
            if item.required and item.skill_id not in preferences.skills
        ]
        if missing:
            cautions.append("Required skills not listed: " + names(missing))
    interests = project.interests
    if interests:
        shared_interests = [
            item.interest.name for item in interests if item.interest_id in preferences.interests
        ]
        points += Fraction(INTEREST_POINTS * len(shared_interests), len(interests))
        if shared_interests:
            reasons.append("Shared interests: " + names(shared_interests))
    hours = project.weekly_hours
    available = preferences.availability_hours
    if hours is not None and available is not None:
        if available >= hours:
            points += AVAILABILITY_POINTS
            reasons.append(f"Time: {hours} hrs/week fits your availability")
        else:
            cautions.append(f"Time: needs {hours} hrs/week; you listed {available}")
    minimum = project.minimum_experience_years
    experience = preferences.experience_years
    if minimum is not None and experience is not None:
        if experience >= minimum:
            points += EXPERIENCE_POINTS
            reasons.append(
                "No prior experience required"
                if minimum == 0
                else f"Experience: meets the {minimum}-year minimum"
            )
        else:
            cautions.append(f"Experience: needs {minimum} years; you listed {experience}")
    # Round half up using exact arithmetic, then sort integer-score ties by UUID.
    return Match(int(points + Fraction(1, 2)), reasons, cautions)
