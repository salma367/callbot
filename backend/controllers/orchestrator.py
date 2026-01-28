# backend/controllers/orchestrator.py

from backend.services.confidence_manager import ConfidenceManager
from backend.services.escalation_policy import EscalationPolicy
from backend.logs.logger import Logger
from backend.models.agent import Agent
from backend.controllers.ActionType import ActionType

confidence_manager = ConfidenceManager()
escalation_policy = EscalationPolicy()
logger = Logger()


class Orchestrator:
    """Central decision-maker for conversational turns."""

    def on_call_started(self, call_session):
        """Log the start of a new call session."""
        logger.log_session(
            call_session.call_id, getattr(call_session, "caller_type", "UNKNOWN")
        )
        print(f"[ORCHESTRATOR] Call started: {call_session.call_id}")

    def process_turn(
        self,
        call_session,
        intent,
        asr_conf: float,
        nlu_conf: float,
        ambiguous: bool = False,
    ):
        """Process a single turn of the conversation with detailed debugging."""

        # 1️⃣ Compute global confidence
        global_confidence = confidence_manager.compute_global_confidence(
            asr_confidence=asr_conf, nlu_confidence=nlu_conf, ambiguous=ambiguous
        )
        call_session.global_confidence = global_confidence
        print(f"[DEBUG ORCH] Global confidence: {global_confidence}")

        logger.log_confidence(
            session_id=call_session.call_id,
            asr=asr_conf,
            nlu=nlu_conf,
            global_score=global_confidence,
        )

        # 2️⃣ Determine intent name
        intent_name = intent.name if intent else "UNKNOWN"
        call_session.current_intent = intent_name
        print(
            f"[DEBUG ORCH] Detected intent: {intent_name} | ASR: {asr_conf}, NLU: {nlu_conf}"
        )

        # 3️⃣ Decide if escalation is needed
        user_text = call_session.messages[-1] if call_session.messages else ""
        escalate, reason = escalation_policy.should_escalate(
            global_confidence=global_confidence,
            intent_name=intent_name,
            ambiguity_count=call_session.clarification_count,
            user_text=user_text,
        )
        print(
            f"[DEBUG ORCH] Escalation check -> escalate: {escalate}, reason: {reason}"
        )

        logger.log_decision(
            session_id=call_session.call_id,
            decision="ESCALATE" if escalate else "AUTO",
            reason=reason,
        )

        # 4️⃣ Handle escalation
        if escalate:
            agent = Agent(agent_id="A1", name="Sara", department="Claims")
            call_session.status = "ESCALATED"
            call_session.agent_id = agent.agent_id
            call_session.add_message(f"Call escalated to agent {agent.name}.")

            print(f"[DEBUG ORCH] Action: AGENT | Escalated to {agent.name}")
            return {
                "decision": ActionType.AGENT.value,
                "agent": {
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name,
                    "department": agent.department,
                },
                "reason": reason,
                "call_id": call_session.call_id,
                "escalated_message": f"You have been escalated to agent {agent.name}.",
            }

        # 5️⃣ Handle clarification (moderate confidence)
        if 0.4 <= global_confidence < 0.7:
            call_session.clarification_count += 1
            clarification = "Pouvez-vous préciser votre demande ?"
            call_session.add_message(clarification)
            print(
                f"[DEBUG ORCH] Action: CLARIFICATION | Count: {call_session.clarification_count}"
            )
            return {
                "decision": ActionType.CLARIFICATION.value,
                "message": clarification,
                "clarification_count": call_session.clarification_count,
            }

        # 6️⃣ Otherwise auto-handle
        response_text = f"Réponse automatique pour l’intent : {intent_name}"
        call_session.add_message(response_text)
        print(f"[DEBUG ORCH] Action: AUTO | Response: {response_text}")
        return {
            "decision": ActionType.AUTO.value,
            "response": response_text,
            "confidence": global_confidence,
        }

    @staticmethod
    def serialize_call_session(call_session):
        """Return a dict representation of the call session."""
        return {
            "call_id": call_session.call_id,
            "client_id": getattr(call_session, "client_id", None),
            "status": call_session.status,
            "current_intent": getattr(call_session, "current_intent", None),
            "clarification_count": getattr(call_session, "clarification_count", 0),
            "messages": getattr(call_session, "messages", []),
            "global_confidence": getattr(call_session, "global_confidence", None),
        }
