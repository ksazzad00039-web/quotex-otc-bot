import time
import logging
import asyncio
from threading import Lock
from typing import Dict, Any, Optional, List, Tuple, Set

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
    Enterprise Session States Definition.
    Strictly aligned with Multi-timeframe pipeline (1D Macro -> 1H Core Execution) & Machine Learning Training Engine.
    """
    IDLE = "IDLE"
    TRAINING = "TRAINING"
    WAITING_1D = "WAITING_1D"
    WAITING_1H = "WAITING_1H"
    ANALYZING_1H = "ANALYZING_1H"
    PROCESSING = "PROCESSING"
    COOLDOWN = "COOLDOWN"
    EXPIRED = "EXPIRED"


class UserSession:
    """
    High-Performance Data Model representing isolated user analytical context.
    Calibrated strictly for Quotex OTC 1-Hour Timeframe Strategy Execution.
    """
    def __init__(self, user_id: int):
        self.user_id: int = user_id
        self.state: str = SessionState.IDLE
        self.data_1d: Optional[Dict[str, Any]] = None
        self.data_1h: Optional[Dict[str, Any]] = None
        self.last_interaction: float = time.time()
        self.created_at: float = time.time()
        self.last_request_timestamp: float = 0.0
        self.request_timestamps: List[float] = []  # Sliding window tracking for Rate Limiter
        self.analysis_count: int = 0
        self.training_count: int = 0
        self.is_admin: bool = False
        self.cooldown_until: float = 0.0
        self.session_metadata: Dict[str, Any] = {}

    def update_interaction(self) -> None:
        """Refreshes interaction timestamp to prevent premature session garbage collection."""
        self.last_interaction = time.time()

    def set_cooldown(self, seconds: int = 10) -> None:
        """Enforces anti-spam cooldown lock on user session."""
        self.cooldown_until = time.time() + seconds
        self.state = SessionState.COOLDOWN
        self.update_interaction()

    def is_in_cooldown(self) -> Tuple[bool, float]:
        """Checks if active session is under anti-spam cooldown constraint."""
        now = time.time()
        if now < self.cooldown_until:
            return True, round(self.cooldown_until - now, 1)
        return False, 0.0

    def record_request_timestamp(self) -> None:
        """Appends current request time for sliding window rate limiting."""
        now = time.time()
        self.last_request_timestamp = now
        self.request_timestamps.append(now)
        # Retain timestamps only within the last 60 seconds
        self.request_timestamps = [t for t in self.request_timestamps if now - t <= 60.0]

    def increment_analysis(self) -> None:
        """Tracks successful 1H live signal completions."""
        self.analysis_count += 1
        self.record_request_timestamp()
        self.update_interaction()

    def increment_training(self) -> int:
        """Tracks pattern screenshot uploads during Machine Learning Training Mode."""
        self.training_count += 1
        self.record_request_timestamp()
        self.update_interaction()
        return self.training_count

    def reset(self) -> None:
        """Resets state machine back to IDLE while maintaining user identification parameters."""
        self.state = SessionState.IDLE
        self.data_1d = None
        self.data_1h = None
        self.training_count = 0
        self.cooldown_until = 0.0
        self.session_metadata.clear()
        self.update_interaction()
        logger.info(f"UserSession context for user_id={self.user_id} successfully reset to IDLE.")


class SessionManager:
    """
    Enterprise Thread-Safe Session State Machine & Memory Store.
    Features: Multi-user Thread Isolation, Sliding Window Anti-Spam, Automatic GC & State Recovery.
    """
    def __init__(self, session_ttl_seconds: int = 1800, cooldown_seconds: int = 5):
        self._sessions: Dict[int, UserSession] = {}
        self.ttl_seconds: int = session_ttl_seconds  # Extended 30-Minute Dynamic TTL
        self.cooldown_seconds: int = cooldown_seconds
        self._lock: Lock = Lock()
        self._banned_users: Set[int] = set()

    def get_or_create_session(self, user_id: int) -> UserSession:
        """
        Retrieves existing active session or initializes a new thread-safe session.
        """
        with self._lock:
            if user_id in self._sessions:
                session = self._sessions[user_id]
                # Check for session inactivity timeout
                if time.time() - session.last_interaction > self.ttl_seconds:
                    logger.info(f"Session for user_id={user_id} expired due to inactivity. Triggering auto-reset.")
                    session.reset()
                else:
                    session.update_interaction()
                return session
            else:
                logger.info(f"Creating isolated thread-safe UserSession context for user_id={user_id}.")
                new_session = UserSession(user_id)
                self._sessions[user_id] = new_session
                return new_session

    def validate_request_rate(self, user_id: int, max_requests_per_window: int = 5, window_seconds: float = 10.0) -> Tuple[bool, str]:
        """
        Sliding Window Dynamic Rate Limiter for DDoS & Bot Abuse Protection.
        """
        if user_id in self._banned_users:
            return False, "⛔ সিস্টেম স্প্যাম সুরক্ষার কারণে আপনার অ্যাক্সেস সাময়িকভাবে স্থগিত রয়েছে।"

        session = self.get_or_create_session(user_id)
        in_cooldown, remaining = session.is_in_cooldown()

        if in_cooldown:
            return False, f"⚠️ সিস্টেম ব্যস্ত! অনুগ্রহ করে {remaining} সেকেন্ড পর আবার চেষ্টা করুন।"

        now = time.time()
        # Filter timestamps within active sliding window
        recent_requests = [t for t in session.request_timestamps if now - t <= window_seconds]

        if len(recent_requests) >= max_requests_per_window:
            session.set_cooldown(self.cooldown_seconds * 3)
            logger.warning(f"Abuse Detected: User {user_id} triggered rate-limit threshold ({len(recent_requests)} requests).")
            return False, "⚠️ স্প্যামিং সনাক্ত করা হয়েছে! বারবার দ্রুত ক্লিক না করে কিছুটা বিরতি দিন।"

        return True, "ALLOWED"

    def set_state(self, user_id: int, state: str) -> None:
        """Safely updates user execution state."""
        session = self.get_or_create_session(user_id)
        with self._lock:
            session.state = state
            session.update_interaction()
        logger.info(f"User {user_id} state transition -> {state}")

    def increment_training_count(self, user_id: int) -> int:
        """Increments pattern collection count in Training Mode."""
        session = self.get_or_create_session(user_id)
        with self._lock:
            return session.increment_training()

    def store_1d_analysis(self, user_id: int, vision_data: Dict[str, Any]) -> None:
        """Caches macro 1D timeframe structural analysis context."""
        session = self.get_or_create_session(user_id)
        with self._lock:
            session.data_1d = vision_data
            session.update_interaction()
        logger.info(f"User {user_id} cached macro 1D vision context.")

    def store_1h_analysis(self, user_id: int, vision_data: Dict[str, Any]) -> None:
        """Caches 1H timeframe execution analysis context."""
        session = self.get_or_create_session(user_id)
        with self._lock:
            session.data_1h = vision_data
            session.increment_analysis()
            session.state = SessionState.PROCESSING
        logger.info(f"User {user_id} successfully cached 1H execution context.")

    def store_macro_1d_analysis(self, user_id: int, vision_data: Dict[str, Any]) -> None:
        """Alias method for store_1d_analysis backward compatibility."""
        self.store_1d_analysis(user_id, vision_data)

    def get_session_context(self, user_id: int) -> Dict[str, Any]:
        """Retrieves aggregated user state & vision memory payload."""
        session = self.get_or_create_session(user_id)
        with self._lock:
            return {
                "user_id": session.user_id,
                "state": session.state,
                "data_1h": session.data_1h or {},
                "data_1d": session.data_1d or {},
                "analysis_count": session.analysis_count,
                "training_count": session.training_count,
                "last_interaction": session.last_interaction
            }

    def clear_session(self, user_id: int) -> None:
        """Forces immediate clearing of user context."""
        with self._lock:
            if user_id in self._sessions:
                self._sessions[user_id].reset()

    def cleanup_expired_sessions(self) -> int:
        """Thread-safe Garbage Collector to purge inactive sessions from system RAM."""
        now = time.time()
        expired_users: List[int] = []

        with self._lock:
            for uid, sess in self._sessions.items():
                if now - sess.last_interaction > self.ttl_seconds:
                    expired_users.append(uid)

            for uid in expired_users:
                del self._sessions[uid]

        if expired_users:
            logger.info(f"Session Garbage Collection: Purged {len(expired_users)} stale session(s) from memory.")
        return len(expired_users)

    async def start_periodic_garbage_collection(self, interval_seconds: int = 300) -> None:
        """Asynchronous background loop to run automated garbage collection at regular intervals."""
        while True:
            await asyncio.sleep(interval_seconds)
            purged_count = self.cleanup_expired_sessions()
            if purged_count > 0:
                logger.info(f"Automated GC Daemon successfully cleaned {purged_count} idle sessions.")

    def export_session_state(self) -> Dict[int, Dict[str, Any]]:
        """Exports session state snapshot for persistence across application reloads."""
        snapshot = {}
        with self._lock:
            for uid, sess in self._sessions.items():
                snapshot[uid] = {
                    "state": sess.state,
                    "data_1d": sess.data_1d,
                    "data_1h": sess.data_1h,
                    "training_count": sess.training_count,
                    "analysis_count": sess.analysis_count
                }
        return snapshot

    def get_active_user_count(self) -> int:
        """Returns the total number of non-expired active sessions."""
        self.cleanup_expired_sessions()
        with self._lock:
            return len(self._sessions)


# Global Engine Instance Export
session_manager = SessionManager()
# Class Alias for Flexible Import System
EnterpriseSessionManager = SessionManager

if __name__ == "__main__":
    print("Quotex OTC Quant Enterprise SessionManager v10.2 Ready & Operational.")
