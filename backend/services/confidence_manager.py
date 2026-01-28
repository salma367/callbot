# backend/services/confidence_manager.py


class ConfidenceManager:
    def __init__(
        self,
        asr_weight=0.4,
        nlu_weight=0.6,
        ambiguity_penalty=0.15,
        low_conf_threshold=0.4,
    ):
        self.asr_weight = asr_weight
        self.nlu_weight = nlu_weight
        self.ambiguity_penalty = ambiguity_penalty
        self.low_conf_threshold = low_conf_threshold
        self.history = []

    def compute(
        self,
        session,
        asr_confidence: float,
        nlu_confidence: float,
        ambiguous: bool = False,
    ) -> dict:
        """Compute weighted global confidence and log to session."""
        score = asr_confidence * self.asr_weight + nlu_confidence * self.nlu_weight

        if ambiguous:
            score -= self.ambiguity_penalty

        score = round(max(0.0, min(score, 1.0)), 2)

        record = {
            "session_id": getattr(session, "call_id", session),
            "asr": asr_confidence,
            "nlu": nlu_confidence,
            "ambiguous": ambiguous,
            "global": score,
        }

        self.history.append(record)

        # if session object has update method, log there too
        if hasattr(session, "update_confidence"):
            session.update_confidence(score)

        return record

    def compute_global_confidence(
        self, asr_confidence: float, nlu_confidence: float, ambiguous=False
    ) -> float:
        """Simple global confidence computation without session logging."""
        score = asr_confidence * self.asr_weight + nlu_confidence * self.nlu_weight
        if ambiguous:
            score -= self.ambiguity_penalty
        return round(max(0.0, min(score, 1.0)), 2)

    def is_confidence_low(self, global_conf: float) -> bool:
        return global_conf < self.low_conf_threshold

    def ambiguity_count(self) -> int:
        return sum(1 for h in self.history if h["ambiguous"])
