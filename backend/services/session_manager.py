from typing import Dict
from backend.models.call_session import CallSession
import uuid  # add this import


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, CallSession] = {}

    def create(self, client_id=None) -> CallSession:
        """Create a new CallSession with a generated call_id."""
        call_id = str(uuid.uuid4())
        if client_id is None:
            client_id = "UNKNOWN"

        session = CallSession(call_id=call_id, client_id=client_id)  # pass both
        self.sessions[session.call_id] = session
        return session

    def get(self, call_id: str) -> CallSession:
        return self.sessions.get(call_id)

    def clear(self, call_id: str):
        if call_id in self.sessions:
            del self.sessions[call_id]
