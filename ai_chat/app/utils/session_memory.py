from typing import Dict, List, Optional

# Structure for a message in a conversation
class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

# Simple in-memory session store (singleton pattern)
class SessionMemory:
    def __init__(self):
        # Maps session_id to list of Message
        self.sessions: Dict[str, List[Message]] = {}

    def get_history(self, session_id: str) -> List[Message]:
        return self.sessions.get(session_id, [])

    def append_message(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(Message(role, content))

    def clear_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]

# Singleton instance for importing
session_memory = SessionMemory()
