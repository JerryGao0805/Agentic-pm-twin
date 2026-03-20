import pytest
from pydantic import ValidationError

from app.kanban import BoardPayload, default_board


def test_default_board_passes_validation() -> None:
    payload = BoardPayload.model_validate(default_board())
    assert len(payload.columns) == 5
    assert payload.cards["card-1"].title == "Align roadmap themes"


def test_rejects_column_card_that_does_not_exist() -> None:
    invalid_board = default_board()
    invalid_board["columns"][0]["cardIds"].append("missing-card")

    with pytest.raises(ValidationError):
        BoardPayload.model_validate(invalid_board)


def test_rejects_orphaned_card() -> None:
    invalid_board = default_board()
    removed_card_id = invalid_board["columns"][0]["cardIds"].pop(0)
    assert removed_card_id == "card-1"

    with pytest.raises(ValidationError):
        BoardPayload.model_validate(invalid_board)


def test_accepts_custom_column_ids() -> None:
    board = {
        "columns": [
            {"id": "col-todo", "title": "To Do", "cardIds": ["c1"]},
            {"id": "col-doing", "title": "Doing", "cardIds": []},
            {"id": "col-done", "title": "Done", "cardIds": []},
        ],
        "cards": {
            "c1": {"id": "c1", "title": "A task", "details": "Some details"},
        },
    }
    payload = BoardPayload.model_validate(board)
    assert len(payload.columns) == 3


def test_rejects_empty_columns() -> None:
    board = {
        "columns": [],
        "cards": {},
    }
    with pytest.raises(ValidationError):
        BoardPayload.model_validate(board)


def test_rejects_too_many_columns() -> None:
    columns = [
        {"id": f"col-{i}", "title": f"Col {i}", "cardIds": []}
        for i in range(21)
    ]
    board = {"columns": columns, "cards": {}}
    with pytest.raises(ValidationError):
        BoardPayload.model_validate(board)


def test_rejects_duplicate_column_ids() -> None:
    board = {
        "columns": [
            {"id": "col-a", "title": "A", "cardIds": []},
            {"id": "col-a", "title": "B", "cardIds": []},
        ],
        "cards": {},
    }
    with pytest.raises(ValidationError):
        BoardPayload.model_validate(board)


def test_card_with_priority_and_due_date() -> None:
    board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": ["c1"]},
        ],
        "cards": {
            "c1": {
                "id": "c1",
                "title": "Task",
                "details": "Details",
                "priority": "high",
                "due_date": "2026-03-25",
                "assignee": "alice",
            },
        },
    }
    payload = BoardPayload.model_validate(board)
    assert payload.cards["c1"].priority == "high"
    assert payload.cards["c1"].due_date == "2026-03-25"
    assert payload.cards["c1"].assignee == "alice"


def test_card_with_invalid_priority_rejected() -> None:
    board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": ["c1"]},
        ],
        "cards": {
            "c1": {
                "id": "c1",
                "title": "Task",
                "details": "Details",
                "priority": "critical",
            },
        },
    }
    with pytest.raises(ValidationError):
        BoardPayload.model_validate(board)


def test_card_with_null_optional_fields() -> None:
    board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": ["c1"]},
        ],
        "cards": {
            "c1": {
                "id": "c1",
                "title": "Task",
                "details": "",
                "priority": None,
                "due_date": None,
                "assignee": None,
            },
        },
    }
    payload = BoardPayload.model_validate(board)
    assert payload.cards["c1"].priority is None
    assert payload.cards["c1"].due_date is None


def test_card_without_optional_fields_uses_defaults() -> None:
    board = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": ["c1"]},
        ],
        "cards": {
            "c1": {
                "id": "c1",
                "title": "Task",
                "details": "Details",
            },
        },
    }
    payload = BoardPayload.model_validate(board)
    assert payload.cards["c1"].priority is None
    assert payload.cards["c1"].due_date is None
    assert payload.cards["c1"].assignee is None
