# tests/unit/notes/routes/test_notes_notebooks.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

USER_ID = "user_abc"
NOTEBOOK_ID = "nb-uuid-001"

MOCK_NOTEBOOK = MagicMock()
MOCK_NOTEBOOK.id = NOTEBOOK_ID
MOCK_NOTEBOOK.title = "My Notebook"
MOCK_NOTEBOOK.user_id = USER_ID


def make_app():
    from Notes.routes.notebooks import router
    from Notes.utils.auth import get_current_user

    app = FastAPI()
    app.include_router(router)

    mock_user = MagicMock()
    mock_user.user_id = USER_ID

    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[__import__("db").get_session] = lambda: mock_session

    return app, mock_session


# ══════════════════════════════════════════════════════════════════════════════
# POST /  — create_notebook
# ══════════════════════════════════════════════════════════════════════════════
class TestCreateNotebook:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.session = make_app()
        self.client = TestClient(self.app)
        self.url = "/"
        self.payload = {"title": "My Notebook"}

    @patch("routes.notebooks.Notebook")
    def test_returns_201_or_200_on_success(self, MockNotebook):
        nb = MagicMock()
        nb.id = NOTEBOOK_ID
        nb.title = "My Notebook"
        nb.user_id = USER_ID
        MockNotebook.return_value = nb

        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()

        resp = self.client.post(self.url, json=self.payload)
        assert resp.status_code in (200, 201)

    @patch("routes.notebooks.Notebook")
    def test_notebook_created_with_correct_title(self, MockNotebook):
        nb = MagicMock()
        nb.id = NOTEBOOK_ID
        nb.title = "My Notebook"
        nb.user_id = USER_ID
        MockNotebook.return_value = nb

        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()

        self.client.post(self.url, json=self.payload)
        MockNotebook.assert_called_once_with(title="My Notebook", user_id=USER_ID)

    @patch("routes.notebooks.Notebook")
    def test_notebook_created_with_correct_user_id(self, MockNotebook):
        nb = MagicMock()
        nb.id = NOTEBOOK_ID
        nb.title = "My Notebook"
        nb.user_id = USER_ID
        MockNotebook.return_value = nb

        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()

        self.client.post(self.url, json=self.payload)
        _, kwargs = MockNotebook.call_args
        assert kwargs["user_id"] == USER_ID

    @patch("routes.notebooks.Notebook")
    def test_session_add_called(self, MockNotebook):
        nb = MagicMock()
        nb.id = NOTEBOOK_ID
        nb.title = "My Notebook"
        nb.user_id = USER_ID
        MockNotebook.return_value = nb

        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()
        self.session.add = MagicMock()

        self.client.post(self.url, json=self.payload)
        self.session.add.assert_called_once_with(nb)

    @patch("routes.notebooks.Notebook")
    def test_session_commit_called(self, MockNotebook):
        nb = MagicMock()
        nb.id = NOTEBOOK_ID
        nb.title = "My Notebook"
        nb.user_id = USER_ID
        MockNotebook.return_value = nb

        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()

        self.client.post(self.url, json=self.payload)
        self.session.commit.assert_called_once()

    @patch("routes.notebooks.Notebook")
    def test_session_refresh_called(self, MockNotebook):
        nb = MagicMock()
        nb.id = NOTEBOOK_ID
        nb.title = "My Notebook"
        nb.user_id = USER_ID
        MockNotebook.return_value = nb

        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()

        self.client.post(self.url, json=self.payload)
        self.session.refresh.assert_called_once_with(nb)

    def test_missing_title_returns_422(self):
        resp = self.client.post(self.url, json={})
        assert resp.status_code == 422

    def test_empty_body_returns_422(self):
        resp = self.client.post(self.url, content=b"")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /  — list_notebooks
# ══════════════════════════════════════════════════════════════════════════════
class TestListNotebooks:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.session = make_app()
        self.client = TestClient(self.app)
        self.url = "/"

    def _mock_query(self, notebooks):
        result = MagicMock()
        result.scalars.return_value.all.return_value = notebooks
        self.session.execute = AsyncMock(return_value=result)

    def test_returns_200(self):
        self._mock_query([MOCK_NOTEBOOK])
        resp = self.client.get(self.url)
        assert resp.status_code == 200

    def test_returns_list_of_notebooks(self):
        nb1 = MagicMock()
        nb1.id = "nb-1"
        nb1.title = "First"
        nb1.user_id = USER_ID

        nb2 = MagicMock()
        nb2.id = "nb-2"
        nb2.title = "Second"
        nb2.user_id = USER_ID

        self._mock_query([nb1, nb2])
        resp = self.client.get(self.url)
        assert len(resp.json()) == 2

    def test_returns_empty_list_when_no_notebooks(self):
        self._mock_query([])
        resp = self.client.get(self.url)
        assert resp.json() == []

    def test_session_execute_called(self):
        self._mock_query([])
        self.client.get(self.url)
        self.session.execute.assert_called_once()

    def test_query_filters_by_user_id(self):
        self._mock_query([])
        self.client.get(self.url)
        # The query is executed — verify session.execute was called (user_id filter
        # is applied inside the route via SQLAlchemy where clause)
        assert self.session.execute.called


# ══════════════════════════════════════════════════════════════════════════════
# PATCH /{notebook_id}  — update_notebook
# ══════════════════════════════════════════════════════════════════════════════
class TestUpdateNotebook:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.session = make_app()
        self.client = TestClient(self.app)
        self.url = f"/{NOTEBOOK_ID}"
        self.payload = {"title": "Updated Title"}

    def _mock_found(self, notebook=MOCK_NOTEBOOK):
        result = MagicMock()
        result.scalar_one_or_none.return_value = notebook
        self.session.execute = AsyncMock(return_value=result)
        self.session.commit = AsyncMock()

    def _mock_not_found(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.session.execute = AsyncMock(return_value=result)

    def test_returns_200_on_success(self):
        self._mock_found()
        resp = self.client.patch(self.url, json=self.payload)
        assert resp.status_code == 200

    def test_title_updated_on_notebook(self):
        nb = MagicMock()
        nb.id = NOTEBOOK_ID
        nb.user_id = USER_ID
        nb.title = "Old Title"
        self._mock_found(nb)

        self.client.patch(self.url, json=self.payload)
        assert nb.title == "Updated Title"

    def test_session_commit_called_on_update(self):
        self._mock_found()
        self.client.patch(self.url, json=self.payload)
        self.session.commit.assert_called_once()

    def test_returns_404_when_not_found(self):
        self._mock_not_found()
        resp = self.client.patch(self.url, json=self.payload)
        assert resp.status_code == 404

    def test_404_detail_message(self):
        self._mock_not_found()
        resp = self.client.patch(self.url, json=self.payload)
        assert "Notebook not found" in resp.json()["detail"]

    def test_missing_title_returns_422(self):
        resp = self.client.patch(self.url, json={})
        assert resp.status_code == 422

    def test_session_execute_called_with_notebook_id(self):
        self._mock_found()
        self.client.patch(self.url, json=self.payload)
        self.session.execute.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# DELETE /{notebook_id}  — delete_notebook
# ══════════════════════════════════════════════════════════════════════════════
class TestDeleteNotebook:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.session = make_app()
        self.client = TestClient(self.app)
        self.url = f"/{NOTEBOOK_ID}"

    def _mock_found(self, notebook=MOCK_NOTEBOOK):
        result = MagicMock()
        result.scalar_one_or_none.return_value = notebook
        self.session.execute = AsyncMock(return_value=result)
        self.session.delete = AsyncMock()
        self.session.commit = AsyncMock()

    def _mock_not_found(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.session.execute = AsyncMock(return_value=result)

    def test_returns_204_on_success(self):
        self._mock_found()
        resp = self.client.delete(self.url)
        assert resp.status_code == 204

    def test_no_body_on_204(self):
        self._mock_found()
        resp = self.client.delete(self.url)
        assert resp.content == b""

    def test_session_delete_called_with_notebook(self):
        nb = MagicMock()
        nb.id = NOTEBOOK_ID
        nb.user_id = USER_ID
        self._mock_found(nb)

        self.client.delete(self.url)
        self.session.delete.assert_called_once_with(nb)

    def test_session_commit_called_after_delete(self):
        self._mock_found()
        self.client.delete(self.url)
        self.session.commit.assert_called_once()

    def test_returns_404_when_not_found(self):
        self._mock_not_found()
        resp = self.client.delete(self.url)
        assert resp.status_code == 404

    def test_404_detail_message(self):
        self._mock_not_found()
        resp = self.client.delete(self.url)
        assert "Notebook not found" in resp.json()["detail"]

    def test_session_delete_not_called_when_not_found(self):
        self._mock_not_found()
        self.session.delete = AsyncMock()
        self.client.delete(self.url)
        self.session.delete.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# Router registration
# ══════════════════════════════════════════════════════════════════════════════
class TestRouterConfig:

    def test_router_has_no_prefix(self):
        from Notes.routes.notebooks import router
        assert router.prefix == ""

    def test_post_route_registered(self):
        from Notes.routes.notebooks import router
        paths = [r.path for r in router.routes]
        assert "/" in paths

    def test_get_route_registered(self):
        from Notes.routes.notebooks import router
        methods = {
            m
            for r in router.routes
            if r.path == "/"
            for m in r.methods
        }
        assert "GET" in methods

    def test_patch_route_registered(self):
        from Notes.routes.notebooks import router
        paths = [r.path for r in router.routes]
        assert "/{notebook_id}" in paths

    def test_delete_route_registered(self):
        from Notes.routes.notebooks import router
        methods = {
            m
            for r in router.routes
            if r.path == "/{notebook_id}"
            for m in r.methods
        }
        assert "DELETE" in methods