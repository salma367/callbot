# backend/services/escalation_policy.py


class EscalationPolicy:
    """
    AI-first escalation policy:
    - Rarely escalates under normal circumstances.
    - Escalates immediately for critical emergencies (life/death, danger, legal).
    - Allows several clarifications or low-confidence turns before escalation.
    """

    def __init__(
        self,
        confidence_limit: float = 0.3,  # very low, rarely triggers immediate escalation
        sensitive_intents: list[str] = None,
        max_ambiguity: int = 5,  # allow several clarifications
    ):
        self.confidence_limit = confidence_limit
        self.max_ambiguity = max_ambiguity
        self.sensitive_intents = sensitive_intents or [
            "CLAIM",
            "LEGAL_ISSUE",
            "CONTRACT_CANCELLATION",
        ]

        self.sensitive_keywords = [
            # life-threatening
            "mort",
            "assassinat",
            "tué",
            "meurtre",
            "danger",
            "blessé",
            "sang",
            "incendie",
            "brûler",
            "feu",
            "explosion",
            "accident grave",
            "urgence",
            "risque vital",
            # crime / violence
            "violence",
            "attaque",
            "agression",
            "kidnapping",
            "vol",
            "braquage",
            "criminel",
            # health / safety
            "maladie grave",
            "infection",
            "empoisonnement",
            "choc",
            "fracture",
            "accident",
            # privacy / legal
            "privé",
            "confidentiel",
            "données personnelles",
            "secret",
            "litige",
            "avocat",
            # extreme cases
            "arme",
            "terrorisme",
            "attaque armée",
            "menace",
            "sûreté",
            "alarme",
        ]

    def should_escalate(
        self,
        global_confidence: float,
        intent_name: str,
        ambiguity_count: int = 0,
        user_text: str = "",
    ) -> tuple[str, str]:
        """
        Determines whether to escalate, ask clarification, or handle automatically.

        Returns:
            (decision, reason) where decision is one of:
                - "ESCALATE"        # escalate to human agent
                - "ASK_CLARIFICATION"  # ask user to clarify
                - "AUTO_HANDLED"    # AI can handle directly
        """
        text_lower = user_text.lower()

        # 1️⃣ Immediate escalation if emergency keywords appear
        if any(word in text_lower for word in self.sensitive_keywords):
            return "ESCALATE", "SENSITIVE_TEXT"

        # 2️⃣ Escalate if extremely low confidence after max clarifications
        if global_confidence < self.confidence_limit:
            if ambiguity_count >= self.max_ambiguity:
                return "ESCALATE", "REPEATED_AMBIGUITY"
            else:
                return "ASK_CLARIFICATION", "LOW_CONFIDENCE"

        # 3️⃣ Escalate for sensitive intents with relevant keywords
        if intent_name.upper() in self.sensitive_intents:
            if any(word in text_lower for word in self.sensitive_keywords):
                return "ESCALATE", "SENSITIVE_INTENT"

        # 4️⃣ Default: AI handles automatically
        return "AUTO_HANDLED", "AUTO_HANDLED"
