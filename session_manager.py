import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("OTC_Enterprise_Quant.SessionManager")

class SessionState:
    """
    Session States Enum Definition.
    IDLE: Idle state, waiting for menu choice.
    TRAINING: Continuously capturing and saving training patterns.
    WAITING_1D: Live mode activated, awaiting 1D chart screenshot.
    WAITING_1H: 1D chart analyzed, awaiting 1H chart screenshot.
    PROCESSING: Engine analyzing multi-timeframe confluent setup.
    """
    IDLE = "IDLE"
    TRAINING = "TRAINING"
    WAITING_1D = "WAITING_1D"
    WAITING_1H = "WAITING_1H"
    PROCESSING = "PROCESSING"

class UserSession:
    """
    Data model representing an active user's analysis state.
    """
    def __init__(self, user_id: int):
        self.user_id: int = user_id
        self.state: str = SessionState.IDLE
        self.data_1d: Optional[Dict[str, Any]] = None
        self.data_1h: Optional[Dict[str, Any]] = None
        self.last_interaction: float = time.time()
        self.created_at: float = time.time()
        self.training_count: int = 0

    def update_interaction(self):
        """Refreshes the timestamp of user interaction to extend active session."""
        self.last_interaction = time.time()

    def reset(self):
        """Resets the session state back to IDLE while preserving session metadata."""
        self.state = SessionState.IDLE
        self.data_1d = None
        self.data_1h = None
        self.update_interaction()
        logger.info(f"UserSession for user_id={self.user_id} successfully reset to IDLE.")


class SessionManager:
    """
    Enterprise State Machine and Session Store for tracking active user workflows.
    Ensures safe multi-user isolation, memory cleanup, and timeout handling.
    """
    def __init__(self, session_ttl_seconds: int = 900):
        # Dictionary holding user_id mapped to UserSession instance
        self._sessions: Dict[int, UserSession] = {}
        self.ttl_seconds: int = session_ttl_seconds  # Default 15 minutes timeout

    def get_or_create_session(self, user_id: int) -> UserSession:
        """
        Retrieves existing session or instantiates a new one if not present or expired.
        """
        if user_id in self._sessions:
            session = self._sessions[user_id]
            # Check if session has timed out due to inactivity
            if time.time() - session.last_interaction > self.ttl_seconds:
                logger.info(f"Session for user_id={user_id} expired. Auto-resetting.")
                session.reset()
            else:
                session.update_interaction()
            return session
        else:
            logger.info(f"Creating new UserSession context for user_id={user_id}.")
            new_session = UserSession(user_id)
            self._sessions[user_id] = new_session
            return new_session

    def set_state(self, user_id: int, state: str) -> None:
        """
        Updates session state for a given user.
        """
        session = self.get_or_create_session(user_id)
        session.state = state
        session.update_interaction()
        logger.info(f"User {user_id} state transition -> {state}")

    def store_1d_analysis(self, user_id: int, vision_data: Dict[str, Any]) -> None:
        """
        Stores the outcome of the 1D timeframe Gemini analysis into user session.
        """
        session = self.get_or_create_session(user_id)
        session.data_1d = vision_data
        session.state = SessionState.WAITING_1H
        session.update_interaction()
        logger.info(f"User {user_id} successfully cached 1D vision context.")

    def store_1h_analysis(self, user_id: int, vision_data: Dict[str, Any]) -> None:
        """
        Stores the outcome of the 1H timeframe Gemini analysis into user session.
        """
        session = self.get_or_create_session(user_id)
        session.data_1h = vision_data
        session.update_interaction()
        logger.info(f"User {user_id} successfully cached 1H vision context.")

    def clear_session(self, user_id: int) -> None:
        """
        Explicitly clears and resets a user session.
        """
        if user_id in self._sessions:
            self._sessions[user_id].reset()

    def increment_training_count(self, user_id: int) -> int:
        """
        Tracks number of training patterns saved by this user in current active run.
        """
        session = self.get_or_create_session(user_id)
        session.training_count += 1
        return session.training_count

    def purge_stale_sessions() -> int:
        """
        Garbage collector method to purge inactive sessions from RAM.
        Can be scheduled periodically in main loop.
        """
        now = time.time()
        stale_ids = [
            uid for uid, sess in self._sessions.items() 
            if (now - sess.last_interaction) > self.ttl_seconds
        ]
        for uid in stale_ids:
            del self._sessions[uid]
        if stale_ids:
            logger.info(f"Purged {len(stale_ids)} stale user sessions from memory.")
        return len(stale_ids)
