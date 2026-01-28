# backend/controllers/orchestrator.py

from backend.services.confidence_manager import ConfidenceManager
from backend.services.escalation_policy import EscalationPolicy
from backend.controllers.ActionType import ActionType
from backend.models.agent import Agent
from backend.logs.logger import Logger

logger = Logger()
confidence_manager = ConfidenceManager()
escalation_policy = EscalationPolicy(
    confidence_limit=0.3
)  # low threshold for rare escalation

SENSITIVE_INTENTS = ["CLAIM", "LEGAL_ISSUE", "CONTRACT_CANCELLATION"]


class Orchestrator:
    """AI-first orchestrator: prioritizes AI handling, escalates only if necessary."""

    MAX_CLARIFICATIONS = 2  # maximum AI clarification attempts before escalation

    def __init__(self, llm_service=None):
        if llm_service is None:
            raise ValueError("LLMService instance must be provided")
        self.llm_service = llm_service

    def on_call_started(self, call_session):
        """Log the start of a call session."""
        logger.log_session(
            call_session.call_id, getattr(call_session, "caller_type", "UNKNOWN")
        )
        print(f"[ORCH] Call started: {call_session.call_id}")

    def process_turn(self, call_session, intent, asr_conf, nlu_conf, ambiguous=False):
        """Process a single user turn with AI-first logic."""

        # Detect explicit agent request
        user_lower = call_session.messages[-1].lower()
        if any(kw in user_lower for kw in ["agent", "humain", "représentant"]):
            agent = Agent(agent_id="A1", name="Sara", department="Claims")
            call_session.status = "ESCALATED"
            call_session.agent_id = agent.agent_id
            call_session.add_message(f"Call escalated to agent {agent.name}.")
            return {
                "decision": ActionType.AGENT.value,
                "agent": {
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name,
                    "department": agent.department,
                },
                "reason": "USER_REQUEST_AGENT",
                "call_id": call_session.call_id,
                "escalated_message": f"You have been escalated to agent {agent.name}.",
            }
        # 1️⃣ Compute global confidence
        global_conf = confidence_manager.compute_global_confidence(
            asr_confidence=asr_conf,
            nlu_confidence=nlu_conf,
            ambiguous=ambiguous,
        )
        call_session.global_confidence = global_conf

        # 2️⃣ Set current intent
        intent_name = intent.name if intent else "UNKNOWN"
        call_session.current_intent = intent_name

        print(f"[ORCH] Intent={intent_name}, GlobalConf={global_conf}")

        # 🔚 Handle GOODBYE / explicit call end
        if intent_name == "GOODBYE":
            call_session.status = "ENDED"
            call_session.add_message("Call ended by user.")

            return {
                "decision": (
                    ActionType.END_CALL.value
                    if hasattr(ActionType, "END_CALL")
                    else ActionType.LLM.value
                ),
                "message": "Au revoir ! L'appel est terminé.",
                "reason": "USER_GOODBYE",
                "call_id": call_session.call_id,
            }

        # 3️⃣ Check escalation policy
        decision, reason = escalation_policy.should_escalate(
            global_confidence=global_conf,
            intent_name=intent_name,
            ambiguity_count=call_session.clarification_count,
            user_text=call_session.messages[-1] if call_session.messages else "",
        )

        # 4️⃣ Handle ESCALATE decision
        if decision == "ESCALATE":
            agent = Agent(agent_id="A1", name="Sara", department="Claims")
            call_session.status = "ESCALATED"
            call_session.agent_id = agent.agent_id
            call_session.add_message(f"Call escalated to agent {agent.name}.")
            print(f"[ORCH] Action: AGENT | Escalated to {agent.name}")

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

        # 5️⃣ Handle ASK_CLARIFICATION decision
        elif decision == "ASK_CLARIFICATION":
            call_session.clarification_count += 1
            clarification_prompt = (
                "Je n'ai pas bien compris. Pourriez-vous préciser votre demande ?"
            )
            call_session.add_message(clarification_prompt)
            print(
                f"[ORCH] Action: ASK_CLARIFICATION | Count={call_session.clarification_count}"
            )

            # backward compatible: treat as AUTO_HANDLED for layers expecting False/True
            return {
                "decision": ActionType.LLM.value,
                "message": clarification_prompt,
                "confidence": global_conf,
                "clarification_count": call_session.clarification_count,
                "reason": reason,
            }

        # 6️⃣ Handle auto-handled calls (AI response)
        context_text = " ".join(call_session.messages[-5:])
        llm_response = self.llm_service.generate_response(
            user_text=call_session.messages[-1],
            context=context_text,
            language="fr",
            intent=intent_name,
        )

        call_session.add_message(llm_response)
        print("[ORCH] Action: LLM_RESPONSE")

        return {
            "decision": ActionType.LLM.value,
            "message": llm_response,
            "confidence": global_conf,
            "clarification_count": call_session.clarification_count,
            "reason": reason,  # backward compatible
        }

    @staticmethod
    def serialize_call_session(call_session):
        """Return dict representation for logging or API."""
        return {
            "call_id": call_session.call_id,
            "client_id": getattr(call_session, "client_id", None),
            "status": call_session.status,
            "current_intent": getattr(call_session, "current_intent", None),
            "clarification_count": getattr(call_session, "clarification_count", 0),
            "messages": getattr(call_session, "messages", []),
            "global_confidence": getattr(call_session, "global_confidence", None),
        }
