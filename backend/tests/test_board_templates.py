"""Tests for board templates."""
from copy import deepcopy
from typing import Any

import pytest

from app.board_templates import TEMPLATES, TEMPLATE_NAMES, get_template_board
from app.kanban import BoardPayload, default_board


class TestTemplateDefinitions:
    @pytest.mark.parametrize("name", TEMPLATE_NAMES)
    def test_template_produces_valid_board_payload(self, name: str):
        board = get_template_board(name)
        payload = BoardPayload.model_validate(board)
        assert payload is not None

    def test_get_template_returns_deep_copy(self):
        board1 = get_template_board("sprint")
        board2 = get_template_board("sprint")
        board1["columns"][0]["title"] = "MUTATED"
        assert board2["columns"][0]["title"] != "MUTATED"

    def test_unknown_template_raises(self):
        with pytest.raises(ValueError, match="Unknown template"):
            get_template_board("nonexistent")

    def test_template_names_list(self):
        assert "empty" in TEMPLATE_NAMES
        assert "sprint" in TEMPLATE_NAMES
        assert "bug_tracker" in TEMPLATE_NAMES
        assert "product_roadmap" in TEMPLATE_NAMES

    def test_empty_template_has_no_cards(self):
        board = get_template_board("empty")
        assert board["cards"] == {}
        assert len(board["columns"]) == 1

    def test_sprint_template_has_labels(self):
        board = get_template_board("sprint")
        assert len(board["labels"]) == 3
        label_names = {lbl["name"] for lbl in board["labels"]}
        assert "Bug" in label_names
        assert "Feature" in label_names

    def test_bug_tracker_has_five_columns(self):
        board = get_template_board("bug_tracker")
        assert len(board["columns"]) == 5


class TestCreateBoardWithTemplate:
    """API-level test for creating a board with a template."""

    def _setup(self, monkeypatch):
        from fastapi.testclient import TestClient
        import app.main as main_module
        from app.config import settings

        class FakeBoardService:
            def __init__(self):
                self._boards: dict[int, dict[str, Any]] = {}
                self._next_id = 1

            def create_board(self, username, name, template=None):
                if template:
                    board = get_template_board(template)
                else:
                    board = default_board()
                board["id"] = self._next_id
                board["name"] = name
                self._boards[self._next_id] = board
                self._next_id += 1
                return board

            def list_boards(self, username):
                return []

            def get_board(self, username, board_id=None):
                return self._boards.get(board_id)

            def save_board(self, username, board, board_id=None):
                return board

            def delete_board(self, username, board_id):
                return True

            def rename_board(self, username, board_id, name):
                return True

        fake = FakeBoardService()
        monkeypatch.setattr(main_module, "board_service", fake)
        client = TestClient(main_module.app)
        client.cookies.set(settings.auth_cookie_name, settings.sign_session("testuser"))
        return client, fake

    def test_create_board_with_sprint_template(self, monkeypatch):
        client, _ = self._setup(monkeypatch)
        resp = client.post("/api/boards", json={"name": "My Sprint", "template": "sprint"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Sprint"
        col_titles = [c["title"] for c in data["columns"]]
        assert "To Do" in col_titles
        assert "In Progress" in col_titles
        assert "Done" in col_titles

    def test_create_board_with_invalid_template(self, monkeypatch):
        client, _ = self._setup(monkeypatch)
        resp = client.post("/api/boards", json={"name": "Bad", "template": "invalid"})
        assert resp.status_code == 422

    def test_create_board_without_template_uses_default(self, monkeypatch):
        client, _ = self._setup(monkeypatch)
        resp = client.post("/api/boards", json={"name": "Default Board"})
        assert resp.status_code == 201
        data = resp.json()
        col_titles = [c["title"] for c in data["columns"]]
        assert "Backlog" in col_titles
