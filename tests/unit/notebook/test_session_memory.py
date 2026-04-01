# tests/unit/notes/utils/test_session_memory.py

import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import patch


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_memory(max_history=50, cleanup_hours=24):
    from Notes.utils.session_memory import SessionMemory
    return SessionMemory(
        max_history_per_session=max_history,
        cleanup_interval_hours=cleanup_hours,
    )


SESSION_A = "user_1_nb-abc"
SESSION_B = "user_2_nb-xyz"


# ══════════════════════════════════════════════════════════════════════════════
# __init__
# ══════════════════════════════════════════════════════════════════════════════
class TestSessionMemoryInit:

    def test_max_history_stored(self):
        mem = _make_memory(max_history=10)
        assert mem.max_history == 10

    def test_cleanup_interval_stored_as_timedelta(self):
        mem = _make_memory(cleanup_hours=12)
        assert mem.cleanup_interval == timedelta(hours=12)

    def test_sessions_empty_on_init(self):
        mem = _make_memory()
        assert len(mem._sessions) == 0

    def test_session_timestamps_empty_on_init(self):
        mem = _make_memory()
        assert len(mem._session_timestamps) == 0

    def test_lock_is_rlock(self):
        import threading
        mem = _make_memory()
        assert isinstance(mem._lock, type(threading.RLock()))


# ══════════════════════════════════════════════════════════════════════════════
# add_message
# ══════════════════════════════════════════════════════════════════════════════
class TestAddMessage:

    def test_message_stored_in_session(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "Hello!")
        history = mem.get_history(SESSION_A)
        assert len(history) == 1

    def test_message_has_correct_role(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "Hi")
        assert mem.get_history(SESSION_A)[0]["role"] == "user"

    def test_message_has_correct_content(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "assistant", "Hello there!")
        assert mem.get_history(SESSION_A)[0]["content"] == "Hello there!"

    def test_message_has_timestamp(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "msg")
        assert "timestamp" in mem.get_history(SESSION_A)[0]

    def test_timestamp_is_iso_string(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "msg")
        ts = mem.get_history(SESSION_A)[0]["timestamp"]
        # Should parse without error
        datetime.fromisoformat(ts)

    def test_multiple_messages_appended_in_order(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "first")
        mem.add_message(SESSION_A, "assistant", "second")
        history = mem.get_history(SESSION_A)
        assert history[0]["content"] == "first"
        assert history[1]["content"] == "second"

    def test_session_timestamp_updated_on_add(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "msg")
        assert SESSION_A in mem._session_timestamps

    def test_different_sessions_isolated(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "session A msg")
        mem.add_message(SESSION_B, "user", "session B msg")
        assert len(mem.get_history(SESSION_A)) == 1
        assert len(mem.get_history(SESSION_B)) == 1

    def test_max_history_enforced(self):
        mem = _make_memory(max_history=3)
        for i in range(5):
            mem.add_message(SESSION_A, "user", f"msg {i}")
        assert len(mem.get_history(SESSION_A)) == 3

    def test_oldest_messages_dropped_when_max_reached(self):
        mem = _make_memory(max_history=3)
        for i in range(5):
            mem.add_message(SESSION_A, "user", f"msg {i}")
        history = mem.get_history(SESSION_A)
        contents = [m["content"] for m in history]
        assert "msg 0" not in contents
        assert "msg 4" in contents

    def test_thread_safe_concurrent_adds(self):
        mem = _make_memory(max_history=1000)
        errors = []

        def add_msgs():
            try:
                for i in range(50):
                    mem.add_message(SESSION_A, "user", f"msg {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_msgs) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(mem.get_history(SESSION_A)) <= 1000


# ══════════════════════════════════════════════════════════════════════════════
# get_history
# ══════════════════════════════════════════════════════════════════════════════
class TestGetHistory:

    def test_empty_session_returns_empty_list(self):
        mem = _make_memory()
        assert mem.get_history("nonexistent-session") == []

    def test_returns_list_type(self):
        mem = _make_memory()
        assert isinstance(mem.get_history(SESSION_A), list)

    def test_returns_copy_not_internal_deque(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "msg")
        history = mem.get_history(SESSION_A)
        history.append({"role": "user", "content": "injected"})
        # Internal storage must not be modified
        assert len(mem.get_history(SESSION_A)) == 1

    def test_updates_session_timestamp_on_access(self):
        mem = _make_memory()
        before = datetime.now()
        mem.get_history(SESSION_A)
        after = datetime.now()
        ts = mem._session_timestamps.get(SESSION_A)
        assert ts is not None
        assert before <= ts <= after

    def test_returns_all_messages(self):
        mem = _make_memory()
        for i in range(5):
            mem.add_message(SESSION_A, "user", f"msg {i}")
        assert len(mem.get_history(SESSION_A)) == 5


# ══════════════════════════════════════════════════════════════════════════════
# clear_history
# ══════════════════════════════════════════════════════════════════════════════
class TestClearHistory:

    def test_clears_all_messages(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "msg")
        mem.clear_history(SESSION_A)
        assert mem.get_history(SESSION_A) == []

    def test_clear_nonexistent_session_no_error(self):
        mem = _make_memory()
        try:
            mem.clear_history("ghost-session")
        except Exception:
            pytest.fail("clear_history raised on nonexistent session")

    def test_session_timestamp_updated_after_clear(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "msg")
        before = datetime.now()
        mem.clear_history(SESSION_A)
        ts = mem._session_timestamps[SESSION_A]
        assert ts >= before

    def test_other_sessions_unaffected(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "a msg")
        mem.add_message(SESSION_B, "user", "b msg")
        mem.clear_history(SESSION_A)
        assert len(mem.get_history(SESSION_B)) == 1

    def test_can_add_messages_after_clear(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "first")
        mem.clear_history(SESSION_A)
        mem.add_message(SESSION_A, "user", "after clear")
        assert mem.get_history(SESSION_A)[0]["content"] == "after clear"


# ══════════════════════════════════════════════════════════════════════════════
# delete_session
# ══════════════════════════════════════════════════════════════════════════════
class TestDeleteSession:

    def test_session_removed_from_sessions(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "msg")
        mem.delete_session(SESSION_A)
        assert SESSION_A not in mem._sessions

    def test_session_removed_from_timestamps(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "msg")
        mem.delete_session(SESSION_A)
        assert SESSION_A not in mem._session_timestamps

    def test_delete_nonexistent_session_no_error(self):
        mem = _make_memory()
        try:
            mem.delete_session("does-not-exist")
        except Exception:
            pytest.fail("delete_session raised on nonexistent session")

    def test_other_sessions_unaffected_after_delete(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "a")
        mem.add_message(SESSION_B, "user", "b")
        mem.delete_session(SESSION_A)
        assert len(mem.get_history(SESSION_B)) == 1

    def test_get_history_returns_empty_after_delete(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "msg")
        mem.delete_session(SESSION_A)
        # defaultdict recreates the deque — result is empty list
        assert mem.get_history(SESSION_A) == []


# ══════════════════════════════════════════════════════════════════════════════
# get_session_stats
# ══════════════════════════════════════════════════════════════════════════════
class TestGetSessionStats:

    def test_total_sessions_correct(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "a")
        mem.add_message(SESSION_B, "user", "b")
        assert mem.get_session_stats()["total_sessions"] == 2

    def test_total_messages_correct(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "a")
        mem.add_message(SESSION_A, "assistant", "b")
        mem.add_message(SESSION_B, "user", "c")
        assert mem.get_session_stats()["total_messages"] == 3

    def test_empty_memory_stats(self):
        mem = _make_memory()
        stats = mem.get_session_stats()
        assert stats["total_sessions"] == 0
        assert stats["total_messages"] == 0
        assert stats["oldest_session"] is None
        assert stats["newest_session"] is None

    def test_stats_contains_required_keys(self):
        mem = _make_memory()
        stats = mem.get_session_stats()
        assert all(k in stats for k in (
            "total_sessions", "total_messages",
            "sessions_by_size", "oldest_session", "newest_session"
        ))

    def test_oldest_and_newest_session_set(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "a")
        time.sleep(0.01)
        mem.add_message(SESSION_B, "user", "b")
        stats = mem.get_session_stats()
        assert stats["oldest_session"] is not None
        assert stats["newest_session"] is not None

    def test_oldest_session_has_session_id_and_last_activity(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "a")
        stats = mem.get_session_stats()
        oldest = stats["oldest_session"]
        assert "session_id" in oldest
        assert "last_activity" in oldest

    def test_sessions_by_size_is_dict(self):
        mem = _make_memory()
        mem.add_message(SESSION_A, "user", "msg")
        stats = mem.get_session_stats()
        assert isinstance(stats["sessions_by_size"], dict)


# ══════════════════════════════════════════════════════════════════════════════
# cleanup_old_sessions
# ══════════════════════════════════════════════════════════════════════════════
class TestCleanupOldSessions:

    def test_returns_zero_when_nothing_to_clean(self):
        mem = _make_memory(cleanup_hours=24)
        mem.add_message(SESSION_A, "user", "recent msg")
        assert mem.cleanup_old_sessions() == 0

    def test_removes_expired_sessions(self):
        mem = _make_memory(cleanup_hours=1)
        mem.add_message(SESSION_A, "user", "old msg")
        # Force timestamp into the past
        mem._session_timestamps[SESSION_A] = datetime.now() - timedelta(hours=2)

        count = mem.cleanup_old_sessions()
        assert count == 1

    def test_expired_session_removed_from_storage(self):
        mem = _make_memory(cleanup_hours=1)
        mem.add_message(SESSION_A, "user", "old msg")
        mem._session_timestamps[SESSION_A] = datetime.now() - timedelta(hours=2)

        mem.cleanup_old_sessions()
        assert SESSION_A not in mem._sessions

    def test_fresh_sessions_not_removed(self):
        mem = _make_memory(cleanup_hours=1)
        mem.add_message(SESSION_A, "user", "old")
        mem.add_message(SESSION_B, "user", "fresh")
        mem._session_timestamps[SESSION_A] = datetime.now() - timedelta(hours=2)

        mem.cleanup_old_sessions()
        assert SESSION_B in mem._sessions

    def test_returns_count_of_removed_sessions(self):
        mem = _make_memory(cleanup_hours=1)
        for sid in ["s1", "s2", "s3"]:
            mem.add_message(sid, "user", "old")
            mem._session_timestamps[sid] = datetime.now() - timedelta(hours=2)

        count = mem.cleanup_old_sessions()
        assert count == 3

    def test_empty_memory_returns_zero(self):
        mem = _make_memory()
        assert mem.cleanup_old_sessions() == 0

    def test_cleanup_all_when_all_expired(self):
        mem = _make_memory(cleanup_hours=1)
        mem.add_message(SESSION_A, "user", "old a")
        mem.add_message(SESSION_B, "user", "old b")
        past = datetime.now() - timedelta(hours=2)
        mem._session_timestamps[SESSION_A] = past
        mem._session_timestamps[SESSION_B] = past

        count = mem.cleanup_old_sessions()
        assert count == 2
        assert len(mem._sessions) == 0