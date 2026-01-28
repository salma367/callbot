class Intent:
    def __init__(self, name, entities=None, confidence=None):
        self.name = name
        self.entities = entities or []
        self.confidence = confidence
