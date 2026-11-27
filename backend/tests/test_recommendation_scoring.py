from uuid import UUID

import pytest

from app.models import Interest, Project, ProjectInterest, ProjectSkill, Skill
from app.modules.recommendations.scoring import Preferences, score_project


def requirements(*, skills=(), interests=(), hours=None, experience=None):
    return Project(
        weekly_hours=hours,
        minimum_experience_years=experience,
        skills=[
            ProjectSkill(
                skill_id=UUID(int=id_), skill=Skill(id=UUID(int=id_), name=name), required=required
            )
            for id_, name, required in skills
        ],
        interests=[
            ProjectInterest(
                interest_id=UUID(int=id_), interest=Interest(id=UUID(int=id_), name=name)
            )
            for id_, name in interests
        ],
    )


def preferences(*, skills=(), interests=(), hours=None, experience=None):
    return Preferences(
        frozenset(UUID(int=id_) for id_ in skills),
        frozenset(UUID(int=id_) for id_ in interests),
        hours,
        experience,
    )


def test_exact_fit_earns_one_hundred_points_with_matching_evidence():
    result = score_project(
        requirements(
            skills=[(1, "react", True)], interests=[(2, "community")], hours=5, experience=2
        ),
        preferences(skills=[1], interests=[2], hours=5, experience=2),
    )
    assert result.score == 100
    assert result.cautions == []
    assert result.reasons == [
        "Shared skills: react",
        "Shared interests: community",
        "Time: 5 hrs/week fits your availability",
        "Experience: meets the 2-year minimum",
    ]


@pytest.mark.parametrize("selected, expected", [([1], 33), ([2], 17), ([1, 2], 50), ([], 0)])
def test_required_skills_count_twice_as_much_as_optional_skills(selected, expected):
    result = score_project(
        requirements(skills=[(1, "python", True), (2, "react", False)]),
        preferences(skills=selected),
    )
    assert result.score == expected
    assert bool(result.cautions) == (1 not in selected)


def test_interest_overlap_is_proportional_and_rounded_half_up():
    project = requirements(interests=[(1, "accessibility"), (2, "education")])
    assert score_project(project, preferences(interests=[1])).score == 13
    assert score_project(project, preferences(interests=[1, 2])).score == 25


def test_missing_user_or_project_values_never_receive_free_points():
    assert (
        score_project(
            requirements(), preferences(skills=[1], interests=[2], hours=20, experience=10)
        ).score
        == 0
    )
    result = score_project(
        requirements(
            skills=[(1, "react", True)], interests=[(2, "education")], hours=0, experience=0
        ),
        preferences(),
    )
    assert result.score == 0 and result.reasons == []
    assert preferences().missing_fields() == [
        "skills",
        "interests",
        "availability_hours",
        "experience_years",
    ]


def test_zero_hours_and_zero_experience_are_known_values():
    prefs = preferences(hours=0, experience=0)
    result = score_project(requirements(hours=0, experience=0), prefs)
    assert result.score == 25 and not result.cautions
    assert prefs.missing_fields() == ["skills", "interests"]
    assert "No prior experience required" in result.reasons


@pytest.mark.parametrize(
    "hours, experience, expected", [(4, 1, 0), (5, 1, 15), (4, 2, 10), (5, 2, 25)]
)
def test_time_and_experience_are_threshold_checks(hours, experience, expected):
    result = score_project(
        requirements(hours=5, experience=2), preferences(hours=hours, experience=experience)
    )
    assert result.score == expected
    assert len(result.cautions) == int(hours < 5) + int(experience < 2)
    assert len(result.reasons) == int(hours >= 5) + int(experience >= 2)


def test_explanations_are_stable_bounded_and_use_catalog_ids():
    skills = [(1, "zoology", True), (2, "react", True), (3, "python", True), (4, "arduino", True)]
    first = score_project(requirements(skills=skills), preferences())
    second = score_project(requirements(skills=list(reversed(skills))), preferences())
    assert first == second
    assert first.cautions == ["Required skills not listed: arduino, python, react (+1 more)"]
    assert (
        score_project(requirements(skills=[(1, "react", True)]), preferences(skills=[2])).score == 0
    )
