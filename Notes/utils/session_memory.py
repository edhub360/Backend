from collections import defaultdict, deque
from typing import List, Dict, Any
import threading
import time
import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class SessionMemory:
    """
    In-memory session management for chat history.
    
    Features:
    - Thread-safe operations
    - Automatic cleanup of old sessions
    - Configurable history limits
    - Memory usage optimization
    """
    
    def __init__(self, max_history_per_session: int = 50, cleanup_interval_hours: int = 24):
        """
        Initialize session memory manager.
        
        Args:
            max_history_per_session: Maximum number of messages to keep per session
            cleanup_interval_hours: Hours after which unused sessions are cleaned up
        """
        # Thread-safe storage for session histories
        self._sessions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_per_session))
        self._session_timestamps: Dict[str, datetime] = {}
        
        # Configuration
        self.max_history = max_history_per_session
        self.cleanup_interval = timedelta(hours=cleanup_interval_hours)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Start background cleanup task
        self._start_cleanup_task()
        
        logger.info(f"SessionMemory initialized with {max_history_per_session} max messages per session")
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to the session history.
        
        Args:
            session_id: Unique identifier for the session
            role: Either 'user' or 'assistant'
            content: The message content
        """
        with self._lock:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            self._sessions[session_id].append(message)
            self._session_timestamps[session_id] = datetime.now()
            
            logger.debug(f"Added {role} message to session {session_id}")
    
    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get the chat history for a session.
        
        Args:
            session_id: Unique identifier for the session
            
        Returns:
            List of message dictionaries with role, content, and timestamp
        """
        with self._lock:
            # Update access timestamp
            self._session_timestamps[session_id] = datetime.now()
            
            # Return copy of messages to avoid external modification
            history = list(self._sessions[session_id])
            
            logger.debug(f"Retrieved {len(history)} messages for session {session_id}")
            return history
    
    def clear_history(self, session_id: str) -> None:
        """
        Clear the chat history for a specific session.
        
        Args:
            session_id: Unique identifier for the session
        """
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].clear()
                self._session_timestamps[session_id] = datetime.now()
                logger.info(f"Cleared history for session {session_id}")
    
    def delete_session(self, session_id: str) -> None:
        """
        Completely delete a session and its history.
        
        Args:
            session_id: Unique identifier for the session
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                del self._session_timestamps[session_id]
                logger.info(f"Deleted session {session_id}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active sessions.
        
        Returns:
            Dictionary with session statistics
        """
        with self._lock:
            stats = {
                "total_sessions": len(self._sessions),
                "total_messages": sum(len(history) for history in self._sessions.values()),
                "sessions_by_size": {},
                "oldest_session": None,
                "newest_session": None
            }
            
            # Calculate sessions by message count
            for session_id, history in self._sessions.items():
                size_bucket = f"{len(history)//10*10}-{len(history)//10*10+9}"
                stats["sessions_by_size"][size_bucket] = stats["sessions_by_size"].get(size_bucket, 0) + 1
            
            # Find oldest and newest sessions
            if self._session_timestamps:
                oldest_time = min(self._session_timestamps.values())
                newest_time = max(self._session_timestamps.values())
                
                for session_id, timestamp in self._session_timestamps.items():
                    if timestamp == oldest_time:
                        stats["oldest_session"] = {
                            "session_id": session_id,
                            "last_activity": timestamp.isoformat()
                        }
                    if timestamp == newest_time:
                        stats["newest_session"] = {
                            "session_id": session_id,
                            "last_activity": timestamp.isoformat()
                        }
            
            return stats
    
    def cleanup_old_sessions(self) -> int:
        """
        Remove sessions that haven't been accessed recently.
        
        Returns:
            Number of sessions cleaned up
        """
        cutoff_time = datetime.now() - self.cleanup_interval
        sessions_to_delete = []
        
        with self._lock:
            for session_id, last_access in self._session_timestamps.items():
                if last_access < cutoff_time:
                    sessions_to_delete.append(session_id)
            
            for session_id in sessions_to_delete:
                del self._sessions[session_id]
                del self._session_timestamps[session_id]
        
        if sessions_to_delete:
            logger.info(f"Cleaned up {len(sessions_to_delete)} old sessions")
        
        return len(sessions_to_delete)
    
    def _start_cleanup_task(self):
        """Start background task for periodic cleanup."""
        def cleanup_worker():
            while True:
                time.sleep(3600)  # Run every hour
                try:
                    self.cleanup_old_sessions()
                except Exception as e:
                    logger.error(f"Error during session cleanup: {str(e)}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("Started background session cleanup task")
