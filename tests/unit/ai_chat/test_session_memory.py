# tests/unit/ai_chat/test_session_memory.py

import pytest


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def fresh_memory():
    """Return a new isolated SessionMemory instance for each test."""
    from ai_chat.app.utils.session_memory import SessionMemory
    return SessionMemory()


# ─────────────────────────────────────────────
# Message
# ─────────────────────────────────────────────

class TestMessage:

    def test_stores_role(self):
        from ai_chat.app.utils.session_memory import Message
        msg = Message(role="user", content="hello")
        assert msg.role == "user"

    def test_stores_content(self):
        from ai_chat.app.utils.session_memory import Message
        msg = Message(role="assistant", content="how can I help?")
        assert msg.content == "how can I help?"

    def test_role_assistant(self):
        from ai_chat.app.utils.session_memory import Message
        msg = Message(role="assistant", content="response")
        assert msg.role == "assistant"

    def test_empty_content_allowed(self):
        from ai_chat.app.utils.session_memory import Message
        msg = Message(role="user", content="")
        assert msg.content == ""


# ─────────────────────────────────────────────
# SessionMemory.get_history
# ─────────────────────────────────────────────

class TestGetHistory:

    def test_unknown_session_returns_empty_list(self):
        mem = fresh_memory()
        result = mem.get_history("nonexistent-session")
        assert result == []

    def test_returns_list_type(self):
        mem = fresh_memory()
        result = mem.get_history("any-id")
        assert isinstance(result, list)

    def test_returns_messages_after_append(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "hello")
        history = mem.get_history("s1")
        assert len(history) == 1

    def test_history_contains_correct_role(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "hi there")
        assert mem.get_history("s1")[0].role == "user"

    def test_history_contains_correct_content(self):
        mem = fresh_memory()
        mem.append_message("s1", "assistant", "welcome")
        assert mem.get_history("s1")[0].content == "welcome"

    def test_different_sessions_are_isolated(self):
        mem = fresh_memory()
        mem.append_message("session-a", "user", "msg for a")
        mem.append_message("session-b", "user", "msg for b")

        assert len(mem.get_history("session-a")) == 1
        assert mem.get_history("session-a")[0].content == "msg for a"

    def test_returns_messages_in_insertion_order(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "first")
        mem.append_message("s1", "assistant", "second")
        mem.append_message("s1", "user", "third")

        history = mem.get_history("s1")
        assert [m.content for m in history] == ["first", "second", "third"]


# ─────────────────────────────────────────────
# SessionMemory.append_message
# ─────────────────────────────────────────────

class TestAppendMessage:

    def test_creates_session_on_first_append(self):
        mem = fresh_memory()
        mem.append_message("new-session", "user", "hello")
        assert "new-session" in mem.sessions

    def test_appended_message_is_message_instance(self):
        from ai_chat.app.utils.session_memory import Message
        mem = fresh_memory()
        mem.append_message("s1", "user", "hi")
        assert isinstance(mem.get_history("s1")[0], Message)

    def test_multiple_appends_to_same_session(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "q1")
        mem.append_message("s1", "assistant", "a1")
        mem.append_message("s1", "user", "q2")
        assert len(mem.get_history("s1")) == 3

    def test_append_to_different_sessions_independently(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "hello")
        mem.append_message("s2", "user", "world")

        assert len(mem.get_history("s1")) == 1
        assert len(mem.get_history("s2")) == 1

    def test_role_preserved_on_append(self):
        mem = fresh_memory()
        mem.append_message("s1", "assistant", "response")
        assert mem.get_history("s1")[0].role == "assistant"

    def test_content_preserved_on_append(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "what is python?")
        assert mem.get_history("s1")[0].content == "what is python?"

    def test_does_not_overwrite_existing_session(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "first message")
        mem.append_message("s1", "assistant", "second message")
        history = mem.get_history("s1")

        assert len(history) == 2
        assert history[0].content == "first message"

    def test_append_empty_content(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "")
        assert mem.get_history("s1")[0].content == ""

    def test_large_number_of_messages(self):
        mem = fresh_memory()
        for i in range(100):
            mem.append_message("s1", "user", f"message {i}")
        assert len(mem.get_history("s1")) == 100


# ─────────────────────────────────────────────
# SessionMemory.clear_session
# ─────────────────────────────────────────────

class TestClearSession:

    def test_clear_removes_session(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "hello")
        mem.clear_session("s1")
        assert mem.get_history("s1") == []

    def test_clear_nonexistent_session_does_not_raise(self):
        mem = fresh_memory()
        mem.clear_session("ghost-session")  # should not raise

    def test_clear_does_not_affect_other_sessions(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "keep me")
        mem.append_message("s2", "user", "delete me")

        mem.clear_session("s2")

        assert len(mem.get_history("s1")) == 1
        assert mem.get_history("s2") == []

    def test_session_key_removed_from_sessions_dict(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "hi")
        mem.clear_session("s1")
        assert "s1" not in mem.sessions

    def test_can_reuse_session_id_after_clear(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "old message")
        mem.clear_session("s1")
        mem.append_message("s1", "user", "new message")

        history = mem.get_history("s1")
        assert len(history) == 1
        assert history[0].content == "new message"

    def test_clear_all_sessions_independently(self):
        mem = fresh_memory()
        mem.append_message("s1", "user", "a")
        mem.append_message("s2", "user", "b")
        mem.append_message("s3", "user", "c")

        mem.clear_session("s1")
        mem.clear_session("s2")
        mem.clear_session("s3")

        assert mem.sessions == {}


# ─────────────────────────────────────────────
# Singleton instance
# ─────────────────────────────────────────────

class TestSingletonInstance:

    def test_module_exposes_session_memory_instance(self):
        from ai_chat.app.utils.session_memory import session_memory, SessionMemory
        assert isinstance(session_memory, SessionMemory)

    def test_same_instance_on_multiple_imports(self):
        from ai_chat.app.utils.session_memory import session_memory as sm1
        from ai_chat.app.utils.session_memory import session_memory as sm2
        assert sm1 is sm2

    def test_singleton_state_shared_across_imports(self):
        from ai_chat.app.utils.session_memory import session_memory

        session_memory.append_message("singleton-test", "user", "persistent")
        history = session_memory.get_history("singleton-test")

        assert len(history) >= 1
        # cleanup so other tests aren't affected
        session_memory.clear_session("singleton-test")