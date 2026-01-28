from backend.models.call_session import CallSession


class CallReport:
    def __init__(self, call_session: CallSession):
        self.report_id = call_session.call_id
        self.call_id = call_session.call_id
        self.client_id = call_session.client_id
        self.start_time = call_session.start_time
        self.end_time = call_session.end_time
        self.status = call_session.status
        self.messages = call_session.messages
        self.final_decision = None
        self.average_confidence = None
        self.summary_text = None

    def generateSummary(self):
        duration = (self.end_time - self.start_time).seconds

        summary = (
            f"Appel {self.call_id} d'une durée de {duration} secondes. "
            f"Le client a formulé {len(self.messages)} messages. "
            f"La décision finale du système est : {self.final_decision}. "
            f"Le score moyen de confiance est de {round(self.average_confidence, 2)}."
        )

        if self.final_decision == "AGENT":
            summary += " L'appel a été transféré à un agent humain."

        self.summary_text = summary
        return summary
