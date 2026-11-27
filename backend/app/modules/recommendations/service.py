from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.projects import repository
from app.modules.projects.service import project_response
from app.modules.recommendations.schemas import ProjectRecommendation, RecommendedProjects
from app.modules.recommendations.scoring import Preferences, score_project
from app.modules.users.service import read_me

RECOMMENDATION_LIMIT = 10


def recommend(session: Session, user_id: UUID) -> RecommendedProjects:
    user = read_me(session, user_id)
    profile = user.profile
    preferences = Preferences(
        skills=frozenset(item.skill_id for item in user.skills),
        interests=frozenset(item.interest_id for item in user.interests),
        availability_hours=profile.availability_hours if profile else None,
        experience_years=profile.experience_years if profile else None,
    )
    missing = preferences.missing_fields()
    if len(missing) == 4:
        return RecommendedProjects(items=[], missing_fields=missing)
    ranked = []
    for project, count in repository.recommendation_candidates(session, user_id):
        match = score_project(project, preferences)
        if match.score > 0:
            ranked.append((project, count, match))
    ranked.sort(key=lambda item: (-item[2].score, item[0].id))
    return RecommendedProjects(
        items=[
            ProjectRecommendation(
                project=project_response(project, count),
                score=match.score,
                reasons=match.reasons,
                cautions=match.cautions,
            )
            for project, count, match in ranked[:RECOMMENDATION_LIMIT]
        ],
        missing_fields=missing,
    )
