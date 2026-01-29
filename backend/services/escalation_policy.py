# backend/services/escalation_policy.py


class EscalationPolicy:

    def __init__(
        self,
        confidence_limit: float = 0.3,  # very low, rarely triggers immediate escalation
        sensitive_intents: list[str] = None,
        max_ambiguity: int = 3,
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
            "tué",
            "meurtre",
            "blessé",
            "sang",
            "brûler",
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

        text_lower = user_text.lower()

        if any(word in text_lower for word in self.sensitive_keywords):
            return "ESCALATE", "SENSITIVE_TEXT"

        if global_confidence < self.confidence_limit:
            if ambiguity_count >= self.max_ambiguity:
                return "ESCALATE", "REPEATED_AMBIGUITY"
            else:
                return "ASK_CLARIFICATION", "LOW_CONFIDENCE"

        if intent_name.upper() in self.sensitive_intents:
            if any(word in text_lower for word in self.sensitive_keywords):
                return "ESCALATE", "SENSITIVE_INTENT"

        return "AUTO_HANDLED", "AUTO_HANDLED"
