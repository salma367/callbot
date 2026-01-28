from typing import Dict
from backend.models.call_session import CallSession


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, CallSession] = {}

    def create(self, client_id=None) -> CallSession:
        """Create a new CallSession and store it by call_id."""
        session = CallSession(client_id=client_id)
        self.sessions[session.call_id] = session
        return session

    def get(self, call_id: str) -> CallSession:
        return self.sessions.get(call_id)

    def clear(self, call_id: str):
        if call_id in self.sessions:
            del self.sessions[call_id]
