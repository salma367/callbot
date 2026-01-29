from typing import Dict
from backend.models.call_session import CallSession
from backend.repositories.client_repo import get_or_create_client
import uuid


class SessionManager:
    """Manages active call sessions in memory."""

    def __init__(self):
        self.sessions: Dict[str, CallSession] = {}

    def create(self, user_name=None, phone_number=None) -> CallSession:
        """
        Create a new CallSession with a generated call_id and associated client_id.
        If the client already exists in the clients table (based on phone_number),
        it reuses the client_id.
        """

        # Fallback defaults
        user_name = user_name or "FrontEnd User"
        phone_number = phone_number or "000000000"

        # Get or create a client in the database
        client_id = get_or_create_client(full_name=user_name, phone_number=phone_number)

        # Generate a unique call ID
        call_id = str(uuid.uuid4())

        # Create the session object
        session = CallSession(
            call_id=call_id,
            client_id=client_id,
            user_name=user_name,
            phone_number=phone_number,
        )

        # Store in memory
        self.sessions[session.call_id] = session
        return session

    def get(self, call_id: str) -> CallSession:
        """Retrieve a CallSession by its call_id."""
        return self.sessions.get(call_id)

    def clear(self, call_id: str):
        """Remove a session from memory."""
        if call_id in self.sessions:
            del self.sessions[call_id]
