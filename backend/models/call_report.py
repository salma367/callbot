from datetime import datetime
from backend.services.llm_service import LLMService

llmservice = LLMService()


def generate_llm_summary(llm_service, call_session):
    """Helper to generate a professional summary via LLM."""
    transcript = "\n".join(call_session.messages)

    prompt = f"""
Tu es un système de reporting.

Résume l’appel suivant de manière professionnelle et concise.
Inclure :
- Le problème du client
- Pourquoi l’appel s’est terminé (résolu ou escaladé)
- Toute information importante fournie par le client

Conversation :
{transcript}
"""

    return llm_service.generate_response(
        user_text=prompt,
        context="",
        language="fr",
        intent="CALL_SUMMARY",
    )


class CallReport:
    def __init__(self, call_session):
        self.call_id = call_session.call_id
        self.client_id = call_session.client_id
        self.agent_name = getattr(call_session, "agent_name", "Unknown")
        self.status = call_session.status
        self.start_time = call_session.start_time
        self.end_time = getattr(call_session, "end_time", datetime.now())
        self.messages = call_session.messages
        self.summary_text = None

    def generate_summary(self, llm_service=None):
        if llm_service:
            self.summary_text = generate_llm_summary(llm_service, self)
        else:
            # fallback simple summary
            duration = (self.end_time - self.start_time).seconds
            self.summary_text = (
                f"Call {self.call_id} lasted {duration}s. "
                f"{len(self.messages)} messages. Final status: {self.status}."
            )
        return self.summary_text
