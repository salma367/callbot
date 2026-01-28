from enum import Enum


class ActionType(str, Enum):
    LLM = "LLM"
    CLARIFICATION = "CLARIFICATION"
    AGENT = "AGENT"
