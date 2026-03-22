from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Keep for backwards compatibility / AI assistant reference
DEFAULT_COLUMN_IDS = (
    "col-backlog",
    "col-discovery",
    "col-progress",
    "col-review",
    "col-done",
)

# M7: Shared ChatRole type
ChatRole = Literal["user", "assistant"]

_MAX_CARDS_PER_BOARD = 200
_MAX_COLUMNS_PER_BOARD = 20
_MIN_COLUMNS_PER_BOARD = 1
_MAX_LABELS_PER_BOARD = 50

LABEL_COLORS = (
    "red", "orange", "yellow", "green", "blue", "indigo", "purple", "pink",
)


class LabelPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str = Field(max_length=50)
    color: str = Field(max_length=20)


class CardPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = Field(max_length=500)
    details: str = Field(default="", max_length=5000)
    priority: Literal["low", "medium", "high"] | None = None
    due_date: str | None = Field(default=None, max_length=10)
    assignee: str | None = Field(default=None, max_length=100)
    label_ids: list[str] = Field(default_factory=list)


class ColumnPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    cardIds: list[str]


class BoardPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: list[ColumnPayload]
    cards: dict[str, CardPayload]
    labels: list[LabelPayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_kanban_structure(self) -> BoardPayload:
        if len(self.cards) > _MAX_CARDS_PER_BOARD:
            raise ValueError(
                f"Board cannot have more than {_MAX_CARDS_PER_BOARD} cards."
            )

        if len(self.columns) < _MIN_COLUMNS_PER_BOARD:
            raise ValueError(
                f"Board must have at least {_MIN_COLUMNS_PER_BOARD} column."
            )

        if len(self.columns) > _MAX_COLUMNS_PER_BOARD:
            raise ValueError(
                f"Board cannot have more than {_MAX_COLUMNS_PER_BOARD} columns."
            )

        column_ids = [column.id for column in self.columns]
        unique_column_ids = set(column_ids)

        if len(column_ids) != len(unique_column_ids):
            raise ValueError("Column IDs must be unique.")

        all_column_card_ids: list[str] = []
        for column in self.columns:
            all_column_card_ids.extend(column.cardIds)

        if len(all_column_card_ids) != len(set(all_column_card_ids)):
            raise ValueError("Each card ID must appear in at most one column.")

        unknown_cards = [card_id for card_id in all_column_card_ids if card_id not in self.cards]
        if unknown_cards:
            raise ValueError("Columns reference unknown card IDs.")

        if set(self.cards.keys()) != set(all_column_card_ids):
            raise ValueError("Every card must appear in exactly one column.")

        for card_key, card in self.cards.items():
            if card_key != card.id:
                raise ValueError("Card map keys must match each card object's id.")

        # Label validation
        if len(self.labels) > _MAX_LABELS_PER_BOARD:
            raise ValueError(
                f"Board cannot have more than {_MAX_LABELS_PER_BOARD} labels."
            )

        label_ids = [label.id for label in self.labels]
        if len(label_ids) != len(set(label_ids)):
            raise ValueError("Label IDs must be unique.")

        valid_label_ids = set(label_ids)
        for label in self.labels:
            if label.color not in LABEL_COLORS:
                raise ValueError(
                    f"Invalid label color '{label.color}'. Must be one of: {', '.join(LABEL_COLORS)}."
                )

        for card in self.cards.values():
            for lid in card.label_ids:
                if lid not in valid_label_ids:
                    raise ValueError(
                        f"Card '{card.id}' references unknown label ID '{lid}'."
                    )

        return self


INITIAL_BOARD_DATA: dict[str, Any] = {
    "labels": [],
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {
            "id": "col-progress",
            "title": "In Progress",
            "cardIds": ["card-4", "card-5"],
        },
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
            "priority": "high",
            "due_date": None,
            "assignee": None,
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
            "priority": "medium",
            "due_date": None,
            "assignee": None,
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
            "priority": None,
            "due_date": None,
            "assignee": None,
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
            "priority": "low",
            "due_date": None,
            "assignee": None,
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
            "priority": None,
            "due_date": None,
            "assignee": None,
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
            "priority": "medium",
            "due_date": None,
            "assignee": None,
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
            "priority": None,
            "due_date": None,
            "assignee": None,
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
            "priority": None,
            "due_date": None,
            "assignee": None,
        },
    },
}


def default_board() -> dict[str, Any]:
    return deepcopy(INITIAL_BOARD_DATA)
