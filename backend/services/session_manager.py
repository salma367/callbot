from collections import defaultdict
from backend.services.streaming_session import StreamingSession


class SessionManager:
    def __init__(self):
        self.sessions = defaultdict(StreamingSession)

    def get(self, session_id: str) -> StreamingSession:
        return self.sessions[session_id]

    def clear(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
