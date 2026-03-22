from __future__ import annotations

from copy import deepcopy
from typing import Any


TEMPLATES: dict[str, dict[str, Any]] = {
    "empty": {
        "labels": [],
        "columns": [
            {"id": "col-todo", "title": "To Do", "cardIds": []},
        ],
        "cards": {},
    },
    "sprint": {
        "labels": [
            {"id": "lbl-bug", "name": "Bug", "color": "red"},
            {"id": "lbl-feature", "name": "Feature", "color": "blue"},
            {"id": "lbl-chore", "name": "Chore", "color": "yellow"},
        ],
        "columns": [
            {"id": "col-todo", "title": "To Do", "cardIds": ["card-s1", "card-s2"]},
            {"id": "col-progress", "title": "In Progress", "cardIds": []},
            {"id": "col-done", "title": "Done", "cardIds": []},
        ],
        "cards": {
            "card-s1": {
                "id": "card-s1",
                "title": "Sprint planning",
                "details": "Define sprint goals and assign story points.",
                "priority": "high",
                "due_date": None,
                "assignee": None,
                "label_ids": [],
            },
            "card-s2": {
                "id": "card-s2",
                "title": "Daily standup setup",
                "details": "Schedule recurring standup and set agenda template.",
                "priority": "medium",
                "due_date": None,
                "assignee": None,
                "label_ids": [],
            },
        },
    },
    "bug_tracker": {
        "labels": [
            {"id": "lbl-critical", "name": "Critical", "color": "red"},
            {"id": "lbl-major", "name": "Major", "color": "orange"},
            {"id": "lbl-minor", "name": "Minor", "color": "yellow"},
            {"id": "lbl-ui", "name": "UI", "color": "purple"},
            {"id": "lbl-backend", "name": "Backend", "color": "blue"},
        ],
        "columns": [
            {"id": "col-new", "title": "New", "cardIds": []},
            {"id": "col-triaged", "title": "Triaged", "cardIds": []},
            {"id": "col-progress", "title": "In Progress", "cardIds": []},
            {"id": "col-fixed", "title": "Fixed", "cardIds": []},
            {"id": "col-verified", "title": "Verified", "cardIds": []},
        ],
        "cards": {},
    },
    "product_roadmap": {
        "labels": [
            {"id": "lbl-must", "name": "Must Have", "color": "red"},
            {"id": "lbl-should", "name": "Should Have", "color": "orange"},
            {"id": "lbl-nice", "name": "Nice to Have", "color": "green"},
        ],
        "columns": [
            {"id": "col-ideas", "title": "Ideas", "cardIds": ["card-r1"]},
            {"id": "col-evaluating", "title": "Evaluating", "cardIds": []},
            {"id": "col-planned", "title": "Planned", "cardIds": []},
            {"id": "col-progress", "title": "In Progress", "cardIds": []},
            {"id": "col-shipped", "title": "Shipped", "cardIds": []},
        ],
        "cards": {
            "card-r1": {
                "id": "card-r1",
                "title": "Collect feature requests",
                "details": "Aggregate feedback from customers, sales, and support.",
                "priority": None,
                "due_date": None,
                "assignee": None,
                "label_ids": [],
            },
        },
    },
}

TEMPLATE_NAMES = list(TEMPLATES.keys())


def get_template_board(template_name: str) -> dict[str, Any]:
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")
    return deepcopy(TEMPLATES[template_name])
