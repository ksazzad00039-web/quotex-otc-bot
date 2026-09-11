import time
import logging
from threading import Lock
from typing import Dict, Any, Optional, List, Tuple

# Fallback Configuration Logging Setup
try:
    from config import logger
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("OTC_Enterprise_Quant.SessionManager")


class SessionState:
    """
    Enterprise Session States Enum Definition.
    IDLE: Waiting for initial chart analysis trigger.
    TRAINING: Continual machine-learning pattern feedback state.
    ANALYZING_1H: Currently processing strict 1-Hour OTC timeframe screenshot.
    PROCESSING: Master quant pipeline evaluating pattern & liquidity.
    COOLDOWN: Anti-spam protection state enforcing request limits.
    EXPIRED: Stale session flagged for garbage collection.
    """
    IDLE = "IDLE"
    TRAINING = "TRAINING"
    ANALYZING_1H = "ANALYZING_1H"
    PROCESSING = "PROCESSING"
    COOLDOWN = "COOLDOWN"
    EXPIRED = "EXPIRED"


class UserSession:
    """
    Data model representing an active user's analysis state and memory context.
    Strictly calibrated for Quotex OTC 1-Hour Execution Pipelines.
    """
    def __init__(self, user_id: int):
        self.user_id: int = user_id
        self.state: str = SessionState.IDLE
        self.data_1d: Optional[Dict[str, Any]] = None
        self.data_1h: Optional[Dict[str, Any]] = None
        self.last_interaction: float = time.time()
        self.created_at: float = time.time()
        self.last_request_timestamp: float = 0.0
        self.analysis_count: int = 0
        self.is_admin: bool = False
        self.cooldown_until: float = 0.0

    def update_interaction(self) -> None:
        """Refreshes interaction timestamp to keep active session alive."""
        self.last_interaction = time.time()

    def set_cooldown(self, seconds: int = 10) -> None:
        """Enforces anti-spam cooldown lock on user session."""
        self.cooldown_until = time.time() + seconds
        self.state = SessionState.COOLDOWN
        self.update_interaction()

    def is_in_cooldown(self) -> Tuple[bool, float]:
        """Checks if current user session is locked under anti-spam cooldown."""
        now = time.time()
        if now < self.cooldown_until:
            return True, round(self.cooldown_until - now, 1)
        return False, 0.0

    def increment_analysis(self) -> None:
        """Tracks successful analysis completions."""
        self.analysis_count += 1
        self.last_request_timestamp = time.time()
        self.update_interaction()

    def reset(self) -> None:
        """Resets analytical context to IDLE while maintaining user identification."""
        self.state = SessionState.IDLE
        self.data_1d = None
        self.data_1h = None
        self.cooldown_until = 0.0
        self.update_interaction()
        logger.info(f"UserSession context for user_id={self.user_id} successfully reset to IDLE.")


class SessionManager:
    """
    Enterprise Thread-Safe State Machine and Session Memory Store.
    Manages multi-user isolation, anti-spam protections, and automated garbage collection.
    """
    def __init__(self, session_ttl_seconds: int = 900, cooldown_seconds: int = 5):
        self._sessions: Dict[int, UserSession] = {}
        self.ttl_seconds: int = session_ttl_seconds  # Default 15 minutes timeout
        self.cooldown_seconds: int = cooldown_seconds
        self._lock: Lock = Lock()

    def get_or_create_session(self, user_id: int) -> UserSession:
        """
        Retrieves existing session or creates a new one with thread safety.
        """
        with self._lock:
            if user_id in self._sessions:
                session = self._sessions[user_id]
                if time.time() - session.last_interaction > self.ttl_seconds:
                    logger.info(f"Session for user_id={user_id} expired due to inactivity. Auto-resetting.")
                    session.reset()
                else:
                    session.update_interaction()
                return session
            else:
                logger.info(f"Creating new thread-safe UserSession for user_id={user_id}.")
                new_session = UserSession(user_id)
                self._sessions[user_id] = new_session
                return new_session

    def validate_request_rate(self, user_id: int) -> Tuple[bool, str]:
        """
        Validates anti-spam rules before accepting new vision analysis tasks.
        """
        session = self.get_or_create_session(user_id)
        in_cooldown, remaining = session.is_in_cooldown()

        if in_cooldown:
            return False, f"সিস্টেম বিজি! অনুগ্রহ করে {remaining} সেকেন্ড পর আবার চেষ্টা করুন।"

        now = time.time()
        if now - session.last_request_timestamp < self.cooldown_seconds:
            session.set_cooldown(self.cooldown_seconds * 2)
            return False, "স্প্যাম প্রতিরোধ সিস্টেম সক্রিয়! বারবার দ্রুত ক্লিক করবেন না।"

        return True, "ALLOWED"

    def set_state(self, user_id: int, state: str) -> None:
        """Updates user state safely."""
        session = self.get_or_create_session(user_id)
        with self._lock:
            session.state = state
            session.update_interaction()
        logger.info(f"User {user_id} state transition -> {state}")

    def store_1h_analysis(self, user_id: int, vision_data: Dict[str, Any]) -> None:
        """Stores analyzed 1H timeframe vision payload into session memory."""
        session = self.get_or_create_session(user_id)
        with self._lock:
            session.data_1h = vision_data
            session.increment_analysis()
            session.state = SessionState.PROCESSING
        logger.info(f"User {user_id} successfully cached 1H vision context.")

    def store_macro_1d_analysis(self, user_id: int, vision_data: Dict[str, Any]) -> None:
        """Stores macro 1D timeframe context if provided."""
        session = self.get_or_create_session(user_id)
        with self._lock:
            session.data_1d = vision_data
            session.update_interaction()
        logger.info(f"User {user_id} cached macro 1D vision context.")

    def get_session_context(self, user_id: int) -> Dict[str, Any]:
        """Retrieves combined vision & state payload for pipeline evaluation."""
        session = self.get_or_create_session(user_id)
        with self._lock:
            return {
                "user_id": session.user_id,
                "state": session.state,
                "data_1h": session.data_1h or {},
                "data_1d": session.data_1d or {},
                "analysis_count": session.analysis_count
            }

    def clear_session(self, user_id: int) -> None:
        """Forces immediate clearing of user context."""
        with self._lock:
            if user_id in self._sessions:
                self._sessions[user_id].reset()

    def cleanup_expired_sessions(self) -> int:
        """
        Garbage collector to remove idle & expired sessions from RAM.
        """
        now = time.time()
        expired_users: List[int] = []

        with self._lock:
            for uid, sess in self._sessions.items():
                if now - sess.last_interaction > self.ttl_seconds:
                    expired_users.append(uid)

            for uid in expired_users:
                del self._sessions[uid]

        if expired_users:
            logger.info(f"Session GC Cleanup: Purged {len(expired_users)} stale sessions from memory.")
        return len(expired_users)

    def get_active_user_count(self) -> int:
        """Returns total active non-expired sessions."""
        self.cleanup_expired_sessions()
        with self._lock:
            return len(self._sessions)


# Global Engine Instance Export
session_manager = SessionManager()
# Class Alias for Flexible Import
EnterpriseSessionManager = SessionManager

if __name__ == "__main__":
    print("Master Session Manager Ready.")

