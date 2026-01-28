# backend/services/escalation_policy.py


class EscalationPolicy:
    """
    Determines if a call should be escalated to a human agent.
    Considers:
      - Low confidence
      - Sensitive intent
      - Too many clarifications
    """

    def __init__(
        self,
        confidence_limit: float = 0.6,
        sensitive_intents: list[str] = None,
        max_ambiguity: int = 0,
    ):
        self.confidence_limit = confidence_limit
        self.sensitive_intents = sensitive_intents or [
            "CLAIM",
            "CONTRACT_CANCELLATION",
            "COMPLAINT",
            "LEGAL_ISSUE",
            "PRIVATE_INQUIRY",
            "PERSONAL_DATA",
        ]
        self.max_ambiguity = max_ambiguity

    def should_escalate(
        self,
        global_confidence: float,
        intent_name: str,
        ambiguity_count: int = 0,
        user_text: str = "",
    ) -> tuple[bool, str]:
        """
        Returns:
            (True/False, reason)
        """

        # 1️⃣ Escalate if confidence too low
        if global_confidence < self.confidence_limit:
            return True, "LOW_CONFIDENCE"

        # 2️⃣ Escalate for sensitive intents
        if intent_name.upper() in self.sensitive_intents:
            return True, "SENSITIVE_INTENT"

        # 3️⃣ Escalate if too many clarifications
        if ambiguity_count >= self.max_ambiguity:
            return True, "REPEATED_AMBIGUITY"

        # 4️⃣ Optional: check raw user text for sensitive keywords
        sensitive_keywords = [
            "assassinat",
            "tué",
            "meurtre",
            "menace",
            "danger",
            "criminel",
            "privé",
            "données personnelles",
        ]
        lower_text = user_text.lower()
        if any(word in lower_text for word in sensitive_keywords):
            return True, "SENSITIVE_TEXT"

        # Otherwise, handle automatically
        return False, "AUTO_HANDLED"
