from backend.models.call_session import CallSession
from datetime import datetime


class CallReport:
    def __init__(self, call_session: CallSession):
        self.report_id = call_session.call_id
        self.call_id = call_session.call_id
        self.client_id = call_session.client_id
        self.start_time = call_session.start_time
        self.end_time = call_session.end_time or datetime.now()
        self.status = call_session.status
        self.messages = call_session.messages
        self.confidence_timeline = call_session.confidence_timeline
        self.final_decision = call_session.final_decision
        self.average_confidence = call_session.get_average_confidence()
        self.summary_text = None
        self.escalation_reason = getattr(call_session, "escalation_reason", None)

    def generate_summary(self) -> str:
        duration = (self.end_time - self.start_time).seconds

        summary = (
            f"Appel {self.call_id} d'une durée de {duration} secondes.\n"
            f"Client: {self.client_id}\n"
            f"Nombre de messages: {len(self.messages)}\n"
            f"Décision finale: {self.final_decision}\n"
            f"Score moyen de confiance: {round(self.average_confidence, 2)}"
        )

        if self.final_decision == "AGENT" or self.escalation_reason:
            summary += f"\nRaison de l'escalade: {self.escalation_reason or 'AGENT'}"
            summary += "\nL'appel a été transféré à un agent humain."

        self.summary_text = summary
        return summary

    def store_report(self):
        """Save report as a text file."""
        if not self.summary_text:
            self.generate_summary()
        file_path = f"backend/logs/data/report_{self.call_id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.summary_text)
        return file_path
