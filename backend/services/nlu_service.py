from backend.models.intent import Intent


class NLUService:
    def detect_intent(self, text: str) -> Intent:
        t = text.lower()

        if any(w in t for w in ["hello", "hi", "hey", "bonjour", "salut"]):
            return Intent(name="GREETING")

        if any(
            w in t for w in ["problem", "issue", "lost", "stolen", "help", "broken"]
        ):
            return Intent(name="PROBLEM")

        if any(w in t for w in ["bye", "goodbye", "thanks", "thank you"]):
            return Intent(name="GOODBYE")

        return Intent(name="UNKNOWN")
