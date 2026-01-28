import uuid
from datetime import datetime


class CallSession:
    def __init__(self, client_id=None):
        self.call_id = str(uuid.uuid4())
        self.client_id = client_id

        self.start_time = datetime.now()
        self.end_time = None

        self.messages = []

        # 🔹 IA / Decision
        self.current_intent = None
        self.global_confidence = None
        self.confidence_timeline = []
        self.clarification_count = 0

        # 🔹 Escalation
        self.escalated = False
        self.escalation_reason = None

        self.final_decision = None
        self.average_confidence = 0.0

        # 🔹 Agent
        self.agent_id = None

        self.status = "ACTIVE"

    def start(self):
        self.start_time = datetime.now()
        self.status = "Started"

    # ====== MESSAGES ======
    def add_message(self, text):
        self.messages.append(text)

    # ====== CONFIDENCE ======
    def update_confidence(self, score):
        self.global_confidence = score
        self.confidence_timeline.append({"time": datetime.now(), "score": score})

    # ====== INTENT ======
    def update_intent(self, intent_name):
        self.current_intent = intent_name

    # ====== ESCALATION ======
    def escalate(self, reason):
        self.escalated = True
        self.escalation_reason = reason

    # ====== END CALL ======
    def end(self):
        self.status = "ENDED"
        self.end_time = datetime.now()

    def get_average_confidence(self) -> float:
        if not self.confidence_timeline:
            return 0.0
        return sum(c["score"] for c in self.confidence_timeline) / len(
            self.confidence_timeline
        )
