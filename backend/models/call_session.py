# backend/models/call_session.py
from datetime import datetime
import uuid


class CallSession:
    def __init__(
        self, call_id, client_id, user_name=None, phone_number=None, agent_id=None
    ):
        self.call_id = call_id or str(uuid.uuid4())
        self.client_id = client_id
        self.user_name = user_name or "UNKNOWN"
        self.phone_number = phone_number or "UNKNOWN"
        self.agent_id = agent_id
        self.messages = []
        self.status = "ONGOING"
        self.start_time = datetime.now()
        self.end_time = None
        self.clarification_count = 0
        self.current_intent = None
        self.global_confidence = None

    def add_message(self, msg: str):
        self.messages.append(msg)

    def end_call(self, status="RESOLVED"):
        self.status = status
        self.end_time = datetime.now()
