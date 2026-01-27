from typing import Dict
from .call_session import CallSession


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, CallSession] = {}

    def create(self) -> CallSession:
        session = CallSession()
        self.sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> CallSession:
        return self.sessions.get(session_id)

    def clear(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
