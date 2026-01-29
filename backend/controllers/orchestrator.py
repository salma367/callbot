from backend.services.confidence_manager import ConfidenceManager
from backend.services.escalation_policy import EscalationPolicy
from backend.controllers.ActionType import ActionType
from backend.models.agent import Agent
from backend.logs.logger import Logger
from functools import lru_cache
import re

logger = Logger()
confidence_manager = ConfidenceManager()
escalation_policy = EscalationPolicy(
    confidence_limit=0.3,
    use_ai_validation=True,  # Enable AI validation from improved escalation policy
)

SENSITIVE_INTENTS = ["CLAIM", "LEGAL_ISSUE", "CONTRACT_CANCELLATION"]


class Orchestrator:
    """AI-first orchestrator: prioritizes AI handling, escalates only if necessary."""

    MAX_CLARIFICATIONS = 2

    # Explicit agent request patterns (faster than AI check)
    AGENT_REQUEST_PATTERNS = [
        r"\b(je veux|je souhaite|passez[-\s]?moi)\s+(un\s+)?(agent|humain|représentant)",
        r"\b(parler|discuter)\s+(à|avec)\s+(un\s+)?(agent|humain|représentant)",
        r"\btransférez[-\s]?moi\b",
        r"\bun\s+(vrai\s+)?(agent|humain)\b",
    ]

    def __init__(self, llm_service=None):
        if llm_service is None:
            raise ValueError("LLMService instance must be provided")
        self.llm_service = llm_service
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.AGENT_REQUEST_PATTERNS
        ]

    def _is_explicit_agent_request(self, text: str) -> bool:
        """Fast pattern-based agent request detection."""
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                return True
        return False

    def on_call_started(self, call_session):
        """Log the start of a call session."""
        logger.log_session(
            call_session.call_id, getattr(call_session, "caller_type", "UNKNOWN")
        )
        print(f"[ORCH] Call started: {call_session.call_id}")

    def process_turn(self, call_session, intent, asr_conf, nlu_conf, ambiguous=False):
        """Process a single user turn with AI-first logic."""

        # Get user text safely
        if not call_session.messages:
            print("[ORCH] No messages in session")
            return self._create_clarification_response(call_session, 0.0, "NO_INPUT")

        user_text = call_session.messages[-1]
        user_lower = user_text.lower().strip()

        # ═══════════════════════════════════════════════════════════
        # TIER 1: EXPLICIT AGENT REQUEST (fast pattern matching)
        # ═══════════════════════════════════════════════════════════
        if self._is_explicit_agent_request(user_lower):
            return self._escalate_to_agent(call_session, "USER_REQUEST_AGENT")

        # ═══════════════════════════════════════════════════════════
        # TIER 2: COMPUTE CONFIDENCE
        # ═══════════════════════════════════════════════════════════
        global_conf = confidence_manager.compute_global_confidence(
            asr_confidence=asr_conf,
            nlu_confidence=nlu_conf,
            ambiguous=ambiguous,
        )
        call_session.global_confidence = global_conf

        intent_name = intent.name if intent else "UNKNOWN"
        call_session.current_intent = intent_name

        print(f"[ORCH] Intent={intent_name}, GlobalConf={global_conf:.2f}")

        # ═══════════════════════════════════════════════════════════
        # TIER 3: GOODBYE HANDLING
        # ═══════════════════════════════════════════════════════════
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

        # ═══════════════════════════════════════════════════════════
        # TIER 4: ESCALATION POLICY (with AI validation)
        # ═══════════════════════════════════════════════════════════
        decision, reason = escalation_policy.should_escalate(
            global_confidence=global_conf,
            intent_name=intent_name,
            ambiguity_count=call_session.clarification_count,
            user_text=user_text,
        )

        if decision == "ESCALATE":
            return self._escalate_to_agent(call_session, reason)

        if decision == "ASK_CLARIFICATION":
            return self._create_clarification_response(
                call_session, global_conf, reason
            )

        # ═══════════════════════════════════════════════════════════
        # TIER 5: AI HANDLES (generate response)
        # ═══════════════════════════════════════════════════════════
        return self._generate_ai_response(
            call_session, user_text, intent_name, global_conf, reason
        )

    def _escalate_to_agent(self, call_session, reason: str) -> dict:
        """Helper to escalate call to human agent."""
        agent = Agent(agent_id="A1", name="Sara", department="Claims")
        call_session.status = "ESCALATED"
        call_session.agent_id = agent.agent_id
        call_session.add_message(f"Call escalated to agent {agent.name}.")
        print(f"[ORCH] Action: AGENT | Escalated to {agent.name} | Reason: {reason}")

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

    def _create_clarification_response(
        self, call_session, global_conf: float, reason: str
    ) -> dict:
        """Helper to create clarification response."""
        call_session.clarification_count += 1
        clarification_prompt = (
            "Je n'ai pas bien compris. Pourriez-vous préciser votre demande ?"
        )
        call_session.add_message(clarification_prompt)

        print(
            f"[ORCH] Action: ASK_CLARIFICATION | Count={call_session.clarification_count} | Reason: {reason}"
        )

        return {
            "decision": ActionType.LLM.value,
            "message": clarification_prompt,
            "confidence": global_conf,
            "clarification_count": call_session.clarification_count,
            "reason": reason,
        }

    def _generate_ai_response(
        self,
        call_session,
        user_text: str,
        intent_name: str,
        global_conf: float,
        reason: str,
    ) -> dict:
        """Helper to generate AI response."""
        # Build context from recent messages (last 5 turns)
        context_text = " ".join(call_session.messages[-5:])

        try:
            llm_response = self.llm_service.generate_response(
                user_text=user_text,
                context=context_text,
                language="fr",
                intent=intent_name,
            )
        except Exception as e:
            print(f"[ORCH] LLM error: {e}")
            llm_response = (
                "Je suis désolé, je rencontre un problème. Un instant s'il vous plaît."
            )

        call_session.add_message(llm_response)
        print(f"[ORCH] Action: LLM_RESPONSE | Confidence: {global_conf:.2f}")

        return {
            "decision": ActionType.LLM.value,
            "message": llm_response,
            "confidence": global_conf,
            "clarification_count": call_session.clarification_count,
            "reason": reason,
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
