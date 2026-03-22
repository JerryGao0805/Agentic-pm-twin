"""Tests for label support in kanban models and API."""
from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from app.kanban import BoardPayload, LabelPayload, LABEL_COLORS, default_board


def _make_board(**overrides: Any) -> dict[str, Any]:
    board = default_board()
    board.update(overrides)
    return board


class TestLabelPayload:
    def test_valid_label(self):
        label = LabelPayload(id="lbl-1", name="Bug", color="red")
        assert label.id == "lbl-1"
        assert label.name == "Bug"
        assert label.color == "red"

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            LabelPayload(id="lbl-1", name="x" * 51, color="red")

    def test_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            LabelPayload(id="lbl-1", name="Bug", color="red", unknown="field")


class TestBoardPayloadWithLabels:
    def test_board_with_valid_labels(self):
        board = _make_board(
            labels=[
                {"id": "lbl-1", "name": "Bug", "color": "red"},
                {"id": "lbl-2", "name": "Feature", "color": "blue"},
            ]
        )
        payload = BoardPayload.model_validate(board)
        assert len(payload.labels) == 2
        assert payload.labels[0].name == "Bug"

    def test_board_without_labels_backward_compat(self):
        board = default_board()
        # Remove labels key to test backward compat (default_factory kicks in)
        board.pop("labels", None)
        payload = BoardPayload.model_validate(board)
        assert payload.labels == []

    def test_board_with_empty_labels(self):
        board = _make_board(labels=[])
        payload = BoardPayload.model_validate(board)
        assert payload.labels == []

    def test_invalid_label_color_rejected(self):
        board = _make_board(
            labels=[{"id": "lbl-1", "name": "Bug", "color": "neon"}]
        )
        with pytest.raises(ValidationError, match="Invalid label color"):
            BoardPayload.model_validate(board)

    def test_duplicate_label_ids_rejected(self):
        board = _make_board(
            labels=[
                {"id": "lbl-1", "name": "Bug", "color": "red"},
                {"id": "lbl-1", "name": "Feature", "color": "blue"},
            ]
        )
        with pytest.raises(ValidationError, match="Label IDs must be unique"):
            BoardPayload.model_validate(board)

    def test_too_many_labels_rejected(self):
        board = _make_board(
            labels=[
                {"id": f"lbl-{i}", "name": f"Label {i}", "color": "red"}
                for i in range(51)
            ]
        )
        with pytest.raises(ValidationError, match="more than 50 labels"):
            BoardPayload.model_validate(board)

    def test_all_label_colors_valid(self):
        labels = [
            {"id": f"lbl-{i}", "name": f"Label {i}", "color": color}
            for i, color in enumerate(LABEL_COLORS)
        ]
        board = _make_board(labels=labels)
        payload = BoardPayload.model_validate(board)
        assert len(payload.labels) == len(LABEL_COLORS)


class TestCardLabelIds:
    def test_card_with_valid_label_ids(self):
        board = _make_board(
            labels=[
                {"id": "lbl-1", "name": "Bug", "color": "red"},
                {"id": "lbl-2", "name": "Feature", "color": "blue"},
            ]
        )
        board["cards"]["card-1"]["label_ids"] = ["lbl-1", "lbl-2"]
        payload = BoardPayload.model_validate(board)
        assert payload.cards["card-1"].label_ids == ["lbl-1", "lbl-2"]

    def test_card_with_empty_label_ids(self):
        board = _make_board(
            labels=[{"id": "lbl-1", "name": "Bug", "color": "red"}]
        )
        board["cards"]["card-1"]["label_ids"] = []
        payload = BoardPayload.model_validate(board)
        assert payload.cards["card-1"].label_ids == []

    def test_card_default_label_ids_is_empty(self):
        board = _make_board()
        payload = BoardPayload.model_validate(board)
        assert payload.cards["card-1"].label_ids == []

    def test_card_unknown_label_id_rejected(self):
        board = _make_board(
            labels=[{"id": "lbl-1", "name": "Bug", "color": "red"}]
        )
        board["cards"]["card-1"]["label_ids"] = ["lbl-999"]
        with pytest.raises(ValidationError, match="unknown label ID"):
            BoardPayload.model_validate(board)

    def test_card_label_id_requires_labels_defined(self):
        board = _make_board(labels=[])
        board["cards"]["card-1"]["label_ids"] = ["lbl-1"]
        with pytest.raises(ValidationError, match="unknown label ID"):
            BoardPayload.model_validate(board)


class TestBoardApiLabels:
    """API-level tests for label roundtrip through board save."""

    def _make_fake_board_service(self):
        from app.kanban import default_board as db

        class FakeBoardService:
            def __init__(self):
                self._boards: dict[int, dict[str, Any]] = {}
                self._next_id = 1

            def get_board(self, username, board_id=None):
                if board_id is not None:
                    return deepcopy(self._boards.get(board_id))
                board = db()
                board["id"] = 1
                board["name"] = "Default"
                return board

            def save_board(self, username, board, board_id=None):
                validated = BoardPayload.model_validate(
                    {k: v for k, v in board.items() if k not in ("id", "name")}
                )
                result = validated.model_dump()
                result["id"] = board_id or self._next_id
                result["name"] = board.get("name", "Board")
                if board_id:
                    self._boards[board_id] = result
                else:
                    self._boards[self._next_id] = result
                    self._next_id += 1
                return result

            def list_boards(self, username):
                return [{"id": bid, "name": b.get("name", "Board"), "updated_at": "2026-01-01"} for bid, b in self._boards.items()]

            def create_board(self, username, name, template=None):
                board = db()
                board["id"] = self._next_id
                board["name"] = name
                self._boards[self._next_id] = board
                self._next_id += 1
                return board

            def delete_board(self, username, board_id):
                return self._boards.pop(board_id, None) is not None

            def rename_board(self, username, board_id, name):
                if board_id in self._boards:
                    self._boards[board_id]["name"] = name
                    return True
                return False

        return FakeBoardService()

    def _get_client(self, monkeypatch):
        from fastapi.testclient import TestClient
        import app.main as main_module
        from app.config import settings

        fake = self._make_fake_board_service()
        monkeypatch.setattr(main_module, "board_service", fake)

        client = TestClient(main_module.app)
        client.cookies.set(settings.auth_cookie_name, settings.sign_session("testuser"))
        return client, fake

    def test_save_board_with_labels(self, monkeypatch):
        client, fake = self._get_client(monkeypatch)

        board = default_board()
        board["labels"] = [
            {"id": "lbl-1", "name": "Bug", "color": "red"},
            {"id": "lbl-2", "name": "Feature", "color": "blue"},
        ]
        board["cards"]["card-1"]["label_ids"] = ["lbl-1"]

        resp = client.put("/api/boards/1", json=board)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["labels"]) == 2
        assert data["cards"]["card-1"]["label_ids"] == ["lbl-1"]

    def test_save_board_with_invalid_label_rejected(self, monkeypatch):
        client, fake = self._get_client(monkeypatch)

        board = default_board()
        board["labels"] = [{"id": "lbl-1", "name": "Bug", "color": "neon"}]

        resp = client.put("/api/boards/1", json=board)
        assert resp.status_code == 422
