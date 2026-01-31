from typing import Dict
from backend.models.call_session import CallSession
from backend.repositories.client_repo import get_or_create_client
import uuid


class SessionManager:

    def __init__(self):
        self.sessions: Dict[str, CallSession] = {}

    def create(self, user_name=None, phone_number=None) -> CallSession:

        user_name = user_name or "FrontEnd User"
        phone_number = phone_number or "000000000"

        client_id = get_or_create_client(full_name=user_name, phone_number=phone_number)

        call_id = str(uuid.uuid4())

        session = CallSession(
            call_id=call_id,
            client_id=client_id,
            user_name=user_name,
            phone_number=phone_number,
        )

        self.sessions[session.call_id] = session
        return session

    def get(self, call_id: str) -> CallSession:
        """Retrieve a CallSession by its call_id."""
        return self.sessions.get(call_id)

    def clear(self, call_id: str):
        """Remove a session from memory."""
        if call_id in self.sessions:
            del self.sessions[call_id]
